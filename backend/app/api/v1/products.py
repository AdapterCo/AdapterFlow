from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from uuid import UUID
from app.schemas.product import ProductListResponse, ProductWithDetailsResponse, ProductUpdate, SupplierLinkUpdate
from app.services.product_service import ProductService
from app.api.deps import DBSession

router = APIRouter()
service = ProductService()

@router.get("", response_model=ProductListResponse)
@router.get("/", response_model=ProductListResponse, include_in_schema=False)
async def list_products(db: DBSession, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), search: Optional[str] = None, status: Optional[str] = None):
    return await service.list_products(db, skip, limit, search, status)

@router.get("/{id}", response_model=ProductWithDetailsResponse)
async def get_product(id: UUID, db: DBSession):
    product = await service.get_product_with_details(db, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch("/{id}", response_model=ProductWithDetailsResponse)
async def update_product(id: UUID, data: ProductUpdate, db: DBSession):
    values = data.model_dump(exclude_unset=True)
    if any(values.get(key) is None for key in ("name", "status") if key in values):
        raise HTTPException(422, "Nome e status não podem ser nulos.")
    product = await service.repo.update(db, id, values)
    if not product:
        raise HTTPException(404, "Produto não encontrado.")
    return await service.get_product_with_details(db, id)


@router.patch("/{id}/suppliers/{supplier_data_id}", response_model=ProductWithDetailsResponse)
async def update_supplier_link(id: UUID, supplier_data_id: UUID, data: SupplierLinkUpdate, db: DBSession):
    return await service.update_supplier_link(db, id, supplier_data_id, data)
