FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy generated proto files
COPY ../../generated/python /app/generated/python

# Set Python path to include generated code
ENV PYTHONPATH="/app/generated/python"

# Copy source code
COPY src/ .

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
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Expose gRPC port
EXPOSE 9090

# Run the server
CMD ["python", "camera_stream_grpc_server.py"]