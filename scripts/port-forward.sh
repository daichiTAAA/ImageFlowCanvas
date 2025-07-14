#!/bin/bash

echo "Setting up port forwarding for development..."

# Kill existing port-forward processes
echo "Stopping existing port forwards..."
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 2

echo "Starting new port forwards..."
echo "Access services at:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- Argo Workflows UI: http://localhost:2746"
echo "- MinIO Console: http://localhost:9001"
echo "- Triton Inference Server: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop port forwarding"

# Start port forwarding in background with proper error handling
kubectl port-forward svc/frontend-service -n default 3000:80 &
FRONTEND_PID=$!

kubectl port-forward svc/backend-service -n default 8000:8000 &
BACKEND_PID=$!

kubectl port-forward svc/argo-server -n argo 2746:2746 &
ARGO_PID=$!

kubectl port-forward svc/minio-service -n default 9001:9001 &
MINIO_PID=$!

kubectl port-forward svc/triton-service -n default 8001:8000 &
TRITON_PID=$!

# Wait a moment for port forwards to establish
sleep 3

echo ""
echo "Port forwarding established. Testing connections..."

# Test connections
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend: http://localhost:3000"
else
    echo "❌ Frontend connection failed"
fi

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend: http://localhost:8000"
else
    echo "❌ Backend connection failed"
fi

echo ""
echo "🌐 Open your browser and go to: http://localhost:3000"
echo "📋 Login with: admin/admin123 or user/user123"

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping port forwards..."
    kill $FRONTEND_PID $BACKEND_PID $ARGO_PID $MINIO_PID $TRITON_PID 2>/dev/null || true
    pkill -f "kubectl port-forward" 2>/dev/null || true
    exit 0
}

# Set trap to cleanup on exit
trap cleanup SIGINT SIGTERM

# Wait for interrupt
wait
