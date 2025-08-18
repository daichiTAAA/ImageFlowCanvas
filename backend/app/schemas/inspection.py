"""
検査関連のPydanticスキーマ
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union, Generic, TypeVar
from datetime import datetime
from enum import Enum
import uuid


# 列挙型
class InspectionType(str, Enum):
    VISUAL_INSPECTION = "VISUAL_INSPECTION"
    DIMENSIONAL_INSPECTION = "DIMENSIONAL_INSPECTION"
    FUNCTIONAL_INSPECTION = "FUNCTIONAL_INSPECTION"
    SURFACE_INSPECTION = "SURFACE_INSPECTION"
    COLOR_INSPECTION = "COLOR_INSPECTION"


class JudgmentType(str, Enum):
    BINARY = "BINARY"
    NUMERICAL = "NUMERICAL"
    CATEGORICAL = "CATEGORICAL"
    THRESHOLD = "THRESHOLD"


class InspectionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    AI_COMPLETED = "AI_COMPLETED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class InspectionItemStatus(str, Enum):
    ITEM_PENDING = "ITEM_PENDING"
    ITEM_IN_PROGRESS = "ITEM_IN_PROGRESS"
    ITEM_AI_COMPLETED = "ITEM_AI_COMPLETED"
    ITEM_HUMAN_REVIEW = "ITEM_HUMAN_REVIEW"
    ITEM_COMPLETED = "ITEM_COMPLETED"
    ITEM_FAILED = "ITEM_FAILED"
    ITEM_SKIPPED = "ITEM_SKIPPED"


class JudgmentResult(str, Enum):
    OK = "OK"
    NG = "NG"
    PENDING_REVIEW = "PENDING_REVIEW"
    INCONCLUSIVE = "INCONCLUSIVE"


class DefectSeverity(str, Enum):
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


class ComparisonOperator(str, Enum):
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"


# 基準仕様スキーマ
class BinarySpec(BaseModel):
    expected_value: bool


class NumericalSpec(BaseModel):
    min_value: float
    max_value: float
    unit: Optional[str] = None
    tolerance: Optional[float] = None


class CategoricalSpec(BaseModel):
    allowed_categories: List[str]


class ThresholdSpec(BaseModel):
    threshold: float
    operator: ComparisonOperator


class CriteriaSpec(BaseModel):
    binary: Optional[BinarySpec] = None
    numerical: Optional[NumericalSpec] = None
    categorical: Optional[CategoricalSpec] = None
    threshold: Optional[ThresholdSpec] = None


# AI結果関連スキーマ
class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox: BoundingBox
    attributes: Optional[Dict[str, str]] = {}


class AIResult(BaseModel):
    judgment: JudgmentResult
    confidence_score: float
    detections: Optional[List[Detection]] = []
    measurements: Optional[Dict[str, float]] = {}
    explanation: Optional[str] = None
    processing_time_ms: Optional[int] = None


class HumanResult(BaseModel):
    judgment: JudgmentResult
    comment: Optional[str] = None
    defect_types: Optional[List[str]] = []
    severity: Optional[DefectSeverity] = None
    operator_id: uuid.UUID
    judged_at: datetime


# 検査対象スキーマ
class InspectionTargetBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    # group_id + process_code を主キーとする
    product_name: Optional[str] = Field(None, max_length=255)
    group_id: Optional[uuid.UUID] = None
    group_name: Optional[str] = Field(None, max_length=255)
    process_code: Optional[str] = Field(None, max_length=100)
    version: str = Field(default="1.0", max_length=50)
    # Input payload uses key "metadata"; in DB the column attribute is metadata_
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InspectionTargetCreate(InspectionTargetBase):
    group_id: uuid.UUID
    process_code: str


class InspectionTargetUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    product_name: Optional[str] = Field(None, max_length=255)
    group_id: Optional[uuid.UUID] = None
    process_code: Optional[str] = Field(None, max_length=100)
    group_name: Optional[str] = Field(None, max_length=255)
    version: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None


class InspectionTargetResponse(InspectionTargetBase):
    # Map ORM attribute metadata_ -> JSON field "metadata"
    # Ensure pydantic reads from attribute name and serializes with field name
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Override to set validation alias for ORM attribute
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None


# 検査基準スキーマ
class InspectionCriteriaBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    judgment_type: JudgmentType
    spec: CriteriaSpec


class InspectionCriteriaCreate(InspectionCriteriaBase):
    pass


class InspectionCriteriaUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    judgment_type: Optional[JudgmentType] = None
    spec: Optional[CriteriaSpec] = None


class InspectionCriteriaResponse(InspectionCriteriaBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None


# 型式グループスキーマ
class ProductTypeGroupBase(BaseModel):
    name: str = Field(..., max_length=255)
    group_code: str | None = Field(default=None, max_length=100)
    description: Optional[str] = None
    # vNEXT: group_code を導入（UIからの参照/検索用）
    # 既存レスポンスには追加し、作成/更新は任意


class ProductTypeGroupCreate(ProductTypeGroupBase):
    name: str
    group_code: str


class ProductTypeGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    group_code: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class ProductTypeGroupResponse(ProductTypeGroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None


class ProductTypeGroupMemberCreate(BaseModel):
    product_code: str = Field(..., max_length=100)


class ProductTypeGroupMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    group_id: uuid.UUID
    product_code: str
    created_at: datetime


# 工程マスタスキーマ
class ProcessMasterBase(BaseModel):
    process_code: str = Field(..., max_length=100)
    process_name: str = Field(..., max_length=255)


class ProcessMasterCreate(ProcessMasterBase):
    pass


class ProcessMasterUpdate(BaseModel):
    process_name: Optional[str] = Field(None, max_length=255)


class ProcessMasterResponse(ProcessMasterBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# 検査項目スキーマ
class InspectionItemBase(BaseModel):
    target_id: uuid.UUID
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    type: InspectionType
    pipeline_id: Optional[uuid.UUID] = None
    pipeline_params: Optional[Dict[str, Any]] = {}
    execution_order: int = Field(default=1, ge=1)
    is_required: bool = True
    criteria_id: Optional[uuid.UUID] = None


class InspectionItemCreate(InspectionItemBase):
    pass


class InspectionItemUpdate(BaseModel):
    target_id: Optional[uuid.UUID] = None
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    type: Optional[InspectionType] = None
    pipeline_id: Optional[uuid.UUID] = None
    pipeline_params: Optional[Dict[str, Any]] = None
    execution_order: Optional[int] = Field(None, ge=1)
    is_required: Optional[bool] = None
    criteria_id: Optional[uuid.UUID] = None


class InspectionItemResponse(InspectionItemBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    # リレーションフィールド
    target: Optional[InspectionTargetResponse] = None
    criteria: Optional[InspectionCriteriaResponse] = None


# 検査実行スキーマ
class InspectionExecutionBase(BaseModel):
    target_id: uuid.UUID
    operator_id: Optional[uuid.UUID] = None
    qr_code: Optional[str] = None
    # ORM attribute is metadata_ (column name "metadata")
    metadata: Optional[Dict[str, Any]] = {}


class InspectionExecutionCreate(InspectionExecutionBase):
    pass


class InspectionExecutionResponse(InspectionExecutionBase):
    # Map ORM attribute metadata_ -> JSON field "metadata"
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        validation_alias="metadata_",
        serialization_alias="metadata",
    )

    id: uuid.UUID
    status: InspectionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    # リレーションフィールド
    target: Optional[InspectionTargetResponse] = None


# 検査項目実行スキーマ
class InspectionItemExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    execution_id: uuid.UUID
    item_id: uuid.UUID
    status: InspectionItemStatus
    image_file_id: Optional[uuid.UUID] = None
    pipeline_execution_id: Optional[uuid.UUID] = None
    ai_result: Optional[Dict[str, Any]] = None
    human_result: Optional[Dict[str, Any]] = None
    final_result: Optional[JudgmentResult] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    # リレーションフィールド
    item: Optional[InspectionItemResponse] = None


# 検査結果スキーマ
class InspectionResultBase(BaseModel):
    execution_id: uuid.UUID
    item_execution_id: uuid.UUID
    judgment: JudgmentResult
    comment: Optional[str] = None
    evidence_file_ids: Optional[List[uuid.UUID]] = []
    metrics: Optional[Dict[str, Any]] = {}


class InspectionResultCreate(InspectionResultBase):
    pass


class InspectionResultUpdate(BaseModel):
    judgment: Optional[JudgmentResult] = None
    comment: Optional[str] = None
    evidence_file_ids: Optional[List[uuid.UUID]] = None
    metrics: Optional[Dict[str, Any]] = None


class InspectionResultResponse(InspectionResultBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    created_by: Optional[uuid.UUID] = None


# ページネーション用汎用スキーマ
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int


# gRPC用リクエスト・レスポンススキーマ
class ExecuteInspectionRequest(BaseModel):
    target_id: uuid.UUID
    operator_id: Optional[uuid.UUID] = None
    qr_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class ExecuteInspectionResponse(BaseModel):
    execution_id: uuid.UUID
    execution: InspectionExecutionResponse


class SaveInspectionResultRequest(BaseModel):
    execution_id: uuid.UUID
    item_execution_id: uuid.UUID
    judgment: JudgmentResult
    comment: Optional[str] = None
    evidence_file_ids: Optional[List[uuid.UUID]] = []
    metrics: Optional[Dict[str, Any]] = {}


# 検査実行に必要な画像情報
class InspectionImageData(BaseModel):
    image_data: bytes
    image_format: str  # JPEG, PNG, etc.
    width: int
    height: int
    metadata: Optional[Dict[str, Any]] = {}


# パイプライン実行用スキーマ
class PipelineExecutionRequest(BaseModel):
    item_execution_id: uuid.UUID
    pipeline_id: uuid.UUID
    image_data: InspectionImageData
    pipeline_params: Optional[Dict[str, Any]] = {}


class PipelineExecutionResponse(BaseModel):
    execution_id: uuid.UUID
    status: str
    ai_result: Optional[AIResult] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
