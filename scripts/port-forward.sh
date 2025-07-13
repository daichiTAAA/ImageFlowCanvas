#!/bin/bash

echo "Setting up port forwarding for development..."
echo "Access services at:"
echo "- Argo Workflows UI: http://localhost:2746"
echo "- Backend API: http://localhost:8000"
echo "- MinIO Console: http://localhost:9001"
echo "- Triton Inference Server: http://localhost:8001"
echo "- Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop port forwarding"

# Start port forwarding in background
kubectl port-forward svc/argo-server -n argo 2746:2746 &
kubectl port-forward svc/backend-service -n default 8000:8000 &
kubectl port-forward svc/minio-service -n default 9001:9001 &
kubectl port-forward svc/triton-service -n default 8001:8000 &
kubectl port-forward svc/frontend-service -n default 3000:80 &

# Wait for interrupt
wait
