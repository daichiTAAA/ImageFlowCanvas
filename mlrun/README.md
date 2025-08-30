ImageFlowCanvas mlrun サンプル
================================

このフォルダは「docs/0300_設計_アプローチ1/0310_LLM連携画像処理パイプライン設計.md」を元に、MLRunを用いたサンプル・パイプライン実装を示します。LLMが生成したパイプライン定義(JSON)を入力として、画像取得→前処理→AI検出(Triton想定)→フィルタ→集約→結果出力の一連を実行します。

構成
----
- `project.yaml`: MLRun Project 定義
- `workflows/llm_image_flow.py`: KFP/MLRun パイプライン本体（バッチ/DAG想定）
- `functions/`: 各処理ステップのサンプル関数
  - `fetch_images.py`: URL/ローカルから入力画像を収集
  - `resize.py`: 画像の一括リサイズ
  - `triton_infer.py`: Triton Inference Server 呼び出し(ダミー可)
  - `filter.py`: スコア/属性でフィルタ
  - `aggregate.py`: 結果の集約/要約(JSON/CSV出力)
- `examples/steps_example.json`: LLM出力イメージの簡易サンプル
- `serving/llm_image_flow.py`: MLRun Serving Graph（オンライン推論）

前提
----
- Python 3.9+
- mlrun と kfp がインストール済みであること(ローカル実行の例)。
  - `pip install mlrun==1.* kfp==1.*` など。
- Triton を使わない場合でも、`triton_infer.py` はダミー応答で動作可能です。

使い方(ローカル最小例)
----------------------
1) プロジェクトを取得/作成

```
python - << 'PY'
import mlrun
project = mlrun.get_or_create_project("imageflowcanvas", context_dir="./mlrun")
print("project:", project.name, "dir:", project.get_artifact_uri(""))
PY
```

2) ワークフローを起動

```
python - << 'PY'
import json, mlrun
from pathlib import Path
from mlrun import get_or_create_project

project = get_or_create_project("imageflowcanvas", context_dir="./mlrun")

steps = json.loads(Path("mlrun/examples/steps_example.json").read_text())

run = project.run(
    name="llm_image_flow",
    workflow_path="workflows/llm_image_flow.py",
    arguments={
        "input_urls": [
            "https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg"
        ],
        "steps_json": json.dumps(steps),
        "triton_url": "http://triton:8000",  # ダミーでもOK
        "model_name": "yolov5",              # ダミーでもOK
    },
    local=True,  # ローカルで DryRun 的に動かす
)
print("workflow run id:", run.run_id)
PY
```

3) 出力
- 各関数は `artifacts/` に画像/JSON/CSV を出力します(実行時の作業ディレクトリ配下)。

Serving Graph（MockServerでのローカル検証）
----------------------------------------
Kubernetes なしで Serving Graph のロジックを検証できます。

```
python - << 'PY'
import json, mlrun
from mlrun import get_or_create_project

project = get_or_create_project("imageflowcanvas", context_dir="./mlrun")

# project.yaml の serving 関数を取得
fn = project.set_function("serving/llm_image_flow.py", name="serving-llm", kind="serving", image="mlrun/mlrun")

# モックサーバ（ローカル）を起動してテスト
server = fn.to_mock_server()

payload = {
    "input_urls": [
        "https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg"
    ],
    "steps": json.loads(open("mlrun/examples/steps_example.json").read())
}

resp = server.test("/", body=payload)
print("final:", json.dumps(resp.get("final_results"), ensure_ascii=False))
PY
```

備考: 実際にオンライン提供（HTTPエンドポイント化）するには、Kubernetes 上で MLRun Serving をデプロイするか、Nuclio へのデプロイを行います。

Docker Compose での起動
----------------------
本リポジトリの Compose に、 Serving 用の軽量HTTPサーバ（モック）を追加しました。

1) ビルドと起動

```
./scripts/build_services.sh     # mlrun-serving イメージを含めビルド
./scripts/run-compose.sh up     # 既存サービスと合わせて起動
```

2) ヘルスチェック/呼び出し

```
curl http://localhost:8085/health
curl -X POST http://localhost:8085/ \
  -H 'Content-Type: application/json' \
  -d '{"input_urls":["https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg"], "steps": {"steps": [{"name":"resize","params":{"width":640,"height":640,"keep_aspect":true}},{"name":"detect","params":{"simulate":true}},{"name":"filter","params":{"min_score":0.5}}]}}'
```

リクエストBody例（ファイルパス指定）:

```
{
  "input_urls": ["/workspace/test-qr-codes/sample.jpg"],
  "steps": {
    "steps": [
      {"name": "resize", "params": {"width": 640, "height": 640, "keep_aspect": true}},
      {"name": "detect", "params": {"simulate": true}},
      {"name": "filter", "params": {"min_score": 0.5}}
    ]
  }
}
```

補足:
- 画像ダウンロードが制限される環境では、`input_urls` にホスト側のローカルパスを指定してください。`mlrun-serving` コンテナに `/workspace` としてリポジトリルートがマウントされています。
- 本サーバは `serving/llm_image_flow.py` のチェーンを FastAPI で公開する最小構成です。将来的に MLRun の `to_mock_server()` を直接HTTP公開する方式に置き換え可能です。

備考
----
- 設計書にある既存 gRPC Executor 連携は、このサンプルでは `aggregate.py` が `final_results.json` を出力するところまでを想定しています。実運用連携は Backend 側の実装に合わせて Webhook/gRPC 呼び出し等を追加してください。
- KFP 上で動かす場合は、プロジェクト/イメージのビルドや権限設定が別途必要です。
 - Serving Graph はローカルの MockServer で検証可能ですが、本番運用は Kubernetes 環境（k3s/kind/k3d/EKS等）を推奨します。
