FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8085 \
    MLRUN_PROJECT_DIR=/workspace/mlrun

WORKDIR /opt/mlrun-app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 libsm6 libxext6 libxrender1 \
    curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Python deps (pin major to keep lightweight)
RUN pip install --no-cache-dir \
    "mlrun>=1.6,<2.0" \
    "fastapi>=0.110,<1.0" \
    "uvicorn[standard]>=0.29,<1.0" \
    pillow requests pandas

# Copy minimal app code; volume mount can override at runtime
COPY mlrun /opt/mlrun-app/mlrun

EXPOSE 8085

CMD ["python", "-u", "mlrun/serving/entrypoint.py"]

