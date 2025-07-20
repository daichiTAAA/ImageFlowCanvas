FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy generated protobuf files
COPY generated/python /app/generated/python

# Copy application source
COPY src/ .

# Set Python path to include generated code
ENV PYTHONPATH="/app/generated/python"

# Install grpc health probe
RUN apt-get update && apt-get install -y wget && \
    wget -qO /bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.34/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Expose gRPC port
EXPOSE 9090

# Set default environment variables
ENV GRPC_PORT=9090
ENV MINIO_ENDPOINT=minio-service:9000
ENV MINIO_ACCESS_KEY=minioadmin
ENV MINIO_SECRET_KEY=minioadmin
ENV TRITON_GRPC_URL=triton-service:8001

# Run the gRPC server
CMD ["python", "ai_detection_grpc_server.py"]