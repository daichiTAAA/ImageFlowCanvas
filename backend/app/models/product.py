from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    Date,
    DateTime,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class ProductMaster(Base):
    __tablename__ = "product_master"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id = Column(String(100), nullable=False)
    instruction_id = Column(String(100), nullable=False)
    product_type = Column(String(100), nullable=False)
    machine_number = Column(String(100), nullable=False)
    production_date = Column(Date, nullable=False)
    monthly_sequence = Column(Integer, nullable=False)

    qr_raw_data = Column(Text)
    status = Column(String(50), nullable=False, default="ACTIVE")
    is_cached = Column(Boolean, nullable=False, default=True)
    server_sync_status = Column(String(50), nullable=False, default="SYNCED")

    access_count = Column(Integer, nullable=False, default=0)
    last_accessed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_product_master_work_order", "work_order_id"),
        Index("idx_product_master_instruction", "instruction_id"),
        Index("idx_product_master_product_type", "product_type"),
        Index("idx_product_master_machine_number", "machine_number"),
        Index(
            "idx_product_master_unique_key",
            "work_order_id",
            "instruction_id",
            "machine_number",
            "monthly_sequence",
            unique=True,
        ),
    )

