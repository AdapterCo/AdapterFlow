from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PricingProfileBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    channel: str = Field("CUSTOM", max_length=50)
    marketplace_commission_percent: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)
    fixed_fee: Decimal = Field(default=Decimal("0.0"), ge=0)
    fixed_fee_threshold: Decimal | None = Field(default=None, ge=0)
    tax_percent: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)
    operating_cost_percent: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)
    fixed_cost: Decimal = Field(default=Decimal("0.0"), ge=0)
    target_margin_percent: Decimal = Field(default=Decimal("15.0"), ge=-100, le=100)
    free_shipping_threshold: Decimal | None = Field(default=None, ge=0)
    free_shipping_cost: Decimal | None = Field(default=None, ge=0)
    rounding_rule: str = Field("ENDS_90", max_length=30)
    is_default: bool = False
    is_active: bool = True


class PricingProfileCreate(PricingProfileBase):
    pass


class PricingProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    channel: str | None = None
    marketplace_commission_percent: Decimal | None = None
    fixed_fee: Decimal | None = None
    fixed_fee_threshold: Decimal | None = None
    tax_percent: Decimal | None = None
    operating_cost_percent: Decimal | None = None
    fixed_cost: Decimal | None = None
    target_margin_percent: Decimal | None = None
    free_shipping_threshold: Decimal | None = None
    free_shipping_cost: Decimal | None = None
    rounding_rule: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class PricingProfileResponse(PricingProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PricingProfileListResponse(BaseModel):
    items: list[PricingProfileResponse]
    total: int


class PriceSimulationRequest(BaseModel):
    cost_basis: Decimal = Field(..., ge=0)
    marketplace_commission_percent: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)
    fixed_fee: Decimal = Field(default=Decimal("0.0"), ge=0)
    fixed_fee_threshold: Decimal | None = Field(default=None, ge=0)
    tax_percent: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)
    operating_cost_percent: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)
    fixed_cost: Decimal = Field(default=Decimal("0.0"), ge=0)
    target_margin_percent: Decimal = Field(default=Decimal("15.0"), ge=-100, le=100)
    free_shipping_threshold: Decimal | None = Field(default=None, ge=0)
    free_shipping_cost: Decimal | None = Field(default=None, ge=0)
    rounding_rule: str = "ENDS_90"
    manual_override_price: Decimal | None = Field(default=None, gt=0)


class PriceSimulationResponse(BaseModel):
    suggested_price: Decimal
    cost_basis: Decimal
    marketplace_commission: Decimal
    taxes: Decimal
    operating_costs: Decimal
    shipping_cost: Decimal
    fixed_fee: Decimal
    net_margin_value: Decimal
    net_margin_percent: Decimal
    breakdown: dict[str, Any]


class ProductPricingCalculateRequest(BaseModel):
    pricing_profile_id: UUID
    manual_override_price: Decimal | None = Field(default=None, gt=0)


class ProductChannelPriceResponse(BaseModel):
    id: UUID
    product_id: UUID
    pricing_profile_id: UUID
    profile_name: str | None = None
    channel: str | None = None
    calculated_price: Decimal
    cost_basis: Decimal
    channel_commission: Decimal
    taxes: Decimal
    operating_costs: Decimal
    shipping_cost: Decimal
    fixed_fee: Decimal
    net_margin_value: Decimal
    net_margin_percent: Decimal
    breakdown: dict[str, Any] | None = None
    is_manual_override: bool
    manual_price: Decimal | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductPricingListResponse(BaseModel):
    items: list[ProductChannelPriceResponse]
    total: int
