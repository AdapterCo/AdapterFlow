from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body, Query
from fastapi.responses import StreamingResponse
from uuid import UUID
from typing import Optional
import logging
from sqlalchemy import select, func
from app.models.import_job import ImportItem

from app.schemas.import_job import (
    ImportJobResponse,
    ImportJobListResponse,
    ImportItemResponse,
    ImportItemListResponse,
    ImportPageListResponse,
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
    normalized_importer = (importer_type or "lehmox").strip().lower()
    if normalized_importer not in {"lehmox", "pdf", "catalog", "generic"}:
        normalized_importer = "lehmox"
    if not file.filename or len(file.filename) > 255 or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos no formato PDF são aceitos.")

    supplier = await supplier_repo.get_by_id(db, supplier_id)
    if not supplier or not supplier.is_active:
        raise HTTPException(status_code=404, detail="Fornecedor selecionado não foi encontrado no sistema.")

    try:
        if await file.read(5) != b"%PDF-":
            raise HTTPException(422, "Conteúdo não reconhecido como PDF.")
        await file.seek(0)
        job = await service.create_import_stream(db, supplier_id, file.filename, file.file, storage)

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


@router.get("/{id}/pages", response_model=ImportPageListResponse)
async def get_import_pages(id: UUID, db: DBSession, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=50)):
    if not await repo.get_job(db, id):
        raise HTTPException(404, "Importação não encontrada.")
    return {
        "items": await repo.list_pages(db, id, skip=skip, limit=limit),
        "total": await repo.count_pages(db, id),
    }


@router.get("/{id}/source")
async def get_import_source(id: UUID, db: DBSession, storage: Storage):
    job = await repo.get_job(db, id)
    if not job or not storage.exists(job.file_path):
        raise HTTPException(404, "PDF original não encontrado.")
    return StreamingResponse(storage.iter_bytes(job.file_path), media_type="application/pdf", headers={
        "Content-Disposition": 'inline; filename="catalogo.pdf"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
    })


@router.post("/{id}/pages/{number}/retry", response_model=ImportJobResponse)
async def retry_page(id: UUID, number: int, db: DBSession, ocr: bool = False):
    return await service.retry_page(db, id, number, ocr)


@router.post("/{id}/pages/{number}/items", response_model=ImportItemResponse)
async def add_manual_item(id: UUID, number: int, data: ImportItemUpdateRequest, db: DBSession):
    return await service.add_manual_item(db, id, number, data)


@router.post("/{id}/retry", response_model=ImportJobResponse)
async def retry_import(id: UUID, db: DBSession):
    return await service.retry_import(db, id)


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


@router.post("/{id}/items/{item_id}/unavailable", response_model=ImportItemResponse)
async def mark_supplier_unavailable(id: UUID, item_id: UUID, db: DBSession):
    from app.models.import_job import ImportJob
    from app.models.product import ProductSupplierData
    from app.models.pricing import ProductChannelPrice
    from sqlalchemy import update
    job = await db.scalar(select(ImportJob).where(ImportJob.id == id).with_for_update())
    if not job or job.status not in {"REVIEW_REQUIRED", "IMPORTED"}:
        raise HTTPException(409, "Importação indisponível para revisão.")
    item = await repo.get_item(db, item_id)
    if not item or item.import_id != id:
        raise HTTPException(404, "Item não encontrado nesta importação.")
    if item.status == "IMPORTED":
        return item
    values = {**(item.normalized_data or {}), **(item.user_edits or {})}
    if not values.get("is_out_of_stock") or not values.get("normalized_code"):
        raise HTTPException(422, "A origem deve indicar esgotamento e código do fornecedor.")
    link = await db.scalar(select(ProductSupplierData).where(ProductSupplierData.supplier_id == job.supplier_id, ProductSupplierData.supplier_code == values["normalized_code"]).with_for_update())
    if not link:
        raise HTTPException(409, "Não existe vínculo com este código; revise o produto ou ignore o item.")
    link.is_active = False
    await db.execute(update(ProductChannelPrice).where(ProductChannelPrice.product_id == link.product_id).values(is_stale=True))
    item.product_id = link.product_id
    item.status = "IMPORTED"
    item.review_notes = "Disponibilidade do fornecedor atualizada pelo operador a partir do esgotamento no catálogo."
    job.total_imported = (job.total_imported or 0) + 1
    await db.flush()
    return item

@router.patch("/items/{item_id}", response_model=ImportItemResponse)
async def update_import_item_alias(item_id: UUID, data: ImportItemUpdateRequest, db: DBSession):
    item = await service.update_item(db, item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.post("/{id}/approve-all")
async def approve_all_import_items(id: UUID, db: DBSession):
    return await service.approve_all_items(db, id)


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
