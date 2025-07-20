#!/bin/bash

# Optimized deployment script for ImageFlowCanvas gRPC services
# This script deploys the performance-optimized gRPC services

set -e

echo "🚀 Deploying optimized ImageFlowCanvas gRPC services"

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

# Build optimized gRPC services
echo "📦 Building optimized gRPC services..."
./scripts/build_grpc_services.sh

# Apply namespace configuration
echo "🏗️  Applying namespace configuration..."
kubectl apply -f k8s/grpc/namespace-config.yaml

# Apply RBAC configuration
echo "🔐 Applying RBAC configuration..."
kubectl apply -f k8s/grpc/grpc-workflow-rbac.yaml
kubectl apply -f k8s/grpc/grpc-workflow-token.yaml

# Deploy optimized gRPC services
echo "🎯 Deploying optimized gRPC services with health checks..."
kubectl apply -f k8s/grpc/grpc-services-optimized.yaml

# Deploy workflow templates
echo "⚡ Deploying workflow templates..."
kubectl apply -f k8s/workflows/grpc-pipeline-templates.yaml

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/resize-grpc-service -n image-processing
kubectl wait --for=condition=available --timeout=300s deployment/ai-detection-grpc-service -n image-processing  
kubectl wait --for=condition=available --timeout=300s deployment/filter-grpc-service -n image-processing
kubectl wait --for=condition=available --timeout=300s deployment/grpc-gateway -n image-processing

# Check service health
echo "🏥 Checking service health..."
echo "Services status:"
kubectl get pods -n image-processing -o wide

echo "Service endpoints:"
kubectl get services -n image-processing

# Test basic connectivity
echo "🧪 Testing basic service connectivity..."
echo "Testing gRPC Gateway health..."
timeout 10s kubectl exec -n image-processing deployment/grpc-gateway -- curl -f http://localhost:8080/health || echo "Gateway health check failed"

echo "Testing individual gRPC services..."
timeout 10s kubectl exec -n image-processing deployment/resize-grpc-service -- /bin/grpc_health_probe -addr=:9090 || echo "Resize service health check failed"
timeout 10s kubectl exec -n image-processing deployment/ai-detection-grpc-service -- /bin/grpc_health_probe -addr=:9090 || echo "AI Detection service health check failed"
timeout 10s kubectl exec -n image-processing deployment/filter-grpc-service -- /bin/grpc_health_probe -addr=:9090 || echo "Filter service health check failed"

echo ""
echo "✅ Optimized gRPC services deployment completed!"
echo ""
echo "Performance optimizations applied:"
echo "• ✅ Increased resource allocations (CPU/Memory)"
echo "• ✅ Added health checks with gRPC health probe"
echo "• ✅ Optimized thread pool configurations"
echo "• ✅ Added connection pooling and service warm-up"
echo "• ✅ Improved error handling and timing metrics"
echo ""
echo "Expected performance improvements:"
echo "• 🎯 Target processing time: 1-3 seconds"
echo "• 📈 Improved from 60-94 seconds (old Pod-based system)"
echo "• 🔄 Services now run constantly (no Pod startup time)"
echo "• 🏥 Better reliability with health monitoring"
echo ""
echo "Next steps:"
echo "1. Run performance tests:"
echo "   python3 scripts/performance_monitor.py --gateway-url http://localhost:8080"
echo ""
echo "2. Port-forward to test locally:"
echo "   kubectl port-forward -n image-processing service/grpc-gateway 8080:8080"
echo ""
echo "3. Monitor service logs:"
echo "   kubectl logs -f -n image-processing deployment/grpc-gateway"
echo "   kubectl logs -f -n image-processing deployment/resize-grpc-service"