# ImageFlowCanvas

ImageFlowCanvasは、Webインターフェースを通じて画像処理の各機能を「部品」として組み合わせ、動的な処理パイプラインを構築・実行できるクラウドネイティブシステムです。

## 特徴

- **超高速gRPCアーキテクチャ**: 直接gRPC呼び出しによりパイプライン処理時間40-100ms
- **デュアル処理方式**: バッチ処理（パイプライン実行）とリアルタイム処理（映像ストリーミング）の両方に対応
- **マイクロサービスアーキテクチャ**: 各処理コンポーネントを独立したgRPC常駐サービスとして構築
- **動的パイプライン構築**: Web UIを通じて処理フローを視覚的に設計・実行
- **Kubernetesネイティブ**: K3s + 直接gRPC呼び出しによる堅牢で高性能な実行基盤
- **リアルタイム監視**: WebSocketによる進捗のリアルタイム表示とKafka経由での包括的な監視
- **スケーラブル**: 処理負荷に応じた自動スケーリング対応

## アーキテクチャ

### 超高速gRPCアーキテクチャ

#### デュアル処理方式

**バッチ処理（パイプライン実行）**:
- **実行方式**: 直接gRPC呼び出し（メイン）、Kafkaフォールバック
- **処理時間**: 40-100ms
- **用途**: 画像ファイル処理、バッチ分析、結果保存

**リアルタイム処理（映像ストリーミング）**:
- **実行方式**: gRPCストリーミング
- **レイテンシ**: <50ms
- **用途**: ライブ映像処理、リアルタイム監視

#### gRPCコンポーネント

- **Protocol Buffers**: 型安全で高性能な通信スキーマ
- **gRPC常駐サービス**: リサイズ、AI検知、フィルタ処理の高速常駐サービス
- **gRPCゲートウェイ**: HTTP-to-gRPC変換による高性能通信
- **直接gRPC呼び出し**: Kafkaオーバーヘッドを排除した超高速実行
- **バイナリプロトコル**: 通信オーバーヘッドを50-70%削減

#### Kafkaの役割
- **進捗通知**: パイプライン実行の進捗をリアルタイム配信
- **監視メトリクス**: システム状態とパフォーマンス指標の収集
- **フォールバック処理**: 直接gRPC実行失敗時の代替処理
- **映像アーカイブ**: リアルタイム処理の選択的永続化

### 技術スタック

- **Frontend**: React + TypeScript + Material-UI
- **Backend**: FastAPI + Python
- **Message Queue**: Apache Kafka（進捗通知・監視・フォールバック用）
- **Pipeline Execution**: 直接gRPC呼び出し（40-100ms処理）+ Kafkaフォールバック
- **Streaming Processing**: gRPCストリーミング（<50msレイテンシ）
- **Container Platform**: Kubernetes (K3s)
- **Object Storage**: MinIO
- **AI Inference**: Triton Inference Server
- **Processing Services**: OpenCV, PyTorch, YOLO11
- **Communication**: gRPC + Protocol Buffers（直接呼び出し）
- **Service Gateway**: gRPC Gateway for HTTP compatibility

## 📁 プロジェクト構成

```
ImageFlowCanvas/
├── deploy/                          # デプロイ設定（環境別）
│   ├── compose/
│   │   └── docker-compose.yml      # Docker Compose設定
│   ├── k3s/
│   │   ├── core/                   # コアサービス（MinIO, Kafka, etc）
│   │   └── grpc/                   # gRPCサービス設定
│   └── nomad/
│       ├── infrastructure.nomad    # インフラサービス
│       ├── grpc-services.nomad     # gRPCサービス
│       └── application.nomad       # アプリケーション
│
├── scripts/                        # ビルド・デプロイスクリプト
│   ├── build_services.sh          # 共通ビルドスクリプト
│   ├── run-compose.sh             # Docker Compose管理
│   ├── setup-k3s.sh               # K3sセットアップ
│   └── setup-nomad-consul.sh      # Nomadセットアップ
│
├── services/                       # gRPCサービス
│   ├── resize-grpc-app/           # 画像リサイズ
│   ├── ai-detection-grpc-app/     # AI物体検知
│   ├── filter-grpc-app/           # 画像フィルタ
│   ├── camera-stream-grpc-app/    # カメラストリーミング
│   └── grpc-gateway/              # gRPCゲートウェイ
│
├── backend/                        # バックエンドAPI
├── frontend/                       # フロントエンド
└── proto/                          # Protocol Buffers定義
```

### 🔄 環境比較

| 環境 | 用途 | 利点 | 欠点 |
|------|------|------|------|
| **Docker Compose** | ローカル開発・テスト | • 簡単セットアップ<br>• 軽量<br>• 1コマンドで起動 | • 本番環境と差異<br>• スケーリング制限 |
| **K3s** | ステージング・本番 | • Kubernetes準拠<br>• 高可用性<br>• 本番環境に近い | • 設定複雑<br>• リソース消費大 |
| **Nomad** | 混合ワークロード | • 軽量オーケストレーター<br>• .NET/Java対応<br>• 柔軟なスケジュール | • エコシステム小<br>• 学習コスト |

## セットアップ

ImageFlowCanvasは、3つの異なるデプロイメント環境をサポートしています：

- **Docker Compose**: ローカルでの手軽な開発・テスト用
- **K3s**: 本番に近い環境でのステージング・検証用  
- **Nomad**: 混合ワークロード（.NET EXEなど）を視野に入れた本番・ステージング用

### 🚀 クイックスタート

どの環境でも、まず共通の準備作業を行います：

```bash
# conda環境を作成・アクティベート
conda create -n imageflowcanvas python=3.12 -y
conda activate imageflowcanvas

# 必要なパッケージをインストール
pip install requests ultralytics grpcio grpcio-tools

# Protocol Buffersとサービスをビルド
./scripts/generate_protos.sh
./scripts/build_services.sh
```

### 🐳 Docker Compose（推奨：ローカル開発）

**最も簡単な方法 - すべてが含まれた開発環境:**

```bash
# サービスをビルドして起動
./scripts/run-compose.sh build

# または、既にビルド済みの場合
./scripts/run-compose.sh up
```

**アクセス:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

**管理コマンド:**
```bash
./scripts/run-compose.sh status    # サービス状態確認
./scripts/run-compose.sh logs     # ログ表示
./scripts/run-compose.sh stop     # サービス停止
./scripts/run-compose.sh down     # サービス削除
./scripts/run-compose.sh health   # ヘルスチェック
```

### ⚙️ K3s（本番に近い環境）

**Kubernetesベースの高性能環境:**

```bash
# K3sセットアップ（Linux推奨）
sudo ./scripts/setup-k3s.sh

# ポートフォワーディング開始（別ターミナル）
./scripts/port-forward.sh
```

**アクセス:**
- Frontend: http://localhost:3000  
- Backend API: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

### 🏗️ Nomad（混合ワークロード対応）

**柔軟なワークロード管理が可能なオーケストレーター:**

```bash
# Nomad + Consulセットアップ
./scripts/setup-nomad-consul.sh

# サービス状態確認
./scripts/setup-nomad-consul.sh status

# ログ確認
./scripts/setup-nomad-consul.sh logs
```

**アクセス:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- MinIO Console: http://localhost:9001
- Nomad UI: http://localhost:4646
- Consul UI: http://localhost:8500

### 📊 環境状態確認

すべての環境の状態を一度に確認できます：

```bash
# すべての環境の状態確認
./scripts/status.sh

# 特定の環境のみ確認
./scripts/status.sh compose    # Docker Compose
./scripts/status.sh k3s        # K3s
./scripts/status.sh nomad      # Nomad
```

### 🔄 環境の切り替え

異なる環境間での切り替えは簡単です：

```bash
# Docker Composeを停止してK3sを開始
./scripts/run-compose.sh down
sudo ./scripts/setup-k3s.sh

# K3sからNomadに切り替え
kubectl delete --all deployments --all-namespaces
./scripts/setup-nomad-consul.sh

# すべて停止
./scripts/run-compose.sh down                    # Docker Compose停止
kubectl delete --all deployments --all-namespaces # K3s停止  
./scripts/setup-nomad-consul.sh stop            # Nomad停止
```

### 🖥️ OS別セットアップ詳細

上記のクイックスタートが動作しない場合や、詳細な設定が必要な場合は以下を参照してください。

#### Linux環境（直接インストール）

すべての環境（Docker Compose, K3s, Nomad）が利用可能です。上記のクイックスタート手順をそのまま実行してください。

#### macOS環境（Lima使用）

**Lima固有の準備手順:**
```bash
# Limaのインストール
brew install lima

# Ubuntu VMの作成と起動
limactl create --name=k3s template://ubuntu-lts
limactl start k3s

# ポートフォワーディング設定
limactl stop k3s
limactl edit k3s
```

Lima VM設定ファイルに以下のポートフォワーディングを追加：
```yaml
portForwards:
  - guestPort: 3000  # Frontend
    hostPort: 3000
  - guestPort: 8000  # Backend
    hostPort: 8000  
  - guestPort: 9001  # MinIO Console
    hostPort: 9001
```

```bash
# VM再起動と環境構築
limactl start k3s
limactl shell k3s

# VM内でプロジェクトをクローンし、クイックスタート手順を実行
```

#### Windows環境（WSL2使用）

**WSL2固有の準備手順:**
```bash
# PowerShellで実行
wsl --install Ubuntu-22.04

```

### 📋 使用方法

#### バッチ処理
1. **ログイン**: admin/admin123 または user/user123
2. **パイプライン作成**: コンポーネントをドラッグ&ドロップで配置
3. **実行**: 画像をアップロードしてパイプラインを実行（40-100msで完了）
4. **監視**: リアルタイムで進捗を確認

#### リアルタイムカメラ処理 🆕
1. **ログイン**: admin/admin123 または user/user123
2. **パイプライン作成**: まずWeb UIでパイプラインを作成・保存
3. **カメラアクセス**: 「リアルタイム処理」タブを選択
4. **カメラ初期化**: PCカメラへのアクセスを許可
5. **パイプライン選択**: 作成したパイプラインを選択
6. **ストリーミング開始**: リアルタイム処理を開始（<50msレイテンシ）
7. **結果表示**: 映像にAI検知結果がリアルタイムでオーバーレイ表示

### gRPCサービスのテスト

高性能gRPCアーキテクチャの動作確認：

```bash
# gRPCサービスの動作テスト
./scripts/test_grpc_services.py

# 個別サービスの動作確認
kubectl get pods -n image-processing
kubectl logs -n image-processing deployment/resize-grpc-service

# カメラストリーミングのテスト 🆕
python test_camera_stream_integration.py
```

### カメラストリーミング機能 🆕

#### 新機能の概要
- **リアルタイム映像処理**: PCカメラからの映像をリアルタイムで処理（<50msレイテンシ）
- **Web UI統合**: 既存のパイプライン作成機能と完全連携
- **gRPCストリーミング**: 双方向ストリーミングによる高性能処理
- **多様なパイプライン**: AIデータ検知、フィルタ処理など既存のコンポーネントをリアルタイムで利用

#### セットアップ
```bash
# 新規セットアップ（完全版）
sudo ./scripts/setup-complete.sh

# 既存環境にカメラ機能を追加
./scripts/setup-camera-stream.sh
```

#### 利用方法
1. ブラウザで http://localhost:3000 にアクセス
2. 「リアルタイム処理」タブを選択
3. カメラアクセスを許可
4. Web UIで作成したパイプラインを選択
5. 「ストリーミング開始」をクリック
6. リアルタイムでAI検知結果を確認

#### 技術仕様
- **プロトコル**: gRPC双方向ストリーミング
- **WebSocket**: クライアント-バックエンド間通信
- **処理レイテンシ**: 30-50ms
- **対応カメラ**: PC/USB、Webカメラ
- **同時ストリーム**: 複数カメラ対応


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

# gRPCサービスのビルド（カメラストリーミング含む）
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
- **camera-stream-grpc-app**: リアルタイム映像処理gRPCサービス 🆕
- **grpc-gateway**: HTTP-to-gRPC変換ゲートウェイ

gRPCサービスは常駐型で、パイプライン処理時間を大幅に短縮します（60-94秒→1-3秒）。

# K3s内のgRPCサービスイメージ確認
```bash
# gRPCサービスのイメージ一覧を確認
sudo k3s ctr images list | grep -E "(resize-grpc-app|ai-detection-grpc-app|filter-grpc-app|camera-stream-grpc-app|grpc-gateway)"

# gRPCサービスの動作確認
kubectl get pods -n image-processing
kubectl get services -n image-processing

# gRPCサービスのテスト
./scripts/test_grpc_services.py

# カメラストリーミングの動作確認 🆕
kubectl logs -n image-processing deployment/camera-stream-grpc-service
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
kubectl logs -f -n image-processing deployment/camera-stream-grpc-service
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

ImageFlowCanvasの超高速gRPCアーキテクチャは、以下の革命的な性能向上を実現しています：

#### 性能比較
- **パイプライン処理時間**: 60-94秒 → 40-100ms（99%以上短縮）
- **Pod起動時間**: 30-50秒 → 0秒（常駐サービス化）
- **通信オーバーヘッド**: HTTP/1.1（100-200ms） → 直接gRPC（10-30ms）
- **リアルタイム処理**: 従来不可 → 現在可能（<50msレイテンシ）
- **同時処理能力**: 単発処理 → 100並列パイプライン対応

#### 主要コンポーネント

1. **Protocol Buffers**（`proto/imageflow/v1/`）
   - 型安全な通信スキーマ
   - コンパイル時の型チェック
   - バイナリプロトコルによる超高速通信

2. **gRPC常駐サービス**（`services/*-grpc-app/`）
   - `resize-grpc-app`: 画像リサイズサービス
   - `ai-detection-grpc-app`: AI物体検知サービス（YOLO11）
   - `filter-grpc-app`: 画像フィルタサービス

3. **gRPCゲートウェイ**（`services/grpc-gateway/`）
   - HTTP-to-gRPC変換
   - 高性能通信基盤の維持
   - RESTful API エンドポイントの提供

4. **直接gRPC実行エンジン**（`backend/app/services/`）
   - Kafkaオーバーヘッドを完全排除
   - 40-100ms超高速パイプライン実行
   - リアルタイム進捗通知

5. **Kubernetesデプロイメント**（`k8s/grpc/`）
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

**注意**: 2025年7月20日のアップデートにより、直接gRPC呼び出し方式に移行しました。パイプラインの実行時間が60-94秒から40-100msに短縮され（99%以上の改善）、リアルタイム処理とバッチ処理の両方が可能になっています。Kafkaは進捗通知、監視メトリクス、フォールバック処理に特化して使用されています。

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

