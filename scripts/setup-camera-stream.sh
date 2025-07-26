#!/bin/bash

# Setup script specifically for camera streaming features
# Use this if you already have the base ImageFlowCanvas setup and want to add camera streaming

set -e

echo "📹 Setting up camera streaming features for ImageFlowCanvas..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if K3s is running
check_k3s() {
    if ! command_exists kubectl; then
        echo "❌ kubectl not found. Please run the main setup first."
        exit 1
    fi
    
    if ! kubectl get nodes >/dev/null 2>&1; then
        echo "❌ K3s cluster not accessible. Please run the main setup first."
        exit 1
    fi
    
    echo "✅ K3s cluster is accessible"
}

# Function to check existing services
check_existing_services() {
    echo "🔍 Checking existing services..."
    
    # Check if gRPC services are running
    if ! kubectl get deployment grpc-gateway -n image-processing >/dev/null 2>&1; then
        echo "❌ gRPC services not found. Please run the main setup first."
        exit 1
    fi
    
    echo "✅ Existing gRPC services found"
}

# Function to generate camera stream Protocol Buffers
generate_camera_protos() {
    echo "📋 Generating camera stream Protocol Buffers..."
    
    # Check if camera_stream.proto exists
    if [ ! -f "proto/imageflow/v1/camera_stream.proto" ]; then
        echo "❌ camera_stream.proto not found. This should have been created in previous commits."
        exit 1
    fi
    
    # Regenerate all protos to include camera stream
    ./scripts/generate_protos.sh
    echo "✅ Protocol Buffers updated with camera stream definitions"
}

# Function to build camera stream service
build_camera_stream_service() {
    echo "🏗️  Building camera stream gRPC service..."
    
    # Check if camera-stream-grpc-app exists
    if [ ! -d "services/camera-stream-grpc-app" ]; then
        echo "❌ Camera stream service directory not found."
        exit 1
    fi
    
    # Build just the camera stream service
    echo "Building camera-stream-grpc service..."
    
    BASE_DIR="$(pwd)"
    REGISTRY="imageflow"
    TAG="local"
    
    # Copy generated protobuf files to service directory
    if [ -d "$BASE_DIR/generated/python" ]; then
        mkdir -p "services/camera-stream-grpc-app/generated"
        cp -r "$BASE_DIR/generated/python" "services/camera-stream-grpc-app/generated/"
        echo "✓ Copied protobuf files to camera-stream service"
    fi
    
    # Build Docker image
    docker build -t "$REGISTRY/camera-stream-grpc:$TAG" "services/camera-stream-grpc-app"
    echo "✓ Built $REGISTRY/camera-stream-grpc:$TAG"
    
    # Clean up copied files
    if [ -d "services/camera-stream-grpc-app/generated" ]; then
        rm -rf "services/camera-stream-grpc-app/generated"
        echo "✓ Cleaned up temporary files"
    fi
    
    # Import to K3s
    docker save "$REGISTRY/camera-stream-grpc:$TAG" | sudo k3s ctr images import -
    echo "✅ Camera stream service built and imported to K3s"
}

# Function to deploy camera stream service
deploy_camera_stream() {
    echo "🚀 Deploying camera stream service..."
    
    # Apply camera stream service configuration
    kubectl apply -f k8s/grpc/grpc-services.yaml
    
    # Wait for deployment to be ready
    echo "Waiting for camera stream service to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/camera-stream-grpc-service -n image-processing
    
    echo "✅ Camera stream service deployed successfully"
}

# Function to update backend with camera stream features
update_backend() {
    echo "🔄 Updating backend with camera stream features..."
    
    # Check if camera_stream.py exists in backend
    if [ ! -f "backend/app/api/camera_stream.py" ]; then
        echo "❌ Backend camera stream API not found."
        exit 1
    fi
    
    # Rebuild and redeploy backend
    echo "Rebuilding backend with camera stream support..."
    docker build -t imageflow/backend:local ./backend
    docker save imageflow/backend:local | sudo k3s ctr images import -
    
    # Restart backend deployment
    kubectl rollout restart deployment/backend -n default
    kubectl wait --for=condition=available --timeout=300s deployment/backend -n default
    
    echo "✅ Backend updated with camera stream features"
}

# Function to update frontend with camera streaming UI
update_frontend() {
    echo "🎨 Updating frontend with camera streaming UI..."
    
    # Check if CameraStream.tsx exists
    if [ ! -f "frontend/src/pages/CameraStream.tsx" ]; then
        echo "❌ Frontend camera stream component not found."
        exit 1
    fi
    
    # Rebuild and redeploy frontend
    echo "Rebuilding frontend with camera streaming UI..."
    docker build -t imageflow/frontend:local ./frontend
    docker save imageflow/frontend:local | sudo k3s ctr images import -
    
    # Restart frontend deployment
    kubectl rollout restart deployment/frontend -n default
    kubectl wait --for=condition=available --timeout=300s deployment/frontend -n default
    
    echo "✅ Frontend updated with camera streaming UI"
}

# Function to validate camera stream setup
validate_camera_stream() {
    echo "🔍 Validating camera stream setup..."
    
    # Test gRPC Gateway health
    echo "Testing gRPC Gateway..."
    if kubectl exec -n image-processing deploy/grpc-gateway -- curl -s http://localhost:8080/health >/dev/null; then
        echo "✅ gRPC Gateway is healthy"
    else
        echo "⚠️  gRPC Gateway health check failed"
    fi
    
    # Test camera stream service
    echo "Testing camera stream service..."
    if kubectl get pod -n image-processing -l app=camera-stream-grpc-service --field-selector=status.phase=Running | grep -q camera-stream; then
        echo "✅ Camera stream service is running"
    else
        echo "❌ Camera stream service is not running"
        kubectl logs -n image-processing -l app=camera-stream-grpc-service --tail=20
    fi
    
    # Test backend camera stream API
    echo "Testing backend camera stream API..."
    if kubectl exec deploy/backend -- curl -s http://localhost:8000/api/camera-stream/v1/camera-stream/health >/dev/null 2>&1; then
        echo "✅ Backend camera stream API is available"
    else
        echo "⚠️  Backend camera stream API test inconclusive"
    fi
    
    echo "✅ Camera stream validation completed"
}

# Function to show usage instructions
show_usage() {
    echo ""
    echo "🎉 Camera streaming setup completed!"
    echo ""
    echo "New features available:"
    echo "✅ Real-time camera streaming with gRPC"
    echo "✅ WebSocket endpoints for live video processing"
    echo "✅ PC camera integration in Web UI"
    echo "✅ Pipeline selection for real-time processing"
    echo ""
    echo "How to use:"
    echo "1. Run './scripts/port-forward.sh' if not already running"
    echo "2. Open http://localhost:3000 in your browser"
    echo "3. Navigate to the 'リアルタイム処理' tab"
    echo "4. Allow camera access when prompted"
    echo "5. Select a pipeline created in the Web UI"
    echo "6. Click 'ストリーミング開始' to start real-time processing"
    echo ""
    echo "API endpoints:"
    echo "- WebSocket: ws://localhost:8000/v1/ws/camera-stream/{camera_id}"
    echo "- HTTP test: http://localhost:8000/api/camera-stream/v1/camera-stream/test"
    echo "- Pipelines list: http://localhost:8000/api/camera-stream/v1/camera-stream/pipelines"
}

# Main execution
main() {
    echo "🎯 Setting up camera streaming features..."
    echo "This adds real-time camera processing to your existing ImageFlowCanvas installation"
    echo ""
    
    # Step 1: Check prerequisites
    check_k3s
    check_existing_services
    
    # Step 2: Generate Protocol Buffers
    generate_camera_protos
    
    # Step 3: Build camera stream service
    build_camera_stream_service
    
    # Step 4: Deploy camera stream service
    deploy_camera_stream
    
    # Step 5: Update backend
    update_backend
    
    # Step 6: Update frontend
    update_frontend
    
    # Step 7: Validate setup
    validate_camera_stream
    
    # Step 8: Show usage instructions
    show_usage
}

# Check if this is being called as a subcommand of the main setup
if [ "$1" = "--subcommand" ]; then
    echo "📹 Adding camera streaming to existing setup..."
    generate_camera_protos
    build_camera_stream_service
    deploy_camera_stream
    echo "✅ Camera streaming features added"
else
    # Run as standalone script
    main "$@"
fi