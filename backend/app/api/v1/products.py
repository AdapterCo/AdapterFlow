from fastapi import APIRouter, HTTPException, Depends, Response
from typing import Optional
from uuid import UUID
from app.schemas.product import ProductResponse, ProductListResponse, ProductWithDetailsResponse
from app.services.product_service import ProductService
from app.api.deps import DBSession, Storage
import mimetypes

router = APIRouter()
service = ProductService()

@router.get("", response_model=ProductListResponse)
@router.get("/", response_model=ProductListResponse, include_in_schema=False)
async def list_products(db: DBSession, skip: int = 0, limit: int = 100, search: Optional[str] = None, status: Optional[str] = None):
    return await service.list_products(db, skip, limit, search, status)

@router.get("/{id}", response_model=ProductWithDetailsResponse)
async def get_product(id: UUID, db: DBSession):
    product = await service.get_product_with_details(db, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/{id}/images/{image_path:path}")
async def get_product_image(id: UUID, image_path: str, storage: Storage):
    try:
        data = storage.get(image_path)
        mime_type, _ = mimetypes.guess_type(image_path)
        return Response(content=data, media_type=mime_type or "application/octet-stream")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
