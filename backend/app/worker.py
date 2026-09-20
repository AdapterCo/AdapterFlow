"""Durable database queue: one bounded extraction at a time per worker."""
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.import_job import ImportJob
from app.services.import_service import ImportService
from app.storage.service import StorageService


async def run():
    service = ImportService()
    storage = StorageService(settings.STORAGE_PATH)
    while True:
        async with async_session_maker() as session:
            await session.execute(update(ImportJob).where(
                ImportJob.status == "PROCESSING",
                ImportJob.started_at < datetime.now(timezone.utc) - timedelta(minutes=10),
            ).values(status="FAILED", error_message="Processamento interrompido. Reenvie o catálogo.", completed_at=datetime.now(timezone.utc)))
            job_id = await session.scalar(select(ImportJob.id).where(ImportJob.status == "UPLOADED").order_by(ImportJob.created_at).limit(1))
            await session.commit()
        if job_id:
            await service.process_import_background(job_id, storage)
        else:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run())
