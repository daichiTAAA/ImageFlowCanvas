#!/bin/bash

# Setup script for K3s development environment
set -e

echo "Setting up ImageFlowCanvas development environment with K3s..."

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Warning: This script is designed for Linux. For other platforms, please use Docker Desktop with Kubernetes enabled."
fi

# Install K3s if not already installed
if ! command -v k3s &> /dev/null; then
    echo "Installing K3s..."
    curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
    
    # Wait for K3s to be ready
    echo "Waiting for K3s to be ready..."
    sudo k3s kubectl wait --for=condition=ready node --all --timeout=300s
else
    echo "K3s is already installed"
fi

# Set up kubectl alias
if ! command -v kubectl &> /dev/null; then
    echo "Setting up kubectl alias..."
    sudo cp /usr/local/bin/k3s /usr/local/bin/kubectl
    sudo chmod +x /usr/local/bin/kubectl
fi

# Create kubeconfig for current user
echo "Setting up kubeconfig..."
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config

# Apply custom configurations
echo "Applying custom configurations..."

# Create default namespace resources
echo "Creating core infrastructure..."
kubectl apply -f deploy/k3s/core/minio-pv-pvc.yaml
kubectl apply -f deploy/k3s/core/minio-deployment.yaml
kubectl apply -f deploy/k3s/core/postgres-deployment.yaml
kubectl apply -f deploy/k3s/core/kafka-deployment.yaml
kubectl apply -f deploy/k3s/core/triton-deployment.yaml

# Wait for core services to be ready
echo "Waiting for core services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/minio -n default
kubectl wait --for=condition=available --timeout=300s deployment/postgres -n default
kubectl wait --for=condition=available --timeout=300s deployment/kafka -n default
kubectl wait --for=condition=available --timeout=300s deployment/triton-inference-server -n default

# Check if required images exist
echo "Checking for required Docker images..."
if ! docker image inspect imageflow/backend:local >/dev/null 2>&1; then
    echo "Error: Backend image not found. Please run './scripts/build_services.sh' first."
    exit 1
fi

if ! docker image inspect imageflow/frontend:local >/dev/null 2>&1; then
    echo "Error: Frontend image not found. Please run './scripts/build_services.sh' first."
    exit 1
fi

# Import backend and frontend images to K3s
echo "Importing backend image to K3s..."
docker save imageflow/backend:local | sudo k3s ctr images import -

echo "Importing frontend image to K3s..."
docker save imageflow/frontend:local | sudo k3s ctr images import -

# Deploy backend and frontend
echo "Deploying backend and frontend..."
kubectl apply -f deploy/k3s/core/app-deployments.yaml

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/backend -n default

# Deploy gRPC services
echo "Deploying gRPC services..."
kubectl apply -f deploy/k3s/grpc/namespace-config.yaml

# Check if required gRPC images exist and import them
echo "Checking and importing gRPC service images..."
GRPC_SERVICES=("resize-grpc" "ai-detection-grpc" "filter-grpc" "grpc-gateway" "camera-stream-grpc")

for service in "${GRPC_SERVICES[@]}"; do
    if docker image inspect imageflow/$service:local >/dev/null 2>&1; then
        echo "Importing $service image to K3s..."
        docker save imageflow/$service:local | sudo k3s ctr images import -
    else
        echo "Warning: $service image not found. Please run './scripts/build_services.sh' first."
    fi
done

kubectl apply -f deploy/k3s/grpc/grpc-services.yaml

# Wait for gRPC services to be ready
echo "Waiting for gRPC services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/resize-grpc-service -n image-processing
kubectl wait --for=condition=available --timeout=300s deployment/ai-detection-grpc-service -n image-processing
kubectl wait --for=condition=available --timeout=300s deployment/filter-grpc-service -n image-processing
kubectl wait --for=condition=available --timeout=300s deployment/grpc-gateway -n image-processing
kubectl wait --for=condition=available --timeout=300s deployment/camera-stream-grpc-service -n image-processing

# Setup port forwarding script
cat > scripts/port-forward.sh << 'EOF'
#!/bin/bash
echo "Setting up port forwarding for development..."
echo "Access services at:"
echo "- Backend API: http://localhost:8000"
echo "- MinIO Console: http://localhost:9001"
echo "- Triton Inference Server: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop port forwarding"

# Start port forwarding in background
kubectl port-forward svc/backend-service -n default 8000:8000 &
kubectl port-forward svc/minio-service -n default 9001:9001 &
kubectl port-forward svc/triton-service -n default 8001:8000 &

# Wait for interrupt
wait
EOF

chmod +x scripts/port-forward.sh

echo ""
echo "Setup completed successfully!"
echo ""
echo "Prerequisites (run before this script):"
echo "1. ./scripts/generate_protos.sh   # Generate Protocol Buffers"
echo "2. ./scripts/build_services.sh    # Build all Docker images"
echo ""
echo "Next steps:"
echo "1. Run './scripts/port-forward.sh' to access services"
echo "2. Place YOLO model at 'models/yolo/1/model.onnx'"
echo "3. Start frontend development server: cd frontend && npm install && npm run dev"
echo ""
echo "Access points:"
echo "- Backend API: http://localhost:8000"
echo "- MinIO Console: http://localhost:9001 (admin/admin123)"
echo "- Triton Server: http://localhost:8001"
echo "- Frontend: http://localhost:3000"