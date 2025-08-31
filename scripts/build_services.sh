#!/bin/bash

# Common build script for ImageFlowCanvas services across all environments
#
# Usage:
#   ./scripts/build_services.sh                    # Build all services
#   ./scripts/build_services.sh grpc              # Build only gRPC services  
#   ./scripts/build_services.sh web               # Build only web services
#
# Environment variables:
#   REGISTRY   - Docker registry prefix (default: imageflow)
#   TAG        - Docker image tag (default: local)

set -e

REGISTRY=${REGISTRY:-"imageflow"}
TAG=${TAG:-"local"}
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_TYPE=${1:-"all"}

echo "🔧 Building ImageFlowCanvas Services"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Build Type: $BUILD_TYPE"
echo "Base Directory: $BASE_DIR"

# Function to build and tag Docker image
build_service() {
    local service_name=$1
    local context_dir=$2
    
    echo "📦 Building $service_name..."
    
    # Copy generated protobuf files to service directory if needed
    if [ -d "$BASE_DIR/generated/python" ] && [[ "$service_name" == *"grpc"* || "$service_name" == "backend" ]]; then
        mkdir -p "$context_dir/generated"
        cp -r "$BASE_DIR/generated/python" "$context_dir/generated/"
        echo "  ✓ Copied protobuf files to $service_name"
    fi
    
    # Build Docker image
    # Backend and web use base directory context due to their relative paths in Dockerfile
    if [ "$service_name" == "backend" ] || [ "$service_name" == "web" ]; then
        docker build -t "$REGISTRY/$service_name:$TAG" "$BASE_DIR" -f "$context_dir/Dockerfile"
        echo "  ✓ Built $REGISTRY/$service_name:$TAG"
    elif [ -f "$context_dir/Dockerfile" ]; then
        docker build -t "$REGISTRY/$service_name:$TAG" "$context_dir"
        echo "  ✓ Built $REGISTRY/$service_name:$TAG"
    else
        # For services that use the base directory context
        docker build -t "$REGISTRY/$service_name:$TAG" "$BASE_DIR" -f "$context_dir/Dockerfile"
        echo "  ✓ Built $REGISTRY/$service_name:$TAG"
    fi
    
    # # Clean up copied files
    # if [ -d "$context_dir/generated" ]; then
    #     rm -rf "$context_dir/generated"
    #     echo "  ✓ Cleaned up temporary files"
    # fi
}

# Generate Protocol Buffers if not already done
if [ ! -d "$BASE_DIR/generated/python" ]; then
    echo "📋 Generating Protocol Buffers..."
    cd "$BASE_DIR"
    ./scripts/generate_protos.sh
    echo "  ✓ Protocol Buffers generated"
fi

# Build services based on type
if [[ "$BUILD_TYPE" == "all" || "$BUILD_TYPE" == "grpc" ]]; then
    echo "🚀 Building gRPC services..."
    build_service "resize-grpc" "$BASE_DIR/services/resize-grpc-app"
    build_service "ai-detection-grpc" "$BASE_DIR/services/ai-detection-grpc-app"
    build_service "filter-grpc" "$BASE_DIR/services/filter-grpc-app"
    build_service "grpc-gateway" "$BASE_DIR/services/grpc-gateway"
    build_service "camera-stream-grpc" "$BASE_DIR/services/camera-stream-grpc-app"
    build_service "inspection-evaluator-grpc" "$BASE_DIR/services/inspection-evaluator-grpc-app"
    echo "✅ gRPC services built successfully!"
fi

if [[ "$BUILD_TYPE" == "all" || "$BUILD_TYPE" == "web" ]]; then
    echo "🚀 Building web services..."
    build_service "backend" "$BASE_DIR/backend"
    build_service "web" "$BASE_DIR/web"
    echo "✅ Web services built successfully!"
fi

echo "🎉 Build completed successfully!"
echo ""
echo "Next steps:"
echo "- For Docker Compose: ./scripts/run-compose.sh"
echo "- For K3s: ./scripts/setup-k3s.sh"
echo "- For Nomad: ./scripts/setup-nomad-consul.sh"
