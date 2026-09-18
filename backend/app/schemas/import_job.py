from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class ImportItemResponse(BaseModel):
    id: UUID
    import_id: UUID
    product_id: Optional[UUID] = None
    raw_data: Optional[dict] = None
    normalized_data: Optional[dict] = None
    status: str
    confidence: Optional[Decimal] = None
    review_notes: Optional[str] = None
    error_message: Optional[str] = None
    image_path: Optional[str] = None
    duplicate_of_product_id: Optional[UUID] = None
    user_edits: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ImportJobResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    file_name: str
    file_size: Optional[int] = None
    importer_type: str
    status: str
    total_detected: Optional[int] = None
    total_imported: Optional[int] = None
    total_errors: Optional[int] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ImportJobListResponse(BaseModel):
    items: List[ImportJobResponse]
    total: int

class ImportItemUpdateRequest(BaseModel):
    status: Optional[str] = None
    user_edits: Optional[dict] = None
    review_notes: Optional[str] = None

class ImportConfirmRequest(BaseModel):
    approved_item_ids: List[UUID]
    rejected_item_ids: List[UUID]
