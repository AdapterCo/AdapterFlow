from pydantic import BaseModel, ConfigDict, Field, computed_field
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from typing import Literal
from app.schemas.supplier import SupplierResponse

class SupplierProductPriceResponse(BaseModel):
    id: UUID
    price: Decimal
    raw_value: Optional[str] = None
    effective_at: datetime
    import_id: Optional[UUID] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProductSupplierDataResponse(BaseModel):
    id: UUID
    supplier: SupplierResponse | None = None
    supplier_id: UUID
    supplier_code: str
    supplier_name: Optional[str] = None
    pcs_per_box: Optional[int] = None
    current_cost: Optional[Decimal] = None
    raw_cost_value: Optional[str] = None
    is_active: bool
    prices: List[SupplierProductPriceResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ProductImageResponse(BaseModel):
    @computed_field
    @property
    def url(self) -> str:
        from urllib.parse import quote
        return f"/api/v1/storage/{quote(self.storage_path, safe='/')}"

    @computed_field
    @property
    def is_primary(self) -> bool:
        return self.position == 0

    id: UUID
    storage_path: str
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    position: int
    source: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProductResponse(BaseModel):
    id: UUID
    sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    ean: Optional[str] = None
    gtin: Optional[str] = None
    dimensions: Optional[str] = None
    color: Optional[str] = None
    weight: Optional[Decimal] = None
    height: Optional[Decimal] = None
    width: Optional[Decimal] = None
    length: Optional[Decimal] = None
    status: Literal["ACTIVE", "INACTIVE", "DRAFT"]
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ProductWithDetailsResponse(ProductResponse):
    supplier_data: List[ProductSupplierDataResponse] = []
    images: List[ProductImageResponse] = []

class ProductListResponse(BaseModel):
    items: List[ProductWithDetailsResponse]
    total: int

class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    sku: str | None = Field(None, max_length=100)
    description: str | None = None
    brand: str | None = Field(None, max_length=255)
    model: str | None = Field(None, max_length=255)
    ean: str | None = Field(None, pattern=r"^\d{8,14}$")
    gtin: str | None = Field(None, pattern=r"^\d{8,14}$")
    color: str | None = Field(None, max_length=100)
    dimensions: str | None = None
    status: Literal["ACTIVE", "INACTIVE", "DRAFT"] | None = None
    model_config = ConfigDict(extra="forbid")


class SupplierLinkUpdate(BaseModel):
    is_active: bool
    activation_reason: str = Field(..., min_length=1, max_length=2000)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
