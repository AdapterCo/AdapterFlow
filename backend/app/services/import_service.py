import asyncio
import base64
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.import_job import ImportJob, ImportItem
from app.models.supplier import Supplier
from app.repositories.import_repository import ImportRepository
from app.services.product_service import ProductService
from app.storage.service import StorageService

logger = logging.getLogger(__name__)


def extract_isolated(storage: StorageService, path: str) -> list[dict]:
    with storage.materialize(path) as source, TemporaryDirectory() as directory:
        output = Path(directory) / "result.json"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "app.importers.runner", str(source), str(output)],
                timeout=300, capture_output=True, check=False,
                cwd=directory,
                env={**{key: value for key, value in os.environ.items() if key.upper() in {"PATH", "SYSTEMROOT", "TEMP", "TMP", "TESSDATA_PREFIX"}},
                     "PYTHONPATH": str(Path(__file__).resolve().parents[2]), "PYTHONUTF8": "1",
                     "OCR_ENABLED": str(settings.OCR_ENABLED), "OCR_LANGUAGE": settings.OCR_LANGUAGE, "MAX_PDF_PAGES": str(settings.MAX_PDF_PAGES)},
            )
        except subprocess.TimeoutExpired:
            raise ValueError("A extração excedeu 5 minutos. Tente processar um intervalo menor de páginas ou revise o OCR do arquivo.") from None
        if result.returncode:
            # The runner returns only classified errors; never expose subprocess stderr.
            error = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
            raise ValueError(error.get("error", "Falha ao extrair PDF."))
        return json.loads(output.read_text(encoding="utf-8"))


class ImportService:
    def __init__(self):
        self.repo = ImportRepository()
        self.product_svc = ProductService()

    async def create_import(self, session: AsyncSession, supplier_id: UUID, file_name: str, file_content: bytes, storage: StorageService):
        job_id = uuid4()
        path = f"imports/{supplier_id}/{job_id}.pdf"
        storage.put(path, file_content)
        try:
            job = await self.repo.create_job(session, {
                "id": job_id, "supplier_id": supplier_id, "file_name": file_name,
                "file_path": path, "file_size": len(file_content),
                "file_hash": hashlib.sha256(file_content).hexdigest(),
                "importer_type": "lehmox", "status": "UPLOADED",
            })
            await session.commit()  # File ownership is durable before the worker sees it.
            return job
        except Exception:
            await session.rollback()
            storage.delete(path)
            raise

    async def process_import(self, session: AsyncSession, job_id: UUID, storage: StorageService):
        await self.process_import_background(job_id, storage)
        return await self.repo.get_job(session, job_id)

    async def process_import_background(self, job_id: UUID, storage: StorageService):
        from app.core.database import async_session_maker
        saved_images = []
        async with async_session_maker() as session:
            job = await session.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
            if not job or job.status != "UPLOADED":
                return
            job.status = "PROCESSING"
            job.started_at = datetime.now(timezone.utc)
            await session.commit()
            try:
                extracted = await asyncio.to_thread(extract_isolated, storage, job.file_path)
                if not extracted:
                    raise ValueError("Nenhum produto identificado. Verifique se o layout é suportado.")
                for item in extracted:
                    image_path = None
                    if item.get("image_data"):
                        ext = item.get("image_extension")
                        if ext not in {"png", "jpg", "jpeg", "webp"}:
                            item.setdefault("warnings", []).append("Formato de imagem não suportado.")
                        else:
                            image_path = f"products/{job.supplier_id}/{job.id}/{uuid4()}.{ext}"
                            storage.put(image_path, base64.b64decode(item["image_data"], validate=True))
                            saved_images.append(image_path)
                    unavailable = item.get("is_out_of_stock", False)
                    raw = {key: value for key, value in item.items() if key.startswith("raw_")}
                    raw.update(page_number=item.get("page_number"), bbox=item.get("bbox"))
                    normalized = {key: value for key, value in item.items() if key.startswith("normalized_")}
                    normalized.update(is_out_of_stock=unavailable, warnings=item.get("warnings", []))
                    session.add(ImportItem(
                        import_id=job.id, raw_data=raw, normalized_data=normalized,
                        confidence=item.get("confidence"), image_path=image_path,
                        status="IGNORED" if unavailable else "DETECTED",
                        review_notes="Esgotado explicitamente no catálogo." if unavailable else None,
                    ))
                job.status = "REVIEW_REQUIRED"
                job.total_detected = len(extracted)
                job.total_errors = 0
                job.processing_log = {"adapter": "lehmox", "source_hash": job.file_hash}
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                for path in saved_images:
                    storage.delete(path)
                job = await self.repo.get_job(session, job_id)
                job.status = "FAILED"
                job.error_message = str(exc)[:400] if isinstance(exc, ValueError) else "Falha na extração; consulte o administrador."
                job.completed_at = datetime.now(timezone.utc)
                logger.error("Extração falhou job=%s tipo=%s", job_id, type(exc).__name__)
                await session.commit()

    async def update_item(self, session: AsyncSession, item_id: UUID, data, job_id: UUID | None = None):
        item = await self.repo.get_item(session, item_id)
        if not item or (job_id is not None and item.import_id != job_id):
            raise HTTPException(404, "Item não encontrado nesta importação.")
        job = await session.scalar(select(ImportJob).where(ImportJob.id == item.import_id).with_for_update())
        await session.refresh(item)
        if job.status != "REVIEW_REQUIRED" or item.status == "IMPORTED":
            raise HTTPException(409, "Esta importação não está disponível para revisão.")
        values = data.model_dump(exclude_unset=True, mode="json")
        if "status" in values:
            if values["status"] is None:
                raise HTTPException(422, "Status não pode ser nulo.")
            item.status = values.pop("status")
        if "review_notes" in values:
            item.review_notes = values.pop("review_notes")
        item.user_edits = {**(item.user_edits or {}), **values}
        await session.flush()
        await session.refresh(item)
        return item

    async def confirm_import(self, session: AsyncSession, job_id: UUID, approved_ids=None, rejected_ids=None, storage=None):
        job = await session.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
        if not job:
            return None
        if job.status == "IMPORTED":
            return job  # Idempotent confirmation.
        if job.status != "REVIEW_REQUIRED":
            raise HTTPException(409, "Aguarde a extração antes de confirmar.")
        supplier = await session.scalar(select(Supplier).where(Supplier.id == job.supplier_id).with_for_update())
        if not supplier or not supplier.is_active:
            raise HTTPException(409, "Fornecedor inativo.")
        items = await self.repo.get_items_by_job(session, job_id)
        by_id = {item.id: item for item in items}
        approved = set(approved_ids or [])
        rejected = set(rejected_ids or [])
        if not (approved | rejected).issubset(by_id) or approved & rejected:
            raise HTTPException(422, "Seleção de itens inválida para esta importação.")
        for item_id in approved:
            if by_id[item_id].status == "IMPORTED":
                continue
            by_id[item_id].status = "APPROVED"
        for item_id in rejected:
            if by_id[item_id].status == "IMPORTED":
                raise HTTPException(409, "Item já importado não pode ser rejeitado.")
            by_id[item_id].status = "REJECTED"
        if any(item.status in {"DETECTED", "ERROR"} for item in items):
            raise HTTPException(409, "Revise todos os itens: aprove ou ignore cada pendência.")
        for item in items:
            if item.status == "APPROVED":
                await self.product_svc.create_from_import(session, item, job.supplier_id)
        job.total_imported = sum(item.status == "IMPORTED" for item in items)
        job.total_errors = 0
        job.status = "IMPORTED"
        job.completed_at = datetime.now(timezone.utc)
        await session.flush()
        return await self.repo.get_job(session, job_id)
