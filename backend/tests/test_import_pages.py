"""API and storage contracts for complete, ordered PDF page evidence."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.dialects import postgresql

from app.api.v1 import imports
from app.core.database import get_db
from app.main import app
from app.repositories.import_repository import ImportRepository
from app.schemas.import_job import ImportJobResponse, ImportPageResponse


def page_values(job_id):
    return {
        "id": uuid4(), "import_id": job_id, "page_number": 2,
        "width": 595.0, "height": 842.0, "status": "NEEDS_REVIEW",
        "raw_text": "Synthetic test page with an unfamiliar layout.",
        "text_blocks": [{"text": "Synthetic fixture", "bbox": [10.0, 20.0, 90.0, 40.0]}],
        "image_paths": ["imports/synthetic-test/page 2.png"],
        "warnings": ["No product boundaries detected."],
        "product_count": 0, "error_message": None,
        "created_at": datetime.now(timezone.utc),
    }


def test_page_schema_preserves_raw_content_without_inventing_product_data():
    values = page_values(uuid4())
    result = ImportPageResponse.model_validate(SimpleNamespace(**values))
    assert result.raw_text == values["raw_text"]
    assert result.product_count == 0
    assert result.text_blocks == values["text_blocks"]
    assert result.image_urls == ["/api/v1/storage/imports/synthetic-test/page%202.png"]


def test_legacy_job_does_not_claim_known_page_progress():
    result = ImportJobResponse(
        id=uuid4(), supplier_id=uuid4(), file_name="synthetic.pdf",
        importer_type="lehmox", status="UPLOADED", created_at=datetime.now(timezone.utc),
    )
    assert result.total_pages is None
    assert result.processed_pages is None
    assert result.last_progress_at is None


@pytest.mark.asyncio
async def test_pages_api_returns_persisted_evidence_and_page_count():
    job_id = uuid4()
    values = page_values(job_id)
    app.dependency_overrides[get_db] = lambda: object()
    with (
        patch.object(imports.repo, "get_job", AsyncMock(return_value=object())),
        patch.object(imports.repo, "list_pages", AsyncMock(return_value=[SimpleNamespace(**values)])) as pages,
        patch.object(imports.repo, "count_pages", AsyncMock(return_value=25)),
    ):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/imports/{job_id}/pages?skip=1&limit=1")
    assert response.status_code == 200
    assert response.json()["total"] == 25
    assert response.json()["items"][0]["page_number"] == 2
    assert response.json()["items"][0]["raw_text"] == values["raw_text"]
    assert pages.call_args.kwargs == {"skip": 1, "limit": 1}


@pytest.mark.asyncio
async def test_pages_api_rejects_unknown_job_and_unbounded_pagination():
    app.dependency_overrides[get_db] = lambda: object()
    with patch.object(imports.repo, "get_job", AsyncMock(return_value=None)):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            missing = await client.get(f"/api/v1/imports/{uuid4()}/pages")
            invalid = await client.get(f"/api/v1/imports/{uuid4()}/pages?limit=10000")
    assert missing.status_code == 404
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_page_repository_filters_import_and_sorts_by_document_order():
    job_id = uuid4()
    session = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [])))
    assert await ImportRepository().list_pages(session, job_id, skip=10, limit=5) == []
    query = str(session.scalars.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert str(job_id) in query
    assert "ORDER BY import_pages.page_number" in query
    assert "LIMIT 5 OFFSET 10" in query
