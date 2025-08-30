from __future__ import annotations

import io
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# -------------------------
# Utilities
# -------------------------


def _get_body(event) -> Dict[str, Any]:
    # MLRun Serving の event か、素の dict かを吸収
    if hasattr(event, "body"):
        return event.body or {}
    return event or {}


def _extract_step_cfg(steps: Dict[str, Any] | None, step_name: str) -> Dict[str, Any]:
    steps = steps or {}
    arr = steps.get("steps", [])
    for step in arr:
        if step.get("name") == step_name:
            return {"enabled": True, **(step.get("params") or {})}
    # 未指定なら無効ではなく「パススルー」扱い
    return {"enabled": False}


def _download(url: str, dst_dir: Path) -> Optional[Path]:
    dst_dir.mkdir(parents=True, exist_ok=True)
    if url.startswith("http://") or url.startswith("https://"):
        import requests  # type: ignore

        r = requests.get(url, timeout=30)
        r.raise_for_status()
        name = Path(url).name or "image.jpg"
        dst = dst_dir / name
        dst.write_bytes(r.content)
        return dst

    src = Path(url).expanduser()
    if src.is_dir():
        # ディレクトリ入力は最初の画像だけ拾う簡易版
        for p in src.iterdir():
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}:
                dst = dst_dir / p.name
                shutil.copy2(p, dst)
                return dst
        return None
    if src.is_file():
        dst = dst_dir / src.name
        shutil.copy2(src, dst)
        return dst
    return None


# -------------------------
# Steps
# -------------------------


class Fetch:
    def __init__(self, out_dir: str = "/tmp/serving/raw"):
        self.out_dir = Path(out_dir)

    def do(self, event):
        body = _get_body(event)
        input_urls: List[str] = body.get("input_urls") or []
        if not input_urls:
            raise ValueError("input_urls is required for Fetch step")

        items: List[Dict[str, Any]] = []
        for i, url in enumerate(input_urls):
            saved = _download(url, self.out_dir)
            if saved is None:
                continue
            items.append({"id": f"{i:04d}", "path": str(saved)})

        body["items"] = items
        return body


class Resize:
    def __init__(self):
        from PIL import Image  # noqa: F401  (validate dependency exists)

    def do(self, event):
        from PIL import Image

        body = _get_body(event)
        steps = body.get("steps") or body.get("steps_json")
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except Exception:
                steps = {}
        cfg = _extract_step_cfg(steps, "resize")
        if not cfg.get("enabled"):
            return body

        width = int(cfg.get("width", 640))
        height = int(cfg.get("height", 640))
        keep_aspect = bool(cfg.get("keep_aspect", True))

        out_items = []
        out_dir = Path("/tmp/serving/resized")
        out_dir.mkdir(parents=True, exist_ok=True)
        for it in body.get("items", []):
            src = Path(it["path"]).expanduser()
            if not src.exists():
                continue
            dst = out_dir / Path(src.name).with_suffix(".jpg")
            with Image.open(src) as im:
                if keep_aspect:
                    im = im.convert("RGB")
                    im.thumbnail((width, height), Image.LANCZOS)
                else:
                    im = im.convert("RGB").resize((width, height), Image.LANCZOS)
                im.save(dst, format="JPEG", quality=90)
            out_items.append({"id": it.get("id"), "path": str(dst)})

        body["items"] = out_items
        return body


class Detect:
    def __init__(self):
        pass

    def _simulate_detection(self, img_name: str) -> List[Dict[str, Any]]:
        random.seed(img_name)
        k = random.randint(1, 3)
        labels = ["person", "car", "bottle", "cat", "dog"]
        dets = []
        for _ in range(k):
            label = random.choice(labels)
            score = round(random.uniform(0.5, 0.95), 3)
            x1 = round(random.uniform(0.2, 0.4), 3)
            y1 = round(random.uniform(0.2, 0.4), 3)
            x2 = round(random.uniform(0.6, 0.8), 3)
            y2 = round(random.uniform(0.6, 0.8), 3)
            dets.append({"label": label, "score": score, "bbox": [x1, y1, x2, y2]})
        return dets

    def do(self, event):
        body = _get_body(event)
        steps = body.get("steps") or body.get("steps_json")
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except Exception:
                steps = {}
        cfg = _extract_step_cfg(steps, "detect")

        simulate = bool(cfg.get("simulate", True)) or not cfg.get("enabled", False)
        triton_url = body.get("triton_url") or cfg.get("triton_url")
        model_name = body.get("model_name") or cfg.get("model_name")

        results = []
        for it in body.get("items", []):
            if simulate or not (triton_url and model_name):
                dets = self._simulate_detection(Path(it["path"]).name)
            else:
                # 実運用: TritonにHTTP/gRPCで推論を投げる処理を実装
                # ここではダミーで simulate と同じ処理
                dets = self._simulate_detection(Path(it["path"]).name)
            results.append({"id": it.get("id"), "path": it.get("path"), "detections": dets})

        body["items"] = results
        return body


class Filter:
    def do(self, event):
        body = _get_body(event)
        steps = body.get("steps") or body.get("steps_json")
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except Exception:
                steps = {}
        cfg = _extract_step_cfg(steps, "filter")
        if not cfg.get("enabled", True):
            return body

        min_score = float(cfg.get("min_score", 0.5))
        label_in = cfg.get("label_in")
        label_ex = cfg.get("label_exclude") or cfg.get("label_not_in")

        filtered = []
        for it in body.get("items", []):
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

        body["items"] = filtered
        return body


class Aggregate:
    def do(self, event):
        from collections import Counter

        body = _get_body(event)
        cnt = Counter()
        for it in body.get("items", []):
            for d in it.get("detections", []):
                lbl = d.get("label")
                if lbl:
                    cnt[lbl] += 1

        body["final_results"] = {"labels": dict(cnt), "num_items": len(body.get("items", []))}
        return body


# -------------------------
# Serving graph entrypoint
# -------------------------


def init_context(context):
    """MLRun Serving Graph の初期化。

    リクエスト例:
      POST /  with JSON body
      {
        "input_urls": ["https://.../image.jpg"],
        "steps": { ...  (mlrun_server/examples/steps_example.json と同等) ... },
        "triton_url": "http://triton:8000",
        "model_name": "yolov5"
      }

    レスポンス例:
      { "final_results": {"labels": {"person": 1}, "num_items": 1}, "items": [...] }
    """
    # Serving Graph DSL: fetch -> resize -> detect -> filter -> aggregate -> respond
    graph = context.graph
    graph.to(Fetch()).to(Resize()).to(Detect()).to(Filter()).to(Aggregate())
    graph.respond()


# -------------------------
# Local dev helper (optional)
# -------------------------

if __name__ == "__main__":
    # 依存があれば、MLRun抜きでも直列に動かせる簡易テスト
    payload = {
        "input_urls": [
            "https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg"
        ],
        "steps": {
            "steps": [
                {"name": "resize", "params": {"width": 640, "height": 640, "keep_aspect": True}},
                {"name": "detect", "params": {"simulate": True}},
                {"name": "filter", "params": {"min_score": 0.5}}
            ]
        },
    }
    out = Aggregate().do(
        Filter().do(
            Detect().do(
                Resize().do(
                    Fetch().do(payload)
                )
            )
        )
    )
    print(json.dumps(out["final_results"], ensure_ascii=False, indent=2))
