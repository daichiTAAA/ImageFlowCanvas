FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
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

# Expose HTTP port
EXPOSE 8080

# Set default environment variables
ENV HTTP_PORT=8080
ENV HOST=0.0.0.0
ENV RESIZE_GRPC_ENDPOINT=resize-grpc-service:9090
ENV AI_DETECTION_GRPC_ENDPOINT=ai-detection-grpc-service:9090
ENV FILTER_GRPC_ENDPOINT=filter-grpc-service:9090

# Run the gateway
CMD ["python", "grpc_gateway.py"]