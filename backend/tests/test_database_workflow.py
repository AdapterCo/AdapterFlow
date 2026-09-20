"""Run only against a dedicated migrated TEST_DATABASE_URL; rolled back fixtures."""
import os
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fastapi import HTTPException
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.import_job import ImportJob, ImportItem
from app.services.import_service import ImportService
from app.schemas.import_job import ImportItemUpdateRequest
from app.schemas.product import ProductWithDetailsResponse
from app.repositories.product_repository import ProductRepository

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Dedicated PostgreSQL integration database not configured")

@pytest.mark.asyncio
async def test_import_identity_review_idempotency_and_atomicity():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], hide_parameters=True)
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as session:
                service = ImportService()
                suppliers = [Supplier(name="Synthetic test supplier " + str(uuid4())) for _ in range(2)]
                session.add_all(suppliers)
                await session.flush()
                jobs = []
                for supplier in suppliers:
                    job = ImportJob(supplier_id=supplier.id, file_name="synthetic-test.pdf", file_path=str(uuid4()), importer_type="lehmox", status="REVIEW_REQUIRED")
                    session.add(job)
                    await session.flush()
                    item = ImportItem(import_id=job.id, status="DETECTED", normalized_data={"normalized_name": "Synthetic fixture", "normalized_code": "SAME-TEST-CODE", "normalized_price": "12.3456"}, raw_data={"raw_price": "12,3456"})
                    session.add(item)
                    await session.flush()
                    await service.update_item(session, item.id, ImportItemUpdateRequest(normalized_color="test-only", status="APPROVED"), job.id)
                    result = await service.confirm_import(session, job.id)
                    assert result.total_imported == 1
                    assert item.user_edits["normalized_color"] == "test-only"
                    product = await ProductRepository().get_with_details(session, item.product_id)
                    response = ProductWithDetailsResponse.model_validate(product)
                    assert response.sku is None
                    assert response.supplier_data[0].current_cost == Decimal("12.3456")
                    assert (await service.confirm_import(session, job.id)).total_imported == 1
                    jobs.append((job, item))
                assert jobs[0][1].product_id != jobs[1][1].product_id
                count_before = await session.scalar(select(func.count(Product.id)))
                with pytest.raises(HTTPException):
                    async with session.begin_nested():
                        job = ImportJob(supplier_id=suppliers[0].id, file_name="atomic-test.pdf", file_path=str(uuid4()), importer_type="lehmox", status="REVIEW_REQUIRED")
                        session.add(job)
                        await session.flush()
                        session.add_all([ImportItem(import_id=job.id, status="APPROVED", normalized_data={"normalized_name": "Synthetic fixture", "normalized_code": "NEW-TEST-CODE", "normalized_price": "1"}), ImportItem(import_id=job.id, status="APPROVED", normalized_data={"normalized_code": "MISSING-NAME"})])
                        await session.flush()
                        await service.confirm_import(session, job.id)
                assert await session.scalar(select(func.count(Product.id))) == count_before
            await outer.rollback()
    finally:
        await engine.dispose()
