from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple, Set

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.thinklet import ThinkletDevice, ThinkletWorkSession, ThinkletCommandEvent
from app.models.inspection import DeviceProcessMapping, ProcessMaster
from app.schemas.thinklet import (
    WorkSessionStartRequest,
    WorkSessionEndRequest,
    DeviceStatusUpdate,
    WorkSessionResponse,
    WorkSessionListResponse,
    DeviceStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_device_by_name(db: AsyncSession, device_name: str) -> Optional[ThinkletDevice]:
    stmt = select(ThinkletDevice).where(
        func.lower(ThinkletDevice.device_name) == device_name.lower()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _ensure_device(
    db: AsyncSession, device_name: str, device_identifier: Optional[str]
) -> ThinkletDevice:
    existing = await _get_device_by_name(db, device_name)
    if existing:
        if device_identifier and not existing.device_identifier:
            existing.device_identifier = device_identifier
        return existing

    device = ThinkletDevice(
        device_name=device_name,
        device_identifier=device_identifier,
        last_state="IDLE",
        last_seen_at=datetime.utcnow(),
    )
    db.add(device)
    await db.flush()
    return device


async def _get_process_info(
    db: AsyncSession, device_identifier: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    if not device_identifier:
        return None, None

    stmt = (
        select(DeviceProcessMapping.process_code, ProcessMaster.process_name)
        .outerjoin(
            ProcessMaster,
            ProcessMaster.process_code == DeviceProcessMapping.process_code,
        )
        .where(DeviceProcessMapping.device_id == device_identifier)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None, None
    return row[0], row[1]

def _as_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _device_identifier(device: ThinkletDevice) -> str:
    return device.device_identifier or str(device.id)


def _to_session_response(
    session: ThinkletWorkSession, device: ThinkletDevice
) -> WorkSessionResponse:
    return WorkSessionResponse(
        sessionId=str(session.id),
        deviceId=_device_identifier(device),
        deviceUuid=str(device.id),
        deviceIdentifier=device.device_identifier,
        deviceName=device.device_name,
        status=session.status,
        startedAt=session.started_at,
        endedAt=session.ended_at,
        lastEvent=session.end_command or session.start_command,
    )


def _to_device_response(
    device: ThinkletDevice,
    process_code: Optional[str] = None,
    process_name: Optional[str] = None,
) -> DeviceStatusResponse:
    return DeviceStatusResponse(
        deviceId=_device_identifier(device),
        deviceUuid=str(device.id),
        deviceIdentifier=device.device_identifier,
        deviceName=device.device_name,
        state=device.last_state,
        sessionId=str(device.last_session_id) if device.last_session_id else None,
        batteryLevel=device.battery_level,
        temperatureC=device.temperature_c,
        networkQuality=device.network_quality,
        isStreaming=device.is_streaming,
        lastSeenAt=device.last_seen_at,
        processCode=process_code,
        processName=process_name,
    )


def _merge_metadata(base: Optional[Dict[str, Any]], extra: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    metadata: Dict[str, Any] = dict(base or {})
    for key, value in extra.items():
        if value is not None:
            metadata[key] = value
    return metadata or None


@router.post("/work-sessions/start", response_model=WorkSessionResponse)
async def start_work_session(
    payload: WorkSessionStartRequest,
    db: AsyncSession = Depends(get_db),
):
    device = await _ensure_device(db, payload.device_name, payload.device_identifier)

    # Close existing open session if present
    stmt = (
        select(ThinkletWorkSession)
        .where(
            ThinkletWorkSession.device_id == device.id,
            ThinkletWorkSession.status == "OPEN",
        )
        .order_by(ThinkletWorkSession.started_at.desc())
    )
    result = await db.execute(stmt)
    existing_session = result.scalar_one_or_none()
    if existing_session:
        existing_session.status = "CLOSED"
        if existing_session.ended_at is None:
            existing_session.ended_at = payload.started_at

    session = ThinkletWorkSession(
        device_id=device.id,
        started_at=_as_naive_utc(payload.started_at),
        status="OPEN",
        start_command=payload.command,
        start_confidence=payload.confidence,
        start_recognized_text=payload.recognized_text,
        metadata_=_merge_metadata(
            payload.metadata,
            {
                "networkQuality": payload.network_quality,
                "batteryLevel": payload.battery_level,
                "temperatureC": payload.temperature_c,
            },
        ),
    )
    db.add(session)
    await db.flush()

    event = ThinkletCommandEvent(
        device_id=device.id,
        session_id=session.id,
        command=payload.command,
        normalized_command=payload.normalized_command,
        confidence=payload.confidence,
        recognized_text=payload.recognized_text,
        metadata_=_merge_metadata(
            payload.metadata,
            {
                "networkQuality": payload.network_quality,
                "batteryLevel": payload.battery_level,
                "temperatureC": payload.temperature_c,
            },
        ),
        source="voice",
    )
    db.add(event)

    device.last_state = "WORKING"
    device.last_session_id = session.id
    device.battery_level = payload.battery_level
    device.temperature_c = payload.temperature_c
    device.network_quality = payload.network_quality
    device.is_streaming = True
    device.last_seen_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)
    await db.refresh(device)

    return _to_session_response(session, device)


@router.post("/work-sessions/end", response_model=WorkSessionResponse)
async def end_work_session(
    payload: WorkSessionEndRequest,
    db: AsyncSession = Depends(get_db),
):
    device = await _get_device_by_name(db, payload.device_name)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")

    session: Optional[ThinkletWorkSession] = None
    if payload.session_id:
        try:
            session_uuid = uuid.UUID(payload.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid sessionId")
        stmt = select(ThinkletWorkSession).where(ThinkletWorkSession.id == session_uuid)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
    if session is None:
        stmt = (
            select(ThinkletWorkSession)
            .where(
                ThinkletWorkSession.device_id == device.id,
                ThinkletWorkSession.status == "OPEN",
            )
            .order_by(ThinkletWorkSession.started_at.desc())
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="active session not found")

    session.status = "CLOSED"
    session.ended_at = _as_naive_utc(payload.ended_at)
    session.end_command = payload.command
    session.end_confidence = payload.confidence
    session.end_recognized_text = payload.recognized_text
    session.metadata_ = _merge_metadata(
        session.metadata_,
        {
            "endMetadata": payload.metadata,
            "networkQuality": payload.network_quality,
            "batteryLevel": payload.battery_level,
            "temperatureC": payload.temperature_c,
        },
    )

    event = ThinkletCommandEvent(
        device_id=device.id,
        session_id=session.id,
        command=payload.command,
        normalized_command=payload.normalized_command,
        confidence=payload.confidence,
        recognized_text=payload.recognized_text,
        metadata_=_merge_metadata(
            payload.metadata,
            {
                "networkQuality": payload.network_quality,
                "batteryLevel": payload.battery_level,
                "temperatureC": payload.temperature_c,
            },
        ),
        source="voice",
    )
    db.add(event)

    device.last_state = "IDLE"
    device.last_session_id = None
    device.battery_level = payload.battery_level
    device.temperature_c = payload.temperature_c
    device.network_quality = payload.network_quality
    device.is_streaming = False
    device.last_seen_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)
    await db.refresh(device)

    return _to_session_response(session, device)


@router.get("/work-sessions/{session_id}", response_model=WorkSessionResponse)
async def get_work_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(ThinkletWorkSession).where(ThinkletWorkSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    device_stmt = select(ThinkletDevice).where(ThinkletDevice.id == session.device_id)
    device_result = await db.execute(device_stmt)
    device = device_result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    return _to_session_response(session, device)


@router.get("/work-sessions/status", response_model=WorkSessionListResponse)
async def list_active_sessions(db: AsyncSession = Depends(get_db)):
    stmt = select(ThinkletWorkSession, ThinkletDevice).join(
        ThinkletDevice, ThinkletDevice.id == ThinkletWorkSession.device_id
    ).where(ThinkletWorkSession.status == "OPEN")

    result = await db.execute(stmt)
    rows = result.all()
    sessions = [
        _to_session_response(session=row[0], device=row[1]) for row in rows
    ]
    return WorkSessionListResponse(sessions=sessions)


@router.get("/devices/status", response_model=List[DeviceStatusResponse])
async def list_device_statuses(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            ThinkletDevice,
            DeviceProcessMapping.process_code,
            ProcessMaster.process_name,
        )
        .outerjoin(
            DeviceProcessMapping,
            DeviceProcessMapping.device_id == ThinkletDevice.device_identifier,
        )
        .outerjoin(
            ProcessMaster,
            ProcessMaster.process_code == DeviceProcessMapping.process_code,
        )
        .order_by(ThinkletDevice.device_name)
    )
    result = await db.execute(stmt)
    responses: List[DeviceStatusResponse] = []
    seen: Set[str] = set()
    for device, process_code, process_name in result.all():
        key = device.device_identifier or str(device.id)
        if key in seen:
            continue
        seen.add(key)
        responses.append(_to_device_response(device, process_code, process_name))
    return responses


@router.post("/devices/{device_name}/status", response_model=DeviceStatusResponse)
async def update_device_status(
    device_name: str,
    payload: DeviceStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    device = await _ensure_device(db, device_name, payload.device_identifier)

    device.last_state = payload.state
    if payload.session_id:
        try:
            device.last_session_id = uuid.UUID(payload.session_id)
        except ValueError:
            logger.warning("Invalid sessionId in status update: %s", payload.session_id)
    else:
        device.last_session_id = None
    device.battery_level = payload.battery_level
    device.temperature_c = payload.temperature_c
    device.network_quality = payload.network_quality
    device.is_streaming = payload.is_streaming
    device.last_seen_at = _as_naive_utc(payload.timestamp)
    device.metadata_ = _merge_metadata(device.metadata_, payload.metadata or {})

    event = ThinkletCommandEvent(
        device_id=device.id,
        session_id=device.last_session_id,
        command=payload.state,
        normalized_command=None,
        confidence=None,
        recognized_text=None,
        metadata_=_merge_metadata(payload.metadata, {"source": "device-status"}),
        source="status",
    )
    db.add(event)

    await db.commit()
    await db.refresh(device)

    process_code, process_name = await _get_process_info(
        db, device.device_identifier
    )

    return _to_device_response(device, process_code, process_name)
