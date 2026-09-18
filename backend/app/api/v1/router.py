from fastapi import APIRouter
from app.api.v1 import suppliers, products, imports

api_router = APIRouter()
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
