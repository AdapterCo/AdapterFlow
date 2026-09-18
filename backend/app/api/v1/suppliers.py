from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse, SupplierList
from app.services.supplier_service import SupplierService
from app.api.deps import DBSession

router = APIRouter()
service = SupplierService()

@router.post("", response_model=SupplierResponse)
@router.post("/", response_model=SupplierResponse, include_in_schema=False)
async def create_supplier(data: SupplierCreate, db: DBSession):
    return await service.create(db, data)

@router.get("", response_model=SupplierList)
@router.get("/", response_model=SupplierList, include_in_schema=False)
async def list_suppliers(db: DBSession, skip: int = 0, limit: int = 100):
    items = await service.list_all(db, skip, limit)
    total = await service.count(db)
    return {"items": items, "total": total}

@router.get("/{id}", response_model=SupplierResponse)
async def get_supplier(id: UUID, db: DBSession):
    supplier = await service.get_by_id(db, id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.patch("/{id}", response_model=SupplierResponse)
async def update_supplier(id: UUID, data: SupplierUpdate, db: DBSession):
    supplier = await service.update(db, id, data)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.delete("/{id}", response_model=SupplierResponse)
async def deactivate_supplier(id: UUID, db: DBSession):
    supplier = await service.deactivate(db, id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier
