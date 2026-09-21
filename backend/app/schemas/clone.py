from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ClonePreviewRequest(BaseModel):
    url_or_id: str = Field(..., min_length=3, max_length=1500, description="URL do produto no Mercado Livre ou identificador MLB")


class ClonePreviewResponse(BaseModel):
    mlb_id: str
    name: str
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    ean: Optional[str] = None
    gtin: Optional[str] = None
    color: Optional[str] = None
    dimensions: Optional[str] = None
    weight: Optional[Decimal] = None
    category_id: Optional[str] = None
    pictures: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    permalink: Optional[str] = None


class CloneProductRequest(BaseModel):
    url_or_id: str = Field(..., min_length=3, max_length=1500)
    supplier_id: Optional[UUID] = None
    cost_price: Optional[Decimal] = Field(None, ge=0)
    status: Literal["ACTIVE", "DRAFT"] = "ACTIVE"
