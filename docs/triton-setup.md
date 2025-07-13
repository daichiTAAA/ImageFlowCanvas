# Triton Inference Server Setup Guide

## Overview

This guide explains how to set up and use Triton Inference Server for YOLO11 object detection in the ImageFlowCanvas project.

## Architecture

The Triton Inference Server serves as the AI inference backend, providing:
- High-performance YOLO11 model inference
- Model versioning and management
- Health monitoring and metrics
- Support for multiple model formats (ONNX, PyTorch, TensorRT)

## Setup Instructions

### 1. Model Preparation

Download and convert YOLO11 model and place it in the correct directory:

```bash
# Use the automated setup script (recommended)
python scripts/setup-yolo11.py

# Or manually:
# 1. Create the model directory structure
mkdir -p models/yolo/1

# 2. Download and convert YOLO11n model
pip install ultralytics
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt').export(format='onnx', imgsz=640, dynamic=False)"
mv yolo11n.onnx models/yolo/1/model.onnx
```

### 2. Development Environment

#### Option A: Docker Compose (Recommended for development)

```bash
# Start all services including Triton
docker-compose up -d

# Check Triton server status
curl http://localhost:8001/v2/health/ready
```

#### Option B: Kubernetes (K3s)

```bash
# Setup K3s and Argo Workflows
sudo ./scripts/setup-k3s.sh

# Start development environment
./scripts/dev-start.sh

# Setup port forwarding
./scripts/port-forward.sh
```

### 3. Model Configuration

The model configuration is defined in `models/yolo/config.pbtxt`:

```protobuf
name: "yolo"
platform: "onnxruntime_onnx"
max_batch_size: 8
input [
  {
    name: "images"
    data_type: TYPE_FP32
    dims: [ 3, 640, 640 ]
  }
]
output [
  {
    name: "output0"
    data_type: TYPE_FP32
    dims: [ 84, 8400 ]
  }
]
```

## Model Format Requirements

### Input
- **Name**: `images`
- **Type**: `FP32`
- **Shape**: `[batch_size, 3, 640, 640]`
- **Format**: RGB image data normalized to [0, 1]

### Output
- **Name**: `output0`
- **Type**: `FP32`
- **Shape**: `[batch_size, 84, 8400]`
- **Format**: YOLOv8 detection format (4 bbox coords + 80 class probabilities)

## API Usage

### Health Check

```bash
# Check if server is live
curl http://localhost:8001/v2/health/live

# Check if server is ready
curl http://localhost:8001/v2/health/ready

# Check model status
curl http://localhost:8001/v2/models/yolo/ready
```

### Model Information

```bash
# Get model metadata
curl http://localhost:8001/v2/models/yolo

# Get model configuration
curl http://localhost:8001/v2/models/yolo/config
```

### Inference

The inference is handled automatically by the backend API through the `TritonYOLOClient` class.

## Troubleshooting

### Common Issues

1. **Model not loading**
   - Check if the model file exists at `models/yolo/1/model.onnx`
   - Verify the model format is correct (ONNX for YOLOv8)
   - Check Triton logs: `docker logs <triton-container-id>`

2. **Out of memory errors**
   - Reduce batch size in `config.pbtxt`
   - Use the YOLO11n model (already optimized for efficiency)
   - Adjust container memory limits

3. **Connection errors**
   - Verify Triton server is running: `curl http://localhost:8001/v2/health/ready`
   - Check network connectivity between backend and Triton
   - Verify environment variable `TRITON_URL` is set correctly

### Performance Optimization

1. **GPU Support**
   - Install nvidia-docker runtime
   - Uncomment GPU configuration in `docker-compose.yml`
   - Update `config.pbtxt` to use `KIND_GPU`

2. **Model Optimization**
   - Convert ONNX to TensorRT for better GPU performance
   - Use FP16 precision for faster inference
   - Enable dynamic batching

### Monitoring

1. **Metrics Endpoint**
   ```bash
   curl http://localhost:8003/metrics
   ```

2. **Logs**
   ```bash
   # Docker Compose
   docker-compose logs triton
   
   # Kubernetes
   kubectl logs deployment/triton-inference-server -n default
   ```

## Environment Variables

- `TRITON_URL`: Triton server endpoint (default: "localhost:8000")
- `YOLO_MODEL_NAME`: Model name in Triton (default: "yolo")
- `YOLO_MODEL_VERSION`: Model version (default: "1")

## Advanced Configuration

### Multiple Model Versions

```bash
# Add a new model version
mkdir -p models/yolo/2
cp your-new-model.onnx models/yolo/2/model.onnx

# Triton will automatically detect and load the new version
```

### Custom Model Repository

```bash
# Mount external model repository
docker run -v /path/to/models:/models tritonserver --model-repository=/models
```

### TensorRT Optimization

```bash
# Convert ONNX to TensorRT (requires NVIDIA GPU)
trtexec --onnx=yolo11n.onnx --saveEngine=yolo11n.trt --fp16
```

## References

- [Triton Inference Server Documentation](https://docs.nvidia.com/deeplearning/triton-inference-server/)
- [YOLO11 Model Zoo](https://github.com/ultralytics/ultralytics)
- [Ultralytics Documentation](https://docs.ultralytics.com/)
- [ONNX Model Format](https://onnx.ai/)