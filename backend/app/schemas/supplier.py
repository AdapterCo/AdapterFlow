from pydantic import BaseModel, ConfigDict, computed_field, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=100)
    contact_info: Optional[dict] = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("code", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("name", "is_active", mode="before")
    @classmethod
    def non_null(cls, value):
        if value is None:
            raise ValueError("Nome e atividade não podem ser nulos.")
        return value

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=100)
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
