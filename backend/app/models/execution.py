from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionStep(BaseModel):
    step_id: str
    name: str
    component_name: str  # フロントエンド互換性のため追加
    status: StepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None  # フロントエンド互換性のため
    output_data: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        # component_nameが指定されていない場合はnameをコピー
        if "component_name" not in data and "name" in data:
            data["component_name"] = data["name"]
        # resource_usageが指定されていない場合はoutput_dataをコピー
        if "resource_usage" not in data and "output_data" in data:
            data["resource_usage"] = data["output_data"]
        super().__init__(**data)


class ExecutionProgress(BaseModel):
    current_step: str
    total_steps: int
    completed_steps: int
    percentage: float


class OutputFile(BaseModel):
    file_id: str
    filename: str
    file_size: int
    content_type: str = "application/octet-stream"
    download_url: Optional[str] = None  # オプショナルに変更

    # download_urlの自動生成
    def __init__(self, **data):
        super().__init__(**data)
        if not self.download_url:
            # ファイルサービスのエンドポイントを使用してURLを生成
            self.download_url = f"/v1/files/{self.file_id}/download"


class Execution(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    progress: ExecutionProgress
    steps: List[ExecutionStep] = Field(default_factory=list)
    output_files: List[OutputFile] = Field(default_factory=list)
    workflow_name: Optional[str] = None  # Argo Workflow name
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ExecutionRequest(BaseModel):
    pipeline_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "normal"
