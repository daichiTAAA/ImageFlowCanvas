# ベースイメージとして軽量なPythonイメージを選択
FROM python:3.11-slim

# ワーキングディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 依存ライブラリをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# スクリプトをコンテナにコピー
COPY src/resize.py .

# 実行権限を付与
RUN chmod +x resize.py

# コンテナ実行時のデフォルトコマンド
ENTRYPOINT ["python", "resize.py"]