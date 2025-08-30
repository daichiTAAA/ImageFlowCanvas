from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


def _ensure_ctx(context, name: str):
    try:
        import mlrun

        return context or mlrun.get_or_create_ctx(name)
    except Exception:
        return context


def _mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _download(url: str, dst: Path) -> Path:
    if url.startswith("http://") or url.startswith("https://"):
        import requests  # type: ignore

        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dst.write_bytes(r.content)
        return dst
    # ローカルパス
    src = Path(url)
    if src.is_dir():
        # ディレクトリの場合は中の画像をコピー
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
        copied = None
        for file in src.iterdir():
            if file.suffix.lower() in exts and file.is_file():
                copied = dst.parent / file.name
                shutil.copy2(file, copied)
        return copied or dst
    if src.is_file():
        shutil.copy2(src, dst)
        return dst
    raise FileNotFoundError(f"input not found: {url}")


@dataclass
class ImageItem:
    id: str
    path: str


def handler(
    context=None,
    input_urls: List[str] | None = None,
    output_dir: str = "artifacts/raw",
):
    """画像を取得し、マニフェスト(JSON)を出力する。

    - input_urls: HTTP(S) URL または ローカルファイル/ディレクトリのパス
    - output_dir: 画像と `images_manifest.json` を配置するディレクトリ
    """
    ctx = _ensure_ctx(context, "fetch_images")
    input_urls = input_urls or []
    if not input_urls:
        raise ValueError("input_urls must not be empty")

    out_dir = _mkdir(Path(output_dir))
    images: List[ImageItem] = []

    for i, url in enumerate(input_urls):
        name = Path(url).name or f"img_{i:04d}.jpg"
        dst = out_dir / name
        try:
            saved = _download(url, dst)
            if saved is None:
                continue
            images.append(ImageItem(id=f"{i:04d}", path=str(saved.resolve())))
        except Exception as e:
            if ctx:
                ctx.logger.warning(f"failed to fetch {url}: {e}")
            else:
                print(f"[warn] failed to fetch {url}: {e}", file=sys.stderr)

    manifest_path = out_dir / "images_manifest.json"
    manifest = {"items": [img.__dict__ for img in images]}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    if ctx:
        ctx.log_artifact("raw_images", local_path=str(out_dir))
        ctx.log_artifact("images_manifest", local_path=str(manifest_path), format="json")
        ctx.log_result("num_images", len(images))

    return {"images_manifest": str(manifest_path)}

