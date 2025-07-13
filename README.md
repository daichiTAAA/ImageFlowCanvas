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

### 開発環境での起動

#### オプション1: Docker Compose（簡単な開発用）

1. **Triton用モデルの準備**
   ```bash
   # YOLO11 ONNXモデルをセットアップ（自動ダウンロード・変換）
   python scripts/setup-yolo11.py
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

##### Linux環境（直接インストール）
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

##### macOS環境（Lima使用）
1. **Limaのインストール**
   ```bash
   # Homebrewでインストール
   brew install lima
   
   # または手動インストール
   curl -fsSL https://get.lima.sh | sh
   ```

2. **Ubuntu VMの作成と起動**
   ```bash
   # Ubuntu 22.04 VMを作成
   limactl create --name=k3s template://ubuntu-lts
   
   # VMを起動
   limactl start k3s
   ```

3. **VM内でK3sをセットアップ**
   ```bash
   # VMにシェル接続
   lima k3s
   
   # VM内でプロジェクトをクローン
   git clone <your-repo-url>
   cd ImageFlowCanvas
   
   # K3sセットアップ
   sudo ./scripts/setup-k3s.sh
   ```

4. **ポートフォワーディング設定**
   ```bash
   # Lima VM設定ファイルを編集（ホストマシンで実行）
   limactl edit k3s
   ```
   
   以下の設定を追加：
   ```yaml
   portForwards:
   - guestPort: 6443
     hostPort: 6443
   - guestPort: 2746
     hostPort: 2746
   - guestPort: 8000
     hostPort: 8000
   - guestPort: 9001
     hostPort: 9001
   ```

5. **VM再起動とサービス確認**
   ```bash
   # VM再起動
   limactl stop k3s
   limactl start k3s
   
   # VM内でサービス起動
   lima k3s
   ./scripts/dev-start.sh
   ```

##### Windows環境（WSL2使用）
1. **WSL2のセットアップ**
   ```bash
   # PowerShellで実行
   wsl --install Ubuntu-22.04
   ```

2. **WSL2内でLinux手順を実行**
   ```bash
   # WSL2シェルで実行
   sudo ./scripts/setup-k3s.sh
   ./scripts/dev-start.sh
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

## YOLO11の初期設定

ImageFlowCanvasはYOLO11を使用して高精度な物体検出を提供します。

### YOLO11モデルのセットアップ

1. **自動セットアップ（推奨）**:
   ```bash
   python scripts/setup-yolo11.py
   ```
   
   このスクリプトは以下を自動実行します：
   - YOLO11n.ptモデルのダウンロード
   - ONNX形式への変換
   - Tritonサーバー用の配置

2. **手動セットアップ**:
   ```bash
   # ultralytics パッケージをインストール
   pip install ultralytics
   
   # YOLO11n.ptをダウンロード
   wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt
   
   # ONNX形式に変換
   python -c "from ultralytics import YOLO; YOLO('yolo11n.pt').export(format='onnx', imgsz=640, dynamic=False)"
   
   # 変換されたモデルを配置
   mv yolo11n.onnx models/yolo/1/model.onnx
   ```

### YOLO11の特徴

- **高精度な物体検出**: COCO 80クラスの物体を検出
- **改善されたパフォーマンス**: 前世代YOLOより高速・高精度  
- **小物体検出の向上**: 細かい物体の検出精度が向上
- **CPU/GPU対応**: 環境に応じて最適化

### 使用可能な検出クラス

person, bicycle, car, motorcycle, airplane, bus, train, truck, boat, traffic light, fire hydrant, stop sign, parking meter, bench, bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe, backpack, umbrella, handbag, tie, suitcase, frisbee, skis, snowboard, sports ball, kite, baseball bat, baseball glove, skateboard, surfboard, tennis racket, bottle, wine glass, cup, fork, knife, spoon, bowl, banana, apple, sandwich, orange, broccoli, carrot, hot dog, pizza, donut, cake, chair, couch, potted plant, bed, dining table, toilet, tv, laptop, mouse, remote, keyboard, cell phone, microwave, oven, toaster, sink, refrigerator, book, clock, vase, scissors, teddy bear, hair drier, toothbrush