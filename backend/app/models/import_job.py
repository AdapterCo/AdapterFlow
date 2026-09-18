from uuid import UUID
from sqlalchemy import String, Integer, Text, Numeric, text, func, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from app.core.database import Base
from app.models.supplier import Supplier
from datetime import datetime
from typing import List

class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    importer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="UPLOADED")
    total_detected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_imported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_errors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    supplier: Mapped["Supplier"] = relationship("Supplier", lazy="selectin")
    items: Mapped[List["ImportItem"]] = relationship("ImportItem", back_populates="job", cascade="all, delete-orphan")

class ImportItem(Base):
    __tablename__ = "import_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    import_id: Mapped[UUID] = mapped_column(ForeignKey("import_jobs.id", ondelete="CASCADE"))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    normalized_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DETECTED")
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duplicate_of_product_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    user_edits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    job: Mapped["ImportJob"] = relationship("ImportJob", back_populates="items")
