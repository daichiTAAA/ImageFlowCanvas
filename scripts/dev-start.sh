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
DEPLOYMENTS=("minio" "kafka" "triton-inference-server" "backend" "frontend")
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

# Check Argo Workflows
echo "Checking Argo Workflows..."
if ! kubectl wait --for=condition=available --timeout=300s deployment/argo-server -n argo 2>/dev/null; then
    echo "Warning: Argo Workflows may not be ready. Check with: kubectl get pods -n argo"
fi

echo ""
echo "✅ Development environment is ready!"
echo ""
echo "Access points:"
echo "- Frontend (NodePort): http://192.168.5.15:30080"
echo "- Frontend (port-forward): http://localhost:3000 (run ./scripts/port-forward.sh)"
echo "- Backend API: http://localhost:8000 (via port-forward)"
echo "- Argo Workflows UI: http://localhost:2746 (via port-forward)"
echo "- MinIO Console: http://localhost:9001 (via port-forward, admin/admin123)"
echo "- Triton Server: http://localhost:8001 (via port-forward)"
echo ""
echo "Next steps:"
echo "1. ./scripts/port-forward.sh  # To enable local access via localhost"
echo ""
echo "Login credentials:"
echo "- Admin: admin/admin123"
echo "- User: user/user123"