# Camera Stream Integration with Web UI Pipeline Definitions

This document describes the integration between real-time camera stream processing and Web UI pipeline definitions, allowing pipelines created in the Web interface to be used for both batch and real-time processing.

## Overview

The integration enables:
- **Unified Pipeline Definitions**: Pipelines defined in the Web UI can be used for both batch processing and real-time camera streams
- **Real-time Processing**: Live camera feeds processed through existing gRPC microservices
- **Dynamic Pipeline Selection**: Client applications can choose which pipeline to apply to camera streams
- **Consistent Architecture**: Leverages existing gRPC services running as permanent pods in K3s

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Camera Client │    │   Backend API    │    │  gRPC Services      │
│                 │    │                  │    │                     │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────────┐ │
│ │ WebSocket   │◄┼────┼►│ Camera Stream│ │    │ │ Camera Stream   │ │
│ │ Connection  │ │    │ │ API          │ │    │ │ gRPC Service    │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────────┘ │
│                 │    │        │         │    │          │          │
│ ┌─────────────┐ │    │ ┌──────▼──────┐ │    │ ┌────────▼────────┐ │
│ │ Pipeline    │◄┼────┼►│ Pipeline    │ │    │ │ Processing      │ │
│ │ Selection   │ │    │ │ Service     │ │    │ │ Services:       │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ │ • Resize        │ │
└─────────────────┘    └──────────────────┘    │ │ • AI Detection  │ │
                                               │ │ • Filter        │ │
                                               │ └─────────────────┘ │
                                               └─────────────────────┘
```

## Key Components

### 1. Camera Stream gRPC Service (`services/camera-stream-grpc-app/`)

**Enhanced Features:**
- Fetches pipeline definitions from backend API
- Executes real pipeline processing using existing gRPC services
- Implements component dependency sorting for proper execution order
- Caches pipeline definitions for performance
- Supports resize, AI detection, and filter operations

**Key Methods:**
- `_get_pipeline_definition()`: Fetches pipeline from backend with caching
- `_execute_pipeline()`: Processes frames through defined pipeline steps
- `_execute_resize()`, `_execute_ai_detection()`, `_execute_filter()`: Execute individual components

### 2. Backend API Enhancement (`backend/app/api/camera_stream.py`)

**New Endpoint:**
```http
GET /api/camera-stream/v1/camera-stream/pipelines
```
Returns available pipelines suitable for real-time processing:
```json
{
  "pipelines": [
    {
      "id": "pipeline_123",
      "name": "Object Detection Pipeline",
      "description": "Real-time object detection with YOLO",
      "components": [
        {
          "name": "Resize",
          "type": "resize",
          "parameters": {"width": 640, "height": 480}
        },
        {
          "name": "AI Detection",
          "type": "ai_detection", 
          "parameters": {"model_name": "yolo11n", "confidence_threshold": 0.5}
        }
      ]
    }
  ],
  "supported_components": ["resize", "ai_detection", "filter"]
}
```

### 3. Kubernetes Configuration (`k8s/grpc/grpc-services.yaml`)

**Added Camera Stream Service:**
- Deployment: `camera-stream-grpc-service`
- Service discovery for backend API and gRPC services
- Environment variables for service endpoints
- Health checks and resource limits

## Usage

### 1. Create Pipeline in Web UI

1. Open ImageFlowCanvas Web interface
2. Navigate to Pipeline Builder
3. Create pipeline with supported components:
   - **Resize**: Image resizing operations
   - **AI Detection**: Object detection with YOLO models
   - **Filter**: Image filtering and enhancement
4. Save the pipeline

### 2. Real-time Camera Streaming

**WebSocket Connection:**
```javascript
const websocket = new WebSocket("ws://localhost:8000/v1/ws/camera-stream/camera1");

// Send video frame with pipeline specification
const frameMessage = {
  type: "frame",
  frame_data: base64EncodedImage,  // Base64 encoded JPEG/PNG
  pipeline_id: "pipeline_123",     // ID from Web UI
  timestamp_ms: Date.now(),
  width: 640,
  height: 480,
  processing_params: {
    model_name: "yolo11n",
    confidence_threshold: 0.5
  }
};

websocket.send(JSON.stringify(frameMessage));

// Receive processed results
websocket.onmessage = (event) => {
  const result = JSON.parse(event.data);
  console.log("Processed frame:", result);
  // result.detections contains AI detection results
  // result.processed_data contains processed image (if applicable)
};
```

**HTTP Test Endpoint:**
```bash
curl -X POST "http://localhost:8000/api/camera-stream/v1/camera-stream/test-frame" \
  -F "file=@test_image.jpg" \
  -F "pipeline_id=pipeline_123" \
  -F "source_id=test_camera"
```

### 3. Get Available Pipelines

```javascript
fetch('/api/camera-stream/v1/camera-stream/pipelines', {
  headers: {
    'Authorization': 'Bearer ' + authToken
  }
})
.then(response => response.json())
.then(data => {
  console.log('Available pipelines:', data.pipelines);
});
```

## Deployment

### Prerequisites
- K3s cluster running
- Existing gRPC services deployed (resize, ai-detection, filter)
- Backend API service running

### Deploy Camera Stream Service

```bash
# Apply K8s configuration
kubectl apply -f k8s/grpc/grpc-services.yaml

# Verify deployment
kubectl get pods -n image-processing
kubectl get services -n image-processing

# Check camera stream service
kubectl logs -f -n image-processing deployment/camera-stream-grpc-service
```

### Build and Deploy (if needed)

```bash
# Build camera stream service
cd services/camera-stream-grpc-app
docker build -t imageflow/camera-stream-grpc:latest .

# Import to K3s
sudo k3s ctr images import camera-stream-grpc.tar

# Deploy
kubectl rollout restart -n image-processing deployment/camera-stream-grpc-service
```

## Validation

Run the comprehensive validation script:

```bash
python validate_camera_stream_integration.py
```

This script will:
1. Authenticate with the backend
2. Fetch available pipelines or create a test pipeline
3. Test HTTP frame processing
4. Test WebSocket streaming
5. Validate end-to-end functionality

## Configuration

### Environment Variables

**Camera Stream Service:**
- `BACKEND_API_URL`: Backend API endpoint (default: `http://backend.default.svc.cluster.local:8000`)
- `RESIZE_GRPC_ENDPOINT`: Resize service endpoint
- `AI_DETECTION_GRPC_ENDPOINT`: AI detection service endpoint  
- `FILTER_GRPC_ENDPOINT`: Filter service endpoint
- `MAX_CONCURRENT_STREAMS`: Maximum concurrent camera streams (default: 10)
- `FRAME_SKIP_THRESHOLD`: Frame skip threshold in ms (default: 100)

**Backend API:**
- Existing database configuration for pipeline storage
- Authentication configuration for pipeline access

## Supported Pipeline Components

| Component Type | Description | Parameters |
|----------------|-------------|------------|
| `resize` | Image resizing | `width`, `height`, `maintain_aspect_ratio` |
| `ai_detection` | Object detection | `model_name`, `confidence_threshold`, `nms_threshold` |
| `filter` | Image filtering | `filter_type`, component-specific parameters |

## Error Handling

- **Pipeline Not Found**: Falls back to passthrough mode
- **gRPC Service Unavailable**: Returns error status in response
- **Invalid Frame Data**: Validates image format before processing
- **High Load**: Implements frame skipping based on age threshold

## Performance Considerations

- **Pipeline Caching**: 5-minute TTL for pipeline definitions
- **Persistent gRPC Connections**: Reuses connections to processing services
- **Frame Skipping**: Drops old frames under high load
- **Component Ordering**: Optimizes execution order (resize → AI detection → filter)

## Monitoring

Check service health:
```bash
# Service logs
kubectl logs -f -n image-processing deployment/camera-stream-grpc-service

# Health checks
curl http://localhost:8080/health

# Service metrics
kubectl top pods -n image-processing
```

## Troubleshooting

### Common Issues

1. **Pipeline Not Found**
   - Verify pipeline exists in Web UI
   - Check pipeline ID in client request
   - Ensure user has access to pipeline

2. **gRPC Connection Failures**
   - Verify gRPC services are running: `kubectl get pods -n image-processing`
   - Check service endpoints in environment variables
   - Review network policies and service discovery

3. **Processing Timeouts**
   - Check AI detection service load
   - Verify image format and size
   - Review timeout configurations

4. **WebSocket Connection Issues**
   - Verify backend API is accessible
   - Check authentication token
   - Review WebSocket proxy configuration

This integration provides a seamless experience where users can define processing pipelines once in the Web UI and use them for both batch and real-time processing scenarios.