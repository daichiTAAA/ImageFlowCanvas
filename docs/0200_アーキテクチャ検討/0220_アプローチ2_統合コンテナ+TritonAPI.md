# アプローチ2：統合コンテナ + Triton API - Nomadによる動的パイプライン実現

## **第1章：Nomadによる動的パイプライン構築の可能性**

### **1.1. 結論：Nomadでも動的パイプライン構築は実現可能**

「Web画面から、前処理、AI処理、後処理といった『部品』を自由に組み合わせ、動的なパイプラインを構築したい」という要件に対して、**Nomadを使用したアプローチ2でも十分に実現可能**です。

ただし、実現方法はアプローチ1（K3s + 直接gRPC呼び出し）とは大きく異なります：

- **アプローチ1**: 各処理を独立したコンテナに分離し、直接gRPC呼び出しで動的なパイプラインを構築
- **アプローチ2**: 統合コンテナ内でストラテジーパターンを使用し、Nomadで動的なジョブ定義を生成

### **1.2. Nomadアプローチの特徴**

#### **利点：**
- **学習コストの大幅削減**: Kubernetesの複雑な概念（Pod, Service, Deployment等）を習得する必要がない
- **運用の簡潔性**: 単一のNomadジョブファイルでパイプライン全体を管理
- **高い処理性能**: コンテナ間のデータ転送オーバーヘッドが皆無
- **デバッグの容易さ**: 単一のログストリームで全処理を追跡可能

#### **制約：**
- **処理粒度**: 各処理を独立してスケールできない（パイプライン単位でのスケーリング）
- **再利用性**: 新しい処理部品の追加時は統合コンテナの再ビルドが必要
- **障害分離**: パイプライン内の一つの処理の障害が全体に影響する可能性

## **第2章：Nomadによる動的パイプライン設計アーキテクチャ**

### **2.1. システム全体構成**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │  Backend API    │    │   Nomad Cluster │
│  (Pipeline UI)  │──→│  (Job Generator)│──→│  (Job Executor) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │ Template Engine │    │ Integrated      │
                        │ (Jinja2/Go)     │    │ Container       │
                        └─────────────────┘    │ (Multi-Flow)    │
                                               └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │ Triton Inference│
                                               │ Server (AI)     │
                                               └─────────────────┘
```

### **2.2. 動的パイプライン実現の仕組み**

#### **2.2.1. パイプライン定義の動的生成**

Web UIからユーザーが選択した処理部品の組み合わせを基に、バックエンドAPIが以下の手順で実行可能なNomadジョブを動的生成します：

1. **フロー定義の受信**: Web UIから処理部品の配列と設定パラメータを受信
2. **テンプレート展開**: 選択された部品に基づいてNomadジョブ定義を動的生成
3. **ジョブ投入**: NomadクラスタにジョブをSubmit
4. **実行監視**: ジョブの実行状況をリアルタイムで追跡

#### **2.2.2. 具体的な実装例**

**ユーザー選択例：**
```json
{
  "pipeline_name": "custom-image-processing-001",
  "components": [
    {
      "type": "resize",
      "config": {"width": 512, "height": 512}
    },
    {
      "type": "object_detection",
      "config": {"model": "yolov5s", "confidence": 0.5}
    },
    {
      "type": "blur_faces",
      "config": {"blur_strength": 10}
    }
  ],
  "input_image": "uploads/original/photo-001.jpg"
}
```

**動的生成されるNomadジョブ：**
```hcl
job "custom-image-processing-001" {
  datacenters = ["dc1"]
  type = "batch"

  group "processing" {
    task "pipeline" {
      driver = "docker"

      config {
        image = "your-org/integrated-processor:v1"
        
        # 動的に生成される環境変数
        environment = {
          PIPELINE_FLOW = "resize,object_detection,blur_faces"
          INPUT_IMAGE = "uploads/original/photo-001.jpg"
          OUTPUT_PATH = "processed/custom-image-processing-001/"
          
          # 各コンポーネントの設定
          RESIZE_WIDTH = "512"
          RESIZE_HEIGHT = "512"
          DETECTION_MODEL = "yolov5s"
          DETECTION_CONFIDENCE = "0.5"
          BLUR_STRENGTH = "10"
          
          # Triton Inference Server設定
          TRITON_URL = "http://triton.service.consul:8000"
        }
      }

      # リソース要件（処理内容に応じて動的調整）
      resources {
        cpu    = 1000  # AI処理がある場合は増量
        memory = 2048  # 画像サイズに応じて調整
      }

      # 完了までの制限時間
      kill_timeout = "30s"
    }
  }
}
```

## **第3章：統合コンテナの設計：ストラテジーパターンによる柔軟性**

### **3.1. アーキテクチャ設計原則**

統合コンテナ内では、**ストラテジーパターン**を採用して複数の処理フローを同一コード基盤から実行できるように設計します。

```python
# 処理フロー定義の例
class ProcessingStrategy:
    def execute(self, context: ProcessingContext) -> ProcessingResult:
        pass

class ResizeStrategy(ProcessingStrategy):
    def execute(self, context):
        # リサイズ処理実装
        pass

class ObjectDetectionStrategy(ProcessingStrategy):
    def execute(self, context):
        # Triton Inference Serverと連携したAI推論
        pass

class BlurFacesStrategy(ProcessingStrategy):
    def execute(self, context):
        # 顔のぼかし処理実装
        pass

# フロー実行エンジン
class PipelineExecutor:
    def __init__(self):
        self.strategies = {
            'resize': ResizeStrategy(),
            'object_detection': ObjectDetectionStrategy(),
            'blur_faces': BlurFacesStrategy(),
        }
    
    def execute_pipeline(self, flow_definition):
        context = ProcessingContext()
        
        for step in flow_definition.steps:
            strategy = self.strategies[step.type]
            context = strategy.execute(context)
            
        return context.result
```

### **3.2. 統合コンテナの実装例**

#### **3.2.1. メインエントリーポイント**

```python
#!/usr/bin/env python3
"""
統合画像処理パイプライン
環境変数からフロー定義を読み取り、動的に処理を実行
"""

import os
import logging
import json
from typing import List, Dict
from dataclasses import dataclass

# 設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingContext:
    """処理間でデータを受け渡すためのコンテキスト"""
    current_image_path: str
    metadata: Dict
    temp_files: List[str]

class ImageProcessor:
    def __init__(self):
        self.triton_url = os.getenv('TRITON_URL', 'http://localhost:8000')
        self.input_path = os.getenv('INPUT_IMAGE')
        self.output_path = os.getenv('OUTPUT_PATH')
        self.flow_definition = os.getenv('PIPELINE_FLOW', '').split(',')
        
    def execute(self):
        """メインの処理実行ロジック"""
        logger.info(f"パイプライン開始: {self.flow_definition}")
        
        # 初期コンテキスト作成
        context = ProcessingContext(
            current_image_path=self.input_path,
            metadata={},
            temp_files=[]
        )
        
        try:
            # フローに従って順次処理実行
            for step_name in self.flow_definition:
                if step_name.strip():
                    context = self._execute_step(step_name.strip(), context)
                    
            # 最終結果の保存
            self._save_final_result(context)
            logger.info("パイプライン完了")
            
        except Exception as e:
            logger.error(f"パイプライン実行エラー: {e}")
            raise
        finally:
            self._cleanup(context)
    
    def _execute_step(self, step_name: str, context: ProcessingContext) -> ProcessingContext:
        """個別ステップの実行"""
        logger.info(f"ステップ実行: {step_name}")
        
        if step_name == 'resize':
            return self._resize_image(context)
        elif step_name == 'object_detection':
            return self._detect_objects(context)
        elif step_name == 'blur_faces':
            return self._blur_faces(context)
        else:
            logger.warning(f"未知のステップ: {step_name}")
            return context

if __name__ == "__main__":
    processor = ImageProcessor()
    processor.execute()
```

#### **3.2.2. AI処理のTriton連携**

```python
import requests
import numpy as np
import cv2

class TritonClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        
    def infer(self, model_name: str, input_data: np.ndarray) -> np.ndarray:
        """Triton Inference Serverでの推論実行"""
        
        # 前処理：画像データをTritonの入力形式に変換
        processed_input = self._preprocess_image(input_data)
        
        # Triton APIリクエスト
        inference_request = {
            "inputs": [
                {
                    "name": "input",
                    "shape": processed_input.shape,
                    "datatype": "FP32",
                    "data": processed_input.tolist()
                }
            ]
        }
        
        response = requests.post(
            f"{self.server_url}/v2/models/{model_name}/infer",
            json=inference_request
        )
        
        if response.status_code == 200:
            result = response.json()
            return np.array(result['outputs'][0]['data'])
        else:
            raise Exception(f"Triton推論エラー: {response.text}")

def _detect_objects(self, context: ProcessingContext) -> ProcessingContext:
    """物体検出処理（Triton経由）"""
    model_name = os.getenv('DETECTION_MODEL', 'yolov5s')
    confidence = float(os.getenv('DETECTION_CONFIDENCE', '0.5'))
    
    # 画像読み込み
    image = cv2.imread(context.current_image_path)
    
    # Tritonで推論実行
    triton_client = TritonClient(self.triton_url)
    detection_result = triton_client.infer(model_name, image)
    
    # 結果の後処理
    annotated_image = self._annotate_detections(image, detection_result, confidence)
    
    # 結果画像の保存
    temp_path = f"/tmp/detected_{os.path.basename(context.current_image_path)}"
    cv2.imwrite(temp_path, annotated_image)
    
    # コンテキスト更新
    context.current_image_path = temp_path
    context.temp_files.append(temp_path)
    context.metadata['detections'] = self._parse_detections(detection_result)
    
    return context
```

## **第4章：Nomadクラスタのセットアップと運用**

### **4.1. Nomadクラスタの構築**

#### **4.1.1. 基本インストール**

```bash
# Nomadのインストール（Ubuntu/Debian）
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install nomad

# Consulのインストール（サービスディスカバリ用）
sudo apt-get install consul
```

#### **4.1.2. Nomad設定ファイル**

```hcl
# /etc/nomad.d/nomad.hcl
datacenter = "dc1"
data_dir   = "/opt/nomad/data"
bind_addr  = "0.0.0.0"

# サーバー設定（開発環境では1台で充分）
server {
  enabled          = true
  bootstrap_expect = 1
}

# クライアント設定
client {
  enabled = true
  
  # Dockerドライバーの有効化
  driver_whitelist = ["docker"]
}

# Consulとの連携
consul {
  address = "127.0.0.1:8500"
}
```

#### **4.1.3. サービス起動**

```bash
# Consulサービス開始
sudo systemctl enable consul
sudo systemctl start consul

# Nomadサービス開始
sudo systemctl enable nomad
sudo systemctl start nomad

# 状態確認
nomad node status
consul members
```

### **4.2. Triton Inference Serverのデプロイ**

#### **4.2.1. Triton用Nomadジョブ定義**

```hcl
# triton-server.nomad
job "triton-inference-server" {
  datacenters = ["dc1"]
  type = "service"

  group "triton" {
    task "inference-server" {
      driver = "docker"

      config {
        image = "nvcr.io/nvidia/tritonserver:24.07-py3"
        
        args = [
          "tritonserver",
          "--model-repository=/models",
          "--allow-http=true",
          "--http-port=8000"
        ]
        
        ports = ["http"]
        
        volumes = [
          "/opt/triton/models:/models:ro"
        ]
      }

      resources {
        cpu    = 2000
        memory = 4096
        
        # GPU利用の場合
        # device "nvidia/gpu" {
        #   count = 1
        # }
      }

      service {
        name = "triton"
        port = "http"
        
        check {
          type     = "http"
          path     = "/v2/health/ready"
          interval = "10s"
          timeout  = "3s"
        }
      }
    }

    network {
      port "http" {
        static = 8000
      }
    }
  }
}
```

#### **4.2.2. モデルリポジトリの準備**

```bash
# モデルディレクトリ構造
sudo mkdir -p /opt/triton/models
cd /opt/triton/models

# YOLOv5モデルの配置例
sudo mkdir -p yolov5s/1
# モデルファイルを配置...

# モデル設定ファイル
sudo tee yolov5s/config.pbtxt <<EOF
name: "yolov5s"
platform: "pytorch_libtorch"
max_batch_size: 8

input [
  {
    name: "input"
    data_type: TYPE_FP32
    dims: [ 3, 640, 640 ]
  }
]

output [
  {
    name: "output"
    data_type: TYPE_FP32
    dims: [ 25200, 85 ]
  }
]
EOF
```

### **4.3. 動的ジョブ生成バックエンドAPI**

#### **4.3.1. FastAPI APIサーバー**

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import requests
from jinja2 import Template
import uvicorn

app = FastAPI(title="Dynamic Pipeline API", version="1.0.0")

# リクエストモデル定義
class ComponentConfig(BaseModel):
    type: str
    config: Dict[str, str] = {}

class PipelineRequest(BaseModel):
    pipeline_name: str
    components: List[ComponentConfig]
    input_image: str

class PipelineResponse(BaseModel):
    job_id: str
    status: str
    pipeline_name: str

# Nomadジョブテンプレート
NOMAD_JOB_TEMPLATE = """
job "{{ pipeline_name }}" {
  datacenters = ["dc1"]
  type = "batch"

  group "processing" {
    task "pipeline" {
      driver = "docker"

      config {
        image = "your-org/integrated-processor:v1"
        
        environment = {
          PIPELINE_FLOW = "{{ pipeline_flow }}"
          INPUT_IMAGE = "{{ input_image }}"
          OUTPUT_PATH = "{{ output_path }}"
          {% for key, value in config.items() %}
          {{ key }} = "{{ value }}"
          {% endfor %}
          TRITON_URL = "http://triton.service.consul:8000"
        }
      }

      resources {
        cpu    = {{ cpu_requirement }}
        memory = {{ memory_requirement }}
      }
    }
  }
}
"""

@app.post("/api/pipeline/submit", response_model=PipelineResponse)
async def submit_pipeline(pipeline_request: PipelineRequest):
    """パイプライン実行リクエストを受け取り、Nomadジョブを生成・投入"""
    
    # パイプライン定義の検証
    if not _validate_pipeline_request(pipeline_request):
        raise HTTPException(status_code=400, detail="Invalid pipeline definition")
    
    try:
        # Nomadジョブ定義の生成
        nomad_job = _generate_nomad_job(pipeline_request)
        
        # Nomadへのジョブ投入
        job_id = _submit_to_nomad(nomad_job)
        
        return PipelineResponse(
            job_id=job_id,
            status="submitted",
            pipeline_name=pipeline_request.pipeline_name
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _validate_pipeline_request(pipeline_request: PipelineRequest) -> bool:
    """パイプライン定義の検証"""
    if not pipeline_request.pipeline_name:
        return False
    if not pipeline_request.components:
        return False
    if not pipeline_request.input_image:
        return False
    return True

def _generate_nomad_job(pipeline_request: PipelineRequest) -> str:
    """パイプライン定義からNomadジョブを動的生成"""
    
    # フロー文字列の生成
    pipeline_flow = ','.join([comp.type for comp in pipeline_request.components])
    
    # 設定パラメータの展開
    config = {}
    for component in pipeline_request.components:
        for key, value in component.config.items():
            config[f"{component.type.upper()}_{key.upper()}"] = value
    
    # リソース要件の動的計算
    cpu_requirement = _calculate_cpu_requirement(pipeline_request.components)
    memory_requirement = _calculate_memory_requirement(pipeline_request.components)
    
    # テンプレート展開
    template = Template(NOMAD_JOB_TEMPLATE)
    nomad_job_hcl = template.render(
        pipeline_name=pipeline_request.pipeline_name,
        pipeline_flow=pipeline_flow,
        input_image=pipeline_request.input_image,
        output_path=f"processed/{pipeline_request.pipeline_name}/",
        config=config,
        cpu_requirement=cpu_requirement,
        memory_requirement=memory_requirement
    )
    
    return nomad_job_hcl

def _calculate_cpu_requirement(components: List[ComponentConfig]) -> int:
    """処理コンポーネントに基づいてCPU要件を計算"""
    base_cpu = 1000  # 1 CPU core
    for component in components:
        if component.type in ['object_detection', 'face_recognition']:
            base_cpu += 1000
        elif component.type in ['resize', 'blur_faces']:
            base_cpu += 500
    return base_cpu

def _calculate_memory_requirement(components: List[ComponentConfig]) -> int:
    """処理コンポーネントに基づいてメモリ要件を計算"""
    base_memory = 1024  # 1GB
    for component in components:
        if component.type in ['object_detection', 'face_recognition']:
            base_memory += 2048
        elif component.type in ['resize', 'blur_faces']:
            base_memory += 512
    return base_memory

def _submit_to_nomad(nomad_job_hcl: str) -> str:
    """Nomadクラスタにジョブを投入"""
    
    # HCLをJSONに変換（実際の実装では外部ツールを使用）
    # ここでは簡略化
    
    nomad_api_url = "http://localhost:4646/v1/jobs"
    
    response = requests.post(nomad_api_url, json={
        "Job": nomad_job_hcl  # 実際はJSON形式で送信
    })
    
    if response.status_code == 200:
        return response.json()['EvalID']
    else:
        raise Exception(f"Nomad job submission failed: {response.text}")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)
```

## **第5章：運用監視とスケーリング戦略**

### **5.1. Nomadによる監視と管理**

#### **5.1.1. 基本的な監視コマンド**

```bash
# 実行中ジョブの確認
nomad job status

# 特定ジョブの詳細表示
nomad job status custom-image-processing-001

# ジョブログの確認
nomad logs <alloc-id>

# クラスタ全体の状況
nomad node status
nomad server members
```

#### **5.1.2. Web UIによる監視**

Nomadは標準でWeb UIを提供します：

```bash
# NomadクラスタのWeb UIにアクセス
# http://localhost:4646
```

### **5.2. スケーリング戦略**

#### **5.2.1. 水平スケーリング**

同一パイプラインの並列実行：

```bash
# 同じパイプライン定義で複数ジョブを並列実行
nomad job run pipeline-batch-001.nomad
nomad job run pipeline-batch-002.nomad
nomad job run pipeline-batch-003.nomad
```

#### **5.2.2. リソースベースの自動スケーリング**

```hcl
# オートスケーリング設定例
job "image-processor" {
  # ...
  
  group "processing" {
    # インスタンス数の動的調整
    count = 3
    
    scaling {
      enabled = true
      min     = 1
      max     = 10
      
      policy {
        cooldown            = "1m"
        evaluation_interval = "10s"
        
        check "cpu_usage" {
          source = "nomad-apm"
          query  = "avg_cpu_usage"
          
          strategy "target-value" {
            target = 70
          }
        }
      }
    }
  }
}
```

## **第6章：比較まとめ：アプローチ1 vs アプローチ2**

### **6.1. 動的パイプライン構築の実現度比較**

| 観点                       | アプローチ1 (K3s + 直接gRPC) | アプローチ2 (Nomad + 統合)   |
| -------------------------- | ---------------------------- | ---------------------------- |
| **動的フロー構築**         | ◎ DAGによる完全動的構築      | ○ 環境変数による動的制御     |
| **部品の組み合わせ自由度** | ◎ 任意の組み合わせ可能       | ○ 事前定義部品の組み合わせ   |
| **新部品追加の容易さ**     | ◎ 独立したコンテナ追加       | △ 統合コンテナの再ビルド必要 |
| **実行時パフォーマンス**   | ○ コンテナ間転送あり         | ◎ メモリ内処理で高速         |
| **リソース効率**           | ◎ 部品単位でスケール         | ○ パイプライン単位でスケール |

### **6.2. 運用観点での比較**

| 観点               | アプローチ1              | アプローチ2            |
| ------------------ | ------------------------ | ---------------------- |
| **学習コスト**     | △ Kubernetes習得必要     | ◎ 既存スキルで対応可能 |
| **デバッグ難易度** | △ 分散システムの知識必要 | ◎ 単一ログで追跡可能   |
| **導入スピード**   | △ 数ヶ月の学習期間       | ◎ 数週間で導入可能     |
| **長期保守性**     | ◎ マイクロサービスの利点 | ○ モノリスの制約あり   |

### **6.3. 推奨選択基準**

**アプローチ2（Nomad）を選択すべき場合：**
- チームにKubernetes経験者がいない
- 短期間（1-3ヶ月）でのMVP構築が必要
- 処理フローが比較的固定的
- 運用の簡潔性を最優先する
- 高い処理性能が要求される

**アプローチ1（K3s）を選択すべき場合：**
- 動的パイプライン構築が絶対要件
- 処理部品の頻繁な追加・変更が想定される
- 長期的なシステム拡張性を重視
- チームの技術力向上を戦略的投資として捉える

## **結論**

Nomadを使用したアプローチ2でも、「Web画面から部品を自由に組み合わせる動的パイプライン構築」は**十分に実現可能**です。実現方法は異なりますが、要件を満たす実用的なシステムを短期間で構築できます。

重要なのは、プロジェクトの制約（時間、予算、技術スキル）と要件（柔軟性、性能、拡張性）のバランスを考慮して、最適なアプローチを選択することです。