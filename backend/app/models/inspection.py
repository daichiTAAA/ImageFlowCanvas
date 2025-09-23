"""
検査関連のデータベースモデル
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Float,
    JSON,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class inspectionInstruction(Base):
    """検査指示マスタ"""

    __tablename__ = "inspection_instructions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    product_name = Column(String(255))
    # 型式グループ紐付け（product_code単位の管理を簡素化）
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("product_code_groups.id"), nullable=True
    )
    group_name = Column(String(255))
    version = Column(String(50), nullable=False, default="1.0")
    process_code = Column(
        String(100)
    )  # FK to process_masters.process_code (added vNEXT)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))

    # リレーション
    group = relationship("ProductTypeGroup", back_populates="inspection_instructions")
    inspection_items = relationship(
        "InspectionItem", back_populates="instruction", cascade="all, delete-orphan"
    )
    inspection_executions = relationship(
        "InspectionExecution", back_populates="instruction"
    )

    # インデックス
    __table_args__ = (
        Index("idx_inspection_instructions_group_id", "group_id"),
        Index("idx_inspection_instructions_process_code", "process_code"),
        Index("idx_inspection_instructions_created_at", "created_at"),
    )


class ProductTypeGroup(Base):
    """型式グループ（複数の型式コードをまとめる）"""

    __tablename__ = "product_code_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    group_code = Column(String(100), unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))

    # リレーション
    members = relationship(
        "ProductTypeGroupMember", back_populates="group", cascade="all, delete-orphan"
    )
    inspection_instructions = relationship(
        "inspectionInstruction", back_populates="group"
    )

    __table_args__ = (
        Index("idx_product_code_groups_name", "name"),
        Index("idx_product_code_groups_group_code", "group_code"),
    )


class ProcessMaster(Base):
    """工程マスタ"""

    __tablename__ = "process_masters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_code = Column(String(100), unique=True, nullable=False)
    process_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    device_mappings = relationship(
        "DeviceProcessMapping",
        back_populates="process",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_process_masters_code", "process_code"),
        Index("idx_process_masters_name", "process_name"),
    )


class DeviceProcessMapping(Base):
    """カメラ device_id と工程コードの紐付け"""

    __tablename__ = "device_process_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), unique=True, nullable=False)
    process_code = Column(
        String(100),
        ForeignKey("process_masters.process_code", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    process = relationship(
        "ProcessMaster",
        back_populates="device_mappings",
        lazy="joined",
    )

    __table_args__ = (
        Index("idx_device_process_mappings_device_id", "device_id"),
        Index("idx_device_process_mappings_process_code", "process_code"),
    )


class ProductTypeGroupMember(Base):
    """型式グループのメンバー（製品の型式コード）"""

    __tablename__ = "product_code_group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("product_code_groups.id"), nullable=False
    )
    product_code = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    group = relationship("ProductTypeGroup", back_populates="members")

    __table_args__ = (
        UniqueConstraint("group_id", "product_code", name="uq_group_product_code"),
        Index("idx_ptg_members_group_id", "group_id"),
        Index("idx_ptg_members_product_code", "product_code"),
    )


class ProductCodeName(Base):
    """型式コードと型式名の1対1マスタ"""

    __tablename__ = "product_code_names"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_code = Column(String(100), unique=True, nullable=False)
    product_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_product_code_names_code", "product_code"),
        Index("idx_product_code_names_name", "product_name"),
    )


class InspectionCriteria(Base):
    """検査基準マスタ"""

    __tablename__ = "inspection_criterias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    judgment_type = Column(
        String(50), nullable=False
    )  # BINARY, NUMERICAL, CATEGORICAL, THRESHOLD
    spec = Column(JSON, nullable=False)  # 基準仕様
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))

    # リレーション
    inspection_items = relationship("InspectionItem", back_populates="criteria")

    # インデックス
    __table_args__ = (
        Index("idx_inspection_criterias_name", "name"),
        Index("idx_inspection_criterias_judgment_type", "judgment_type"),
    )


class InspectionItem(Base):
    """検査項目マスタ"""

    __tablename__ = "inspection_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instruction_id = Column(
        UUID(as_uuid=True), ForeignKey("inspection_instructions.id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(
        String(50), nullable=False
    )  # VISUAL_INSPECTION, DIMENSIONAL_INSPECTION, etc.
    pipeline_id = Column(UUID(as_uuid=True))  # WebUIで定義されたパイプラインID
    pipeline_params = Column(JSON, default=dict)  # パイプライン実行パラメータ
    execution_order = Column(Integer, default=1)
    is_required = Column(Boolean, default=True)
    criteria_id = Column(UUID(as_uuid=True), ForeignKey("inspection_criterias.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))

    # リレーション
    instruction = relationship(
        "inspectionInstruction", back_populates="inspection_items"
    )
    criteria = relationship("InspectionCriteria", back_populates="inspection_items")
    item_executions = relationship("InspectionItemExecution", back_populates="item")

    # インデックス
    __table_args__ = (
        Index("idx_inspection_items_instruction_id", "instruction_id"),
        Index("idx_inspection_items_pipeline_id", "pipeline_id"),
        Index("idx_inspection_items_execution_order", "execution_order"),
        # Note: Uniqueness of (instruction_id, pipeline_id) is NOT enforced to allow
        # multiple items sharing the same pipeline. Evaluator uses item_id to disambiguate.
        # If you want to enforce uniqueness operationally, add a DB migration explicitly.
    )


class InspectionExecution(Base):
    """検査実行"""

    __tablename__ = "inspection_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instruction_id = Column(
        UUID(as_uuid=True), ForeignKey("inspection_instructions.id"), nullable=False
    )
    operator_id = Column(UUID(as_uuid=True))  # 検査実施者ID
    status = Column(String(50), nullable=False, default="PENDING")
    qr_code = Column(String(255))
    metadata_ = Column("metadata", JSON, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)

    # リレーション
    instruction = relationship(
        "inspectionInstruction", back_populates="inspection_executions"
    )
    item_executions = relationship(
        "InspectionItemExecution",
        back_populates="execution",
        cascade="all, delete-orphan",
    )
    results = relationship(
        "InspectionResult", back_populates="execution", cascade="all, delete-orphan"
    )

    # インデックス
    __table_args__ = (
        Index("idx_inspection_executions_instruction_id", "instruction_id"),
        Index("idx_inspection_executions_operator_id", "operator_id"),
        Index("idx_inspection_executions_status", "status"),
        Index("idx_inspection_executions_started_at", "started_at"),
    )


class InspectionItemExecution(Base):
    """検査項目実行"""

    __tablename__ = "inspection_item_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True), ForeignKey("inspection_executions.id"), nullable=False
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("inspection_items.id"), nullable=False
    )
    status = Column(String(50), nullable=False, default="ITEM_PENDING")
    image_file_id = Column(UUID(as_uuid=True))  # 撮影画像のファイルID
    pipeline_execution_id = Column(UUID(as_uuid=True))  # パイプライン実行ID
    ai_result = Column(JSON)  # AI検査結果
    human_result = Column(JSON)  # 人による検査結果
    final_result = Column(String(50))  # 最終判定結果
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)

    # リレーション
    execution = relationship("InspectionExecution", back_populates="item_executions")
    item = relationship("InspectionItem", back_populates="item_executions")
    results = relationship(
        "InspectionResult",
        back_populates="item_execution",
        cascade="all, delete-orphan",
    )

    # インデックス
    __table_args__ = (
        Index("idx_inspection_item_executions_execution_id", "execution_id"),
        Index("idx_inspection_item_executions_item_id", "item_id"),
        Index("idx_inspection_item_executions_status", "status"),
        Index("idx_inspection_item_executions_final_result", "final_result"),
    )


class InspectionResult(Base):
    """検査結果"""

    __tablename__ = "inspection_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True), ForeignKey("inspection_executions.id"), nullable=False
    )
    item_execution_id = Column(
        UUID(as_uuid=True), ForeignKey("inspection_item_executions.id"), nullable=False
    )
    judgment = Column(
        String(50), nullable=False
    )  # OK, NG, PENDING_REVIEW, INCONCLUSIVE
    comment = Column(Text)
    evidence_file_ids = Column(JSON, default=list)  # 根拠画像等のファイルID配列
    metrics = Column(JSON, default=dict)  # 測定値等
    confidence_score = Column(Float)  # AI信頼度スコア
    processing_time_ms = Column(Integer)  # 処理時間
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))

    # リレーション
    execution = relationship("InspectionExecution", back_populates="results")
    item_execution = relationship("InspectionItemExecution", back_populates="results")

    # インデックス
    __table_args__ = (
        Index("idx_inspection_results_execution_id", "execution_id"),
        Index("idx_inspection_results_item_execution_id", "item_execution_id"),
        Index("idx_inspection_results_judgment", "judgment"),
        Index("idx_inspection_results_created_at", "created_at"),
    )
