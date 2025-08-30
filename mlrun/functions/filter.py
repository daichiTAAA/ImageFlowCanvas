from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    step_name: str = "filter",
):
    """検出結果のフィルタリング。該当ステップが無効ならパススルー。"""
    ctx = _ensure_ctx(context, "filter")
    cfg = _extract_step_cfg(steps_json, step_name)
    enabled = cfg.get("enabled", False)

    det = _load_json(detections)
    items = det.get("items", [])

    if not enabled:
        # パススルー
        out_dir = Path("artifacts/filter")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "detections.json"
        out_path.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2))
        if ctx:
            ctx.log_artifact("detections", local_path=str(out_path), format="json")
        return {"detections": str(out_path)}

    min_score = float(cfg.get("min_score", 0.5))
    label_in: Optional[List[str]] = cfg.get("label_in")
    label_ex: Optional[List[str]] = cfg.get("label_exclude") or cfg.get("label_not_in")

    filtered = []
    for it in items:
        dets = []
        for d in it.get("detections", []):
            if d.get("score", 0.0) < min_score:
                continue
            label = d.get("label")
            if label_in and label not in label_in:
                continue
            if label_ex and label in label_ex:
                continue
            dets.append(d)
        filtered.append({"id": it.get("id"), "path": it.get("path"), "detections": dets})

    out_dir = Path("artifacts/filter")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "detections.json"
    out_path.write_text(json.dumps({"items": filtered}, ensure_ascii=False, indent=2))

    if ctx:
        ctx.log_artifact("detections", local_path=str(out_path), format="json")
        ctx.log_result("num_items", len(filtered))

    return {"detections": str(out_path)}

