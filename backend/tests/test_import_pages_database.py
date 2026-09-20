"""Persist real page evidence against the dedicated PostgreSQL test database."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.import_job import ImportJob, ImportPage
from app.models.supplier import Supplier


pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Dedicated PostgreSQL integration database not configured")


@pytest.mark.asyncio
async def test_page_evidence_survives_commit_and_cannot_be_duplicated():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], hide_parameters=True)
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as session:
                supplier = Supplier(name="Synthetic page evidence fixture " + str(uuid4()))
                session.add(supplier)
                await session.flush()
                job = ImportJob(supplier_id=supplier.id, file_name="synthetic.pdf", file_path=str(uuid4()), importer_type="lehmox", status="PROCESSING", total_pages=3, processed_pages=1)
                session.add(job)
                await session.flush()
                page = ImportPage(import_id=job.id, page_number=1, status="NEEDS_REVIEW", raw_text="Synthetic raw text preserved exactly: R$ 1,00", product_count=0, text_blocks=[], image_paths=[], warnings=["Unrecognized layout"])
                session.add(page)
                await session.commit()
                stored = await session.scalar(select(ImportPage).where(ImportPage.import_id == job.id))
                assert stored.raw_text == page.raw_text
                assert stored.created_at.tzinfo is not None
                with pytest.raises(IntegrityError):
                    async with session.begin_nested():
                        session.add(ImportPage(import_id=job.id, page_number=1, status="EMPTY", product_count=0))
                        await session.flush()
                assert await session.scalar(select(ImportPage.id).where(ImportPage.import_id == job.id)) == page.id
            await outer.rollback()
    finally:
        await engine.dispose()
