#!/bin/bash

# Build and deployment script for ImageFlowCanvas backend and frontend services
#
# Usage:
#   ./scripts/build_web_services.sh                     # Build only
#   DEPLOY=true ./scripts/build_web_services.sh         # Build and deploy
#   PUSH=true ./scripts/build_web_services.sh           # Build and push to registry
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

echo "🔧 Building ImageFlowCanvas Web Services (Backend & Frontend)"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Base Directory: $BASE_DIR"

# Generate Protocol Buffers if not already done (needed for backend)
if [ ! -d "$BASE_DIR/generated/python" ]; then
    echo "📋 Generating Protocol Buffers..."
    cd "$BASE_DIR"
    ./scripts/generate_protos.sh
    echo "  ✓ Protocol Buffers generated"
fi

# Build backend service
echo "📦 Building backend..."
docker build -t "$REGISTRY/backend:$TAG" "$BASE_DIR" -f "$BASE_DIR/backend/Dockerfile"
echo "  ✓ Built $REGISTRY/backend:$TAG"

# Build frontend service
echo "📦 Building frontend..."
docker build -t "$REGISTRY/frontend:$TAG" "$BASE_DIR" -f "$BASE_DIR/frontend/Dockerfile"
echo "  ✓ Built $REGISTRY/frontend:$TAG"

echo "✅ All web services built successfully!"

# Import images to K3s cluster if not in registry mode
if [ "$PUSH" != "true" ] || [ "$DEPLOY" != "true" ]; then
    echo "📥 Importing web service images to K3s cluster..."
    
    # Save images as tar files and import to K3s
    docker save "$REGISTRY/backend:$TAG" | sudo k3s ctr images import -
    docker save "$REGISTRY/frontend:$TAG" | sudo k3s ctr images import -
    
    echo "✅ All web service images imported to K3s cluster!"
fi

# Push to registry if requested
if [ "$PUSH" = "true" ]; then
    echo "📤 Pushing web service images to registry..."
    docker push "$REGISTRY/backend:$TAG"
    docker push "$REGISTRY/frontend:$TAG"
    echo "✅ All web service images pushed to registry!"
fi

# Deploy to Kubernetes if requested
if [ "$DEPLOY" = "true" ]; then
    echo "🚀 Deploying web services to Kubernetes..."

    echo "🔐 Applying RBAC configuration for gRPC monitoring..."
    kubectl apply -f deploy/k3s/grpc/grpc-monitor-rbac.yaml

    echo "🌐 Deploying backend and frontend..."
    kubectl apply -f deploy/k3s/core/app-deployments.yaml

    echo "🔄 Restarting web services to apply changes..."
    kubectl rollout restart deployment/frontend deployment/backend

    echo "✅ Web services deployment completed!"
fi

echo "🎉 Web services build completed successfully!"
echo ""
echo "Next steps:"
echo "1. For manual Kubernetes deployment:"
echo "   kubectl apply -f deploy/k3s/grpc/grpc-monitor-rbac.yaml"
echo "   kubectl apply -f deploy/k3s/core/app-deployments.yaml"
echo ""
echo "2. For automated deployment with rollout:"
echo "   DEPLOY=true ./scripts/build_web_services.sh"
echo ""
echo "3. Check service status:"
echo "   kubectl get pods -l app=backend"
echo "   kubectl get pods -l app=frontend"
echo ""
echo "4. Access the application:"
echo "   kubectl port-forward svc/frontend 3000:80"
echo "   kubectl port-forward svc/backend 8000:8000"
