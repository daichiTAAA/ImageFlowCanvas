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
- **Processing Services**: OpenCV, PyTorch, YOLO

## セットアップ

### 開発環境での起動

#### オプション1: Docker Compose（簡単な開発用）

1. **Triton用モデルの準備**
   ```bash
   # YOLOv8 ONNXモデルをダウンロード（例）
   mkdir -p models/yolo/1
   wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx -O models/yolo/1/model.onnx
   ```

2. **Docker Composeでの起動**
   ```bash
   docker compose up -d
   ```

3. **サービスの確認**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - MinIO Console: http://localhost:9001
   - Triton Inference Server: http://localhost:8001

#### オプション2: K3s + Argo Workflows（本格的な開発用）

1. **K3sとArgo Workflowsのセットアップ**
   ```bash
   sudo ./scripts/setup-k3s.sh
   ```

2. **開発環境の起動**
   ```bash
   ./scripts/dev-start.sh
   ```

3. **ポートフォワーディングの開始**
   ```bash
   ./scripts/port-forward.sh
   ```

4. **フロントエンドの起動**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### アクセスポイント

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Argo Workflows UI**: http://localhost:2746
- **MinIO Console**: http://localhost:9001 (admin/admin123)
- **Triton Inference Server**: http://localhost:8001

### 使用方法

1. **ログイン**: admin/admin123 または user/user123
2. **パイプライン作成**: コンポーネントをドラッグ&ドロップで配置
3. **実行**: 画像をアップロードしてパイプラインを実行
4. **監視**: リアルタイムで進捗を確認