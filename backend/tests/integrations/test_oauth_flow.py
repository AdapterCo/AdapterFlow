"""HTTP OAuth sequence with real service logic and mocked persistence/provider."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4

from cryptography.fernet import Fernet
from pydantic import SecretStr
import httpx
import pytest

from app.main import app
from app.api.v1.marketplaces import service
from app.core.database import get_db
from app.core.config import settings
from app.core.tokens import decrypt_token


@pytest.mark.asyncio
async def test_authorize_cookie_exchange_encryption_and_replay(monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", SecretStr(Fernet.generate_key().decode()))
    monkeypatch.setattr(settings, "MERCADOLIVRE_REDIRECT_URI", "https://test.invalid/marketplaces/callback")
    monkeypatch.setattr(service.client, "app_id", "123456")
    monkeypatch.setattr(service.client, "client_secret", "synthetic-secret")
    monkeypatch.setattr(service.client, "redirect_uri", settings.MERCADOLIVRE_REDIRECT_URI)
    db = AsyncMock(); db.add = MagicMock()
    async def dependency():
        yield db
    app.dependency_overrides[get_db] = dependency
    exchange = AsyncMock(return_value={"access_token": "synthetic-access", "refresh_token": "synthetic-refresh", "user_id": 123,
                                     "token_expires_at": datetime.now(timezone.utc) + timedelta(hours=6)})
    monkeypatch.setattr(service.client, "exchange_code_for_token", exchange)
    monkeypatch.setattr(service.client, "get_user_info", AsyncMock(return_value={"id": 123, "nickname": "Synthetic account", "site_id": "MLB"}))
    saved = {}
    async def upsert(session, marketplace, seller_id, name, access, refresh, expires, **kwargs):
        saved.update(access=access, refresh=refresh)
        return SimpleNamespace(id=uuid4(), marketplace=marketplace, seller_id=seller_id, account_name=name,
            site_id="MLB", is_active=True, token_expires_at=expires, created_at=datetime.now(timezone.utc),
            updated_at=None, settings=None, verified_at=None, connection_error=None)
    monkeypatch.setattr(service.repo, "upsert_account", upsert)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test.invalid") as client:
        response = await client.get("/api/v1/marketplaces/mercadolivre/auth-url")
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
        params = parse_qs(urlsplit(response.json()["auth_url"]).query)
        state = params["state"][0]
        assert params["client_id"] == ["123456"]
        attempt = db.add.call_args.args[0]
        assert attempt.state_hash != state and attempt.browser_hash not in cookie
        db.scalar.return_value = attempt
        callback = await client.post("/api/v1/marketplaces/mercadolivre/oauth/callback", json={"code": "synthetic-code", "state": state})
        assert callback.status_code == 201, callback.text
        assert callback.json()["seller_id"] == "123"
        assert "synthetic-access" not in callback.text and "synthetic-refresh" not in callback.text
        assert decrypt_token(saved["access"]) == "synthetic-access"
        assert decrypt_token(saved["refresh"]) == "synthetic-refresh"
        assert attempt.consumed_at is not None
        replay = await client.post("/api/v1/marketplaces/mercadolivre/oauth/callback", json={"code": "synthetic-code", "state": state})
        assert replay.status_code == 400
        exchange.assert_awaited_once()


@pytest.mark.asyncio
async def test_configuration_reports_app_identity_without_secrets(monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", SecretStr(Fernet.generate_key().decode()))
    monkeypatch.setattr(service.client, "app_id", "654321")
    monkeypatch.setattr(service.client, "client_secret", "do-not-expose")
    monkeypatch.setattr(service.client, "redirect_uri", "https://test.invalid/marketplaces/callback")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test.invalid") as client:
        response = await client.get("/api/v1/marketplaces/mercadolivre/configuration")
        assert response.json()["app_id"] == "654321"
        assert response.json()["ready"] is True
        assert "do-not-expose" not in response.text
