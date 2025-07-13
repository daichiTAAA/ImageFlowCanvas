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
    component_name: str
    status: StepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None

class ExecutionProgress(BaseModel):
    current_step: str
    total_steps: int
    completed_steps: int
    percentage: float

class OutputFile(BaseModel):
    file_id: str
    filename: str
    download_url: str
    file_size: int

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