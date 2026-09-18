from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

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
    color: Optional[str] = None
    weight: Optional[Decimal] = None
    height: Optional[Decimal] = None
    width: Optional[Decimal] = None
    length: Optional[Decimal] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ProductWithDetailsResponse(ProductResponse):
    supplier_data: List[ProductSupplierDataResponse] = []
    images: List[ProductImageResponse] = []

class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
