from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MarketplaceAccountResponse(BaseModel):
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


class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class CategoryPredictionItem(BaseModel):
    category_id: str
    category_name: str
    domain_id: Optional[str] = None
    domain_name: Optional[str] = None


class PublishProductRequest(BaseModel):
    product_id: UUID
    account_id: UUID
    pricing_profile_id: Optional[UUID] = None
    title: Optional[str] = None
    category_id: str
    listing_type_id: str = "gold_special"
    available_quantity: int = Field(default=1, ge=1)
    condition: str = "new"
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
