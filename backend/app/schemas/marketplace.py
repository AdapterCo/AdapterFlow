from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MarketplaceAccountResponse(BaseModel):
    verified_at: datetime | None = None
    connection_error: str | None = None
    id: UUID
    marketplace: str
    account_name: str
    seller_id: str
    site_id: str
    is_active: bool
    token_expires_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MarketplaceChannelStatus(BaseModel):
    marketplace: str
    name: str
    is_configured: bool
    is_connected: bool
    accounts_count: int
    auth_url: Optional[str] = None


class MarketplacesOverviewResponse(BaseModel):
    channels: list[MarketplaceChannelStatus]
    accounts: list[MarketplaceAccountResponse]


class MercadoLivreConfigurationResponse(BaseModel):
    app_id: str | None
    redirect_uri: str | None
    ready: bool
    issues: list[str]


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str = Field(..., min_length=20, max_length=200)


class CategoryPredictionItem(BaseModel):
    category_id: str
    category_name: str
    domain_id: Optional[str] = None
    domain_name: Optional[str] = None


class PublishProductRequest(BaseModel):
    product_id: UUID
    account_id: UUID
    pricing_profile_id: UUID
    request_id: UUID
    title: str = Field(..., min_length=1, max_length=60)
    category_id: str = Field(..., pattern=r"^MLB[0-9]+$")
    listing_type_id: Literal["gold_special", "gold_pro"]
    available_quantity: int = Field(..., ge=1)
    condition: Literal["new", "used", "not_specified"]
    attributes: Optional[list[dict[str, Any]]] = None


class MarketplaceListingResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: Optional[str] = None
    account_id: UUID
    account_name: Optional[str] = None
    marketplace: str
    external_listing_id: Optional[str] = None
    title: str
    price: Decimal
    available_quantity: int
    category_id: str
    listing_type_id: str
    status: str
    permalink: Optional[str] = None
    error_message: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MarketplaceListingListResponse(BaseModel):
    items: list[MarketplaceListingResponse]
    total: int
