from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from uuid import UUID

class SupplierService:
    def __init__(self):
        self.repo = SupplierRepository()
        
    async def create(self, session: AsyncSession, data: SupplierCreate):
        return await self.repo.create(session, data)
        
    async def get_by_id(self, session: AsyncSession, id: UUID):
        return await self.repo.get_by_id(session, id)
        
    async def list_all(self, session: AsyncSession, skip: int = 0, limit: int = 100):
        return await self.repo.list_all(session, skip, limit)
        
    async def count(self, session: AsyncSession):
        return await self.repo.count(session)
        
    async def update(self, session: AsyncSession, id: UUID, data: SupplierUpdate):
        return await self.repo.update(session, id, data)
        
    async def deactivate(self, session: AsyncSession, id: UUID):
        return await self.repo.deactivate(session, id)
