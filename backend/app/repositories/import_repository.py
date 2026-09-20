from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from app.models.import_job import ImportJob, ImportItem, ImportPage
from uuid import UUID
from typing import List

class ImportRepository:
    async def create_job(self, session: AsyncSession, data: dict) -> ImportJob:
        job = ImportJob(**data)
        session.add(job)
        await session.flush()
        await session.refresh(job)
        return job

    async def get_job(self, session: AsyncSession, id: UUID) -> ImportJob | None:
        result = await session.execute(
            select(ImportJob).options(selectinload(ImportJob.supplier)).where(ImportJob.id == id)
        )
        return result.scalars().first()

    async def list_jobs(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> List[ImportJob]:
        result = await session.execute(
            select(ImportJob)
            .options(selectinload(ImportJob.supplier))
            .order_by(ImportJob.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_jobs(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count(ImportJob.id)))
        return result.scalar() or 0

    async def list_pages(self, session: AsyncSession, job_id: UUID, skip: int = 0, limit: int = 10) -> List[ImportPage]:
        result = await session.scalars(
            select(ImportPage)
            .where(ImportPage.import_id == job_id)
            .order_by(ImportPage.page_number)
            .offset(skip)
            .limit(limit)
        )
        return list(result.all())

    async def count_pages(self, session: AsyncSession, job_id: UUID) -> int:
        return await session.scalar(
            select(func.count()).select_from(ImportPage).where(ImportPage.import_id == job_id)
        ) or 0

    async def update_job(self, session: AsyncSession, id: UUID, data: dict) -> ImportJob | None:
        if data:
            await session.execute(update(ImportJob).where(ImportJob.id == id).values(**data))
            await session.flush()
        return await self.get_job(session, id)

    async def create_item(self, session: AsyncSession, data: dict) -> ImportItem:
        item = ImportItem(**data)
        session.add(item)
        await session.flush()
        await session.refresh(item)
        return item

    async def create_items_bulk(self, session: AsyncSession, items: List[dict]) -> List[ImportItem]:
        instances = [ImportItem(**item) for item in items]
        session.add_all(instances)
        await session.flush()
        return instances

    async def get_items_by_job(self, session: AsyncSession, job_id: UUID) -> List[ImportItem]:
        result = await session.execute(select(ImportItem).where(ImportItem.import_id == job_id))
        return list(result.scalars().all())

    async def get_item(self, session: AsyncSession, id: UUID) -> ImportItem | None:
        result = await session.execute(select(ImportItem).where(ImportItem.id == id))
        return result.scalars().first()

    async def update_item(self, session: AsyncSession, id: UUID, data: dict) -> ImportItem | None:
        if data:
            await session.execute(update(ImportItem).where(ImportItem.id == id).values(**data))
            await session.flush()
        return await self.get_item(session, id)
