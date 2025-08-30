ImageFlowCanvas mlrun サンプル（Serving）
=======================================

このフォルダは「docs/0300_設計_アプローチ1/0310_LLM連携画像処理パイプライン設計.md」を元に、オンライン推論向けの MLRun Serving Graph 実装を示します。LLM が生成したパイプライン定義(JSON)を入力として、画像取得 → 前処理 → AI 検出(Triton 想定) → フィルタ → 集約 → 結果返却を行います。

重要: 旧来の KFP/MLRun ワークフロー（mlrun/workflows 配下）は削除し、Serving 構成で統一しました。

構成
----
- `project.yaml`: MLRun Project 定義（Serving の依存ライブラリ管理など）
- `serving/llm_image_flow.py`: MLRun Serving Graph（オンライン推論の処理チェーン）
- `serving/entrypoint.py`: FastAPI ベースの軽量 HTTP サーバ（Docker Compose で起動）
- `functions/`: ステップ処理のリファレンス実装（Serving に反映済み。バッチ用途にも流用可）
  - `fetch_images.py`, `resize.py`, `triton_infer.py`, `filter.py`, `aggregate.py`
- `examples/steps_example.json`: LLM 出力イメージの簡易サンプル

前提
----
- Docker / Docker Compose が利用可能であること。
- Triton を使わない場合でも、Detect ステップは `simulate: true` 指定でダミー応答で動作可能です。

Serving Graph（参考: MLRun MockServer でのローカル検証）
------------------------------------------------------
Kubernetes なしでも MLRun の `to_mock_server()` で Serving ロジックを検証できます（任意）。

```
python - << 'PY'
import json, mlrun
from mlrun import get_or_create_project

project = get_or_create_project("imageflowcanvas", context_dir="./mlrun")
fn = project.set_function("serving/llm_image_flow.py", name="serving-llm", kind="serving", image="mlrun/mlrun")
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

Docker Compose での起動
----------------------
本リポジトリの Compose に、Serving 用の軽量 HTTP サーバ（FastAPI ベース）を追加しました。

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

リクエスト Body 例（ファイルパス指定）:

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
- 本サーバは `serving/llm_image_flow.py` のチェーンを FastAPI で公開する最小構成です。

備考
----
- 設計書にある既存 gRPC Executor 連携は、このサンプルでは `aggregate.py` が `final_results.json` を出力するところまでを想定しています。実運用連携は Backend 側の実装に合わせて Webhook/gRPC 呼び出し等を追加してください。
- Serving Graph はローカルの MockServer で検証可能ですが、本番運用は Docker Compose または Kubernetes 環境での提供を想定します。
