#!/bin/bash

# エラー時にスクリプトを終了
set -e

echo "ベースイメージのビルドを開始します..."

# ベースイメージをビルド
if docker build \
  --build-arg PROXY=${http_proxy} \
  -f container/Dockerfile.baseimage \
  -t imageflow-base:latest \
  .; then
  echo "✅ ベースイメージ 'imageflow-base:latest' のビルドが完了しました"
else
  echo "❌ エラー: ベースイメージのビルドに失敗しました"
  exit 1
fi
