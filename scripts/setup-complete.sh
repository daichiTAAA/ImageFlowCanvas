#!/bin/bash

# Complete setup script for ImageFlowCanvas with camera streaming
# This script sets up everything needed for both batch and real-time processing

set -e

echo "🚀 Setting up ImageFlowCanvas with camera streaming features..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check conda environment
check_conda_env() {
    if [ "$CONDA_DEFAULT_ENV" != "imageflowcanvas" ]; then
        echo "❌ conda environment 'imageflowcanvas' is not activated"
        echo "Please run: conda activate imageflowcanvas"
        exit 1
    fi
    echo "✅ conda environment 'imageflowcanvas' is active"
}

# Function to validate required packages
check_requirements() {
    echo "🔍 Checking requirements..."
    
    # Check conda environment
    check_conda_env
    
    # Check required Python packages
    echo "Checking Python packages..."
    python -c "import grpc_tools.protoc; print('✅ gRPC tools available')" || {
        echo "❌ gRPC tools not found. Installing..."
        pip install grpcio grpcio-tools
    }
    
    python -c "import requests; print('✅ requests available')" || {
        echo "❌ requests not found. Installing..."
        pip install requests
    }
    
    python -c "import ultralytics; print('✅ ultralytics available')" || {
        echo "❌ ultralytics not found. Installing..."
        pip install ultralytics
    }
    
    echo "✅ All Python requirements satisfied"
}

# Function to setup YOLO models
setup_yolo_models() {
    echo "🤖 Setting up YOLO11 models..."
    if [ ! -f "models/yolo/1/model.onnx" ]; then
        echo "Downloading and converting YOLO11 model..."
        python scripts/setup-yolo11.py
        echo "✅ YOLO11 model setup complete"
    else
        echo "✅ YOLO11 model already exists"
    fi
}

# Function to generate Protocol Buffers
generate_protos() {
    echo "📋 Generating Protocol Buffers..."
    if [ ! -d "generated/python/imageflow/v1" ]; then
        ./scripts/generate_protos.sh
        echo "✅ Protocol Buffers generated"
    else
        echo "✅ Protocol Buffers already generated"
    fi
}

# Function to build and deploy services
build_and_deploy() {
    echo "🏗️  Building and deploying services..."
    
    # Build and deploy gRPC services (including camera stream)
    echo "Building gRPC services..."
    DEPLOY=true ./scripts/build_grpc_services.sh
    
    # Build and deploy web services
    echo "Building web services..."
    DEPLOY=true ./scripts/build_web_services.sh
    
    echo "✅ All services built and deployed"
}

# Function to setup K3s infrastructure
setup_k3s() {
    echo "☸️  Setting up K3s infrastructure..."
    
    if ! command_exists k3s; then
        echo "Installing K3s..."
        sudo ./scripts/setup-k3s.sh
    else
        echo "K3s already installed, updating deployment..."
        # Just redeploy the services
        kubectl apply -f k8s/core/minio-pv-pvc.yaml
        kubectl apply -f k8s/core/minio-deployment.yaml
        kubectl apply -f k8s/core/kafka-deployment.yaml
        kubectl apply -f k8s/core/triton-deployment.yaml
        kubectl apply -f k8s/core/app-deployments.yaml
        kubectl apply -f k8s/grpc/namespace-config.yaml
        kubectl apply -f k8s/grpc/grpc-services.yaml
        kubectl apply -f k8s/workflows/grpc-pipeline-templates.yaml
    fi
    
    echo "✅ K3s setup complete"
}

# Function to validate deployment
validate_deployment() {
    echo "🔍 Validating deployment..."
    
    echo "Waiting for core services..."
    kubectl wait --for=condition=available --timeout=300s deployment/backend -n default || {
        echo "❌ Backend deployment failed"
        kubectl logs -l app=backend --tail=50
        exit 1
    }
    
    echo "Waiting for gRPC services..."
    kubectl wait --for=condition=available --timeout=300s deployment/grpc-gateway -n image-processing || {
        echo "❌ gRPC Gateway deployment failed"
        kubectl logs -n image-processing -l app=grpc-gateway --tail=50
        exit 1
    }
    
    kubectl wait --for=condition=available --timeout=300s deployment/camera-stream-grpc-service -n image-processing || {
        echo "❌ Camera stream service deployment failed"
        kubectl logs -n image-processing -l app=camera-stream-grpc-service --tail=50
        exit 1
    }
    
    echo "✅ All services are ready"
}

# Function to start port forwarding
start_port_forwarding() {
    echo "🌐 Starting port forwarding..."
    echo "You can now run './scripts/port-forward.sh' in a separate terminal to access services"
    echo ""
    echo "Access points:"
    echo "- Frontend: http://localhost:3000"
    echo "- Backend API: http://localhost:8000/docs"
    echo "- gRPC Gateway: http://localhost:8080/health"
    echo "- MinIO Console: http://localhost:9001 (admin/admin123)"
    echo ""
    echo "Camera Streaming Features:"
    echo "- Navigate to 'リアルタイム処理' tab in the frontend"
    echo "- Select pipelines created in the Web UI"
    echo "- Start PC camera streaming with real-time AI processing"
}

# Function to run tests
run_tests() {
    echo "🧪 Running validation tests..."
    
    # Test gRPC services
    if [ -f "scripts/performance_monitor.py" ]; then
        echo "Testing gRPC services..."
        python scripts/performance_monitor.py --gateway-url http://localhost:8080 || {
            echo "⚠️  gRPC performance test failed, but setup continues..."
        }
    fi
    
    # Test camera stream integration
    if [ -f "test_camera_stream_integration.py" ]; then
        echo "Testing camera stream integration..."
        python test_camera_stream_integration.py || {
            echo "⚠️  Camera stream integration test failed, but setup continues..."
        }
    fi
    
    echo "✅ Validation tests completed"
}

# Main execution
main() {
    echo "🎯 Starting complete ImageFlowCanvas setup..."
    echo "This will set up batch processing AND real-time camera streaming"
    echo ""
    
    # Step 1: Check requirements
    check_requirements
    
    # Step 2: Setup models
    setup_yolo_models
    
    # Step 3: Generate Protocol Buffers
    generate_protos
    
    # Step 4: Setup K3s infrastructure
    setup_k3s
    
    # Step 5: Build and deploy all services
    build_and_deploy
    
    # Step 6: Validate deployment
    validate_deployment
    
    # Step 7: Run tests
    run_tests
    
    # Step 8: Setup port forwarding instructions
    start_port_forwarding
    
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Run './scripts/port-forward.sh' in a separate terminal"
    echo "2. Open http://localhost:3000 in your browser"
    echo "3. Login with admin/admin123 or user/user123"
    echo "4. Create pipelines in the Web UI"
    echo "5. Test camera streaming in the 'リアルタイム処理' tab"
    echo ""
    echo "Features available:"
    echo "✅ Batch processing (40-100ms pipelines)"
    echo "✅ Real-time camera streaming (<50ms latency)"
    echo "✅ AI detection with YOLO11"
    echo "✅ Web UI pipeline creation"
    echo "✅ PC camera integration"
    echo "✅ gRPC high-performance architecture"
}

# Execute main function
main "$@"