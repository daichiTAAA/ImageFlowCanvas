from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class WorkSessionStartRequest(BaseModel):
    device_name: str = Field(alias="deviceName")
    device_identifier: Optional[str] = Field(default=None, alias="deviceIdentifier")
    command: str
    normalized_command: Optional[str] = Field(default=None, alias="normalizedCommand")
    recognized_text: Optional[str] = Field(default=None, alias="recognizedText")
    confidence: float
    started_at: datetime = Field(alias="startedAt")
    session_hint: Optional[str] = Field(default=None, alias="sessionHint")
    network_quality: Optional[str] = Field(default=None, alias="networkQuality")
    battery_level: Optional[int] = Field(default=None, alias="batteryLevel")
    temperature_c: Optional[float] = Field(default=None, alias="temperatureC")
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")

    class Config:
        populate_by_name = True


class WorkSessionEndRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    device_name: str = Field(alias="deviceName")
    command: str
    normalized_command: Optional[str] = Field(default=None, alias="normalizedCommand")
    recognized_text: Optional[str] = Field(default=None, alias="recognizedText")
    confidence: float
    ended_at: datetime = Field(alias="endedAt")
    network_quality: Optional[str] = Field(default=None, alias="networkQuality")
    battery_level: Optional[int] = Field(default=None, alias="batteryLevel")
    temperature_c: Optional[float] = Field(default=None, alias="temperatureC")
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")

    class Config:
        populate_by_name = True


class DeviceStatusUpdate(BaseModel):
    device_identifier: Optional[str] = Field(default=None, alias="deviceIdentifier")
    state: str
    battery_level: Optional[int] = Field(default=None, alias="batteryLevel")
    temperature_c: Optional[float] = Field(default=None, alias="temperatureC")
    network_quality: Optional[str] = Field(default=None, alias="networkQuality")
    is_streaming: bool = Field(alias="isStreaming")
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")

    class Config:
        populate_by_name = True


class WorkSessionResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    device_id: str = Field(alias="deviceId")
    device_uuid: str = Field(alias="deviceUuid")
    device_identifier: Optional[str] = Field(
        default=None, alias="deviceIdentifier"
    )
    device_name: str = Field(alias="deviceName")
    status: str
    started_at: datetime = Field(alias="startedAt")
    ended_at: Optional[datetime] = Field(default=None, alias="endedAt")
    last_event: Optional[str] = Field(default=None, alias="lastEvent")

    class Config:
        populate_by_name = True


class DeviceStatusResponse(BaseModel):
    device_id: str = Field(alias="deviceId")
    device_uuid: str = Field(alias="deviceUuid")
    device_identifier: Optional[str] = Field(
        default=None, alias="deviceIdentifier"
    )
    device_name: str = Field(alias="deviceName")
    state: Optional[str]
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    battery_level: Optional[int] = Field(default=None, alias="batteryLevel")
    temperature_c: Optional[float] = Field(default=None, alias="temperatureC")
    network_quality: Optional[str] = Field(default=None, alias="networkQuality")
    is_streaming: bool = Field(alias="isStreaming")
    last_seen_at: Optional[datetime] = Field(default=None, alias="lastSeenAt")
    process_code: Optional[str] = Field(default=None, alias="processCode")
    process_name: Optional[str] = Field(default=None, alias="processName")

    class Config:
        populate_by_name = True


class WorkSessionListResponse(BaseModel):
    sessions: List[WorkSessionResponse]
