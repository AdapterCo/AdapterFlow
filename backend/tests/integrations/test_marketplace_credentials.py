"""Tests for database-backed marketplace platform credentials (encrypted, never returned in plaintext)."""
from unittest.mock import AsyncMock
import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_admin
from app.core.tokens import decrypt_token
from app.main import app
from app.models.marketplace import MarketplacePlatformCredential


@pytest.mark.asyncio
async def test_credentials_unauthorized(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", SecretStr("real-password"))
    # Temporarily remove conftest's require_admin override
    original_override = app.dependency_overrides.pop(require_admin, None)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test.invalid") as client:
            response = await client.get("/api/v1/marketplaces/credentials")
            assert response.status_code == 401
    finally:
        if original_override:
            app.dependency_overrides[require_admin] = original_override


@pytest.mark.asyncio
async def test_save_and_retrieve_shopee_credential(monkeypatch):
    test_enc_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", SecretStr(test_enc_key))
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", SecretStr("test-admin-password"))

    # In-memory storage for the mock DB session
    stored_credentials = {}

    db = AsyncMock()

    async def mock_execute(stmt):
        mock_result = AsyncMock()
        compiled = stmt.compile()
        params = compiled.params
        marketplace_param = next((v for k, v in params.items() if "marketplace" in k), None)
        if marketplace_param and marketplace_param in stored_credentials:
            cred = stored_credentials[marketplace_param]
            mock_result.scalar_one_or_none = lambda: cred
            mock_result.scalars = lambda: AsyncMock(all=lambda: [cred])
            return mock_result
        mock_result.scalar_one_or_none = lambda: None
        mock_result.scalars = lambda: AsyncMock(all=lambda: list(stored_credentials.values()))
        return mock_result

    def mock_add(instance):
        if isinstance(instance, MarketplacePlatformCredential):
            stored_credentials[instance.marketplace] = instance

    async def mock_delete(instance):
        if isinstance(instance, MarketplacePlatformCredential):
            stored_credentials.pop(instance.marketplace, None)

    db.execute = AsyncMock(side_effect=mock_execute)
    db.add = mock_add
    db.delete = AsyncMock(side_effect=mock_delete)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://test.invalid",
            headers={"Origin": "https://test.invalid"},
        ) as client:
            # 1. Save Shopee credential
            payload = {
                "app_id": "1002345",
                "app_secret": "my_super_secret_partner_key_1234",
                "redirect_uri": "https://test.invalid/marketplaces/callback/shopee",
                "api_url": "https://partner.shopeemobile.com",
            }
            res_put = await client.put("/api/v1/marketplaces/credentials/SHOPEE", json=payload)
            assert res_put.status_code == 200, res_put.text
            data = res_put.json()

            # Ensure plain secret is NOT returned
            assert "my_super_secret_partner_key_1234" not in res_put.text
            assert data["marketplace"] == "SHOPEE"
            assert data["app_id"] == "1002345"
            assert data["has_secret"] is True
            assert data["secret_preview"] == "••••••••1234"
            assert data["redirect_uri"] == "https://test.invalid/marketplaces/callback/shopee"

            # Check that encrypted secret was saved and can be decrypted
            saved_cred = stored_credentials.get("SHOPEE")
            assert saved_cred is not None
            assert saved_cred.app_secret_encrypted != "my_super_secret_partner_key_1234"
            assert decrypt_token(saved_cred.app_secret_encrypted) == "my_super_secret_partner_key_1234"

            # 2. Get Shopee credential safe
            res_get = await client.get("/api/v1/marketplaces/credentials/SHOPEE")
            assert res_get.status_code == 200
            get_data = res_get.json()
            assert "my_super_secret_partner_key_1234" not in res_get.text
            assert get_data["app_id"] == "1002345"
            assert get_data["has_secret"] is True
            assert get_data["secret_preview"] == "••••••••1234"

            # 3. List platform credentials
            res_list = await client.get("/api/v1/marketplaces/credentials")
            assert res_list.status_code == 200
            list_data = res_list.json()
            assert len(list_data) >= 2
            shopee_item = next(item for item in list_data if item["marketplace"] == "SHOPEE")
            assert shopee_item["app_id"] == "1002345"
            assert "my_super_secret_partner_key_1234" not in res_list.text

            # 4. Delete credential
            res_del = await client.delete("/api/v1/marketplaces/credentials/SHOPEE")
            assert res_del.status_code == 204
            assert "SHOPEE" not in stored_credentials

    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_save_and_update_mercadolivre_credential(monkeypatch):
    test_enc_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", SecretStr(test_enc_key))
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", SecretStr("test-admin-password"))

    stored_credentials = {}
    db = AsyncMock()

    async def mock_execute(stmt):
        mock_result = AsyncMock()
        compiled = stmt.compile()
        params = compiled.params
        marketplace_param = next((v for k, v in params.items() if "marketplace" in k), None)
        if marketplace_param and marketplace_param in stored_credentials:
            cred = stored_credentials[marketplace_param]
            mock_result.scalar_one_or_none = lambda: cred
            mock_result.scalars = lambda: AsyncMock(all=lambda: [cred])
            return mock_result
        mock_result.scalar_one_or_none = lambda: None
        mock_result.scalars = lambda: AsyncMock(all=lambda: list(stored_credentials.values()))
        return mock_result

    def mock_add(instance):
        if isinstance(instance, MarketplacePlatformCredential):
            stored_credentials[instance.marketplace] = instance

    async def mock_delete(instance):
        if isinstance(instance, MarketplacePlatformCredential):
            stored_credentials.pop(instance.marketplace, None)

    db.execute = AsyncMock(side_effect=mock_execute)
    db.add = mock_add
    db.delete = AsyncMock(side_effect=mock_delete)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://test.invalid",
            headers={"Origin": "https://test.invalid"},
        ) as client:
            # 1. First save Mercado Livre
            payload = {
                "app_id": "88776655",
                "app_secret": "ml_client_secret_xyz987",
                "redirect_uri": "https://test.invalid/marketplaces/callback",
            }
            res = await client.put("/api/v1/marketplaces/credentials/MERCADO_LIVRE", json=payload)
            assert res.status_code == 200
            assert "ml_client_secret_xyz987" not in res.text
            data = res.json()
            assert data["app_id"] == "88776655"
            assert data["has_secret"] is True
            assert data["secret_preview"] == "••••••••z987"

            # 2. Update without sending app_secret (e.g. user just changes redirect URI)
            payload_update = {
                "app_id": "88776655",
                "app_secret": "",  # Empty/blank
                "redirect_uri": "https://new.invalid/marketplaces/callback",
            }
            res_update = await client.put("/api/v1/marketplaces/credentials/MERCADO_LIVRE", json=payload_update)
            assert res_update.status_code == 200
            data_update = res_update.json()
            assert data_update["redirect_uri"] == "https://new.invalid/marketplaces/callback"
            # Secret was preserved!
            assert data_update["has_secret"] is True
            assert data_update["secret_preview"] == "••••••••z987"

            # Decrypt verify
            saved_cred = stored_credentials.get("MERCADO_LIVRE")
            assert decrypt_token(saved_cred.app_secret_encrypted) == "ml_client_secret_xyz987"

    finally:
        app.dependency_overrides.pop(get_db, None)

