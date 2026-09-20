from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.models.supplier import Supplier
from app.models.product import ProductSupplierData
from app.models.pricing import ProductChannelPrice
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from uuid import UUID

class SupplierRepository:
    async def create(self, session: AsyncSession, data: SupplierCreate) -> Supplier:
        supplier = Supplier(**data.model_dump())
        session.add(supplier)
        await session.flush()
        await session.refresh(supplier)
        return supplier

    async def get_by_id(self, session: AsyncSession, id: UUID) -> Supplier | None:
        result = await session.execute(select(Supplier).where(Supplier.id == id))
        return result.scalars().first()

    async def get_by_code(self, session: AsyncSession, code: str) -> Supplier | None:
        result = await session.execute(select(Supplier).where(Supplier.code == code))
        return result.scalars().first()

    async def list_all(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Supplier]:
        result = await session.execute(select(Supplier).order_by(Supplier.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count(Supplier.id)))
        return result.scalar() or 0

    async def update(self, session: AsyncSession, id: UUID, data: SupplierUpdate) -> Supplier | None:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(session, id)
        
        if "is_active" in update_data:
            source_ids = select(ProductSupplierData.id).where(ProductSupplierData.supplier_id == id)
            await session.execute(update(ProductChannelPrice).where(ProductChannelPrice.supplier_data_id.in_(source_ids)).values(is_stale=True))
        await session.execute(update(Supplier).where(Supplier.id == id).values(**update_data))
        await session.flush()
        return await self.get_by_id(session, id)

    async def deactivate(self, session: AsyncSession, id: UUID) -> Supplier | None:
        return await self.update(session, id, SupplierUpdate(is_active=False))
