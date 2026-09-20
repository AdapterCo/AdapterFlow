from app.schemas.decimal_input import DecimalInputModel
from pydantic import Field, BaseModel, ConfigDict, computed_field
from uuid import UUID
from datetime import datetime
from typing import Literal, Optional, List
from decimal import Decimal
from app.schemas.supplier import SupplierResponse

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

    @computed_field
    @property
    def image_url(self) -> str | None:
        from urllib.parse import quote
        return f"/api/v1/storage/{quote(self.image_path, safe=chr(47))}" if self.image_path else None
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
        return ({**(self.normalized_data or {}), **(self.user_edits or {})}).get("normalized_code")

    @computed_field
    @property
    def normalized_name(self) -> Optional[str]:
        return ({**(self.normalized_data or {}), **(self.user_edits or {})}).get("normalized_name")

    @computed_field
    @property
    def normalized_price(self) -> str | None:
        value = ({**(self.normalized_data or {}), **(self.user_edits or {})}).get("normalized_price")
        return str(value) if value is not None else None

    @computed_field
    @property
    def normalized_dimensions(self) -> Optional[str]:
        return ({**(self.normalized_data or {}), **(self.user_edits or {})}).get("normalized_dimensions")

    @computed_field
    @property
    def normalized_pcs_per_box(self) -> Optional[int]:
        return ({**(self.normalized_data or {}), **(self.user_edits or {})}).get("normalized_pcs_per_box")

    @computed_field
    @property
    def normalized_color(self) -> Optional[str]:
        return ({**(self.normalized_data or {}), **(self.user_edits or {})}).get("normalized_color")

    @computed_field
    @property
    def confidence_score(self) -> Optional[float]:
        return float(self.confidence) if self.confidence is not None else None

    @computed_field
    @property
    def warnings(self) -> List[str]:
        return ({**(self.normalized_data or {}), **(self.user_edits or {})}).get("warnings", [])

    @computed_field
    @property
    def is_out_of_stock(self) -> bool:
        return bool(({**(self.normalized_data or {}), **(self.user_edits or {})}).get("is_out_of_stock", False))

class ImportItemListResponse(BaseModel):
    items: List[ImportItemResponse]
    total: int

class ImportJobResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    supplier: Optional[SupplierResponse] = None
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

class ImportItemUpdateRequest(DecimalInputModel):
    status: Literal["DETECTED", "APPROVED", "REJECTED", "IGNORED"] | None = None
    normalized_code: str | None = Field(None, min_length=1, max_length=100)
    normalized_name: str | None = Field(None, min_length=1, max_length=500)
    normalized_price: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=4)
    normalized_color: str | None = Field(None, max_length=100)
    review_notes: str | None = Field(None, max_length=2000)
    model_config = ConfigDict(extra="forbid")

class ImportConfirmRequest(BaseModel):
    approved_item_ids: Optional[List[UUID]] = None
    rejected_item_ids: Optional[List[UUID]] = None
