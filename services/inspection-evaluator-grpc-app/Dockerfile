FROM imageflow-base:latest

ARG PROXY
ENV PROXY=$PROXY

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --proxy=$PROXY --no-cache-dir -r requirements.txt

# Copy generated protobuf stubs
COPY generated/python /app/generated/python

# Copy application source
COPY src/ .

# Make generated available on PYTHONPATH
ENV PYTHONPATH="/app/generated/python"

# Install grpc health probe
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

EXPOSE 9090

ENV GRPC_PORT=9090
ENV DATABASE_URL=postgresql+asyncpg://imageflow:imageflow123@postgres:5432/imageflow

ENV no_proxy="localhost,0.0.0.0"
ENV NO_PROXY=${no_proxy}

CMD ["python", "evaluator_grpc_server.py"]

