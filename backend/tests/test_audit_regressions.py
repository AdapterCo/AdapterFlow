"""Synthetic fixtures only: security, source visibility and durable review decisions."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import hashlib
import pytest
import pymupdf as fitz
from fastapi import HTTPException
from pydantic import SecretStr
from starlette.requests import Request
from app.core.config import settings
from app.core.security import require_admin, credential_hash
from app.importers.pdf.lehmox import LehmoxCatalogImporter
from app.services.import_service import ImportService
from app.services.clone_service import parse_mlb_info
from app.storage.service import StorageService

@pytest.mark.asyncio
async def test_session_expiry_password_change_and_forgery(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "synthetic")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", SecretStr("synthetic-password"))
    request = Request({"type":"http", "method":"GET", "headers":[(b"cookie", b"adapterflow_session=synthetic-token")]})
    row = SimpleNamespace(expires_at=datetime.now(timezone.utc)+timedelta(hours=1), username="synthetic", credential_hash=credential_hash("synthetic-token"))
    db = AsyncMock(); db.scalar.return_value=row
    assert await require_admin(request, None, db) == "synthetic"
    row.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    with pytest.raises(HTTPException): await require_admin(request, None, db)
    row.expires_at=datetime.now(timezone.utc)+timedelta(hours=1)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", SecretStr("changed-password"))
    with pytest.raises(HTTPException): await require_admin(request, None, db)
    db.scalar.return_value=None
    with pytest.raises(HTTPException): await require_admin(request, None, db)

def test_hidden_price_does_not_replace_visible_price_and_raw_stays_intact():
    with fitz.open() as doc:
        page=doc.new_page()
        page.insert_text((30,50), "R$ 99,90")
        page.draw_rect(fitz.Rect(20,30,130,60), fill=(1,1,1), color=None, overlay=True)
        page.insert_text((30,50), "R$ 12,34")
        data=page.get_text("dict")
        filtered,count=LehmoxCatalogImporter._visible_text_data(page,data)
        text=" ".join(b["text"] for b in LehmoxCatalogImporter()._extract_text_blocks(filtered,1))
        assert "12,34" in text and "99,90" not in text and count > 0
        assert "99,90" in page.get_text()

def test_streaming_limit_cleans_incomplete_file_and_preserves_digest(tmp_path):
    storage=StorageService(str(tmp_path)); content=b"%PDF-synthetic fixture"
    size,digest=storage.put_stream("ok.pdf",BytesIO(content),100)
    assert size==len(content) and digest==hashlib.sha256(content).hexdigest()
    with pytest.raises(ValueError): storage.put_stream("large.pdf",BytesIO(content),3)
    assert not storage.exists("large.pdf")
    with pytest.raises(FileExistsError): storage.put_stream("ok.pdf",BytesIO(b"changed"),100)
    assert storage.get("ok.pdf")==content

def test_catalog_identity_is_not_listing_identity():
    assert parse_mlb_info("https://www.mercadolivre.com.br/p/MLB123456") == ("MLB123456", True)
    assert parse_mlb_info("https://produto.mercadolivre.com.br/MLB-123456") == ("MLB123456", False)

@pytest.mark.asyncio
async def test_ignored_items_stay_ignored_after_bulk_approval():
    service=ImportService(); db=AsyncMock(); db.scalar.return_value=SimpleNamespace(status="REVIEW_REQUIRED")
    item=SimpleNamespace(status="IGNORED",normalized_data={"normalized_name":"Synthetic", "normalized_code":"test"})
    service.repo.get_items_by_job=AsyncMock(return_value=[item])
    assert await service.approve_all_items(db,uuid4()) == {"approved_count":0,"skipped_count":0}
    assert item.status=="IGNORED"

@pytest.mark.asyncio
async def test_duplicate_approved_codes_fail_before_any_product_write():
    service=ImportService(); db=AsyncMock()
    job=SimpleNamespace(status="REVIEW_REQUIRED",supplier_id=uuid4())
    db.scalar.side_effect=[job,SimpleNamespace(is_active=True)]
    items=[SimpleNamespace(id=uuid4(),status="APPROVED",normalized_data={"normalized_name":"Synthetic", "normalized_code":"same"},user_edits={},raw_data={}) for _ in range(2)]
    service.repo.get_items_by_job=AsyncMock(return_value=items)
    service.product_svc.create_from_import=AsyncMock()
    with pytest.raises(HTTPException) as exc: await service.confirm_import(db,uuid4())
    assert exc.value.status_code==409
    service.product_svc.create_from_import.assert_not_awaited()

@pytest.mark.asyncio
async def test_reprocess_refuses_to_erase_reviewed_page():
    service=ImportService(); db=AsyncMock()
    db.scalar.side_effect=[SimpleNamespace(status="REVIEW_REQUIRED"),SimpleNamespace()]
    service.repo.get_items_by_job=AsyncMock(return_value=[SimpleNamespace(status="APPROVED",raw_data={"page_number":2},user_edits={})])
    with pytest.raises(HTTPException) as exc: await service.retry_page(db,uuid4(),2)
    assert exc.value.status_code==409
    db.delete.assert_not_awaited()
