from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    OBSOLETE = "OBSOLETE"


class SyncStatus(str, Enum):
    SYNCED = "SYNCED"
    PENDING = "PENDING"
    FAILED = "FAILED"


class ProductInfo(BaseModel):
    id: str = Field(default="")
    work_order_id: str = Field(alias="workOrderId")
    instruction_id: str = Field(alias="instructionId")
    product_type: str = Field(alias="productType")
    machine_number: str = Field(alias="machineNumber")
    production_date: str = Field(alias="productionDate")
    monthly_sequence: int = Field(alias="monthlySequence")
    qr_raw_data: Optional[str] = Field(default=None, alias="qrRawData")
    status: ProductStatus = ProductStatus.ACTIVE
    created_at: Optional[int] = Field(default=None, alias="createdAt")
    updated_at: Optional[int] = Field(default=None, alias="updatedAt")
    last_accessed_at: Optional[int] = Field(default=None, alias="lastAccessedAt")
    access_count: int = Field(default=0, alias="accessCount")
    is_cached: bool = Field(default=True, alias="isCached")
    server_sync_status: SyncStatus = Field(default=SyncStatus.SYNCED, alias="serverSyncStatus")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ProductSearchResponse(BaseModel):
    products: List[ProductInfo]
    totalCount: int
    hasMore: bool = False
    nextPageToken: Optional[str] = None


class ProductSuggestion(BaseModel):
    productId: str
    displayText: str
    productType: str
    machineNumber: str
    relevanceScore: float


class ProductSyncResponse(BaseModel):
    updates: List[ProductInfo]
    deletions: List[str]
    syncTimestamp: int
    totalUpdated: int
    totalDeleted: int


class ProductCreate(BaseModel):
    work_order_id: str = Field(alias="workOrderId")
    instruction_id: str = Field(alias="instructionId")
    product_type: str = Field(alias="productType")
    machine_number: str = Field(alias="machineNumber")
    production_date: str = Field(alias="productionDate")
    monthly_sequence: int = Field(alias="monthlySequence")
    qr_raw_data: Optional[str] = Field(default=None, alias="qrRawData")
    status: ProductStatus = ProductStatus.ACTIVE
    is_cached: bool = Field(default=True, alias="isCached")
    server_sync_status: SyncStatus = Field(default=SyncStatus.SYNCED, alias="serverSyncStatus")

    class Config:
        allow_population_by_field_name = True


class ProductUpdate(BaseModel):
    product_type: Optional[str] = Field(default=None, alias="productType")
    machine_number: Optional[str] = Field(default=None, alias="machineNumber")
    production_date: Optional[str] = Field(default=None, alias="productionDate")
    monthly_sequence: Optional[int] = Field(default=None, alias="monthlySequence")
    qr_raw_data: Optional[str] = Field(default=None, alias="qrRawData")
    status: Optional[ProductStatus] = None
    is_cached: Optional[bool] = Field(default=None, alias="isCached")
    server_sync_status: Optional[SyncStatus] = Field(default=None, alias="serverSyncStatus")

    class Config:
        allow_population_by_field_name = True
