#!/bin/bash

echo "Setting up port forwarding for development..."

# Kill existing port-forward processes more thoroughly
echo "Stopping existing port forwards..."
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 3
# Force kill if still running
pkill -9 -f "kubectl port-forward" 2>/dev/null || true
sleep 2

# Check if critical ports are available (with timeout)
echo "Checking critical port availability..."
timeout=10
for port in 3000 8000; do
    count=0
    while lsof -i :$port >/dev/null 2>&1 && [ $count -lt $timeout ]; do
        echo "Waiting for critical port $port to be available... ($count/$timeout)"
        sleep 1
        count=$((count + 1))
    done
    if [ $count -eq $timeout ]; then
        echo "⚠️  Port $port still in use, but continuing..."
    fi
done

echo "Starting new port forwards..."
echo "Access services at:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- gRPC Gateway: http://localhost:8080"
echo "- Argo Workflows UI: http://localhost:2746"
echo "- MinIO Console: http://localhost:9001"
echo "- Triton Inference Server: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop port forwarding"

# Start port forwarding in background with better error handling
echo "Starting frontend service..."
kubectl port-forward svc/frontend-service -n default 3000:80 >/dev/null 2>&1 &
FRONTEND_PID=$!

echo "Starting backend service..."
kubectl port-forward svc/backend-service -n default 8000:8000 >/dev/null 2>&1 &
BACKEND_PID=$!

echo "Starting gRPC Gateway..."
kubectl port-forward svc/grpc-gateway -n image-processing 8080:8080 >/dev/null 2>&1 &
GRPC_GATEWAY_PID=$!

echo "Starting Argo Workflows UI..."
kubectl port-forward svc/argo-server -n argo 2746:2746 >/dev/null 2>&1 &
ARGO_PID=$!

echo "Starting MinIO console..."
kubectl port-forward svc/minio-service -n default 9001:9001 >/dev/null 2>&1 &
MINIO_PID=$!

echo "Starting Triton inference server..."
kubectl port-forward svc/triton-service -n default 8001:8000 >/dev/null 2>&1 &
TRITON_PID=$!

# Wait a moment for port forwards to establish
sleep 5

echo ""
echo "Port forwarding established. Testing connections..."

# Test connections with more detailed feedback
services_status=()

if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend: http://localhost:3000"
    services_status+=("frontend:ok")
else
    echo "❌ Frontend connection failed"
    services_status+=("frontend:fail")
fi

if curl -s http://localhost:8000/v1/health > /dev/null; then
    echo "✅ Backend: http://localhost:8000"
    services_status+=("backend:ok")
else
    echo "❌ Backend connection failed"
    services_status+=("backend:fail")
fi

if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ gRPC Gateway: http://localhost:8080"
    services_status+=("grpc-gateway:ok")
else
    echo "❌ gRPC Gateway connection failed"
    services_status+=("grpc-gateway:fail")
fi

# Test other services
if curl -s http://localhost:2746 > /dev/null; then
    echo "✅ Argo Workflows: http://localhost:2746"
    services_status+=("argo:ok")
else
    echo "⚠️  Argo Workflows: http://localhost:2746 (may need time to start)"
    services_status+=("argo:pending")
fi

if curl -s http://localhost:9001 > /dev/null; then
    echo "✅ MinIO Console: http://localhost:9001"
    services_status+=("minio:ok")
else
    echo "⚠️  MinIO Console: http://localhost:9001 (may need time to start)"
    services_status+=("minio:pending")
fi

if curl -s http://localhost:8001/v2/health/ready > /dev/null; then
    echo "✅ Triton Server: http://localhost:8001"
    services_status+=("triton:ok")
else
    echo "⚠️  Triton Server: http://localhost:8001 (may need time to start)"
    services_status+=("triton:pending")
fi

echo ""
echo "🌐 Open your browser and go to: http://localhost:3000"
echo "📋 Login with: admin/admin123 or user/user123"

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping port forwards..."
    kill $FRONTEND_PID $BACKEND_PID $GRPC_GATEWAY_PID $ARGO_PID $MINIO_PID $TRITON_PID 2>/dev/null || true
    pkill -f "kubectl port-forward" 2>/dev/null || true
    exit 0
}

# Set trap to cleanup on exit
trap cleanup SIGINT SIGTERM

# Wait for interrupt
wait
