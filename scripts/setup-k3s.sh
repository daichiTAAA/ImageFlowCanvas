#!/bin/bash

# Setup script for K3s and Argo Workflows development environment
set -e

echo "Setting up ImageFlowCanvas development environment with K3s and Argo Workflows..."

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

# Install Argo Workflows
echo "Installing Argo Workflows..."
kubectl create namespace argo --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.4/install.yaml

# Apply custom Argo Server configuration
echo "Applying custom Argo Server configuration..."
kubectl apply -f k8s/core/argo-server-deployment.yaml

# Wait for Argo Workflows to be ready
echo "Waiting for Argo Workflows to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/argo-server -n argo
kubectl wait --for=condition=available --timeout=300s deployment/workflow-controller -n argo

# Apply custom configurations
echo "Applying custom configurations..."
kubectl apply -f k8s/core/argo-secret.yaml

# Create default namespace resources
echo "Creating core infrastructure..."
kubectl apply -f k8s/core/minio-pv-pvc.yaml
kubectl apply -f k8s/core/minio-deployment.yaml
kubectl apply -f k8s/core/kafka-deployment.yaml
kubectl apply -f k8s/core/triton-deployment.yaml

# Wait for core services to be ready
echo "Waiting for core services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/minio -n default
kubectl wait --for=condition=available --timeout=300s deployment/kafka -n default
kubectl wait --for=condition=available --timeout=300s deployment/triton-inference-server -n default

# Build and import backend image
echo "Building backend image..."
docker build -t imageflow/backend:latest ./backend
echo "Importing backend image to K3s..."
docker save imageflow/backend:latest | sudo k3s ctr images import -

# Build and import frontend image
echo "Building frontend image..."
docker build -t imageflow/frontend:latest ./frontend
echo "Importing frontend image to K3s..."
docker save imageflow/frontend:latest | sudo k3s ctr images import -

# Deploy backend and frontend
echo "Deploying backend and frontend..."
kubectl apply -f k8s/core/app-deployments.yaml

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/backend -n default

# Setup port forwarding script
cat > scripts/port-forward.sh << 'EOF'
#!/bin/bash
echo "Setting up port forwarding for development..."
echo "Access services at:"
echo "- Argo Workflows UI: http://localhost:2746"
echo "- Backend API: http://localhost:8000"
echo "- MinIO Console: http://localhost:9001"
echo "- Triton Inference Server: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop port forwarding"

# Start port forwarding in background
kubectl port-forward svc/argo-server -n argo 2746:2746 &
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
echo "Next steps:"
echo "1. Run 'sudo ./scripts/setup-k3s.sh' to complete the setup"
echo "2. Run './scripts/port-forward.sh' to access services"
echo "3. Place YOLO model at 'models/yolo/1/model.onnx'"
echo "4. Start frontend development server: cd frontend && npm install && npm run dev"
echo ""
echo "Access points:"
echo "- Argo Workflows UI: http://localhost:2746"
echo "- Backend API: http://localhost:8000"
echo "- MinIO Console: http://localhost:9001 (admin/admin123)"
echo "- Triton Server: http://localhost:8001"
echo "- Frontend: http://localhost:3000"