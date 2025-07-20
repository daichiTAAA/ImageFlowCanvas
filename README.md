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

### K3sへのデプロイ

#### 初回デプロイ
K3sにデプロイするには、以下のコマンドを実行します。
```bash
# アプリケーション（Backend & Frontend）のデプロイ
kubectl apply -f k8s/core/app-deployments.yaml
```

#### デプロイメントファイルの変更を反映
設定ファイル（YAML）を変更した場合：
```bash
# 変更をクラスターに適用
kubectl apply -f k8s/core/app-deployments.yaml

# デプロイメントの状態を確認
kubectl get deployments
kubectl get pods
```

#### コンテナイメージの変更を反映
新しいコンテナイメージを反映する場合は、以下の手順を実行します：

**方法1: イメージをK3sに直接インポート（推奨）**
```bash
# 1. メインアプリケーションイメージの再ビルド
docker build -t imageflow/frontend:latest ./frontend/
docker build -t imageflow/backend:latest ./backend/

# 2. 画像処理サービスイメージの再ビルド
docker build -t resize-app:latest ./services/resize-app/
docker build -t object-detection-app:latest ./services/object-detection-app/
docker build -t filter-app:latest ./services/filter-app/

# 3. K3sにイメージをインポート
docker save imageflow/frontend:latest | sudo k3s ctr images import -
docker save imageflow/backend:latest | sudo k3s ctr images import -
docker save resize-app:latest | sudo k3s ctr images import -
docker save object-detection-app:latest | sudo k3s ctr images import -
docker save filter-app:latest | sudo k3s ctr images import -

# 4. デプロイメントを再起動（imagePullPolicy: Never の場合）
kubectl rollout restart deployment/frontend deployment/backend
# 注意: 画像処理サービスはArgo Workflowsで動的に実行されるため、
# デプロイメントの再起動は不要です。次回のワークフロー実行時に自動的に新しいイメージが使用されます。
```

**方法2: imagePullPolicyを一時的に変更**
```bash
# 1. メインアプリケーションイメージの再ビルド
docker build -t imageflow/frontend:latest ./frontend/
docker build -t imageflow/backend:latest ./backend/

# 2. 画像処理サービスイメージの再ビルド
docker build -t resize-app:latest ./services/resize-app/
docker build -t object-detection-app:latest ./services/object-detection-app/
docker build -t filter-app:latest ./services/filter-app/

# 3. デプロイメントのimagePullPolicyをAlwaysに変更
kubectl patch deployment frontend -p='{"spec":{"template":{"spec":{"containers":[{"name":"frontend","imagePullPolicy":"Always"}]}}}}'
kubectl patch deployment backend -p='{"spec":{"template":{"spec":{"containers":[{"name":"backend","imagePullPolicy":"Always"}]}}}}'

# 4. デプロイメントを再起動
kubectl rollout restart deployment/frontend deployment/backend

# 5. 必要に応じてimagePullPolicyをNeverに戻す
kubectl patch deployment frontend -p='{"spec":{"template":{"spec":{"containers":[{"name":"frontend","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment backend -p='{"spec":{"template":{"spec":{"containers":[{"name":"backend","imagePullPolicy":"Never"}]}}}}'
```

**一括ビルドとインポートのスクリプト例**:
```bash
#!/bin/bash
# 全サービスの一括ビルド・インポートスクリプト

echo "Building all container images..."

# メインアプリケーション
docker build -t imageflow/frontend:latest ./frontend/
docker build -t imageflow/backend:latest ./backend/

# 画像処理サービス
docker build -t resize-app:latest ./services/resize-app/
docker build -t object-detection-app:latest ./services/object-detection-app/
docker build -t filter-app:latest ./services/filter-app/

echo "Importing images to K3s..."

# K3sにインポート
docker save imageflow/frontend:latest | sudo k3s ctr images import -
docker save imageflow/backend:latest | sudo k3s ctr images import -
docker save resize-app:latest | sudo k3s ctr images import -
docker save object-detection-app:latest | sudo k3s ctr images import -
docker save filter-app:latest | sudo k3s ctr images import -

echo "Restarting deployments..."

# メインアプリケーションの再起動
kubectl rollout restart deployment/frontend deployment/backend

echo "All images updated successfully!"
```

#### 画像処理サービスについて

**services/フォルダ内の各サービス**:
- **resize-app**: 画像リサイズ処理サービス
- **object-detection-app**: YOLO11を使用した物体検知サービス
- **filter-app**: 画像フィルタ処理サービス

これらのサービスはArgo Workflowsによって動的に実行されるため、常駐デプロイメントはありません。
ワークフロー実行時にPodとして起動し、処理完了後に自動的に終了します。

**利用可能なイメージの確認**:
```bash
# K3s内のイメージ確認
sudo k3s ctr images list | grep -E "(resize-app|object-detection-app|filter-app)"

# 実行中のワークフロー確認
kubectl get workflows -n argo

# ワークフローのログ確認（実行中の場合）
argo logs <workflow-name> -n argo
```

#### デプロイメントの確認
```bash
# ポッドの状態確認
kubectl get pods -o wide

# メインアプリケーションのログ確認
kubectl logs -f deployment/frontend
kubectl logs -f deployment/backend

# サービスの確認
kubectl get services

# Argo Workflowsの状態確認
kubectl get pods -n argo
kubectl get workflowtemplates -n argo
```

### デプロイメントファイルの変更を反映する場合
deploymentファイルの変更をK3sクラスターに適用するには、以下のコマンドを実行します。
```bash
kubectl apply -f k8s/core/app-deployments.yaml
```

## トラブルシューティング

### パイプラインが保存されてもダッシュボードに表示されない

**症状**: パイプラインビルダーでパイプラインを保存したが、ダッシュボードページで「パイプラインがありません」と表示される

**原因と対処法**:

1. **認証状態の確認**
   ```bash
   # ブラウザでF12キーを押して開発者ツールを開き、Consoleタブで確認
   # 「Not authenticated」エラーが出ている場合は再ログインが必要
   ```

2. **ブラウザキャッシュのクリア**
   ```bash
   # Ctrl+F5 (Windows/Linux) または Cmd+Shift+R (Mac) でハードリフレッシュ
   # または開発者ツール > Application > Storage > Clear storage
   ```

3. **APIの直接テスト**
   ```bash
   # ログインしてトークンを取得
   TOKEN=$(curl -s -X POST -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}' \
     http://localhost:3000/api/auth/login | \
     grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

   # パイプライン一覧を取得
   curl -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/pipelines/
   ```

4. **バックエンドポッドの確認**
   ```bash
   # バックエンドポッドが複数ある場合、データが異なるポッドに保存されている可能性
   kubectl get pods -l app=backend
   kubectl logs -f deployment/backend
   ```


### フロントエンドの変更が反映されない（開発時）

**症状**: フロントエンドのコードを修正してDockerイメージを再ビルド・再デプロイしても、ブラウザで古いコードが実行される

**原因**: ブラウザがJavaScriptファイルをキャッシュしているため、新しいコードが読み込まれない

**対処法**:

1. **ハードリフレッシュ（推奨）**
   - **Chrome/Edge**: `Ctrl+Shift+R` (Windows/Linux) または `Cmd+Shift+R` (Mac)
   - **Firefox**: `Ctrl+F5` (Windows/Linux) または `Cmd+Shift+R` (Mac)

2. **開発者ツールでキャッシュ無効化**
   ```
   1. F12キーで開発者ツールを開く
   2. Networkタブに移動
   3. "Disable cache"にチェックを入れる
   4. ページをリロード（開発者ツールが開いている間はキャッシュが無効化される）
   ```

3. **完全なキャッシュクリア**
   ```
   1. F12キーで開発者ツールを開く
   2. Applicationタブ（Chrome）またはStorageタブ（Firefox）に移動
   3. "Clear storage"をクリック
   4. ページをリロード
   ```

4. **実際のファイル内容確認**
   ```
   1. F12キーで開発者ツールを開く
   2. Sourcesタブに移動
   3. 修正したファイル（例：api.ts）を開いて内容を確認
   4. 修正した内容が反映されていない場合は上記のキャッシュクリア手順を実行
   ```

**開発時のベストプラクティス**:
- フロントエンドの変更をテストする際は、必ずハードリフレッシュを実行
- 開発者ツールの「Disable cache」を有効にしてブラウジング
- APIエンドポイントのURLに末尾スラッシュが不要な場合の修正後は、特にキャッシュクリアが重要

