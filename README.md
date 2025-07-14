# ImageFlowCanvas

ImageFlowCanvasは、Webインターフェースを通じて画像処理の各機能を「部品」として組み合わせ、動的な処理パイプラインを構築・実行できるクラウドネイティブシステムです。

## 特徴

- **マイクロサービスアーキテクチャ**: 各処理コンポーネントを独立したサービスとして構築
- **動的パイプライン構築**: Web UIを通じて処理フローを視覚的に設計
- **Kubernetesネイティブ**: K3s + Argo Workflowsによる堅牢な実行基盤
- **リアルタイム監視**: WebSocketによる進捗のリアルタイム表示
- **スケーラブル**: 処理負荷に応じた自動スケーリング

## アーキテクチャ

### 技術スタック

- **Frontend**: React + TypeScript + Material-UI
- **Backend**: FastAPI + Python
- **Message Queue**: Apache Kafka
- **Workflow Engine**: Argo Workflows
- **Container Platform**: Kubernetes (K3s)
- **Object Storage**: MinIO
- **AI Inference**: Triton Inference Server
- **Processing Services**: OpenCV, PyTorch, YOLO11

## セットアップ

開発環境のセットアップは、お使いのOS（Linux, macOS, Windows）に応じて手順が異なります。

### 共通設定（全OS共通）

以下の手順は、Linux（直接）、macOS（Lima VM内）、Windows（WSL2内）すべてで実行します。

```bash
# アーキテクチャの確認
uname -m  # x86_64 または aarch64 を確認

# miniforgeのインストール（アーキテクチャ別）
# x86_64の場合
curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -o miniforge.sh

# ARM64 (aarch64) の場合
# curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh -o miniforge.sh

bash miniforge.sh -b -p $HOME/miniforge
echo "export PATH=\$HOME/miniforge/bin:\$PATH" >> ~/.bashrc
source ~/.bashrc
conda init

# conda環境の作成
conda create -n imageflowcanvas python=3.12 -y
conda activate imageflowcanvas

# 必要なPythonパッケージのインストール
pip install requests ultralytics

# YOLO11 ONNXモデルをセットアップ（自動ダウンロード・変換）
python scripts/setup-yolo11.py

# K3sとArgo Workflowsのセットアップスクリプトを実行
sudo ./scripts/setup-k3s.sh

# 立ち上がっているか確認
kubectl get pods -A

# 開発用サーバーの起動
./scripts/dev-start.sh

# 別のターミナルを開いて、ポートフォワーディングを開始
./scripts/port-forward.sh
```

### Linux環境（直接インストール）

Linuxでは、上記の「共通設定」をそのまま実行してください。

### macOS環境（Lima使用）

macOSでは、Lima VMを使用してLinux環境を作成し、その中で開発を行います。

**Lima固有の準備手順**:
1. **Limaのインストール**
   ```bash
   # Homebrewでインストール
   brew install lima
   
   # または手動インストール
   curl -fsSL https://get.lima.sh | sh
   ```

2. **Ubuntu VMの作成と起動**
   ```bash
   # Ubuntu 24.04 VMを作成
   limactl create --name=k3s template://ubuntu-lts
   
   # VMを起動
   limactl start k3s
   ```

3. **ポートフォワーディング設定**
   ```bash
   # Lima VM設定ファイルを編集（ホストマシンで実行）
   limactl stop k3s
   limactl edit k3s
   ```
   
   以下の `portForwards` 設定を追加します。これにより、ホストPCからVM内のサービスにアクセスできるようになります。
   ```yaml
   portForwards:
     - guestPort: 3000 # Frontend
       hostPort: 3000
     - guestPort: 8000 # Backend
       hostPort: 8000
     - guestPort: 9001 # MinIO Console
       hostPort: 9001
     - guestPort: 2746 # Argo Workflows UI
       hostPort: 2746
   ```

4. **VM再起動と共通設定の実行**
   ```bash
   # VM再起動
   limactl stop k3s
   limactl start k3s

   # VMにシェル接続
   limactl shell k3s
   
   # VM内でプロジェクトをクローン
   cd ~
   git clone <your-repo-url>
   cd ~/ImageFlowCanvas
   
   # ここで「共通設定」の手順をすべて実行
   ```

   * 【参考】VSCode Remote-SSHでLima VMに接続する方法
     1. VSCode拡張機能「Remote - SSH」をインストール
     2. ターミナルで下記コマンドを実行し、SSH設定内容を確認
        ```bash
        limactl show-ssh k3s
        ```
     3. 出力内容を `~/.ssh/config` に追記
     4. VSCodeで「Remote-SSH: Connect to Host...」を実行し、`lima-k3s` を選択

### Windows環境（WSL2使用）

WindowsではWSL2を使用してLinux環境を作成し、その中で開発を行います。

**WSL2固有の準備手順**:
1. **WSL2のセットアップ**
   ```bash
   # PowerShellで実行
   wsl --install Ubuntu-22.04
   ```

2. **WSL2での共通設定の実行**
   ```bash
   # WSL2シェルを起動し、「共通設定」の手順をすべて実行
   # プロジェクトを適切なディレクトリにクローンしてから実行してください
   ```

### アクセスポイント

セットアップ完了後、以下のURLにブラウザでアクセスしてください。

- **Frontend**: http://localhost:3000
- **Backend API (Swagger UI)**: http://localhost:8000/docs
- **Argo Workflows UI**: http://localhost:2746
- **MinIO Console**: http://localhost:9001 (ID: `minioadmin`, PW: `minioadmin`)

### 使用方法

1. **ログイン**: admin/admin123 または user/user123
2. **パイプライン作成**: コンポーネントをドラッグ&ドロップで配置
3. **実行**: 画像をアップロードしてパイプラインを実行
4. **監視**: リアルタイムで進捗を確認


## 開発ガイド

### ⚠️ Lima VM使用時の注意事項

Lima VMでDockerビルドを行う際は、以下の点にご注意ください：

#### リソース不足でVMがスタックする場合
```bash
# Dockerキャッシュを定期的にクリア
sudo docker system prune -af --volumes

# ディスク使用量の確認
df -h
sudo docker system df
```

#### Lima VM設定の最適化
Lima VMの設定ファイル（`~/.lima/k3s/lima.yaml`）で以下を調整することを推奨：

```yaml
# CPUとメモリの増加
cpus: 4
memory: "8GiB"

# ディスク容量の増加
disk: "100GiB"
```

設定変更後はVMの再起動が必要：
```bash
limactl stop k3s
limactl start k3s
```

### コンテナイメージのビルド
各サービスのDockerイメージをビルドするには、リポジトリのルートディレクトリから以下のコマンドを実行します。

```bash
# ビルド前にディスク容量を確認
df -h

# Frontend
docker build -f frontend/Dockerfile -t imageflow/frontend:latest frontend/

# Backend  
docker build -f backend/Dockerfile -t imageflow/backend:latest backend/

# ビルド後の不要なキャッシュを削除
docker system prune -f
```