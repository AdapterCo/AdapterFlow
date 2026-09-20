from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.product import Product
from decimal import Decimal
import uuid
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PricingProfile(Base):
    __tablename__ = "pricing_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="CUSTOM")

    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    listing_type_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Regras e taxas
    marketplace_commission_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    fixed_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    fixed_fee_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    tax_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    operating_cost_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    fixed_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    target_margin_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    free_shipping_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    free_shipping_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    rounding_rule: Mapped[str] = mapped_column(
        String(30), nullable=False, default="EXACT"
    )

    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    channel_prices: Mapped[list["ProductChannelPrice"]] = relationship(
        "ProductChannelPrice", back_populates="profile", cascade="all, delete-orphan"
    )


class ProductChannelPrice(Base):
    __tablename__ = "product_channel_prices"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "pricing_profile_id", name="uq_product_channel_prices_product_id_pricing_profile_id"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    pricing_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    calculated_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    channel_commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    taxes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    operating_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    fixed_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    net_margin_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_margin_percent: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)

    is_stale: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    supplier_data_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_supplier_data.id", ondelete="SET NULL"), nullable=True)
    breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="channel_prices")
    profile: Mapped["PricingProfile"] = relationship("PricingProfile", back_populates="channel_prices")
