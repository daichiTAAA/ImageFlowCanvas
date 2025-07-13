# YOLO11 Model for Triton Inference Server

This directory should contain the YOLO11 model file. Due to file size limitations, the actual model file is not included in this repository.

## Setup Instructions

1. Run the setup script to download and convert YOLO11n model:
   ```bash
   python scripts/setup-yolo11.py
   ```

Or manually:

1. Download YOLO11n.pt model:
   ```bash
   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt
   ```

2. Convert to ONNX format using ultralytics:
   ```python
   from ultralytics import YOLO
   model = YOLO('yolo11n.pt')
   model.export(format='onnx', imgsz=640, dynamic=False)
   ```

3. Rename the output file to `model.onnx` and place it in this directory: `models/yolo/1/model.onnx`

## Model Requirements

- Format: ONNX
- Input: images tensor with shape [batch_size, 3, 640, 640]  
- Output: predictions tensor with shape [batch_size, 84, 8400]
- Supported architecture: YOLO11n

## Model Configuration

The Triton configuration in `config.pbtxt` is set up for CPU inference. For GPU inference, modify the `instance_group` section to use `KIND_GPU`.

## YOLO11 Features

YOLO11 provides improved accuracy and performance compared to previous YOLO versions:
- Enhanced object detection capabilities
- Better small object detection
- Optimized for both accuracy and speed
- Support for 80 COCO classes