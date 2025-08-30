from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List


def _ensure_ctx(context, name: str):
    try:
        import mlrun

        return context or mlrun.get_or_create_ctx(name)
    except Exception:
        return context


def _load_json(data):
    try:
        return json.loads(data.get())
    except Exception:
        return json.loads(Path(str(data)).read_text())


def _extract_step_cfg(steps_json: str, step_name: str) -> Dict[str, Any]:
    try:
        obj = json.loads(steps_json or "{}")
    except Exception:
        obj = {}
    for step in obj.get("steps", []):
        if step.get("name") == step_name:
            return {"enabled": True, **(step.get("params") or {})}
    return {"enabled": False}


def _simulate_detection(img_path: Path) -> List[Dict[str, Any]]:
    # 簡易ダミー: 中央付近に1~3個のボックスを生成
    random.seed(img_path.name)
    k = random.randint(1, 3)
    labels = ["person", "car", "bottle", "cat", "dog"]
    dets = []
    for i in range(k):
        label = random.choice(labels)
        score = round(random.uniform(0.5, 0.95), 3)
        # ダミーの正規化座標 [x1,y1,x2,y2]
        x1 = round(random.uniform(0.2, 0.4), 3)
        y1 = round(random.uniform(0.2, 0.4), 3)
        x2 = round(random.uniform(0.6, 0.8), 3)
        y2 = round(random.uniform(0.6, 0.8), 3)
        dets.append({"label": label, "score": score, "bbox": [x1, y1, x2, y2]})
    return dets


def handler(
    context=None,
    images_manifest=None,
    steps_json: str = "{}",
    step_name: str = "detect",
    triton_url: str = "",
    model_name: str = "",
):
    """Triton推論ステップ(ダミー可)。

    入力: images_manifest(JSON) -> items[{id, path}]
    出力: detections(JSON)
    """
    ctx = _ensure_ctx(context, "triton_infer")
    cfg = _extract_step_cfg(steps_json, step_name)
    enabled = cfg.get("enabled", False)
    simulate = bool(cfg.get("simulate", True)) or not enabled

    manifest = _load_json(images_manifest)
    out_dir = Path("artifacts/detect")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for item in manifest.get("items", []):
        img_path = Path(item["path"]).expanduser()
        dets: List[Dict[str, Any]]
        if simulate:
            dets = _simulate_detection(img_path)
        else:
            # 実運用: Triton に対して推論リクエストを実施
            # ここでは最小限の枠のみ。モデル依存の前後処理はプロジェクト要件に合わせて実装してください。
            import requests  # type: ignore

            if not triton_url or not model_name:
                raise ValueError("triton_url and model_name are required for real inference")
            # NOTE: 実際のエンドポイントはモデル/サーバ設定に依存します。ここではダミーの呼び出し。
            # requests.post(f"{triton_url}/v2/models/{model_name}/infer", json=payload)
            dets = _simulate_detection(img_path)  # フォールバック: ダミー

        results.append({"id": item.get("id"), "path": str(img_path.resolve()), "detections": dets})

    det_path = out_dir / "detections.json"
    det_path.write_text(json.dumps({"items": results}, ensure_ascii=False, indent=2))

    if ctx:
        ctx.log_artifact("detections", local_path=str(det_path), format="json")
        ctx.log_result("num_items", len(results))

    return {"detections": str(det_path)}

