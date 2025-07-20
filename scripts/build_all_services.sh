#!/bin/bash

# Build and deploy all ImageFlowCanvas services
#
# Usage:
#   ./scripts/build_all_services.sh                     # Build only
#   DEPLOY=true ./scripts/build_all_services.sh         # Build and deploy
#   PUSH=true ./scripts/build_all_services.sh           # Build and push to registry
#
# Environment variables:
#   REGISTRY   - Docker registry prefix (default: imageflow)
#   TAG        - Docker image tag (default: latest)
#   PUSH       - Push images to registry (default: false)
#   DEPLOY     - Deploy to Kubernetes (default: false)

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🚀 Building All ImageFlowCanvas Services"
echo ""

# Build gRPC services
echo "⚙️  Step 1: Building gRPC Services..."
"$BASE_DIR/scripts/build_grpc_services.sh"
echo ""

# Build web services
echo "🌐 Step 2: Building Web Services..."
"$BASE_DIR/scripts/build_web_services.sh"
echo ""

echo "✅ All services built successfully!"
echo ""

if [ "$DEPLOY" = "true" ]; then
    echo "🚀 Deploying all services..."
    
    # Deploy gRPC services
    echo "⚙️  Deploying gRPC services..."
    DEPLOY=true "$BASE_DIR/scripts/build_grpc_services.sh"
    
    # Deploy web services  
    echo "🌐 Deploying web services..."
    DEPLOY=true "$BASE_DIR/scripts/build_web_services.sh"
    
    echo "✅ All services deployed successfully!"
fi

echo ""
echo "🎉 Complete build and deployment finished!"
echo ""
echo "Service management commands:"
echo "1. Check all pods:"
echo "   kubectl get pods --all-namespaces"
echo ""
echo "2. Access the frontend:"
echo "   kubectl port-forward svc/frontend 3000:80"
echo ""
echo "3. Access the backend:"
echo "   kubectl port-forward svc/backend 8000:8000"
echo ""
echo "4. Monitor gRPC services:"
echo "   kubectl get pods -n image-processing"
