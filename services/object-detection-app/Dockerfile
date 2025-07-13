FROM python:3.11-slim

WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# スクリプトをコンテナにコピー
COPY src/detect.py .

# 実行権限を付与
RUN chmod +x detect.py

# 事前にモデルをダウンロード（オプション）
RUN python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"

ENTRYPOINT ["python", "detect.py"]