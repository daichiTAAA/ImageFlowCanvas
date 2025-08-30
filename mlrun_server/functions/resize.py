from __future__ import annotations

import json
import os
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
        # MLRun DataItem を想定
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
    images_manifest=None,
    steps_json: str = "{}",
    step_name: str = "resize",
):
    """画像リサイズ。該当ステップが無効ならパススルー。

    受け取り: images_manifest(JSON) with items: [{id, path}]
    出力: `images_manifest`(JSON) + `resized_images`(dir)
    """
    from PIL import Image

    ctx = _ensure_ctx(context, "resize")
    cfg = _extract_step_cfg(steps_json, step_name)
    manifest = _load_json(images_manifest)

    out_dir = Path("artifacts/resized")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not cfg.get("enabled"):
        # パススルー: マニフェストだけ再出力
        passthrough = out_dir / "images_manifest.json"
        Path(passthrough).write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        if ctx:
            ctx.log_artifact("resized_images", local_path=str(out_dir))
            ctx.log_artifact("images_manifest", local_path=str(passthrough), format="json")
        return {"images_manifest": str(passthrough)}

    width = int(cfg.get("width", 640))
    height = int(cfg.get("height", 640))
    keep_aspect = bool(cfg.get("keep_aspect", True))

    updated_items = []
    for item in manifest.get("items", []):
        src = Path(item["path"]).expanduser()
        if not src.exists():
            if ctx:
                ctx.logger.warning(f"missing image: {src}")
            continue
        dst = out_dir / Path(src.name).with_suffix(".jpg")
        with Image.open(src) as im:
            if keep_aspect:
                im = im.convert("RGB")
                im.thumbnail((width, height), Image.LANCZOS)
            else:
                im = im.convert("RGB").resize((width, height), Image.LANCZOS)
            im.save(dst, format="JPEG", quality=90)
        updated_items.append({"id": item.get("id"), "path": str(dst.resolve())})

    new_manifest = {"items": updated_items}
    manifest_path = out_dir / "images_manifest.json"
    manifest_path.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2))

    if ctx:
        ctx.log_artifact("resized_images", local_path=str(out_dir))
        ctx.log_artifact("images_manifest", local_path=str(manifest_path), format="json")
        ctx.log_result("num_images", len(updated_items))

    return {"images_manifest": str(manifest_path)}

