#!/bin/bash

# Development startup script using K3s instead of docker-compose
set -e

echo "Starting ImageFlowCanvas development environment with K3s..."

# Check if K3s is running
if ! sudo systemctl is-active --quiet k3s; then
    echo "Starting K3s..."
    sudo systemctl start k3s
    sleep 10
fi

# Check if all deployments are running
echo "Checking deployment status..."
kubectl get deployments -n default

# Check if services need to be started
DEPLOYMENTS=("minio" "kafka" "triton-inference-server" "backend")
for deployment in "${DEPLOYMENTS[@]}"; do
    if ! kubectl get deployment $deployment -n default &> /dev/null; then
        echo "Deployment $deployment not found, applying configurations..."
        kubectl apply -f k8s/core/
        break
    fi
done

# Scale up deployments if they're scaled down
for deployment in "${DEPLOYMENTS[@]}"; do
    current_replicas=$(kubectl get deployment $deployment -n default -o jsonpath='{.spec.replicas}')
    if [ "$current_replicas" -eq 0 ]; then
        echo "Scaling up $deployment..."
        kubectl scale deployment $deployment -n default --replicas=1
    fi
done

# Wait for all deployments to be ready
echo "Waiting for all services to be ready..."
for deployment in "${DEPLOYMENTS[@]}"; do
    echo "Waiting for $deployment..."
    kubectl wait --for=condition=available --timeout=300s deployment/$deployment -n default
done

# Start frontend in development mode
echo "Starting frontend development server..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo ""
echo "Development environment is ready!"
echo ""
echo "In separate terminals, run:"
echo "1. ./scripts/port-forward.sh  # To access services"
echo "2. cd frontend && npm run dev  # To start frontend"
echo ""
echo "Or use docker-compose for simpler local development:"
echo "docker-compose up -d"