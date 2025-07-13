# YOLO Model for Triton Inference Server

This directory should contain the YOLO model file. Due to file size limitations, the actual model file is not included in this repository.

## Setup Instructions

1. Download a YOLOv8 ONNX model (e.g., yolov8n.onnx, yolov8s.onnx, etc.)
2. Rename the model file to `model.onnx`
3. Place it in this directory: `models/yolo/1/model.onnx`

## Model Requirements

- Format: ONNX
- Input: images tensor with shape [batch_size, 3, 640, 640]
- Output: predictions tensor with shape [batch_size, 84, 8400]
- Supported architectures: YOLOv8n, YOLOv8s, YOLOv8m, YOLOv8l, YOLOv8x

## Download Example

```bash
# Download YOLOv8n ONNX model from Ultralytics
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx -O models/yolo/1/model.onnx
```

## Note

The Triton configuration in `config.pbtxt` is set up for CPU inference. For GPU inference, modify the `instance_group` section to use `KIND_GPU`.