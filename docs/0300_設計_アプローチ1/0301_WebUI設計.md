# ImageFlowCanvas WebUI設計書

# 文書管理情報

| 項目       | 内容                        |
| ---------- | --------------------------- |
| 文書名     | ImageFlowCanvas WebUI設計書 |
| バージョン | 1.0                         |
| 作成日     | 2025年7月27日               |
| 更新日     | 2025年7月27日               |

---

# 1. 概要

---

# 2. WebUIでのパイプライン作成

WebUIでは、ユーザーが直感的にパイプラインを設計・実行できるよう、以下の機能を提供します。

---


# 3. 処理方式設計
## 3.1. バッチ処理（パイプライン実行）

処理フロー:
```mermaid
sequenceDiagram
    participant C as Client
    participant API as Backend API
    participant gRPC as gRPC Services
    participant MinIO as MinIO Storage
    participant WS as WebSocket

    C->>API: POST /executions (files)
    API->>MinIO: Upload files
    API-->>C: execution_id
    
    Note over API,gRPC: gRPC実行 (40-100ms)
    API->>gRPC: gRPC call
    gRPC->>MinIO: Process & Save
    gRPC-->>API: Progress updates
    API-->>WS: Real-time progress
    gRPC->>API: Final result
    API-->>C: Completion status
```

特徴:
- 実行方式: Backend経由gRPC呼び出し（メイン）
- 処理時間: 40-100ms
- データ永続化: MinIOに保存
- 進捗通知: WebSocket + Kafka
- 用途: 画像ファイル処理、バッチ分析

## 3.2. リアルタイム処理（ストリーミング）

処理フロー:
```mermaid
sequenceDiagram
    participant Cam as Camera Source
    participant GW as API Gateway
    participant Stream as Streaming Service
    participant AI as AI Service
    participant Kafka as Kafka Archive

    Cam->>GW: gRPC Stream (VideoFrame)
    GW->>Stream: Route to processing
    Stream->>AI: Real-time inference
    AI-->>Stream: ProcessedFrame
    Stream-->>GW: Processed stream
    GW-->>Cam: Results
    
    Note over Stream,Kafka: Optional archiving
    Stream-->>Kafka: Archive frames
```

特徴:
- 実行方式: gRPCストリーミング
- レイテンシ: <50ms
- データ: メモリベース処理、選択的アーカイブ
- 用途: ライブ映像処理、リアルタイム監視

---

# 4. マスタ設定


---

# 5. 結果確認


---

# 6. UI/UX 

## 6.1. UI コンポーネント 

### 6.1.1. 画面

```mermaid
graph TD
    Login[ログイン画面]
    Dashboard[ダッシュボード]
    PipelineList[パイプライン一覧]
    PipelineEditor[パイプライン編集]
    ExecutionMonitor[実行監視]
    ResultView[結果表示]
    ComponentList[コンポーネント一覧]
    
    Login --> Dashboard
    Dashboard --> PipelineList
    Dashboard --> ExecutionMonitor
    PipelineList --> PipelineEditor
    ExecutionMonitor --> ResultView
    Dashboard --> ComponentList
```

### 6.1.2. 主要画面仕様

| 画面名           | 機能                   | UI要素                                                                    |
| ---------------- | ---------------------- | ------------------------------------------------------------------------- |
| ダッシュボード   | システム状況表示       | ・実行中パイプライン数<br/>・リソース使用状況<br/>・最近の実行履歴        |
| パイプライン編集 | 視覚的パイプライン構築 | ・コンポーネントパレット<br/>・ドラッグ&ドロップエディタ<br/>・接続線描画 |
| 実行監視         | リアルタイム進捗表示   | ・進捗バー<br/>・ステップ状況<br/>・ログストリーミング                    |
| 結果表示         | 処理結果確認           | ・画像ビューア<br/>・Before/After比較<br/>・メタデータ表示                |
