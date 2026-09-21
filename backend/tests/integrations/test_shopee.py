import hashlib
import hmac
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport, Response
from fastapi import HTTPException

from app.integrations.shopee.client import ShopeeClient
from app.main import app


def test_shopee_client_configuration():
    client_unconfigured = ShopeeClient(partner_id=None, partner_key=None, redirect_uri=None)
    assert not client_unconfigured.is_configured()

    with pytest.raises(HTTPException) as exc_info:
        client_unconfigured.get_authorization_url(state="test_state")
    assert exc_info.value.status_code == 503

    client_configured = ShopeeClient(
        partner_id=12345,
        partner_key="secret_partner_key_shopee",
        redirect_uri="https://flow.adapterco.com.br/marketplaces/callback/shopee",
        base_url="https://partner.shopeemobile.com",
    )
    assert client_configured.is_configured()


def test_shopee_hmac_sha256_signature():
    partner_id = 10001
    partner_key = "my_shopee_secret"
    client = ShopeeClient(
        partner_id=partner_id,
        partner_key=partner_key,
        redirect_uri="https://example.com/callback",
    )

    # Public/Auth endpoint signature
    path = "/api/v2/shop/auth_partner"
    timestamp = 1700000000
    expected_base = f"{partner_id}{path}{timestamp}"
    expected_sign = hmac.new(partner_key.encode("utf-8"), expected_base.encode("utf-8"), hashlib.sha256).hexdigest()
    assert client._generate_sign(path, timestamp) == expected_sign

    # Shop-level API endpoint with access_token and shop_id
    shop_path = "/api/v2/product/get_category"
    access_token = "valid_shopee_token"
    shop_id = 998877
    expected_shop_base = f"{partner_id}{shop_path}{timestamp}{access_token}{shop_id}"
    expected_shop_sign = hmac.new(partner_key.encode("utf-8"), expected_shop_base.encode("utf-8"), hashlib.sha256).hexdigest()
    assert client._generate_sign(shop_path, timestamp, access_token=access_token, shop_id=shop_id) == expected_shop_sign


def test_shopee_authorization_url():
    client = ShopeeClient(
        partner_id=88888,
        partner_key="key_88888",
        redirect_uri="https://flow.adapterco.com.br/marketplaces/callback/shopee",
    )
    url = client.get_authorization_url("state_abc123")
    assert "https://partner.shopeemobile.com/api/v2/shop/auth_partner" in url
    assert "partner_id=88888" in url
    assert "sign=" in url
    assert "timestamp=" in url
    assert "redirect=" in url


@pytest.mark.asyncio
async def test_shopee_exchange_token_mock():
    client = ShopeeClient(
        partner_id=12345,
        partner_key="secret_key",
        redirect_uri="https://example.com/callback",
    )

    fake_response = {
        "error": "",
        "message": "",
        "response": {
            "access_token": "shopee_access_xyz",
            "refresh_token": "shopee_refresh_xyz",
            "expire_in": 14400,
            "merchant_id_list": [],
            "shop_id_list": [991122],
        },
    }

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = Response(200, json=fake_response)
        result = await client.exchange_token(code="code_123", shop_id=991122)
        assert result["access_token"] == "shopee_access_xyz"
        assert result["refresh_token"] == "shopee_refresh_xyz"
        assert result["expire_in"] == 14400


@pytest.mark.asyncio
async def test_shopee_refresh_token_mock():
    client = ShopeeClient(
        partner_id=12345,
        partner_key="secret_key",
        redirect_uri="https://example.com/callback",
    )

    fake_response = {
        "error": "",
        "message": "",
        "response": {
            "access_token": "new_shopee_access_token",
            "refresh_token": "new_shopee_refresh_token",
            "expire_in": 14400,
        },
    }

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = Response(200, json=fake_response)
        result = await client.refresh_token(refresh_token="old_refresh", shop_id=991122)
        assert result["access_token"] == "new_shopee_access_token"
        assert result["refresh_token"] == "new_shopee_refresh_token"


@pytest.mark.asyncio
async def test_shopee_configuration_endpoint():
    from app.core.database import get_db

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/marketplaces/shopee/configuration")
            assert response.status_code == 200
            data = response.json()
            assert "partner_id" in data
            assert "ready" in data
            assert "issues" in data
    finally:
        app.dependency_overrides.pop(get_db, None)
