# ベースイメージを使用（事前にビルドしておく）
FROM imageflow-base:latest

# プロキシ設定を引き継ぎ
ARG PROXY
ENV PROXY=$PROXY

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --proxy=$PROXY --no-cache-dir -r requirements.txt

# Copy generated protobuf files
COPY generated/python /app/generated/python

# Copy source code
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

ENV no_proxy="localhost,0.0.0.0"
ENV NO_PROXY=${no_proxy}

# Run the server
CMD ["python", "camera_stream_grpc_server.py"]