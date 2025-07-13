from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid

class PriorityLevel(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

class ComponentType(str, Enum):
    RESIZE = "resize"
    AI_DETECTION = "ai_detection"
    FILTER = "filter"
    ENHANCEMENT = "enhancement"

class PipelineComponent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    component_type: ComponentType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    
class Pipeline(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    components: List[PipelineComponent]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
class PipelineCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    components: List[PipelineComponent]
    
class PipelineUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    components: Optional[List[PipelineComponent]] = None