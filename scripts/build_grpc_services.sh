#!/bin/bash

# Build and deployment script for ImageFlowCanvas gRPC services only
#
# Usage:
#   ./scripts/build_grpc_services.sh                    # Build only
#   DEPLOY=true ./scripts/build_grpc_services.sh        # Build and deploy
#   PUSH=true ./scripts/build_grpc_services.sh          # Build and push to registry
#
# Environment variables:
#   REGISTRY   - Docker registry prefix (default: imageflow)
#   TAG        - Docker image tag (default: local)
#   PUSH       - Push images to registry (default: false)
#   DEPLOY     - Deploy to Kubernetes (default: false)

set -e

REGISTRY=${REGISTRY:-"imageflow"}
TAG=${TAG:-"local"}
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
        mkdir -p "$context_dir/generated"
        cp -r "$BASE_DIR/generated/python" "$context_dir/generated/"
        echo "  ✓ Copied protobuf files to $service_name"
    fi
    
    # Build Docker image
    docker build -t "$REGISTRY/$service_name:$TAG" "$context_dir"
    echo "  ✓ Built $REGISTRY/$service_name:$TAG"
    
    # Clean up copied files
    if [ -d "$context_dir/generated" ]; then
        rm -rf "$context_dir/generated"
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
build_service "camera-stream-grpc" "$BASE_DIR/services/camera-stream-grpc-app"

echo "✅ All gRPC services built successfully!"

# Import images to K3s cluster if not in registry mode
if [ "$PUSH" != "true" ] || [ "$DEPLOY" != "true" ]; then
    echo "📥 Importing gRPC images to K3s cluster..."
    
    # Save images as tar files and import to K3s
    docker save "$REGISTRY/resize-grpc:$TAG" | sudo k3s ctr images import -
    docker save "$REGISTRY/ai-detection-grpc:$TAG" | sudo k3s ctr images import -
    docker save "$REGISTRY/filter-grpc:$TAG" | sudo k3s ctr images import -
    docker save "$REGISTRY/grpc-gateway:$TAG" | sudo k3s ctr images import -
    docker save "$REGISTRY/camera-stream-grpc:$TAG" | sudo k3s ctr images import -
    
    echo "✅ All gRPC images imported to K3s cluster!"
fi

# Push to registry if requested
if [ "$PUSH" = "true" ]; then
    echo "📤 Pushing gRPC images to registry..."
    docker push "$REGISTRY/resize-grpc:$TAG"
    docker push "$REGISTRY/ai-detection-grpc:$TAG"
    docker push "$REGISTRY/filter-grpc:$TAG"
    docker push "$REGISTRY/grpc-gateway:$TAG"
    docker push "$REGISTRY/camera-stream-grpc:$TAG"
    echo "✅ All gRPC images pushed to registry!"
fi

# Deploy to Kubernetes if requested
if [ "$DEPLOY" = "true" ]; then
    echo "🚀 Deploying gRPC services to Kubernetes..."

    echo "🏗️  Applying namespace configuration..."
    kubectl apply -f deploy/k3s/grpc/namespace-config.yaml

    echo "🔐 Applying RBAC configuration..."
    kubectl apply -f deploy/k3s/grpc/grpc-workflow-rbac.yaml
    kubectl apply -f deploy/k3s/grpc/grpc-workflow-token.yaml

    echo "🎯 Deploying gRPC services..."
    kubectl apply -f deploy/k3s/grpc/grpc-services.yaml

    echo "🔄 Restarting gRPC services to apply changes..."
    kubectl rollout restart -n image-processing deployment/resize-grpc-service
    kubectl rollout restart -n image-processing deployment/ai-detection-grpc-service
    kubectl rollout restart -n image-processing deployment/filter-grpc-service
    kubectl rollout restart -n image-processing deployment/grpc-gateway
    kubectl rollout restart -n image-processing deployment/camera-stream-grpc-service

    echo "✅ gRPC services deployment completed!"
fi

echo "🎉 gRPC services build completed successfully!"
echo ""
echo "Next steps:"
echo "1. For manual Kubernetes deployment:"
echo "   kubectl apply -f deploy/k3s/grpc/namespace-config.yaml"
echo "   kubectl apply -f deploy/k3s/grpc/grpc-workflow-rbac.yaml"
echo "   kubectl apply -f deploy/k3s/grpc/grpc-workflow-token.yaml"
echo "   kubectl apply -f deploy/k3s/grpc/grpc-services.yaml"
echo ""
echo "2. For automated deployment with rollout:"
echo "   DEPLOY=true ./scripts/build_grpc_services.sh"
echo ""
echo "3. Test the services:"
echo "   python3 scripts/performance_monitor.py --gateway-url http://localhost:8080"