"""Synthetic inputs exclusively for regression tests; never production seed data."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr, ValidationError
from starlette.requests import Request
from fastapi.security import HTTPBasicCredentials
from cryptography.fernet import Fernet
from app.core.config import settings
from app.core.security import require_admin
from app.core.tokens import encrypt_token, decrypt_token
from app.storage.service import StorageService
from app.pricing.engine import calculate_selling_price, apply_rounding_rule, to_decimal
from app.schemas.pricing import PricingProfileCreate, PricingProfileUpdate
from app.schemas.import_job import ImportItemResponse, ImportItemUpdateRequest
from app.integrations.mercadolivre.client import MercadoLivreClient
from app.services.mercadolivre_service import MercadoLivreService, digest

@pytest.mark.parametrize("cost,fee,threshold,shipping_threshold,shipping,margin,expected", [
    ("75", "10", "80", None, None, "0", "80"),
    ("100", "6", None, "79", "18", "0", "124"),
    ("100", "6", "200", "79", "18", "20", "155"),
])
def test_threshold_regressions(cost, fee, threshold, shipping_threshold, shipping, margin, expected):
    result = calculate_selling_price(cost, fixed_fee=fee, fixed_fee_threshold=threshold,
        free_shipping_threshold=shipping_threshold, free_shipping_cost=shipping,
        target_margin_percent=margin, rounding_rule="EXACT")
    assert result["suggested_price"] == Decimal(expected)
    assert result["net_margin_percent"] >= Decimal(margin)
    expected_fee = Decimal(fee) if threshold is None or Decimal(expected) < Decimal(threshold) else Decimal(0)
    assert result["fixed_fee"] == expected_fee

@pytest.mark.parametrize("value", [1.2, "NaN", "Infinity", "-Infinity"])
def test_non_decimal_money_rejected(value):
    with pytest.raises(ValueError): to_decimal(value)

def test_commercial_rounding_never_rounds_down():
    assert apply_rounding_rule(Decimal("45.904"), "ENDS_90") == Decimal("46.90")
    with pytest.raises(ValueError): apply_rounding_rule(Decimal(10), "unknown")

@pytest.mark.parametrize("path", ["../storage-other/secret", "../secret", "/etc/passwd", "C:/secret", "a/../../secret", "a\\secret", ""])
def test_storage_boundary(tmp_path, path):
    with pytest.raises(ValueError): StorageService(str(tmp_path)).get(path)

def test_storage_immutable_and_materialized(tmp_path):
    storage = StorageService(str(tmp_path))
    storage.put("imports/source.pdf", b"test fixture")
    with pytest.raises(FileExistsError): storage.put("imports/source.pdf", b"overwrite")
    with storage.materialize("imports/source.pdf") as path:
        assert path.read_bytes() == b"test fixture"
    assert not path.exists()

def test_partial_review_preserves_extraction_and_explicit_null():
    item = ImportItemResponse(id=uuid4(), import_id=uuid4(), status="DETECTED", created_at=datetime.now(timezone.utc),
        normalized_data={"normalized_code": "test-code", "normalized_price": "12.34", "normalized_color": "test-color"},
        user_edits={"normalized_price": None})
    assert item.normalized_code == "test-code"
    assert item.normalized_color == "test-color"
    assert item.normalized_price is None
    with pytest.raises(ValidationError): ImportItemUpdateRequest(status="IMPORTED")
    with pytest.raises(ValidationError): ImportItemUpdateRequest(normalized_price="-1")

def test_profiles_keep_unknown_costs_absent_and_validate_patch():
    assert PricingProfileCreate(name="Test only").fixed_fee is None
    with pytest.raises(ValidationError): PricingProfileUpdate(fixed_fee="-1")
    with pytest.raises(ValidationError): PricingProfileCreate(name="Test only", free_shipping_threshold="79")

@pytest.mark.asyncio
async def test_authentication_and_origin(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "test-operator")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", SecretStr("test-only-password"))
    request = Request({"type": "http", "method": "POST", "headers": []})
    with pytest.raises(HTTPException) as error: await require_admin(request, None, AsyncMock())
    assert error.value.status_code == 401
    credentials = HTTPBasicCredentials(username="test-operator", password="test-only-password")
    assert await require_admin(request, credentials, AsyncMock()) == "test-operator"
    request = Request({"type": "http", "method": "POST", "headers": [(b"origin", b"https://untrusted.invalid")]})
    with pytest.raises(HTTPException) as error: await require_admin(request, credentials, AsyncMock())
    assert error.value.status_code == 403

def test_tokens_encrypted_and_plaintext_rejected(monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", SecretStr(Fernet.generate_key().decode()))
    encrypted = encrypt_token("test-only-token")
    assert "test-only-token" not in encrypted
    assert decrypt_token(encrypted) == "test-only-token"
    with pytest.raises(HTTPException): decrypt_token("legacy-plaintext")

@pytest.mark.asyncio
async def test_external_money_serialization_and_safe_errors():
    client = MercadoLivreClient()
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as request:
        request.return_value = httpx.Response(200, content=b'{"price":12345678.91}')
        result = await client.publish_item({"price": Decimal("12345678.91")}, "test-token")
        assert b'12345678.91' in request.call_args.kwargs["content"]
        assert result["price"] == Decimal("12345678.91")
        request.return_value = httpx.Response(400, text="secret-remote-response")
        with pytest.raises(HTTPException) as error: await client.get_user_info("test-token")
        assert "secret-remote-response" not in error.value.detail

@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["missing", "expired", "consumed", "browser", "owner"])
async def test_invalid_oauth_state_never_exchanges_code(kind):
    from types import SimpleNamespace
    from datetime import timedelta
    service = MercadoLivreService()
    attempt = SimpleNamespace(consumed_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5), owner="operator", browser_hash=digest("browser"))
    if kind == "expired": attempt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    if kind == "consumed": attempt.consumed_at = datetime.now(timezone.utc)
    if kind == "owner": attempt.owner = "another"
    session = AsyncMock()
    session.scalar.return_value = None if kind == "missing" else attempt
    service.client.exchange_code_for_token = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await service.handle_oauth_callback(session, "code", "state", "wrong" if kind == "browser" else "browser", "operator")
    assert error.value.status_code == 400
    service.client.exchange_code_for_token.assert_not_awaited()

@pytest.mark.asyncio
async def test_confirm_rejects_items_of_another_job():
    from types import SimpleNamespace
    from app.services.import_service import ImportService
    service = ImportService()
    job = SimpleNamespace(id=uuid4(), supplier_id=uuid4(), status="REVIEW_REQUIRED")
    session = AsyncMock()
    session.scalar.side_effect = [job, SimpleNamespace(is_active=True)]
    service.repo.get_items_by_job = AsyncMock(return_value=[])
    service.product_svc.create_from_import = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await service.confirm_import(session, job.id, approved_ids=[uuid4()])
    assert error.value.status_code == 422
    service.product_svc.create_from_import.assert_not_awaited()

@pytest.mark.asyncio
async def test_confirm_rejects_unreviewed_items():
    from types import SimpleNamespace
    from app.services.import_service import ImportService
    service = ImportService()
    job = SimpleNamespace(id=uuid4(), supplier_id=uuid4(), status="REVIEW_REQUIRED")
    session = AsyncMock()
    session.scalar.side_effect = [job, SimpleNamespace(is_active=True)]
    service.repo.get_items_by_job = AsyncMock(return_value=[SimpleNamespace(id=uuid4(), status="DETECTED")])
    with pytest.raises(HTTPException) as error: await service.confirm_import(session, job.id)
    assert error.value.status_code == 409
    assert job.status == "REVIEW_REQUIRED"

def test_isolated_parser_rejects_invalid_pdf(tmp_path):
    from app.services.import_service import extract_isolated
    storage = StorageService(str(tmp_path))
    storage.put("bad.pdf", b"%PDF-not-a-real-document")
    with pytest.raises(ValueError): extract_isolated(storage, "bad.pdf")

@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["paused", "timeout"])
async def test_publication_preserves_remote_status_or_uncertainty(outcome, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from app.schemas.marketplace import PublishProductRequest
    from app.services.mercadolivre_service import MercadoLivreService
    service = MercadoLivreService()
    source_id, product_id, account_id, profile_id = uuid4(), uuid4(), uuid4(), uuid4()
    source = SimpleNamespace(id=source_id, is_active=True, supplier=SimpleNamespace(is_active=True), current_cost=Decimal("10"))
    product = SimpleNamespace(id=product_id, name="Synthetic test product", status="ACTIVE", supplier_data=[source], images=[SimpleNamespace(storage_path="test.png")], brand=None, model=None, gtin=None, ean=None, description=None)
    price = SimpleNamespace(is_stale=False, profile=SimpleNamespace(is_active=True, channel="MERCADO_LIVRE", listing_type_id="gold_special", source_notes="Synthetic test source"), supplier_data_id=source_id, cost_basis=Decimal("10"), calculated_price=Decimal("20"))
    service.product_repo.get_with_details = AsyncMock(return_value=product)
    service.pricing_repo.get_product_price = AsyncMock(return_value=price)
    service.get_valid_access_token = AsyncMock(return_value=("synthetic-token", "Test account"))
    service.client.get_category_attributes = AsyncMock(return_value=[])
    service.client.upload_picture = AsyncMock(return_value="synthetic-picture-id")
    service.client.validate_item = AsyncMock()
    service.client.publish_item = AsyncMock(side_effect=httpx.ReadTimeout("test") if outcome == "timeout" else None, return_value={"id":"MLB123", "status":"paused", "price":Decimal("20"), "available_quantity":2})
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
    (tmp_path / "test.png").write_bytes(b"synthetic-file-bytes-client-is-mocked")
    session = AsyncMock()
    records = []
    session.add = Mock(side_effect=records.append)
    async def scalar(_):
        return records[0] if records else None
    async def commit():
        if records:
            records[0].id = records[0].id or uuid4()
            records[0].created_at = datetime.now(timezone.utc)
    session.scalar.side_effect = scalar
    session.commit.side_effect = commit
    request = PublishProductRequest(product_id=product_id, account_id=account_id, pricing_profile_id=profile_id, request_id=uuid4(), title="Synthetic title", category_id="MLB123", listing_type_id="gold_special", available_quantity=2, condition="new")
    if outcome == "timeout":
        with pytest.raises(HTTPException) as error: await service.publish_product(session, request)
        assert error.value.status_code == 409
        assert records[0].status == "UNKNOWN"
    else:
        result = await service.publish_product(session, request)
        assert result.status == "PAUSED"
        assert result.external_listing_id == "MLB123"
    service.client.publish_item.assert_awaited_once()


def test_request_money_never_accepts_json_float():
    with pytest.raises(ValidationError): PricingProfileCreate(name="Test only", fixed_fee=1.23)
    with pytest.raises(ValidationError): ImportItemUpdateRequest(normalized_price=1.23)


def test_real_pdf_through_isolated_runner_if_available(tmp_path):
    from pathlib import Path
    import pymupdf
    from app.services.import_service import extract_isolated
    source = Path(r"C:\Users\AdapterCO\Desktop\TrabalhoFelipe\LEHMOX  2026.09.16 (02).pdf")
    if not source.exists(): pytest.skip("Real catalog is not available on this machine")
    with pymupdf.open(source) as original, pymupdf.open() as sample:
        sample.insert_pdf(original, from_page=106, to_page=106)
        data = sample.tobytes()
    storage = StorageService(str(tmp_path))
    storage.put("source.pdf", data)
    result = extract_isolated(storage, "source.pdf")
    assert result
    assert any(item["is_out_of_stock"] for item in result)
    assert all(item["page_number"] == 1 and item["bbox"] for item in result)
