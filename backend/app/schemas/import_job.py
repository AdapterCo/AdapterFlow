from pydantic import BaseModel, ConfigDict, computed_field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any
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

    @computed_field
    @property
    def raw_code(self) -> Optional[str]:
        return (self.raw_data or {}).get("raw_code")

    @computed_field
    @property
    def raw_name(self) -> Optional[str]:
        return (self.raw_data or {}).get("raw_name")

    @computed_field
    @property
    def raw_price(self) -> Optional[str]:
        return (self.raw_data or {}).get("raw_price")

    @computed_field
    @property
    def raw_dimensions(self) -> Optional[str]:
        return (self.raw_data or {}).get("raw_dimensions")

    @computed_field
    @property
    def raw_pcs_cx(self) -> Optional[str]:
        return (self.raw_data or {}).get("raw_pcs_per_box")

    @computed_field
    @property
    def raw_color(self) -> Optional[str]:
        return (self.raw_data or {}).get("raw_color")

    @computed_field
    @property
    def normalized_code(self) -> Optional[str]:
        return (self.normalized_data or {}).get("normalized_code")

    @computed_field
    @property
    def normalized_name(self) -> Optional[str]:
        return (self.normalized_data or {}).get("normalized_name")

    @computed_field
    @property
    def normalized_price(self) -> Optional[Any]:
        return (self.normalized_data or {}).get("normalized_price")

    @computed_field
    @property
    def normalized_dimensions(self) -> Optional[str]:
        return (self.normalized_data or {}).get("normalized_dimensions")

    @computed_field
    @property
    def normalized_pcs_per_box(self) -> Optional[int]:
        return (self.normalized_data or {}).get("normalized_pcs_per_box")

    @computed_field
    @property
    def normalized_color(self) -> Optional[str]:
        return (self.normalized_data or {}).get("normalized_color")

    @computed_field
    @property
    def confidence_score(self) -> Optional[float]:
        return float(self.confidence) if self.confidence is not None else None

    @computed_field
    @property
    def warnings(self) -> List[str]:
        return (self.normalized_data or {}).get("warnings", [])

class ImportItemListResponse(BaseModel):
    items: List[ImportItemResponse]
    total: int

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

    @computed_field
    @property
    def original_filename(self) -> str:
        return self.file_name

    @computed_field
    @property
    def items_detected(self) -> int:
        return self.total_detected or 0

    @computed_field
    @property
    def items_imported(self) -> int:
        return self.total_imported or 0

    @computed_field
    @property
    def items_failed(self) -> int:
        return self.total_errors or 0

class ImportJobListResponse(BaseModel):
    items: List[ImportJobResponse]
    total: int

class ImportItemUpdateRequest(BaseModel):
    status: Optional[str] = None
    normalized_code: Optional[str] = None
    normalized_price: Optional[Any] = None
    normalized_color: Optional[str] = None
    user_edits: Optional[dict] = None
    review_notes: Optional[str] = None

class ImportConfirmRequest(BaseModel):
    approved_item_ids: Optional[List[UUID]] = None
    rejected_item_ids: Optional[List[UUID]] = None
