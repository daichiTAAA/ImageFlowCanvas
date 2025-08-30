from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


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


def handler(
    context=None,
    detections=None,
    steps_json: str = "{}",
    step_name: str = "aggregate",
):
    """検出結果の集約・要約。常に実行(steps_json未定義でも問題なし)。"""
    ctx = _ensure_ctx(context, "aggregate")
    det = _load_json(detections)

    label_counter = Counter()
    total = 0
    for it in det.get("items", []):
        total += 1
        for d in it.get("detections", []):
            label = d.get("label")
            if label:
                label_counter[label] += 1

    summary = {
        "num_items": total,
        "labels": dict(label_counter),
    }

    out_dir = Path("artifacts/aggregate")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "final_results.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    # ついでにCSVも出力
    csv_path = out_dir / "final_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "count"])
        for k, v in label_counter.items():
            writer.writerow([k, v])

    if ctx:
        ctx.log_artifact("final_results_json", local_path=str(json_path), format="json")
        ctx.log_artifact("final_results_csv", local_path=str(csv_path))
        ctx.log_result("labels", dict(label_counter))

    return {"final_results": str(json_path)}

