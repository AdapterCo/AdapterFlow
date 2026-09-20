from app.schemas.decimal_input import DecimalInputModel
from datetime import datetime
from decimal import Decimal
from typing import Literal
from app.pricing.engine import DREBreakdown
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PricingProfileBase(DecimalInputModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_notes: str | None = Field(None, max_length=2000)
    listing_type_id: Literal["gold_special", "gold_pro"] | None = None
    channel: Literal["CUSTOM", "MERCADO_LIVRE", "SHOPEE", "AMAZON", "TIKTOK"] = "CUSTOM"
    marketplace_commission_percent: Decimal | None = Field(None, ge=0, lt=100, max_digits=12, decimal_places=4)
    fixed_fee: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    fixed_fee_threshold: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    tax_percent: Decimal | None = Field(None, ge=0, lt=100, max_digits=12, decimal_places=4)
    operating_cost_percent: Decimal | None = Field(None, ge=0, lt=100, max_digits=12, decimal_places=4)
    fixed_cost: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    target_margin_percent: Decimal | None = Field(None, ge=-100, lt=100, max_digits=12, decimal_places=4)
    free_shipping_threshold: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    free_shipping_cost: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    rounding_rule: Literal["ENDS_90", "ENDS_99", "EXACT", "ROUND_INTEGER"] = "EXACT"
    is_default: bool = False
    is_active: bool = True
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_rates(self):
        rates = [self.marketplace_commission_percent, self.tax_percent, self.operating_cost_percent, self.target_margin_percent]
        if all(v is not None for v in rates) and sum(rates) >= 100:
            raise ValueError("A soma das taxas e margem deve ser menor que 100%.")
        if (self.free_shipping_threshold is None) != (self.free_shipping_cost is None):
            raise ValueError("Informe limiar e custo de frete conjuntamente.")
        return self


class PricingProfileCreate(PricingProfileBase):
    pass


class PricingProfileUpdate(PricingProfileBase):
    @model_validator(mode="after")
    def validate_rates(self):
        return self  # The repository validates the complete merged profile.

    name: str | None = Field(None, min_length=1, max_length=255)


class PricingProfileResponse(PricingProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PricingProfileListResponse(BaseModel):
    items: list[PricingProfileResponse]
    total: int


class PriceSimulationRequest(DecimalInputModel):
    cost_basis: Decimal = Field(..., ge=0, max_digits=12, decimal_places=4)
    marketplace_commission_percent: Decimal = Field(..., ge=0, lt=100)
    fixed_fee: Decimal = Field(..., ge=0)
    fixed_fee_threshold: Decimal | None = Field(None, ge=0)
    tax_percent: Decimal = Field(..., ge=0, lt=100)
    operating_cost_percent: Decimal = Field(..., ge=0, lt=100)
    fixed_cost: Decimal = Field(..., ge=0)
    target_margin_percent: Decimal = Field(..., ge=-100, lt=100)
    free_shipping_threshold: Decimal | None = Field(None, ge=0)
    free_shipping_cost: Decimal | None = Field(None, ge=0)
    rounding_rule: Literal["ENDS_90", "ENDS_99", "EXACT", "ROUND_INTEGER"]
    manual_override_price: Decimal | None = Field(None, gt=0)


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
    breakdown: DREBreakdown


class ProductPricingCalculateRequest(DecimalInputModel):
    supplier_data_id: UUID
    pricing_profile_id: UUID
    manual_override_price: Decimal | None = Field(default=None, gt=0)


class ProductChannelPriceResponse(BaseModel):
    is_stale: bool
    supplier_data_id: UUID | None = None
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
    breakdown: DREBreakdown | None = None
    is_manual_override: bool
    manual_price: Decimal | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductPricingListResponse(BaseModel):
    items: list[ProductChannelPriceResponse]
    total: int
