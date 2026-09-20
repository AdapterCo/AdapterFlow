"""Synthetic review cases; source values are never substituted with invented data."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.import_job import ImportItem
from app.models.product import ProductSupplierData, SupplierProductPrice
from app.services.product_service import ProductService


def item_with(**changes):
    return ImportItem(
        id=uuid4(), import_id=uuid4(), status="APPROVED",
        normalized_data={"normalized_code": "SOURCE-123", "normalized_name": "Nome da fonte", **changes},
        raw_data={"page_number": 3},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("changes,description", [
    ({"normalized_code": None}, "Código do fornecedor não identificado"),
    ({"normalized_code": "  "}, "Código do fornecedor não identificado"),
    ({"normalized_name": None}, "Nome não identificado"),
    ({"normalized_name": "\t "}, "Nome não identificado"),
    ({"normalized_code": "X" * 101}, "Código do fornecedor excede 100"),
    ({"normalized_name": "X" * 501}, "Nome excede 500"),
    ({"normalized_color": "X" * 101}, "Cor excede 100"),
    ({"normalized_name": "Nome\x00inválido"}, "Nome contém um caractere inválido"),
    ({"normalized_name": ["Nome"]}, "Nome deve ser texto"),
    ({"normalized_price": "não é um preço"}, "Custo inválido"),
    ({"normalized_price": "NaN"}, "Custo deve estar entre"),
    ({"normalized_price": "Infinity"}, "Custo deve estar entre"),
    ({"normalized_price": "-1"}, "Custo deve estar entre"),
    ({"normalized_price": "100000000"}, "Custo deve estar entre"),
    ({"normalized_price": "1.00001"}, "Custo deve ter no máximo quatro"),
    ({"normalized_price": 1.25}, "Custo deve ser um decimal em texto"),
    ({"normalized_price": True}, "Custo deve ser um decimal em texto"),
    ({"normalized_pcs_per_box": 2147483648}, "Quantidade por caixa deve ser"),
    ({"normalized_pcs_per_box": -2}, "Quantidade por caixa deve ser"),
    ({"normalized_pcs_per_box": 1.5}, "Quantidade por caixa deve ser"),
    ({"normalized_pcs_per_box": True}, "Quantidade por caixa deve ser"),
    ({"is_out_of_stock": "false"}, "A indicação de esgotado é inválida"),
])
async def test_invalid_review_returns_actionable_error_before_database_write(changes, description):
    item = item_with(**changes)
    service = ProductService()
    service.repo = AsyncMock()
    session = Mock()
    session.flush = AsyncMock()

    with pytest.raises(HTTPException) as error:
        await service.create_from_import(session, item, uuid4())

    assert error.value.status_code == 422
    assert description in error.value.detail
    assert str(item.id) in error.value.detail
    assert "página 3" in error.value.detail
    assert service.repo.mock_calls == []
    assert session.mock_calls == []
    assert item.status == "APPROVED"
    assert item.product_id is None


def test_explicitly_cleared_identity_does_not_return_from_raw_data():
    item = item_with()
    item.raw_data.update(raw_code="RAW-123", raw_name="Nome bruto")
    item.user_edits = {"normalized_code": None}
    with pytest.raises(HTTPException, match="Código do fornecedor não identificado"):
        ProductService.validate_import_item(item)
    item.user_edits = {"normalized_name": None}
    with pytest.raises(HTTPException, match="Nome não identificado"):
        ProductService.validate_import_item(item)


@pytest.mark.asyncio
async def test_missing_optional_fields_remain_null_and_no_sku_is_fabricated():
    item = item_with()
    service = ProductService()
    service.repo = AsyncMock()
    service.repo.find_by_supplier_code.return_value = None
    service.repo.create.return_value = SimpleNamespace(id=uuid4())
    session = Mock()
    session.flush = AsyncMock()
    supplier_id = uuid4()

    product = await service.create_from_import(session, item, supplier_id)

    service.repo.find_by_supplier_code.assert_awaited_once_with(session, supplier_id, "SOURCE-123")
    data = service.repo.create.call_args.args[1]
    assert data["name"] == "Nome da fonte"
    assert data["sku"] is None
    assert data["color"] is None
    assert data["dimensions"] is None
    link = session.add.call_args_list[0].args[0]
    assert isinstance(link, ProductSupplierData)
    assert link.supplier_code == "SOURCE-123"
    assert link.current_cost is None
    assert link.pcs_per_box is None
    assert not any(isinstance(call.args[0], SupplierProductPrice) for call in session.add.call_args_list)
    assert item.product_id == product.id
    assert item.status == "IMPORTED"


def test_reviewed_values_preserve_decimal_precision_and_respect_storage_boundaries():
    item = item_with(
        normalized_code="X" * 100,
        normalized_name="N" * 500,
        normalized_color="C" * 100,
        normalized_price="99999999.9999",
        normalized_pcs_per_box=2147483647,
    )
    values = ProductService.validate_import_item(item)
    assert values["normalized_price"] == Decimal("99999999.9999")
    item.user_edits = {"normalized_price": "0.00010", "normalized_color": None}
    values = ProductService.validate_import_item(item)
    assert values["normalized_price"] == Decimal("0.0001")
    assert values["normalized_color"] is None
    assert item.normalized_data["normalized_price"] == "99999999.9999"
