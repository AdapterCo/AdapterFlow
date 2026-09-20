import pytest
from httpx import AsyncClient, ASGITransport, Response
from unittest.mock import patch, AsyncMock
from app.integrations.mercadolivre.client import MercadoLivreClient
from app.main import app
from fastapi import HTTPException


def test_client_configuration_check():
    client_unconfigured = MercadoLivreClient(app_id=None, client_secret=None)
    assert not client_unconfigured.is_configured()

    with pytest.raises(HTTPException) as exc_info:
        client_unconfigured.get_authorization_url(state="test-state")
    assert exc_info.value.status_code == 503
    assert "não está configurado" in exc_info.value.detail

    client_configured = MercadoLivreClient(
        app_id="123456789",
        client_secret="test_secret",
        redirect_uri="http://localhost:3099/marketplaces/callback",
    )
    assert client_configured.is_configured()
    url = client_configured.get_authorization_url(state="test_state")
    assert "https://auth.mercadolivre.com.br/authorization" in url
    assert "client_id=123456789" in url
    assert "response_type=code" in url
    assert "state=test_state" in url


@pytest.mark.asyncio
async def test_marketplaces_overview_api():
    from app.core.database import get_db

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    try:
        with patch("app.repositories.marketplace_repository.MarketplaceRepository.list_accounts", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/marketplaces/overview")
                assert response.status_code == 200
                data = response.json()
                assert "channels" in data
                assert "accounts" in data

                # Canais listados
                channel_names = [c["marketplace"] for c in data["channels"]]
                assert "MERCADO_LIVRE" in channel_names
                assert "SHOPEE" in channel_names
                assert "AMAZON" in channel_names
                assert "TIKTOK" in channel_names

                # Shopee, Amazon e TikTok devem estar desabilitados (NOT_IMPLEMENTED)
                for c in data["channels"]:
                    if c["marketplace"] in ("SHOPEE", "AMAZON", "TIKTOK"):
                        assert not c["is_configured"]
                        assert not c["is_connected"]
    finally:
        app.dependency_overrides.pop(get_db, None)



@pytest.mark.asyncio
async def test_oauth_exchange_code_mock():
    client = MercadoLivreClient(
        app_id="123456789",
        client_secret="test_secret",
        redirect_uri="http://localhost:3099/marketplaces/callback",
    )

    fake_response = {
        "access_token": "APP_USR-test-token",
        "token_type": "Bearer",
        "expires_in": 21600,
        "scope": "offline_access read write",
        "user_id": 99887766,
        "refresh_token": "TG-test-refresh",
    }

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, json=fake_response)
        result = await client.exchange_code_for_token("test_code_123")
        assert result["access_token"] == "APP_USR-test-token"
        assert result["user_id"] == 99887766
        assert "token_expires_at" in result
