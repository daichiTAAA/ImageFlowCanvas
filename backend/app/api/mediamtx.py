from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import os
import re
import httpx


router = APIRouter()


def _mediamtx_base() -> str:
    # Control API base (in-cluster DNS)
    return os.getenv("MEDIAMTX_API_BASE", "http://mediamtx:9997")


def _mediamtx_playback_base() -> str:
    # Public HLS base used by browsers
    return os.getenv("MEDIAMTX_HLS_BASE", "http://localhost:8888")


@router.get("/streams", response_model=Dict[str, Any])
async def list_thinklet_streams(page: int = 0, items_per_page: int = 100):
    """List active thinklet streams (paths that match thinklet/<deviceId>)."""
    api = _mediamtx_base()
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{api}/v3/paths/list", params={
                "page": page,
                "itemsPerPage": items_per_page,
            })
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"MediaMTX API error: {e}")

    items = data.get("items", [])
    patt = re.compile(r"^(thinklet/.+|thinklet-.+|[a-f0-9]{16})$")
    hls_base = _mediamtx_playback_base().rstrip("/")

    streams: List[Dict[str, Any]] = []
    for it in items:
        name = it.get("name") or it.get("path")
        if not name or not patt.match(name):
            continue
        if "/" in name:
            device_id = name.split("/", 1)[1]
        elif name.startswith("thinklet-"):
            device_id = name.split("thinklet-",1)[1]
        else:
            device_id = name
        streams.append({
            "path": name,
            "device_id": device_id,
            "state": it.get("state", "unknown"),
            "readers": it.get("readers", 0),
            "publishers": it.get("publishers", 0),
            "hls_url": f"{hls_base}/{name}/index.m3u8",
        })

    return {
        "items": streams,
        "total": len(streams),
        "hls_base": hls_base,
    }


@router.get("/recordings/{path:path}", response_model=Dict[str, Any])
async def get_recordings(path: str):
    """List recordings for a given thinklet path."""
    api = _mediamtx_base()
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{api}/v3/recordings/get/{path}")
            r.raise_for_status()
            rec = r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Path not found or no recordings")
            raise HTTPException(status_code=502, detail=f"MediaMTX API error: {e}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"MediaMTX API error: {e}")

    # annotate playback URLs for each segment
    hls_base = _mediamtx_playback_base().rstrip("/")
    segments = rec.get("segments", [])
    for s in segments:
        # MediaMTX returns relative file names; provide HLS base per path
        s["hls_url"] = f"{hls_base}/{path}/index.m3u8"

    return {"path": path, "segments": segments, "hls_base": hls_base}
