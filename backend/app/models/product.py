from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.product_image import ProductImage
    from app.models.pricing import ProductChannelPrice
from decimal import Decimal
from uuid import UUID
from sqlalchemy import String, Text, Numeric, Boolean, text, func, Integer, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.core.database import Base
from datetime import datetime
from typing import List

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("source_marketplace", "source_external_id", name="uq_products_external_source"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    sku: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    source_marketplace: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gtin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dimensions: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    height: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    width: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    length: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    supplier_data: Mapped[List["ProductSupplierData"]] = relationship("ProductSupplierData", back_populates="product", cascade="all, delete-orphan")
    images: Mapped[List["ProductImage"]] = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    channel_prices: Mapped[List["ProductChannelPrice"]] = relationship("ProductChannelPrice", back_populates="product", cascade="all, delete-orphan")
    marketplace_listings = relationship("MarketplaceListing", back_populates="product", cascade="all, delete-orphan")

class ProductSupplierData(Base):
    __tablename__ = "product_supplier_data"
    __table_args__ = (UniqueConstraint('supplier_id', 'supplier_code'),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"))
    supplier_code: Mapped[str] = mapped_column(String(100))
    supplier_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pcs_per_box: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    activation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_cost_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="supplier_data")
    supplier = relationship("Supplier", lazy="selectin")
    prices: Mapped[List["SupplierProductPrice"]] = relationship("SupplierProductPrice", back_populates="supplier_data", cascade="all, delete-orphan")

class SupplierProductPrice(Base):
    __tablename__ = "supplier_product_prices"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    product_supplier_data_id: Mapped[UUID] = mapped_column(ForeignKey("product_supplier_data.id", ondelete="CASCADE"))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    import_id: Mapped[UUID | None] = mapped_column(ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    supplier_data: Mapped["ProductSupplierData"] = relationship("ProductSupplierData", back_populates="prices")
