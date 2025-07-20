# ImageFlowCanvas

ImageFlowCanvasは、Webインターフェースを通じて画像処理の各機能を「部品」として組み合わせ、動的な処理パイプラインを構築・実行できるクラウドネイティブシステムです。

## 特徴

- **高性能gRPCアーキテクチャ**: パイプライン処理時間を60-94秒から1-3秒に短縮（95%以上の改善）
- **マイクロサービスアーキテクチャ**: 各処理コンポーネントを独立したサービスとして構築
- **動的パイプライン構築**: Web UIを通じて処理フローを視覚的に設計
- **Kubernetesネイティブ**: K3s + 直接gRPC呼び出しによる堅牢な実行基盤
- **リアルタイム監視**: WebSocketによる進捗のリアルタイム表示
- **スケーラブル**: 処理負荷に応じた自動スケーリング

## アーキテクチャ

### 高性能gRPCアーキテクチャ

ImageFlowCanvasは、従来のPodベースの実行方式から、持続的なgRPCサービスを利用したアーキテクチャに移行し、大幅な性能向上を実現しています。

#### パフォーマンス改善

| 項目                     | 従来（Pod方式）     | 新方式（gRPC）      | 改善効果          |
| ------------------------ | ------------------- | ------------------- | ----------------- |
| Pod起動時間              | 30-50秒             | 0秒（常駐サービス） | **-50秒**         |
| 通信オーバーヘッド       | HTTP/1.1: 100-200ms | gRPC: 20-50ms       | **-150ms**        |
| 処理時間                 | 15-20秒             | 1-2秒               | **-18秒**         |
| **合計パイプライン時間** | **60-94秒**         | **1-3秒**           | **95%以上の短縮** |

#### gRPCコンポーネント

- **Protocol Buffers**: 型安全で高性能な通信スキーマ
- **gRPCサービス**: リサイズ、AI検知、フィルタ処理の常駐サービス
- **gRPCゲートウェイ**: HTTP-to-gRPC変換による高性能通信
- **バイナリプロトコル**: 通信オーバーヘッドを50-70%削減

### 技術スタック

- **Frontend**: React + TypeScript + Material-UI
- **Backend**: FastAPI + Python
- **Message Queue**: Apache Kafka
- **Pipeline Execution**: Direct gRPC calls to processing services
- **Container Platform**: Kubernetes (K3s)
- **Object Storage**: MinIO
- **AI Inference**: Triton Inference Server
- **Processing Services**: OpenCV, PyTorch, YOLO11
- **Communication**: gRPC + Protocol Buffers
- **Service Gateway**: gRPC Gateway for HTTP compatibility

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

# gRPC開発用パッケージのインストール
pip install grpcio grpcio-tools

# YOLO11 ONNXモデルをセットアップ（自動ダウンロード・変換）
python scripts/setup-yolo11.py

# gRPCサービス用Protocol Buffersの生成
./scripts/generate_protos.sh

# フロントエンドとバックエンドのビルドとデプロイ
DEPLOY=true ./scripts/build_web_services.sh

# gRPCサービスのビルドとデプロイ
DEPLOY=true ./scripts/build_grpc_services.sh

# ⚠️ エラーが発生した場合
# - `grpc_tools`モジュールエラー: pip install grpcio grpcio-tools
# - Protocol Buffers生成エラー: ./scripts/generate_protos.sh を再実行
# - Docker buildエラー: 生成されたファイルの確認 ls -la generated/python/

# K3sと直接gRPC実行基盤のセットアップスクリプトを実行
sudo ./scripts/setup-k3s.sh

# 立ち上がっているか確認
kubectl get pods -A

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

**ポートフォワーディング経由（推奨）**:
- **Frontend**: http://localhost:3000
- **Backend API (Swagger UI)**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (ID: `minioadmin`, PW: `minioadmin`)

**NodePort経由（直接アクセス）**:
- **Frontend**: http://localhost:30080 （同じノードからのアクセス時）

### 使用方法

1. **ログイン**: admin/admin123 または user/user123
2. **パイプライン作成**: コンポーネントをドラッグ&ドロップで配置
3. **実行**: 画像をアップロードしてパイプラインを実行（1-3秒で完了）
4. **監視**: リアルタイムで進捗を確認

### gRPCサービスのテスト

高性能gRPCアーキテクチャの動作確認：

```bash
# gRPCサービスの動作テスト
./scripts/test_grpc_services.py

# 個別サービスの動作確認
kubectl get pods -n image-processing
kubectl logs -n image-processing deployment/resize-grpc-service
```


## 開発ガイド

### ⚠️ Lima VM使用時の注意事項

Lima VMでDockerビルドを行う際は、以下の点にご注意ください：

#### リソース不足でVMがスタックする場合

**自動クリーンアップスクリプトを使用（推奨）**:
```bash
# 包括的なディスククリーンアップを実行
./scripts/cleanup_disk.sh

# 定期的に実行することを推奨（週1〜2回程度）
```

**手動でのクリーンアップ**:
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
各サービスのDockerイメージをビルドするには、リポジトリのルートディレクトリから以下のスクリプトを実行します。

**前提条件の確認**:
```bash
# conda環境がアクティベートされているか確認
conda info --envs
echo $CONDA_DEFAULT_ENV  # imageflowcanvasと表示されるはず

# 必要なパッケージがインストールされているか確認
python -c "import grpc_tools.protoc; print('gRPC tools: OK')"

# Protocol Buffersが生成されているか確認
ls -la generated/python/imageflow/v1/
```

**ビルド手順**:
```bash
# ビルド前にディスク容量を確認
df -h

# gRPCサービスのビルド
./scripts/build_grpc_services.sh

# バックエンドとフロントエンドサービスのビルド
./scripts/build_web_services.sh

# ビルド後の不要なキャッシュを削除
docker system prune -f
```

### K3sへのデプロイ

#### 初回デプロイ
K3sにデプロイするには、以下のコマンドを実行します。
```bash
# K3sと直接gRPC実行基盤のセットアップ（gRPCサービス群も含む）
sudo ./scripts/setup-k3s.sh

# ⚠️ setup-k3s.shが以下を自動で実行します：
# - K3s + 直接gRPC実行基盤のインストール
# - gRPCサービス群のデプロイ（namespace、services、templates）
# - アプリケーション（Backend & Frontend）のデプロイ
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

**方法1: スクリプトを使用した一括ビルドとインポート（推奨）**
```bash
# gRPCサービスのビルドとK3sインポート
./scripts/build_grpc_services.sh

# バックエンドとフロントエンドサービスのビルドとK3sインポート
./scripts/build_web_services.sh
```

**方法2: ビルドとデプロイを同時実行（自動ロールアウト付き）**
```bash
# gRPCサービスのビルド、インポート、デプロイ、ロールアウト
DEPLOY=true ./scripts/build_grpc_services.sh

# バックエンドとフロントエンドサービスのビルド、インポート、デプロイ、ロールアウト
DEPLOY=true ./scripts/build_web_services.sh
```


#### 画像処理サービスについて

**高性能gRPCサービス**:
- **resize-grpc-app**: 画像リサイズ処理gRPCサービス
- **ai-detection-grpc-app**: YOLO11を使用した物体検知gRPCサービス
- **filter-grpc-app**: 画像フィルタ処理gRPCサービス
- **grpc-gateway**: HTTP-to-gRPC変換ゲートウェイ

gRPCサービスは常駐型で、パイプライン処理時間を大幅に短縮します（60-94秒→1-3秒）。

# K3s内のgRPCサービスイメージ確認
```bash
# gRPCサービスのイメージ一覧を確認
sudo k3s ctr images list | grep -E "(resize-grpc-app|ai-detection-grpc-app|filter-grpc-app|grpc-gateway)"

# gRPCサービスの動作確認
kubectl get pods -n image-processing
kubectl get services -n image-processing

# gRPCサービスのテスト
./scripts/test_grpc_services.py
```

#### デプロイメントの確認
```bash
# ポッドの状態確認
kubectl get pods -o wide

# gRPCサービスの状態確認
kubectl get pods -n image-processing -o wide

# メインアプリケーションのログ確認
kubectl logs -f deployment/frontend
kubectl logs -f deployment/backend

# gRPCサービスのログ確認
kubectl logs -f -n image-processing deployment/resize-grpc-service
kubectl logs -f -n image-processing deployment/ai-detection-grpc-service
kubectl logs -f -n image-processing deployment/filter-grpc-service
kubectl logs -f -n image-processing deployment/grpc-gateway

# サービスの確認
kubectl get services
kubectl get services -n image-processing
```

### デプロイメントファイルの変更を反映する場合
deploymentファイルの変更をK3sクラスターに適用するには、以下のコマンドを実行します。
```bash
# gRPCサービスの設定変更を反映
kubectl apply -f k8s/grpc/grpc-services.yaml
kubectl apply -f k8s/workflows/grpc-pipeline-templates.yaml

# メインアプリケーションの設定変更を反映
kubectl apply -f k8s/core/app-deployments.yaml
```

## gRPCアーキテクチャの詳細

### アーキテクチャの利点

ImageFlowCanvasのgRPCアーキテクチャは、以下の大幅な性能向上を実現しています：

#### 性能比較
- **パイプライン処理時間**: 60-94秒 → 1-3秒（95%以上短縮）
- **Pod起動時間**: 30-50秒 → 0秒（常駐サービス化）
- **通信オーバーヘッド**: HTTP/1.1（100-200ms） → gRPC（20-50ms）
- **リアルタイム処理**: 従来不可 → 現在可能

#### 主要コンポーネント

1. **Protocol Buffers**（`proto/imageflow/v1/`）
   - 型安全な通信スキーマ
   - コンパイル時の型チェック
   - バイナリプロトコルによる高速通信

2. **gRPCサービス**（`services/*-grpc-app/`）
   - `resize-grpc-app`: 画像リサイズサービス
   - `ai-detection-grpc-app`: AI物体検知サービス
   - `filter-grpc-app`: 画像フィルタサービス

3. **gRPCゲートウェイ**（`services/grpc-gateway/`）
   - HTTP-to-gRPC変換
   - 高性能通信基盤の維持
   - RESTful API エンドポイントの提供

4. **Kubernetesデプロイメント**（`k8s/grpc/`）
   - 高可用性サービス設定
   - ヘルスチェック機能
   - リソース制限とスケーリング

### gRPCサービス管理

#### サービスの起動・停止
```bash
# gRPCサービスの起動
kubectl apply -f k8s/grpc/grpc-services.yaml

# サービスの停止
kubectl delete -f k8s/grpc/grpc-services.yaml

# 個別サービスの再起動
kubectl rollout restart -n image-processing deployment/resize-grpc-service
```

#### ヘルスチェック
```bash
# gRPCゲートウェイ経由でのヘルスチェック
curl http://localhost:8080/health
curl http://localhost:8080/v1/health/resize
curl http://localhost:8080/v1/health/detect
curl http://localhost:8080/v1/health/filter

# 直接gRPCサービスへのヘルスチェック
kubectl exec -n image-processing deploy/grpc-gateway -- grpc_health_probe -addr=resize-grpc-service:9090
```

#### パフォーマンステスト
```bash
# 包括的なパフォーマンステスト
./scripts/test_grpc_services.py

# 個別サービステスト
python -c "
import grpc
from generated.python.imageflow.v1 import resize_pb2_grpc
channel = grpc.insecure_channel('localhost:9090')
stub = resize_pb2_grpc.ResizeServiceStub(channel)
print('Resize service connection: OK')
"
```

詳細な実装情報については、[gRPC実装ドキュメント](docs/grpc-implementation.md)を参照してください。

## トラブルシューティング

### gRPCサービスのビルドエラー

#### 症状1: `ModuleNotFoundError: No module named 'grpc_tools'`

**原因**: gRPC開発ツールがインストールされていない

**対処法**:
```bash
# conda環境をアクティベートしてgRPCツールをインストール
conda activate imageflowcanvas
pip install grpcio grpcio-tools

# Protocol Buffersを再生成
./scripts/generate_protos.sh

# gRPCサービスを再ビルド
./scripts/build_grpc_services.sh

# バックエンドとフロントエンドサービスを再ビルド
./scripts/build_web_services.sh
```

#### 症状2: Docker build時に `"/generated/python": not found`

**原因**: Protocol Buffersファイルが生成されていない、または生成に失敗している

**対処法**:
```bash
# 生成されたファイルの確認
ls -la generated/python/

# Protocol Buffersの手動生成
./scripts/generate_protos.sh

# 生成が成功したか確認
ls -la generated/python/imageflow/v1/

# 期待されるファイル:
# - common_pb2.py, common_pb2_grpc.py
# - resize_pb2.py, resize_pb2_grpc.py  
# - ai_detection_pb2.py, ai_detection_pb2_grpc.py
# - filter_pb2.py, filter_pb2_grpc.py
```

#### 症状3: conda環境が見つからない

**原因**: conda環境が正しく作成・アクティベートされていない

**対処法**:
```bash
# conda環境の確認
conda env list

# 環境が存在しない場合は作成
conda create -n imageflowcanvas python=3.12 -y

# 環境をアクティベート
conda activate imageflowcanvas

# 必要なパッケージを再インストール
pip install requests ultralytics grpcio grpcio-tools
```

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
     http://localhost:8000/api/auth/login | \
     grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

   # パイプライン一覧を取得
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/pipelines/
   ```

4. **バックエンドポッドの確認**
   ```bash
   # バックエンドポッドが複数ある場合、データが異なるポッドに保存されている可能性
   kubectl get pods -l app=backend
   kubectl logs -f deployment/backend
   ```

5. **gRPCサービスの状態確認**
   ```bash
   # gRPCサービスが正常に動作しているか確認
   kubectl get pods -n image-processing
   kubectl get services -n image-processing
   
   # gRPCゲートウェイのテスト
   curl http://localhost:8080/health
   ```

**注意**: 2025年7月20日のアップデートにより、直接gRPC呼び出し方式に移行しました。パイプラインの実行時間が60-94秒から1-3秒に短縮され、リアルタイム処理が可能になっています。

### Macでのポートフォワーディングの問題

**症状**: MacでLimaを使用している際に、ポートフォワーディングが正常に動作せず、ホストPCからVM内のサービス（http://localhost:3000、http://localhost:8000等）にアクセスできない

**原因**: Lima VMの設定が正しく読み込まれていない、またはポートフォワーディング設定に問題がある

**対処法**:

1. **VMの再起動（推奨）**
   ```bash
   # ホストマシン（Mac）で実行
   limactl stop k3s
   limactl start k3s
   
   # 再起動後、VMにシェル接続
   limactl shell k3s
   
   # VM内でK3sサービスの状態を確認
   kubectl get pods -A
   ```

2. **ポートフォワーディング設定の確認**
   ```bash
   # ホストマシン（Mac）で実行
   limactl stop k3s
   limactl edit k3s
   
   # 以下の設定が正しく記載されているか確認
   # portForwards:
   #   - guestPort: 3000
   #     hostPort: 3000
   #   - guestPort: 8000
   #     hostPort: 8000
   #   - guestPort: 9001
   #     hostPort: 9001
   #   - guestPort: 2746
   #     hostPort: 2746
   
   # 設定を保存後、VM再起動
   limactl start k3s
   ```

3. **VM内のサービス起動確認**
   ```bash
   # VMにシェル接続
   limactl shell k3s
   
   # ポートフォワーディングスクリプトを実行
   cd ~/ImageFlowCanvas
   ./scripts/port-forward.sh
   
   # 別のターミナルでサービスの動作確認
   curl http://localhost:3000  # Frontend
   curl http://localhost:8000/docs  # Backend API
   ```

4. **Lima VM設定の確認**
   ```bash
   # VM設定の詳細表示
   limactl show-ssh k3s
   
   # VMの状態確認
   limactl list
   ```

**追加のトラブルシューティング**:
- VM再起動後は、VM内で `./scripts/port-forward.sh` を再実行する必要があります
- ホストPCのファイアウォール設定がポートをブロックしていないか確認してください
- 他のアプリケーションが同じポート（3000、8000等）を使用していないか確認してください

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

### ディスク容量不足の問題

**症状**: 開発中にディスク容量が不足し、DockerビルドやK3sの動作に支障が出る

**原因**: containerdイメージ、停止中のコンテナ、Dockerキャッシュなどの蓄積

**対処法**:

1. **自動クリーンアップスクリプトの実行（推奨）**
   ```bash
   # 包括的なディスククリーンアップ
   ./scripts/cleanup_disk.sh
   
   # 実行により以下の作業が自動実行されます：
   # - containerdの不要イメージ削除
   # - 停止中のコンテナ削除
   # - タグ無しイメージの削除
   # - Dockerキャッシュクリア
   # - APTキャッシュクリア
   # - 大きなログファイルのローテート
   ```

2. **手動での緊急クリーンアップ**
   ```bash
   # containerdの不要イメージを削除
   sudo k3s crictl rmi --prune
   
   # 停止中のコンテナを削除
   sudo k3s crictl ps -a | grep Exited | awk '{print $1}' | xargs -r sudo k3s crictl rm
   
   # Dockerキャッシュをクリア
   sudo docker system prune -af --volumes
   
   # ディスク使用量の確認
   df -h
   ```

3. **定期メンテナンス**
   ```bash
   # 週1〜2回の定期実行を推奨
   ./scripts/cleanup_disk.sh
   
   # 大容量ファイルの検索（必要に応じて）
   sudo find / -size +1G -type f 2>/dev/null | head -10
   ```

**予防策**:
- 定期的な `./scripts/cleanup_disk.sh` の実行
- Lima VM使用時はVM設定でディスク容量を十分に確保（100GiB以上推奨）
- 開発作業後の適切なクリーンアップ習慣

