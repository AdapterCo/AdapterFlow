import mimetypes
from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from app.api.deps import DBSession, Storage
from app.models.product_image import ProductImage
from app.models.import_job import ImportItem

router = APIRouter()

@router.get("/{path:path}")
async def get_image(path: str, db: DBSession, storage: Storage):
    mime = mimetypes.guess_type(path)[0]
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(404, "Imagem não encontrada.")
    reference = await db.scalar(select(ProductImage.id).where(ProductImage.storage_path == path).limit(1))
    if not reference:
        reference = await db.scalar(select(ImportItem.id).where(ImportItem.image_path == path).limit(1))
    if not reference:
        raise HTTPException(404, "Imagem não encontrada.")
    try:
        return Response(storage.get(path), media_type=mime, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=300"})
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "Imagem não encontrada.")
