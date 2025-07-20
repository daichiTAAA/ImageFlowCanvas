#!/bin/bash
# ディスク容量クリーンアップスクリプト

echo "=== ディスク容量クリーンアップ開始 ==="
echo "実行前のディスク使用量:"
df -h /

echo ""
echo "=== 1. containerdの不要イメージを削除 ==="
sudo k3s crictl rmi --prune

echo ""
echo "=== 2. 停止中のコンテナを削除 ==="
sudo k3s crictl ps -a | grep Exited | awk '{print $1}' | xargs -r sudo k3s crictl rm

echo ""
echo "=== 3. 不要なタグ無しイメージを削除 ==="
sudo k3s crictl images | grep '<none>' | awk '{print $3}' | xargs -r sudo k3s crictl rmi

echo ""
echo "=== 4. Dockerキャッシュをクリア ==="
sudo docker system prune -af --volumes 2>/dev/null || echo "Dockerが利用できません（正常）"

echo ""
echo "=== 5. APTキャッシュをクリア ==="
sudo apt autoremove -y
sudo apt autoclean

echo ""
echo "=== 6. 大きなログファイルをローテート ==="
sudo find /var/log -name "*.log" -type f -size +50M -exec truncate -s 10M {} \;

echo ""
echo "=== クリーンアップ完了 ==="
echo "実行後のディスク使用量:"
df -h /

echo ""
echo "=== containerdイメージ一覧 ==="
sudo k3s crictl images
