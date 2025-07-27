#!/bin/bash

# Protocol Buffers code generation script for ImageFlowCanvas gRPC services

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="$BASE_DIR/proto"
OUT_DIR="$BASE_DIR/generated"

# Create output directories
mkdir -p "$OUT_DIR/python"
mkdir -p "$OUT_DIR/go"

echo "Generating Python gRPC code..."

# Generate Python code for general use
python -m grpc_tools.protoc \
    --proto_path="$PROTO_DIR" \
    --python_out="$OUT_DIR/python" \
    --grpc_python_out="$OUT_DIR/python" \
    imageflow/v1/common.proto \
    imageflow/v1/resize.proto \
    imageflow/v1/ai_detection.proto \
    imageflow/v1/filter.proto \
    imageflow/v1/camera_stream.proto \
    imageflow/v1/inspection.proto

# Generate Python code specifically for backend
python -m grpc_tools.protoc \
    --proto_path="$PROTO_DIR" \
    --python_out="$BASE_DIR/backend/generated/python" \
    imageflow/v1/common.proto \
    imageflow/v1/resize.proto \
    imageflow/v1/ai_detection.proto \
    imageflow/v1/filter.proto \
    imageflow/v1/camera_stream.proto \
    imageflow/v1/inspection.proto

echo "Python gRPC code generation completed."

# Create __init__.py files for Python package structure
find "$OUT_DIR/python" -type d -exec touch {}/__init__.py \;

echo "Protocol Buffers code generation completed successfully!"
echo "Python files: $OUT_DIR/python"