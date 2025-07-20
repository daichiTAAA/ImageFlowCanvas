FROM python:3.11-slim

# Install system dependencies for OpenCV and JPEG support
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libjpeg62-turbo-dev \
    libpng-dev \
    libtiff5-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force reinstall OpenCV with proper JPEG support
RUN pip uninstall -y opencv-python opencv-python-headless && \
    pip install --no-cache-dir opencv-contrib-python

# Copy generated protobuf files
COPY generated/python /app/generated/python

# Copy application source
COPY src/ .

# Set Python path to include generated code
ENV PYTHONPATH="/app/generated/python"

# Install grpc health probe with architecture detection
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

# Expose gRPC port
EXPOSE 9090

# Set default environment variables
ENV GRPC_PORT=9090
ENV MINIO_ENDPOINT=minio-service:9000
ENV MINIO_ACCESS_KEY=minioadmin
ENV MINIO_SECRET_KEY=minioadmin

# Run the gRPC server
CMD ["python", "resize_grpc_server.py"]