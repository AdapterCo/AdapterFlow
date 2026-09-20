from fastapi import APIRouter, Depends
from app.core.security import require_admin
from app.api.v1 import suppliers, products, imports, pricing, marketplaces

api_router = APIRouter(dependencies=[Depends(require_admin)])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"])
api_router.include_router(marketplaces.router, prefix="/marketplaces", tags=["marketplaces"])

from app.api.v1 import storage
api_router.include_router(storage.router, prefix="/storage", tags=["storage"])
