from kfp import dsl
import mlrun


@dsl.pipeline(name="LLM Image Flow", description="LLM定義に基づく画像処理パイプライン")
def llm_image_flow(
    input_urls: list = None,
    steps_json: str = "{}",
    triton_url: str = "",
    model_name: str = "",
):
    """
    入力:
      - input_urls: 画像URL または ローカルパスの配列
      - steps_json: LLMが出力したステップ定義(JSON文字列)。
        例は `mlrun/examples/steps_example.json` を参照。
      - triton_url: Triton Inference Server のURL (例: http://triton:8000)
      - model_name: Triton上のモデル名 (例: yolov5)

    備考:
      - 各関数は `steps_json` と `step_name` を受け取り、対象ステップが
        無効/未定義の場合は透過的にパススルーします。
    """
    if input_urls is None:
        input_urls = []

    fetch = mlrun.run_function(
        "fetch-images",
        name="fetch_images",
        params={"input_urls": input_urls},
    )

    resize = mlrun.run_function(
        "resize",
        name="resize_images",
        params={
            "steps_json": steps_json,
            "step_name": "resize",
        },
        inputs={"images_manifest": fetch.outputs["images_manifest"]},
    )

    detect = mlrun.run_function(
        "triton-infer",
        name="detect_objects",
        params={
            "steps_json": steps_json,
            "step_name": "detect",
            "triton_url": triton_url,
            "model_name": model_name,
        },
        inputs={"images_manifest": resize.outputs["images_manifest"]},
    )

    filt = mlrun.run_function(
        "filter",
        name="filter_detections",
        params={
            "steps_json": steps_json,
            "step_name": "filter",
        },
        inputs={"detections": detect.outputs["detections"]},
    )

    mlrun.run_function(
        "aggregate",
        name="aggregate_results",
        params={
            "steps_json": steps_json,
            "step_name": "aggregate",
        },
        inputs={"detections": filt.outputs["detections"]},
    )

