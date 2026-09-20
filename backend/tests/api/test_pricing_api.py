import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from decimal import Decimal


@pytest.mark.asyncio
async def test_simulate_pricing_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "cost_basis": "100.00",
            "fixed_fee": "0",
            "marketplace_commission_percent": "14.00",
            "tax_percent": "6.00",
            "operating_cost_percent": "3.00",
            "fixed_cost": "3.00",
            "target_margin_percent": "15.00",
            "free_shipping_threshold": "79.00",
            "free_shipping_cost": "18.00",
            "rounding_rule": "ENDS_90"
        }
        response = await client.post("/api/v1/pricing/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["suggested_price"]) == Decimal("195.90")
        assert Decimal(data["shipping_cost"]) == Decimal("18.00")
        assert "breakdown" in data
        assert data["breakdown"]["gross_revenue"] == "195.90"


@pytest.mark.asyncio
async def test_simulate_pricing_api_impossible_margin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "cost_basis": "100.00",
            "fixed_fee": "0",
            "marketplace_commission_percent": "50.00",
            "tax_percent": "30.00",
            "operating_cost_percent": "25.00",
            "target_margin_percent": "10.00",
            "fixed_cost": "0", "rounding_rule": "EXACT"
        }
        response = await client.post("/api/v1/pricing/simulate", json=payload)
        assert response.status_code == 422
        assert "menor que 100%" in response.json()["detail"]
