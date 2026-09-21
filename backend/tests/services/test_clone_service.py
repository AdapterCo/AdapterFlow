import pytest
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import Response
from fastapi import HTTPException

from app.services.clone_service import parse_mlb_id, CloneService
from app.schemas.clone import CloneProductRequest


def test_parse_mlb_id():
    # Full item URL
    assert parse_mlb_id("https://produto.mercadolivre.com.br/MLB-3829102938-fone-bluetooth-sem-fio_JM") == "MLB3829102938"
    # Catalog / P URL
    assert parse_mlb_id("https://www.mercadolivre.com.br/p/MLB19283746") == "MLB19283746"
    # Dashed MLB code
    assert parse_mlb_id("MLB-1234567890") == "MLB1234567890"
    # Lowercase with space
    assert parse_mlb_id("mlb 5544332211") == "MLB5544332211"
    # Raw code
    assert parse_mlb_id("MLB998877") == "MLB998877"

    # Invalid cases
    with pytest.raises(HTTPException) as exc_info:
        parse_mlb_id("https://google.com/search?q=test")
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_clone_preview_mock():
    service = CloneService()

    mock_item = {
        "id": "MLB123456789",
        "title": "Adaptador USB Tipo C para HDMI 4K Lehmox",
        "price": 49.90,
        "original_price": 59.90,
        "category_id": "MLB1234",
        "permalink": "https://produto.mercadolivre.com.br/MLB-123456789",
        "attributes": [
            {"id": "BRAND", "value_name": "Lehmox"},
            {"id": "MODEL", "value_name": "LX-990"},
            {"id": "GTIN", "value_name": "7891234567890"},
            {"id": "COLOR", "value_name": "Cinza Espacial"},
            {"id": "PACKAGE_WEIGHT", "value_name": "120 g"},
        ],
        "pictures": [
            {"secure_url": "https://http2.mlstatic.com/D_12345-MLA.jpg"},
            {"secure_url": "https://http2.mlstatic.com/D_67890-MLA.jpg"},
        ],
    }

    mock_desc = {"plain_text": "Adaptador de altíssima qualidade com saída HDMI 4K."}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        def side_effect(url, *args, **kwargs):
            if "description" in str(url):
                return Response(200, json=mock_desc)
            return Response(200, json=mock_item)

        mock_get.side_effect = side_effect

        preview = await service.preview("https://produto.mercadolivre.com.br/MLB-123456789")

        assert preview.mlb_id == "MLB123456789"
        assert preview.name == "Adaptador USB Tipo C para HDMI 4K Lehmox"
        assert preview.brand == "Lehmox"
        assert preview.model == "LX-990"
        assert preview.ean == "7891234567890"
        assert preview.color == "Cinza Espacial"
        assert preview.weight == Decimal("0.120")
        assert len(preview.pictures) == 2
        assert preview.description == "Adaptador de altíssima qualidade com saída HDMI 4K."


@pytest.mark.asyncio
async def test_clone_preview_catalog_product():
    service = CloneService()

    mock_catalog_product = {
        "id": "MLB3668875507",
        "name": "Suporte De Carro Para Retrovisor 360",
        "buy_box_winner": {
            "price": 28.90,
            "original_price": 35.00,
            "item_id": "MLB999888",
        },
        "short_description": {"content": "Suporte veicular resistente articulado."},
        "attributes": [
            {"id": "BRAND", "value_name": "CarHolder"},
            {"id": "COLOR", "value_name": "Preto"},
        ],
        "pictures": [
            {"url": "https://http2.mlstatic.com/D_11111-MLB.jpg"},
        ],
        "permalink": "https://www.mercadolivre.com.br/p/MLB3668875507",
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(200, json=mock_catalog_product)
        preview = await service.preview("https://www.mercadolivre.com.br/p/MLB3668875507")

        assert preview.mlb_id == "MLB3668875507"
        assert preview.name == "Suporte De Carro Para Retrovisor 360"
        assert preview.price == Decimal("28.90")
        assert preview.brand == "CarHolder"
        assert preview.color == "Preto"
        assert preview.description == "Suporte veicular resistente articulado."
        assert len(preview.pictures) == 1


@pytest.mark.asyncio
async def test_clone_preview_403_informative_error():
    service = CloneService()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(403, json={"message": "Unauthorized by policy"})
        with pytest.raises(HTTPException) as exc:
            await service.preview("https://produto.mercadolivre.com.br/MLB-123456")

        assert exc.value.status_code == 400
        assert "Marketplaces" in exc.value.detail
