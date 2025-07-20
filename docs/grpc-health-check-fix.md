# gRPC Health Check Fix Documentation

## Issue Summary

常駐gRPCサービス監視ページにて、ステータスが3つの常駐gRPCサービスともタイムアウト "Health check timed out..." となる問題を修正しました。

## Root Cause Analysis

### 1. Kubernetes Health Probe Issue
- **Problem**: `grpc_health_probe` binary の exec format error
- **Cause**: アーキテクチャの不一致（amd64バイナリをARM環境で実行など）

### 2. Backend gRPC Health Check Issue  
- **Problem**: バックエンドからのgRPCヘルスチェックでタイムアウトエラー
- **Cause**: 
  - AI Detection・Filter サービスで標準gRPCヘルスチェックサービスが未登録
  - 不正なサービス名の使用
  - タイムアウト時間が短すぎる

## Solutions Implemented

### 1. grpc_health_probe Binary Fix

**Before (problematic):**
```dockerfile
RUN wget -qO /bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.34/grpc_health_probe-linux-amd64
```

**After (fixed):**
```dockerfile
RUN apt-get update && apt-get install -y wget && \
    ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        GRPC_HEALTH_PROBE_ARCH="linux-amd64"; \
    elif [ "$ARCH" = "arm64" ]; then \
        GRPC_HEALTH_PROBE_ARCH="linux-arm64"; \
    else \
        GRPC_HEALTH_PROBE_ARCH="linux-amd64"; \
    fi && \
    wget -qO /bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.34/grpc_health_probe-${GRPC_HEALTH_PROBE_ARCH} && \
    chmod +x /bin/grpc_health_probe && \
    /bin/grpc_health_probe --version && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
```

**Improvements:**
- ✅ Architecture detection (amd64/arm64)
- ✅ Binary verification with `--version`
- ✅ Enhanced error detection during build

### 2. Standard gRPC Health Service Implementation

#### AI Detection Service (`ai_detection_grpc_server.py`)

**Added:**
```python
from grpc_health.v1 import health_pb2, health_pb2_grpc

class HealthServiceImplementation(health_pb2_grpc.HealthServicer):
    def __init__(self, ai_detection_service):
        self.ai_detection_service = ai_detection_service
    
    def Check(self, request, context):
        response = health_pb2.HealthCheckResponse()
        if self.ai_detection_service._health_check():
            response.status = health_pb2.HealthCheckResponse.SERVING
        else:
            response.status = health_pb2.HealthCheckResponse.NOT_SERVING
        return response
    
    def Watch(self, request, context):
        # Streaming health check implementation
        response = health_pb2.HealthCheckResponse()
        if self.ai_detection_service._health_check():
            response.status = health_pb2.HealthCheckResponse.SERVING
        else:
            response.status = health_pb2.HealthCheckResponse.NOT_SERVING
        yield response

# Register the health service
health_pb2_grpc.add_HealthServicer_to_server(health_service, server)
```

#### Filter Service (`filter_grpc_server.py`)

**Added:** Same implementation as AI Detection Service

#### Dependencies Updated

**Added to requirements.txt:**
```
grpcio-health-checking==1.73.1
```

### 3. Backend Monitoring Service Fix

**File:** `backend/app/services/grpc_monitor_service.py`

**Before:**
```python
health_request.service = service_name  # ❌ Wrong
health_response = health_stub.Check(health_request, timeout=5.0)  # ❌ Too short
```

**After:**
```python
health_request.service = ""  # ✅ Empty for overall service health
health_response = health_stub.Check(health_request, timeout=10.0)  # ✅ Increased timeout
```

**Additional Improvements:**
- Enhanced gRPC connection options
- Better keepalive configuration
- Improved error handling and reporting

## Files Modified

### Dockerfiles
- `services/resize-grpc-app/Dockerfile`
- `services/ai-detection-grpc-app/Dockerfile`
- `services/filter-grpc-app/Dockerfile`

### gRPC Services
- `services/ai-detection-grpc-app/src/ai_detection_grpc_server.py`
- `services/filter-grpc-app/src/filter_grpc_server.py`
- `services/ai-detection-grpc-app/requirements.txt`
- `services/filter-grpc-app/requirements.txt`

### Backend Monitoring
- `backend/app/services/grpc_monitor_service.py`

## Deployment Instructions

### 1. Rebuild Docker Images

```bash
# Rebuild all gRPC service images
cd services/resize-grpc-app
docker build -t docker.io/imageflow/resize-grpc:latest .

cd ../ai-detection-grpc-app  
docker build -t docker.io/imageflow/ai-detection-grpc:latest .

cd ../filter-grpc-app
docker build -t docker.io/imageflow/filter-grpc:latest .
```

### 2. Deploy to Kubernetes

```bash
# Apply the updated deployments
kubectl apply -f k8s/grpc/grpc-services.yaml
```

### 3. Restart Backend Service

```bash
# Restart the backend service to pick up monitoring changes
kubectl rollout restart deployment backend-service -n image-processing
```

## Verification

### 1. Check Kubernetes Health Probes

```bash
# Check pod status - should not show CrashLoopBackOff
kubectl get pods -n image-processing

# Check health probe events
kubectl describe pod <pod-name> -n image-processing
```

### 2. Test Backend Health Monitoring

```bash
# Test the health endpoint
curl http://<backend-url>/api/grpc-services/health

# Expected response:
[
  {
    "service_name": "resize-grpc-service",
    "display_name": "Image Resize Service", 
    "status": "SERVING",
    "response_time_ms": 12.34,
    "endpoint": "resize-grpc-service.image-processing.svc.cluster.local:9090",
    "last_checked": "2024-XX-XX XX:XX:XX"
  },
  {
    "service_name": "ai-detection-grpc-service",
    "display_name": "AI Detection Service",
    "status": "SERVING", 
    "response_time_ms": 15.67,
    "endpoint": "ai-detection-grpc-service.image-processing.svc.cluster.local:9090",
    "last_checked": "2024-XX-XX XX:XX:XX"
  },
  {
    "service_name": "filter-grpc-service",
    "display_name": "Filter Service",
    "status": "SERVING",
    "response_time_ms": 8.91,
    "endpoint": "filter-grpc-service.image-processing.svc.cluster.local:9090", 
    "last_checked": "2024-XX-XX XX:XX:XX"
  }
]
```

### 3. Test gRPC Health Probes Directly

```bash
# Test from within a pod
kubectl exec -it <pod-name> -n image-processing -- /bin/grpc_health_probe -addr=:9090
# Expected: status: SERVING
```

## Expected Results

After applying these fixes:

- ✅ Kubernetes health probes should work without exec format errors
- ✅ Backend monitoring should show "SERVING" status for all 3 services
- ✅ No more "Health check timed out..." errors
- ✅ Proper health status reporting in the monitoring UI

## Troubleshooting

### If health checks still fail:

1. **Check pod logs:**
   ```bash
   kubectl logs <pod-name> -n image-processing
   ```

2. **Verify binary installation:**
   ```bash
   kubectl exec -it <pod-name> -n image-processing -- /bin/grpc_health_probe --version
   ```

3. **Test connectivity:**
   ```bash
   kubectl exec -it <pod-name> -n image-processing -- nc -zv <service-name> 9090
   ```

4. **Check service registration:**
   ```bash
   # Look for "HealthServicer" registration in logs
   kubectl logs <pod-name> -n image-processing | grep -i health
   ```