#!/bin/bash

# Quick validation script for camera streaming setup
# This script checks if all camera streaming components are properly configured

set -e

echo "📹 Validating camera streaming setup..."

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo "✅ $1"
        return 0
    else
        echo "❌ $1 missing"
        return 1
    fi
}

# Function to check if directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo "✅ $1/"
        return 0
    else
        echo "❌ $1/ missing"
        return 1
    fi
}

echo ""
echo "🔍 Checking camera streaming files..."

# Check setup scripts
echo "Setup scripts:"
check_file "scripts/setup-complete.sh"
check_file "scripts/setup-camera-stream.sh"
check_file "scripts/build_grpc_services.sh"

# Check camera stream service
echo ""
echo "Camera stream service:"
check_dir "services/camera-stream-grpc-app"
check_file "services/camera-stream-grpc-app/Dockerfile"
check_file "services/camera-stream-grpc-app/requirements.txt"
check_dir "services/camera-stream-grpc-app/src"

# Check Protocol Buffers
echo ""
echo "Protocol Buffers:"
check_file "proto/imageflow/v1/camera_stream.proto"

# Check backend API
echo ""
echo "Backend camera stream API:"
check_file "backend/app/api/camera_stream.py"

# Check frontend components
echo ""
echo "Frontend camera streaming UI:"
check_file "frontend/src/pages/CameraStream.tsx"

# Check K8s configuration
echo ""
echo "Kubernetes configuration:"
check_file "k8s/grpc/grpc-services.yaml"

# Check if camera-stream service is in K8s config
echo ""
echo "🔍 Checking K8s camera stream service configuration..."
if grep -q "camera-stream-grpc-service" k8s/grpc/grpc-services.yaml; then
    echo "✅ Camera stream service found in K8s configuration"
else
    echo "❌ Camera stream service not found in K8s configuration"
fi

# Check if build script includes camera stream
echo ""
echo "🔍 Checking build script configuration..."
if grep -q "camera-stream-grpc" scripts/build_grpc_services.sh; then
    echo "✅ Camera stream service found in build script"
else
    echo "❌ Camera stream service not found in build script"
fi

# Check test files
echo ""
echo "Test files:"
check_file "test_camera_stream_integration.py"
check_file "docker-compose.camera-stream.yml"

echo ""
echo "📋 Setup validation summary:"
echo ""
echo "Available setup methods:"
echo "1. Complete setup (new installation): sudo ./scripts/setup-complete.sh"
echo "2. Camera-only setup (existing installation): ./scripts/setup-camera-stream.sh"
echo "3. Manual build: ./scripts/build_grpc_services.sh (includes camera stream)"
echo ""
echo "After setup, access camera streaming at:"
echo "- Frontend: http://localhost:3000 → 'リアルタイム処理' tab"
echo "- API docs: http://localhost:8000/docs"
echo ""
echo "✅ Validation completed!"