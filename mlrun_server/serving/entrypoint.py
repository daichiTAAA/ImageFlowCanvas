from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pathlib import Path
import importlib.util


def _load_serving_chain():
    # Dynamically load serving/llm_image_flow.py to avoid name clash with the mlrun library
    project_dir = Path(os.environ.get("MLRUN_PROJECT_DIR", "/workspace/mlrun_server"))
    fallback_dir = Path("/opt/mlrun-app/mlrun_server")
    root = project_dir if (project_dir / "serving/llm_image_flow.py").exists() else fallback_dir
    mod_path = root / "serving/llm_image_flow.py"
    if not mod_path.exists():
        raise FileNotFoundError(f"serving graph not found: {mod_path}")

    spec = importlib.util.spec_from_file_location("ifc_serving_graph", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load serving graph module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    Fetch = getattr(module, "Fetch")
    Resize = getattr(module, "Resize")
    Detect = getattr(module, "Detect")
    Filter = getattr(module, "Filter")
    Aggregate = getattr(module, "Aggregate")

    def run_chain(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = Fetch().do(payload)
        data = Resize().do(data)
        data = Detect().do(data)
        data = Filter().do(data)
        data = Aggregate().do(data)
        return data

    return run_chain


def create_app() -> FastAPI:
    app = FastAPI(title="ImageFlowCanvas mlrun-serving (mock)")
    run_chain = _load_serving_chain()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/")
    async def serve_root(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "invalid JSON"})

        if not isinstance(body, dict):
            return JSONResponse(status_code=400, content={"error": "payload must be a JSON object"})

        try:
            result = run_chain(body)
            return JSONResponse(status_code=200, content=result)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    return app


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8085"))
    uvicorn.run(create_app(), host="0.0.0.0", port=port, log_level="info")
