from decimal import Decimal
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MarketplaceAccount(Base):
    __tablename__ = "marketplace_accounts"
    __table_args__ = (
        UniqueConstraint(
            "marketplace", "seller_id", name="uq_marketplace_accounts_seller"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False, default="MERCADO_LIVRE")
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    seller_id: Mapped[str] = mapped_column(String(100), nullable=False)
    site_id: Mapped[str] = mapped_column(String(20), nullable=False, default="MLB")

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connection_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tokens encrypted by the service before persistence.
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    listings: Mapped[list["MarketplaceListing"]] = relationship(
        "MarketplaceListing", back_populates="account", cascade="all, delete-orphan"
    )


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"
    __table_args__ = (
        UniqueConstraint(
            "account_id", "external_listing_id", name="uq_marketplace_listings_external"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_accounts.id", ondelete="CASCADE"), nullable=False
    )
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False, default="MERCADO_LIVRE")
    external_listing_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    category_id: Mapped[str] = mapped_column(String(100), nullable=False)
    listing_type_id: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    permalink: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    product = relationship("Product", back_populates="marketplace_listings")
    account = relationship("MarketplaceAccount", back_populates="listings")


class OAuthAttempt(Base):
    __tablename__ = "oauth_attempts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True)
    browser_hash: Mapped[str] = mapped_column(String(64))
    owner: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketplacePlatformCredential(Base):
    __tablename__ = "marketplace_platform_credentials"
    __table_args__ = (
        UniqueConstraint("marketplace", name="uq_marketplace_platform_credentials_marketplace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    app_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
