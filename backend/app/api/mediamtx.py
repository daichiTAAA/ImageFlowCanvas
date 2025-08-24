from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
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


def _playback_private_base() -> str:
    # Internal base URL for the MediaMTX playback server (container-to-container)
    return os.getenv("MEDIAMTX_PLAYBACK_PRIVATE_BASE", "http://mediamtx:9996").rstrip("/")


def _playback_public_base() -> str:
    # Public base URL exposed to browsers
    return os.getenv("MEDIAMTX_PLAYBACK_PUBLIC_BASE", "http://localhost:9996").rstrip("/")


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

    # query playback server for precise playable timespans and URLs
    pb_priv = _playback_private_base()
    pb_pub = _playback_public_base()
    playback_items: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            lr = await client.get(f"{pb_priv}/list", params={"path": path})
            lr.raise_for_status()
            items = lr.json()
            # items is a list like [{ start, duration, url }]
            for it in items:
                start = it.get("start")
                dur = it.get("duration")
                # Rebuild URL with public base to ensure browser reachability
                url = f"{pb_pub}/get?path={path}&start={start}&duration={dur}"
                playback_items.append({"start": start, "duration": dur, "url": url})
    except httpx.HTTPError:
        # playback server may be disabled or unreachable; continue without it
        playback_items = []

    # best-effort: attach a playback_url to segments by matching start
    if playback_items:
        by_start = {it.get("start"): it for it in playback_items if it.get("start")}
        for s in segments:
            st = s.get("start")
            if st and st in by_start:
                s["playback_url"] = by_start[st]["url"]

    return {
        "path": path,
        "segments": segments,
        "hls_base": hls_base,
        "playback_base": pb_pub,
        "playback": playback_items,
    }


@router.delete("/recordings/segment", response_model=Dict[str, Any])
async def delete_recording_segment(path: str, start: str):
    """Delete a specific recording segment by path and start timestamp."""
    api = _mediamtx_base()
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.delete(f"{api}/v3/recordings/deletesegment", params={
                "path": path,
                "start": start,
            })
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 404:
                raise HTTPException(status_code=404, detail="segment not found")
            raise HTTPException(status_code=502, detail=f"MediaMTX delete error: {e}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"MediaMTX delete error: {e}")
    return {"status": "ok"}


async def _list_segment_starts(api_base: str, path: str) -> List[str]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{api_base}/v3/recordings/get/{path}")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        rec = r.json()
        return [s.get("start") for s in rec.get("segments", []) if s.get("start")]


def _rfc3339_cmp(a: str, b: str) -> int:
    # assumes normalized RFC3339 strings with Z or timezone; lexical compare is fine
    return -1 if a < b else (1 if a > b else 0)


@router.delete("/recordings/range", response_model=Dict[str, Any])
async def delete_recording_range(path: str, start: str, end: Optional[str] = None):
    """Delete all recording segments for a path whose start is within [start, end].
    If end is omitted, deletes only the segment exactly matching start.
    """
    api = _mediamtx_base()
    all_starts = await _list_segment_starts(api, path)
    if not all_starts:
        return {"deleted": 0, "failed": []}
    to_delete: List[str] = []
    if end:
        s0, e0 = start, end
        for st in all_starts:
            if _rfc3339_cmp(s0, st) <= 0 and _rfc3339_cmp(st, e0) <= 0:
                to_delete.append(st)
    else:
        to_delete = [st for st in all_starts if st == start]

    deleted = 0
    failed: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for st in to_delete:
            try:
                r = await client.delete(f"{api}/v3/recordings/deletesegment", params={"path": path, "start": st})
                r.raise_for_status()
                deleted += 1
            except httpx.HTTPError as e:
                failed.append({"start": st, "error": str(e)})
    return {"deleted": deleted, "failed": failed}


@router.delete("/recordings/all", response_model=Dict[str, Any])
async def delete_recordings_all(path: str):
    """Delete all recording segments for a given path."""
    api = _mediamtx_base()
    all_starts = await _list_segment_starts(api, path)
    if not all_starts:
        return {"deleted": 0, "failed": []}
    deleted = 0
    failed: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for st in all_starts:
            try:
                r = await client.delete(f"{api}/v3/recordings/deletesegment", params={"path": path, "start": st})
                r.raise_for_status()
                deleted += 1
            except httpx.HTTPError as e:
                failed.append({"start": st, "error": str(e)})
    return {"deleted": deleted, "failed": failed}
