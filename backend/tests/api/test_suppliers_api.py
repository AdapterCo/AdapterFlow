import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.deps import DBSession
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_create_and_list_suppliers(monkeypatch):
    # Mocking db session to verify repository/service contracts
    mock_db = AsyncMock()
    
    # Test through AsyncClient directly with mocked get_db
    from app.core.database import get_db
    
    fake_supplier = {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Fornecedor Teste",
        "code": "FORN-TEST",
        "contact_info": None,
        "is_active": True,
        "created_at": "2026-09-18T12:00:00Z",
        "updated_at": None,
    }
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        from app.services.supplier_service import SupplierService
        original_create = SupplierService.create
        original_list = SupplierService.list_all
        original_count = SupplierService.count
        
        # Test mock return
        from app.schemas.supplier import SupplierResponse
        monkeypatch.setattr(SupplierService, "create", AsyncMock(return_value=SupplierResponse(**fake_supplier)))
        monkeypatch.setattr(SupplierService, "list_all", AsyncMock(return_value=[SupplierResponse(**fake_supplier)]))
        monkeypatch.setattr(SupplierService, "count", AsyncMock(return_value=1))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Test POST /api/v1/suppliers
            res_create = await client.post("/api/v1/suppliers", json={"name": "Fornecedor Teste", "code": "FORN-TEST"})
            assert res_create.status_code == 200
            data_create = res_create.json()
            assert data_create["name"] == "Fornecedor Teste"
            assert data_create["code"] == "FORN-TEST"
            
            # 2. Test GET /api/v1/suppliers
            res_list = await client.get("/api/v1/suppliers")
            assert res_list.status_code == 200
            data_list = res_list.json()
            assert data_list["total"] == 1
            assert len(data_list["items"]) == 1
            assert data_list["items"][0]["name"] == "Fornecedor Teste"
            
        SupplierService.create = original_create
        SupplierService.list_all = original_list
        SupplierService.count = original_count
    finally:
        app.dependency_overrides.clear()
