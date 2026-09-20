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
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.import_job import ImportJob, ImportItem, ImportPage
from app.models.supplier import Supplier
from app.repositories.import_repository import ImportRepository
from app.services.product_service import ProductService
from app.storage.service import StorageService

logger = logging.getLogger(__name__)


def run_extractor(source: Path, *arguments: str):
    """Bound each page independently; a large catalog has no whole-file deadline."""
    with TemporaryDirectory() as directory:
        output = Path(directory) / "result.json"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "app.importers.runner", str(source), str(output), *arguments],
                timeout=300, capture_output=True, check=False,
                cwd=directory,
                env={**{key: value for key, value in os.environ.items() if key.upper() in {"PATH", "SYSTEMROOT", "TEMP", "TMP", "TESSDATA_PREFIX"}},
                     "PYTHONPATH": str(Path(__file__).resolve().parents[2]), "PYTHONUTF8": "1",
                     "OCR_ENABLED": str(settings.OCR_ENABLED), "OCR_LANGUAGE": settings.OCR_LANGUAGE, "MAX_PDF_PAGES": str(settings.MAX_PDF_PAGES)},
            )
        except subprocess.TimeoutExpired:
            raise ValueError("A leitura desta página excedeu 5 minutos. As demais páginas foram preservadas; tente novamente.") from None
        if result.returncode:
            # The runner returns only classified errors; never expose subprocess stderr.
            error = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
            raise ValueError(error.get("error", "Falha ao extrair PDF."))
        return json.loads(output.read_text(encoding="utf-8"))


def extract_isolated(storage: StorageService, path: str) -> list[dict]:
    """Compatibility helper; the worker persists each page instead of buffering this list."""
    with storage.materialize(path) as source:
        metadata = run_extractor(source, "--metadata")
        products = []
        for number in range(1, metadata["total_pages"] + 1):
            page = run_extractor(source, "--page", str(number))
            if page["status"] == "FAILED":
                raise ValueError(page["error_message"])
            products.extend(page["products"])
        return products


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
        async with async_session_maker() as session:
            job = await session.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
            if not job or job.status != "UPLOADED":
                return
            job.status = "PROCESSING"
            job.started_at = datetime.now(timezone.utc)
            job.last_progress_at = job.started_at
            job.error_message = None
            job.completed_at = None
            await session.commit()
            try:
                with storage.materialize(job.file_path) as source:
                    metadata = await asyncio.to_thread(run_extractor, source, "--metadata")
                    job.total_pages = metadata["total_pages"]
                    pages = list((await session.scalars(select(ImportPage).where(ImportPage.import_id == job_id))).all())
                    completed = {page.page_number for page in pages if page.status != "FAILED"}
                    job.processed_pages = len(completed)
                    await session.commit()
                    for number in range(1, job.total_pages + 1):
                        if number in completed:
                            continue
                        try:
                            report = await asyncio.to_thread(run_extractor, source, "--page", str(number))
                        except ValueError as exc:
                            report = {"page_number": number, "status": "FAILED", "error_message": str(exc),
                                      "text_blocks": [], "images": [], "products": [], "warnings": []}
                        await self._persist_page(session, job, report, storage)
                    pages = list((await session.scalars(select(ImportPage).where(ImportPage.import_id == job_id))).all())
                failed = [page.page_number for page in pages if page.status == "FAILED"]
                job.status = "FAILED" if failed else "REVIEW_REQUIRED"
                job.total_detected = sum(page.product_count for page in pages)
                job.total_errors = len(failed)
                job.error_message = (f"Falha nas páginas {', '.join(map(str, failed))}. Use Tentar novamente; as páginas concluídas serão mantidas." if failed else None)
                job.processing_log = {"adapter": "lehmox", "source_hash": job.file_hash,
                                      "pages_needing_review": [page.page_number for page in pages if page.status == "NEEDS_REVIEW"]}
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                job = await self.repo.get_job(session, job_id)
                job.status = "FAILED"
                job.error_message = str(exc)[:400] if isinstance(exc, ValueError) else "Falha ao salvar a leitura. As páginas concluídas foram preservadas; tente novamente."
                job.completed_at = datetime.now(timezone.utc)
                logger.error("Extração falhou job=%s tipo=%s", job_id, type(exc).__name__)
                await session.commit()

    async def _persist_page(self, session, job, report, storage):
        """Commit evidence, candidates and progress together before reading the next page."""
        saved_paths = []
        previous_paths = []
        images_by_hash = {}

        def save_image(encoded, extension):
            if not encoded:
                return None
            if extension not in {"png", "jpg", "jpeg", "webp"}:
                report["warnings"].append("Imagem em formato não exibível; consulte o PDF original.")
                return None
            content = base64.b64decode(encoded, validate=True)
            digest = hashlib.sha256(content).hexdigest()
            if digest not in images_by_hash:
                path = f"imports/{job.supplier_id}/{job.id}/pages/{report['page_number']}/{uuid4()}.{extension}"
                storage.put(path, content)
                saved_paths.append(path)
                images_by_hash[digest] = path
            return images_by_hash[digest]

        try:
            previous = await session.scalar(select(ImportPage).where(
                ImportPage.import_id == job.id, ImportPage.page_number == report["page_number"]))
            if previous:
                if previous.status != "FAILED":
                    return
                previous_paths = list(previous.image_paths)
                await session.delete(previous)
                await session.flush()
            for image in report.get("images", []):
                save_image(image.get("data"), image.get("ext"))
            products = report.get("products", []) if report["status"] != "FAILED" else []
            for item in products:
                image_path = save_image(item.get("image_data"), item.get("image_extension"))
                unavailable = item.get("is_out_of_stock", False)
                raw = {key: value for key, value in item.items() if key.startswith("raw_")}
                raw.update(page_number=report["page_number"], bbox=item.get("bbox"))
                normalized = {key: value for key, value in item.items() if key.startswith("normalized_")}
                normalized.update(is_out_of_stock=unavailable, warnings=item.get("warnings", []))
                session.add(ImportItem(
                    import_id=job.id, raw_data=raw, normalized_data=normalized,
                    confidence=item.get("confidence"), image_path=image_path,
                    status="IGNORED" if unavailable else "DETECTED",
                    review_notes="Esgotado explicitamente no catálogo." if unavailable else None,
                ))
            session.add(ImportPage(
                import_id=job.id, page_number=report["page_number"], status=report["status"],
                width=report.get("width"), height=report.get("height"), raw_text=report.get("raw_text"),
                text_blocks=report.get("text_blocks", []), image_paths=saved_paths,
                warnings=report.get("warnings", []), product_count=len(products), error_message=report.get("error_message"),
            ))
            job.processed_pages = (job.processed_pages or 0) + 1
            job.total_detected = (job.total_detected or 0) + len(products)
            job.last_progress_at = datetime.now(timezone.utc)
            await session.commit()
        except Exception:
            await session.rollback()
            for path in saved_paths:
                try:
                    storage.delete(path)
                except OSError:
                    logger.warning("Falha na limpeza de imagem de extração")
            raise
        for path in previous_paths:
            try:
                storage.delete(path)
            except OSError:
                logger.warning("Falha na limpeza de imagem substituída")

    async def retry_import(self, session: AsyncSession, job_id: UUID):
        job = await session.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
        if not job:
            raise HTTPException(404, "Importação não encontrada.")
        if job.status != "FAILED":
            raise HTTPException(409, "Somente importações com falha podem ser retomadas.")
        pages = list((await session.scalars(select(ImportPage).where(ImportPage.import_id == job_id))).all())
        if not pages:
            # Legacy failures had no durable page evidence. Re-extract their source once.
            await session.execute(delete(ImportItem).where(ImportItem.import_id == job_id, ImportItem.status != "IMPORTED"))
        job.status = "UPLOADED"
        job.error_message = None
        job.completed_at = None
        job.total_detected = sum(page.product_count for page in pages if page.status != "FAILED")
        job.processed_pages = sum(page.status != "FAILED" for page in pages)
        job.total_errors = 0
        await session.flush()
        return job

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
        item.error_message = None
        if item.status == "APPROVED":
            self.product_svc.validate_import_item(item)
        await session.flush()
        await session.refresh(item)
        return item

    async def approve_all_items(self, session: AsyncSession, job_id: UUID):
        job = await session.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
        if not job or job.status != "REVIEW_REQUIRED":
            raise HTTPException(409, "Importação não está disponível para revisão.")
        items = await self.repo.get_items_by_job(session, job_id)
        count = 0
        skipped = 0
        for item in items:
            unavailable = bool(item.normalized_data and item.normalized_data.get("is_out_of_stock"))
            if item.status == "DETECTED" and not unavailable:
                try:
                    self.product_svc.validate_import_item(item)
                except HTTPException as exc:
                    item.error_message = str(exc.detail)
                    skipped += 1
                    continue
                item.status = "APPROVED"
                item.error_message = None
                count += 1
        await session.commit()
        return {"approved_count": count, "skipped_count": skipped}

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
            raise HTTPException(409, "Há itens pendentes. Revise, rejeite ou ignore esses itens antes de confirmar.")

        approved_items = [item for item in items if item.status == "APPROVED"]
        if not approved_items:
            raise HTTPException(409, "Nenhum item aprovado para cadastrar. Aprove os produtos que deseja importar antes de confirmar.")

        for item in approved_items:
            self.product_svc.validate_import_item(item)

        for item in approved_items:
            await self.product_svc.create_from_import(session, item, job.supplier_id)

        job.total_imported = sum(item.status == "IMPORTED" for item in items)
        job.total_errors = 0
        job.status = "IMPORTED"
        job.completed_at = datetime.now(timezone.utc)
        await session.flush()
        return await self.repo.get_job(session, job_id)
