from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Response, Body
from uuid import UUID
from typing import Optional
from app.schemas.import_job import (
    ImportJobResponse,
    ImportJobListResponse,
    ImportItemResponse,
    ImportItemListResponse,
    ImportItemUpdateRequest,
    ImportConfirmRequest
)
from app.services.import_service import ImportService
from app.repositories.import_repository import ImportRepository
from app.api.deps import DBSession, Storage
import mimetypes

router = APIRouter()
service = ImportService()
repo = ImportRepository()

async def _handle_upload(db: DBSession, storage: Storage, supplier_id: UUID, file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    content = await file.read()
    job = await service.create_import(db, supplier_id, file.filename, content, storage)
    await service.process_import(db, job.id, storage)
    return await repo.get_job(db, job.id)

@router.post("/", response_model=ImportJobResponse)
async def upload_import(db: DBSession, storage: Storage, supplier_id: UUID = Form(...), file: UploadFile = File(...)):
    return await _handle_upload(db, storage, supplier_id, file)

@router.post("/upload", response_model=ImportJobResponse)
async def upload_import_alias(db: DBSession, storage: Storage, supplier_id: UUID = Form(...), file: UploadFile = File(...)):
    return await _handle_upload(db, storage, supplier_id, file)

@router.get("/", response_model=ImportJobListResponse)
async def list_imports(db: DBSession, skip: int = 0, limit: int = 100):
    items = await repo.list_jobs(db, skip, limit)
    total = await repo.count_jobs(db)
    return {"items": items, "total": total}

@router.get("/{id}", response_model=ImportJobResponse)
async def get_import(id: UUID, db: DBSession):
    job = await repo.get_job(db, id)
    if not job:
        raise HTTPException(status_code=404, detail="Import not found")
    return job

@router.get("/{id}/items", response_model=ImportItemListResponse)
async def get_import_items(id: UUID, db: DBSession):
    items = await repo.get_items_by_job(db, id)
    return {"items": items, "total": len(items)}

@router.patch("/{id}/items/{item_id}", response_model=ImportItemResponse)
async def update_import_item(id: UUID, item_id: UUID, data: ImportItemUpdateRequest, db: DBSession):
    update_dict = data.model_dump(exclude_unset=True)
    item = await repo.update_item(db, item_id, update_dict)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/items/{item_id}", response_model=ImportItemResponse)
async def update_import_item_alias(item_id: UUID, data: ImportItemUpdateRequest, db: DBSession):
    update_dict = data.model_dump(exclude_unset=True)
    item = await repo.update_item(db, item_id, update_dict)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.post("/{id}/confirm", response_model=ImportJobResponse)
async def confirm_import(
    id: UUID, 
    db: DBSession, 
    storage: Storage,
    data: Optional[ImportConfirmRequest] = Body(default=None)
):
    approved_ids = data.approved_item_ids if data else None
    rejected_ids = data.rejected_item_ids if data else None
    job = await service.confirm_import(db, id, approved_ids, rejected_ids, storage)
    if not job:
        raise HTTPException(status_code=404, detail="Import not found")
    return job

@router.get("/images/{path:path}")
async def get_import_image(path: str, storage: Storage):
    try:
        data = storage.get(path)
        mime_type, _ = mimetypes.guess_type(path)
        return Response(content=data, media_type=mime_type or "application/octet-stream")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
