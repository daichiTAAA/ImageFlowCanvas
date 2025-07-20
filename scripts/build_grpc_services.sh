#!/bin/bash

# Build and deployment script for ImageFlowCanvas gRPC services

set -e

REGISTRY=${REGISTRY:-"imageflow"}
TAG=${TAG:-"latest"}
BASE_DIR="/home/runner/work/ImageFlowCanvas/ImageFlowCanvas"

echo "🔧 Building ImageFlowCanvas gRPC Services"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Base Directory: $BASE_DIR"

# Function to build and tag Docker image
build_service() {
    local service_name=$1
    local context_dir=$2
    
    echo "📦 Building $service_name..."
    
    # Copy generated protobuf files to service directory
    if [ -d "$BASE_DIR/generated/python" ]; then
        cp -r "$BASE_DIR/generated/python" "$context_dir/"
        echo "  ✓ Copied protobuf files to $service_name"
    fi
    
    # Build Docker image
    docker build -t "$REGISTRY/$service_name:$TAG" "$context_dir"
    echo "  ✓ Built $REGISTRY/$service_name:$TAG"
    
    # Clean up copied files
    if [ -d "$context_dir/python" ]; then
        rm -rf "$context_dir/python"
        echo "  ✓ Cleaned up temporary files"
    fi
}

# Generate Protocol Buffers if not already done
if [ ! -d "$BASE_DIR/generated/python" ]; then
    echo "📋 Generating Protocol Buffers..."
    cd "$BASE_DIR"
    ./scripts/generate_protos.sh
    echo "  ✓ Protocol Buffers generated"
fi

# Build all gRPC services
echo "🚀 Building gRPC services..."

build_service "resize-grpc" "$BASE_DIR/services/resize-grpc-app"
build_service "ai-detection-grpc" "$BASE_DIR/services/ai-detection-grpc-app"
build_service "filter-grpc" "$BASE_DIR/services/filter-grpc-app"
build_service "grpc-gateway" "$BASE_DIR/services/grpc-gateway"

echo "✅ All services built successfully!"

# Optional: Push to registry if PUSH=true
if [ "$PUSH" = "true" ]; then
    echo "📤 Pushing images to registry..."
    docker push "$REGISTRY/resize-grpc:$TAG"
    docker push "$REGISTRY/ai-detection-grpc:$TAG"
    docker push "$REGISTRY/filter-grpc:$TAG"
    docker push "$REGISTRY/grpc-gateway:$TAG"
    echo "✅ All images pushed to registry!"
fi

echo "🎉 Build completed successfully!"
echo ""
echo "Next steps:"
echo "1. Apply Kubernetes configurations:"
echo "   kubectl apply -f k8s/grpc/namespace-config.yaml"
echo "   kubectl apply -f k8s/grpc/grpc-services.yaml"
echo ""
echo "2. Deploy Argo Workflow templates:"
echo "   kubectl apply -f k8s/workflows/grpc-pipeline-templates.yaml"
echo ""
echo "3. Test the pipeline:"
echo "   kubectl create -f k8s/workflows/grpc-pipeline-templates.yaml -o yaml --dry-run=client | kubectl apply -f -"