from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class SupplierBase(BaseModel):
    name: str
    code: Optional[str] = None
    contact_info: Optional[dict] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    contact_info: Optional[dict] = None
    is_active: Optional[bool] = None

class SupplierResponse(SupplierBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SupplierList(BaseModel):
    items: list[SupplierResponse]
    total: int
