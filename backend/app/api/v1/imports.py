from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body, Query
from uuid import UUID
from typing import Optional
import logging
from app.core.config import settings
from sqlalchemy import select, func
from app.models.import_job import ImportItem

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
from app.repositories.supplier_repository import SupplierRepository
from app.api.deps import DBSession, Storage

router = APIRouter()
service = ImportService()
repo = ImportRepository()
supplier_repo = SupplierRepository()
logger = logging.getLogger(__name__)

async def _handle_upload(
    db: DBSession,
    storage: Storage,
    supplier_id: UUID,
    file: UploadFile,
    importer_type: str,
):
    if importer_type != "lehmox":
        raise HTTPException(501, "Importador não implementado.")
    if not file.filename or len(file.filename) > 255 or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos no formato PDF são aceitos.")

    supplier = await supplier_repo.get_by_id(db, supplier_id)
    if not supplier or not supplier.is_active:
        raise HTTPException(status_code=404, detail="Fornecedor selecionado não foi encontrado no sistema.")

    try:
        content = bytearray()
        while chunk := await file.read(1024 * 1024):
            content.extend(chunk)
            if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                raise HTTPException(413, "Arquivo excede o limite configurado.")
        if not content.startswith(b"%PDF-"):
            raise HTTPException(422, "Conteúdo não reconhecido como PDF.")
        content = bytes(content)
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="O arquivo enviado está vazio.")

        job = await service.create_import(db, supplier_id, file.filename, content, storage)

        # The separate worker consumes the durable UPLOADED job.

        # Fetch fresh job with supplier relation eagerly loaded
        fresh_job = await repo.get_job(db, job.id)
        return fresh_job or job

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Falha no upload tipo=%s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Erro interno ao processar upload.")

@router.post("", response_model=ImportJobResponse)
@router.post("/", response_model=ImportJobResponse, include_in_schema=False)
@router.post("/upload", response_model=ImportJobResponse)
async def upload_import(
    db: DBSession,
    storage: Storage,
    supplier_id: UUID = Form(...),
    file: UploadFile = File(...),
    importer_type: str = Form(...)
):
    return await _handle_upload(db, storage, supplier_id, file, importer_type)

@router.get("", response_model=ImportJobListResponse)
@router.get("/", response_model=ImportJobListResponse, include_in_schema=False)
async def list_imports(db: DBSession, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
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
async def get_import_items(id: UUID, db: DBSession, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    if not await repo.get_job(db, id):
        raise HTTPException(404, "Importação não encontrada.")
    items = (await db.scalars(select(ImportItem).where(ImportItem.import_id == id).order_by(ImportItem.created_at, ImportItem.id).offset(skip).limit(limit))).all()
    total = await db.scalar(select(func.count()).select_from(ImportItem).where(ImportItem.import_id == id))
    return {"items": items, "total": total}

@router.patch("/{id}/items/{item_id}", response_model=ImportItemResponse)
async def update_import_item(id: UUID, item_id: UUID, data: ImportItemUpdateRequest, db: DBSession):
    item = await service.update_item(db, item_id, data, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/items/{item_id}", response_model=ImportItemResponse)
async def update_import_item_alias(item_id: UUID, data: ImportItemUpdateRequest, db: DBSession):
    item = await service.update_item(db, item_id, data)
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
