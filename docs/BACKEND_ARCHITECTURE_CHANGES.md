# Backend Architecture Changes

## Summary

The backend has been modified to align with the design documentation. Image processing and AI inference are no longer performed directly in the backend application. Instead, the backend acts as a coordinator that delegates processing to Argo Workflows.

## Key Changes

### 1. Removed Direct Image Processing
- **Before**: Backend performed resize, AI detection, and filtering directly using OpenCV, YOLO, and Triton
- **After**: Backend only coordinates and delegates to Argo Workflows

### 2. New Argo Workflows Integration
- Added `ArgoWorkflowService` for workflow submission and monitoring
- Modified `ExecutionWorker` to delegate to Argo instead of processing locally
- Workflows are defined in `k8s/workflows/` directory

### 3. Simplified Component Service
- **Before**: Performed actual image processing
- **After**: Only provides component metadata and parameter validation

### 4. Updated Dependencies
- Removed heavy processing libraries: `opencv-python`, `ultralytics`, `tritonclient`, `numpy`
- Added `argo-workflows` client library
- Reduced backend container size and complexity

### 5. Updated Docker Compose
- Removed Triton Inference Server dependency from backend
- Added Argo Workflows environment variables
- Image processing now happens in separate containerized services

## Architecture Flow

```
User Request → Backend API → Kafka → ExecutionWorker → ArgoWorkflowService → Argo Workflows → Processing Containers
```

### Processing Containers
- `services/resize-app/` - Image resizing
- `services/object-detection-app/` - AI object detection
- `services/filter-app/` - Image filtering

### Backend Responsibilities
- Pipeline definition management
- File upload/download coordination
- Workflow submission to Argo
- Progress monitoring via Argo API
- Real-time updates to frontend via WebSocket

## Benefits

1. **Scalability**: Image processing can scale independently on Kubernetes
2. **Resource Isolation**: Heavy processing doesn't affect backend responsiveness
3. **Technology Flexibility**: Processing containers can use different technologies
4. **Fault Tolerance**: Processing failures don't crash the main backend
5. **Alignment**: Matches the original architecture design specification

## Environment Variables

The backend now requires these Argo-related environment variables:

```env
ARGO_SERVER_URL=http://argo-server.argo.svc.cluster.local:2746
ARGO_NAMESPACE=argo
WORKFLOW_TEMPLATE=dynamic-image-processing
```

## Migration Notes

- Existing pipeline definitions continue to work
- Processing results are stored in MinIO as before
- Frontend API remains unchanged
- WebSocket progress updates continue to work

This change ensures the backend follows the "orchestration, not execution" principle specified in the design documentation.