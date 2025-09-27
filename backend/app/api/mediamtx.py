from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.thinklet import ThinkletCommandEvent, ThinkletDevice, ThinkletWorkSession

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


def _whep_base() -> str:
    return os.getenv("MEDIAMTX_WHEP_BASE", "http://localhost:8889").rstrip("/")


UTC = timezone.utc
DEFAULT_SESSION_SPAN = timedelta(hours=4)
EVENT_LOOKBACK = timedelta(minutes=5)
EVENT_LOOKAHEAD = timedelta(minutes=2)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_utc(value)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (ValueError, OverflowError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return _ensure_utc(parsed)
    return None


def _isoformat(dt: Optional[datetime]) -> Optional[str]:
    ensured = _ensure_utc(dt)
    if ensured is None:
        return None
    return ensured.isoformat().replace("+00:00", "Z")


async def _attach_thinklet_metadata(
    device_identifier: str,
    segments: List[Dict[str, Any]],
    db: AsyncSession,
) -> None:
    if not device_identifier or not segments:
        return

    device_stmt = select(ThinkletDevice).where(
        ThinkletDevice.device_identifier == device_identifier
    )
    device_result = await db.execute(device_stmt)
    device = device_result.scalar_one_or_none()
    if device is None:
        return

    timestamps: List[Tuple[str, datetime]] = []
    for seg in segments:
        start_raw = seg.get("start")
        parsed = _parse_timestamp(start_raw)
        if parsed is None:
            continue
        timestamps.append((start_raw, parsed))

    if not timestamps:
        return

    earliest = min(ts for _, ts in timestamps) - EVENT_LOOKBACK
    latest = max(ts for _, ts in timestamps) + EVENT_LOOKAHEAD

    sessions_stmt = (
        select(ThinkletWorkSession)
        .where(
            ThinkletWorkSession.device_id == device.id,
            ThinkletWorkSession.started_at <= latest,
            or_(
                ThinkletWorkSession.ended_at.is_(None),
                ThinkletWorkSession.ended_at >= earliest,
            ),
        )
        .order_by(ThinkletWorkSession.started_at.asc())
    )
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    events_stmt = (
        select(ThinkletCommandEvent)
        .where(
            ThinkletCommandEvent.device_id == device.id,
            ThinkletCommandEvent.created_at >= earliest - EVENT_LOOKBACK,
            ThinkletCommandEvent.created_at <= latest + EVENT_LOOKAHEAD,
        )
        .order_by(ThinkletCommandEvent.created_at.asc())
    )
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    session_windows: List[Tuple[datetime, Optional[datetime], ThinkletWorkSession]] = []
    for session in sessions:
        start = _ensure_utc(session.started_at)
        if start is None:
            continue
        end = _ensure_utc(session.ended_at)
        if end is None:
            end = start + DEFAULT_SESSION_SPAN
        session_windows.append((start, end, session))

    event_windows: List[Tuple[datetime, ThinkletCommandEvent]] = []
    for event in events:
        created = _ensure_utc(event.created_at)
        if created is None:
            continue
        event_windows.append((created, event))

    event_windows.sort(key=lambda item: item[0])

    for raw_start, start_dt in timestamps:
        matched_session: Optional[ThinkletWorkSession] = None
        matched_session_start: Optional[datetime] = None
        matched_session_end: Optional[datetime] = None
        for window_start, window_end, session in session_windows:
            if start_dt < window_start:
                continue
            if window_end is not None and start_dt > window_end:
                continue
            matched_session = session
            matched_session_start = window_start
            matched_session_end = window_end
        matched_event: Optional[ThinkletCommandEvent] = None
        matched_event_ts: Optional[datetime] = None
        for event_time, event in event_windows:
            if event_time > start_dt + EVENT_LOOKAHEAD:
                break
            if event_time < start_dt - EVENT_LOOKBACK:
                continue
            if matched_event_ts is None or event_time >= matched_event_ts:
                matched_event = event
                matched_event_ts = event_time

        identifier = device.device_identifier or str(device.id)
        metadata: Dict[str, Any] = {
            "deviceId": identifier,
            "deviceIdentifier": identifier,
            "deviceUuid": str(device.id),
            "deviceName": device.device_name,
            "deviceLastState": device.last_state,
            "deviceLastSeenAt": _isoformat(device.last_seen_at),
        }

        if matched_session is not None:
            session_payload: Dict[str, Any] = {
                "id": str(matched_session.id),
                "status": matched_session.status,
                "startedAt": _isoformat(matched_session_start),
                "endedAt": _isoformat(matched_session.ended_at),
                "startCommand": matched_session.start_command,
                "startConfidence": matched_session.start_confidence,
                "endCommand": matched_session.end_command,
                "endConfidence": matched_session.end_confidence,
            }
            if matched_session.ended_at is None and matched_session_end is not None:
                session_payload["coverageEnd"] = _isoformat(matched_session_end)
            metadata["session"] = session_payload

        if matched_event is not None:
            metadata["lastEvent"] = {
                "command": matched_event.command,
                "normalizedCommand": matched_event.normalized_command,
                "recognizedText": matched_event.recognized_text,
                "confidence": matched_event.confidence,
                "source": matched_event.source,
                "timestamp": _isoformat(matched_event_ts),
            }

        for seg in segments:
            if seg.get("start") == raw_start:
                seg["thinklet"] = metadata
                seg["thinkletToken"] = (
                    f"{metadata.get('deviceId','')}|"
                    f"{metadata.get('deviceName','')}|"
                    f"{metadata.get('session', {}).get('id', '')}|"
                    f"{metadata.get('lastEvent', {}).get('timestamp', '')}"
                )
                break

    for seg in segments:
        seg.setdefault("thinkletToken", "")


@router.get("/streams", response_model=Dict[str, Any])
async def list_uplink_streams(page: int = 0, items_per_page: int = 100):
    """List active uplink streams (paths that match uplink/<deviceId>)."""
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
    patt = re.compile(r"^(uplink/.+|uplink-.+|[a-f0-9]{16})$")
    hls_base = _mediamtx_playback_base().rstrip("/")
    whep_base = _whep_base().rstrip("/")

    streams: List[Dict[str, Any]] = []
    for it in items:
        name = it.get("name") or it.get("path")
        if not name or not patt.match(name):
            continue
        if not name.startswith("uplink/"):
            continue
        device_id = name.split("/", 1)[1] if "/" in name else name
        streams.append({
            "path": name,
            "device_id": device_id,
            "state": it.get("state", "unknown"),
            "readers": it.get("readers", 0),
            "publishers": it.get("publishers", 0),
            "hls_url": f"{hls_base}/{name}/index.m3u8",
            "whep_url": f"{whep_base}/{name}/whep",
        })

    return {
        "items": streams,
        "total": len(streams),
        "hls_base": hls_base,
        "whep_base": whep_base,
    }


async def _read_recordings_payload(path: str, db: AsyncSession) -> Dict[str, Any]:
    if not path.startswith("uplink/"):
        raise HTTPException(status_code=404, detail="Path not found or no recordings")
    api = _mediamtx_base()
    record_data: Optional[Dict[str, Any]] = None

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{api}/v3/recordings/get/{path}")
            r.raise_for_status()
            record_data = r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Path not found or no recordings")
            raise HTTPException(status_code=502, detail=f"MediaMTX API error: {e}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"MediaMTX API error: {e}")

    hls_base = _mediamtx_playback_base().rstrip("/")
    segments = (record_data or {}).get("segments", [])
    for s in segments:
        s["hls_url"] = f"{hls_base}/{path}/index.m3u8"

    # Attach THINKLET metadata based on device identifier and timestamps
    device_identifier = path.split("/", 1)[1] if "/" in path else path
    await _attach_thinklet_metadata(device_identifier, segments, db)

    pb_priv = _playback_private_base()
    pb_pub = _playback_public_base()
    playback_items: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            lr = await client.get(f"{pb_priv}/list", params={"path": path})
            lr.raise_for_status()
            items = lr.json()
            for it in items:
                start = it.get("start")
                dur = it.get("duration")
                url = f"{pb_pub}/get?path={path}&start={start}&duration={dur}"
                playback_items.append({"start": start, "duration": dur, "url": url})
    except httpx.HTTPError:
        playback_items = []

    if playback_items:
        by_start = {it.get("start"): it for it in playback_items if it.get("start")}
        for s in segments:
            st = s.get("start")
            if st and st in by_start:
                target = by_start[st]
                s["playback_url"] = target.get("url")
                target.setdefault("thinklet", s.get("thinklet"))
                target.setdefault("thinkletToken", s.get("thinkletToken", ""))

    return {
        "path": path,
        "segments": segments,
        "hls_base": hls_base,
        "playback_base": pb_pub,
        "playback": playback_items,
    }


@router.get("/recordings/{path:path}", response_model=Dict[str, Any])
async def get_recordings(path: str, db: AsyncSession = Depends(get_db)):
    """List recordings for a given uplink path."""
    return await _read_recordings_payload(path, db)


@router.get("/recordings", response_model=Dict[str, Any])
async def list_recordings_index(
    page: int = 0,
    items_per_page: int = 200,
    db: AsyncSession = Depends(get_db),
):
    """Return a catalog of recordings grouped by path/device."""
    api = _mediamtx_base()
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(
                f"{api}/v3/recordings/list",
                params={"page": page, "itemsPerPage": items_per_page},
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"MediaMTX API error: {e}")

    items = data.get("items", []) or []
    catalog: List[Dict[str, Any]] = []
    for entry in items:
        raw_name = entry.get("name") or entry.get("path")
        if not raw_name:
            continue
        if not raw_name.startswith("uplink/"):
            continue
        segments_raw = entry.get("segments", []) or []
        segments: List[Dict[str, Any]] = []
        for seg in segments_raw:
            start = seg.get("start")
            if start is None:
                continue
            segments.append({"start": start if isinstance(start, str) else str(start)})
        segments.sort(key=lambda s: s.get("start") or "", reverse=True)
        segment_count = len(segments)
        catalog.append(
            {
                "path": raw_name,
                "device_id": raw_name.split("/", 1)[1] if "/" in raw_name else raw_name,
                "segment_count": segment_count,
                "latest_start": segments[0].get("start") if segment_count else None,
                "earliest_start": segments[-1].get("start") if segment_count else None,
                "segments": segments,
            }
        )

    device_ids = {item["device_id"] for item in catalog if item.get("device_id")}
    if device_ids:
        device_stmt = select(ThinkletDevice).where(
            ThinkletDevice.device_identifier.in_(device_ids)
        )
        device_result = await db.execute(device_stmt)
        device_map = {
            dev.device_identifier: dev for dev in device_result.scalars().all()
        }
        for entry in catalog:
            identifier = entry.get("device_id")
            device = device_map.get(identifier)
            if device:
                entry["device_name"] = device.device_name
                entry["device_last_state"] = device.last_state
                entry["device_last_seen_at"] = _isoformat(device.last_seen_at)

    return {
        "items": catalog,
        "total": data.get("itemCount", len(catalog)),
        "page_count": data.get("pageCount", 1),
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
