#!/bin/bash

# Protocol Buffers code generation script for ImageFlowCanvas gRPC services

set -e

PROTO_DIR="/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/proto"
OUT_DIR="/home/runner/work/ImageFlowCanvas/ImageFlowCanvas/generated"

# Create output directories
mkdir -p "$OUT_DIR/python"
mkdir -p "$OUT_DIR/go"

echo "Generating Python gRPC code..."

# Generate Python code
python -m grpc_tools.protoc \
    --proto_path="$PROTO_DIR" \
    --python_out="$OUT_DIR/python" \
    --grpc_python_out="$OUT_DIR/python" \
    imageflow/v1/common.proto \
    imageflow/v1/resize.proto \
    imageflow/v1/ai_detection.proto \
    imageflow/v1/filter.proto

echo "Python gRPC code generation completed."

# Create __init__.py files for Python package structure
find "$OUT_DIR/python" -type d -exec touch {}/__init__.py \;

echo "Protocol Buffers code generation completed successfully!"
echo "Python files: $OUT_DIR/python"