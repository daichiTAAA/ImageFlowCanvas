import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class ThinkletDevice(Base):
    __tablename__ = "thinklet_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name = Column(String(64), nullable=False, unique=True, index=True)
    device_identifier = Column(String(128), nullable=True, unique=True)

    last_state = Column(String(32), nullable=True)
    last_session_id = Column(UUID(as_uuid=True), nullable=True)
    battery_level = Column(Integer, nullable=True)
    temperature_c = Column(Float, nullable=True)
    network_quality = Column(String(32), nullable=True)
    is_streaming = Column(Boolean, nullable=False, default=False)
    last_seen_at = Column(DateTime, nullable=True)

    metadata_ = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    process_mappings = relationship(
        "DeviceProcessMapping",
        back_populates="thinklet_device",
        cascade="all, delete-orphan",
        lazy="selectin",
        primaryjoin="ThinkletDevice.device_identifier==DeviceProcessMapping.device_id",
    )


class ThinkletWorkSession(Base):
    __tablename__ = "thinklet_work_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("thinklet_devices.id"), nullable=False, index=True)

    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="OPEN", index=True)

    start_command = Column(String(64), nullable=True)
    start_confidence = Column(Float, nullable=True)
    start_recognized_text = Column(Text, nullable=True)

    end_command = Column(String(64), nullable=True)
    end_confidence = Column(Float, nullable=True)
    end_recognized_text = Column(Text, nullable=True)

    metadata_ = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_thinklet_sessions_device_status", "device_id", "status"),
    )


class ThinkletCommandEvent(Base):
    __tablename__ = "thinklet_command_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("thinklet_devices.id"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("thinklet_work_sessions.id"), nullable=True, index=True)

    command = Column(String(64), nullable=False)
    normalized_command = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    recognized_text = Column(Text, nullable=True)
    source = Column(String(32), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    metadata_ = Column(JSONB, nullable=True)
