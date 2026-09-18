from pydantic import BaseModel, ConfigDict, computed_field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

class SupplierBase(BaseModel):
    name: str
    code: Optional[str] = None
    contact_info: Optional[dict] = None

    @field_validator("code", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v

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

    @computed_field
    @property
    def status(self) -> str:
        return "ACTIVE" if self.is_active else "INACTIVE"

class SupplierList(BaseModel):
    items: list[SupplierResponse]
    total: int
