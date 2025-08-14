FROM python:3.12-slim

# プロキシ設定を引き継ぎ
ARG PROXY
ENV PROXY=$PROXY
ENV http_proxy=$PROXY
ENV https_proxy=$PROXY

WORKDIR /app

# システムの依存関係をインストール
# プロキシが設定されている場合はapt用の設定も追加
RUN if [ -n "$PROXY" ]; then \
    echo "Acquire::http::proxy \"$PROXY\";" > /etc/apt/apt.conf.d/01proxy && \
    echo "Acquire::https::proxy \"$PROXY\";" >> /etc/apt/apt.conf.d/01proxy; \
    fi && \
    apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をインストール
COPY backend/requirements.txt .
RUN pip install --proxy=$PROXY --upgrade pip
RUN pip install --proxy=$PROXY setuptools==69.5.1 wheel
# NumPy互換性の問題を避けるため、NumPy を先にインストール
RUN pip install --proxy=$PROXY "numpy<2.0,>=1.24.3"
RUN pip install --proxy=$PROXY --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY backend/app/ ./app/

# 生成されたprotoファイルをコピー
COPY backend/generated/python/ ./

# ポート8000を公開
EXPOSE 8000

ENV no_proxy="localhost,0.0.0.0"
ENV NO_PROXY=${no_proxy}

# アプリケーションを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]