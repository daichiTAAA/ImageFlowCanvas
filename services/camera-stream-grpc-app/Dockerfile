FROM python:3.11-slim

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

# Copy source code
COPY src/ .

# Expose gRPC port
EXPOSE 9090

# Run the server
CMD ["python", "camera_stream_grpc_server.py"]