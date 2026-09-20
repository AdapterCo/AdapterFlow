from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from app.models.product import Product, ProductSupplierData
from uuid import UUID
from typing import List, Optional

class ProductRepository:
    async def create(self, session: AsyncSession, data: dict) -> Product:
        product = Product(**data)
        session.add(product)
        await session.flush()
        await session.refresh(product)
        return product

    async def get_by_id(self, session: AsyncSession, id: UUID) -> Product | None:
        result = await session.execute(select(Product).where(Product.id == id))
        return result.scalars().first()

    async def get_by_sku(self, session: AsyncSession, sku: str) -> Product | None:
        result = await session.execute(select(Product).where(Product.sku == sku))
        return result.scalars().first()

    async def list_all(self, session: AsyncSession, skip: int = 0, limit: int = 100, search: Optional[str] = None, status: Optional[str] = None) -> List[Product]:
        query = select(Product).options(selectinload(Product.images), selectinload(Product.supplier_data).selectinload(ProductSupplierData.prices))
        if search:
            query = query.where(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))
        if status:
            query = query.where(Product.status == status)
        query = query.order_by(Product.created_at.desc()).offset(skip).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def count(self, session: AsyncSession, search: Optional[str] = None, status: Optional[str] = None) -> int:
        query = select(func.count(Product.id))
        if search:
            query = query.where(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))
        if status:
            query = query.where(Product.status == status)
        result = await session.execute(query)
        return result.scalar() or 0

    async def update(self, session: AsyncSession, id: UUID, data: dict) -> Product | None:
        if data:
            await session.execute(update(Product).where(Product.id == id).values(**data))
            await session.flush()
        return await self.get_by_id(session, id)

    async def get_with_details(self, session: AsyncSession, id: UUID) -> Product | None:
        query = select(Product).options(
            selectinload(Product.supplier_data).selectinload(ProductSupplierData.prices),
            selectinload(Product.images)
        ).where(Product.id == id)
        result = await session.execute(query)
        return result.scalars().first()

    async def find_by_supplier_code(self, session: AsyncSession, supplier_id: UUID, supplier_code: str) -> ProductSupplierData | None:
        query = select(ProductSupplierData).where(
            ProductSupplierData.supplier_id == supplier_id,
            ProductSupplierData.supplier_code == supplier_code
        )
        result = await session.execute(query)
        return result.scalars().first()

    async def update_supplier_link(self, session, product_id, supplier_data_id, is_active, reason):
        link = await session.scalar(select(ProductSupplierData).where(ProductSupplierData.id == supplier_data_id, ProductSupplierData.product_id == product_id).with_for_update())
        if not link:
            return None
        link.is_active = is_active
        link.activation_reason = reason
        from app.models.pricing import ProductChannelPrice
        await session.execute(update(ProductChannelPrice).where(ProductChannelPrice.supplier_data_id == supplier_data_id).values(is_stale=True))
        await session.flush()
        return link
