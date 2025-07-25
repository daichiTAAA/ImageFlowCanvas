FROM python:3.12-slim

WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をインストール
COPY backend/requirements.txt .
RUN pip install --upgrade pip
RUN pip install setuptools==69.5.1 wheel
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY backend/app/ ./app/

# 生成されたprotoファイルをコピー
COPY backend/generated/python/ ./

# ポート8000を公開
EXPOSE 8000

# アプリケーションを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]