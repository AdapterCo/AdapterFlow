from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.import_repository import ImportRepository
from app.services.product_service import ProductService
from app.storage.service import StorageService
from app.importers.pdf.lehmox import LehmoxCatalogImporter
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class ImportService:
    def __init__(self):
        self.repo = ImportRepository()
        self.product_svc = ProductService()
        
    async def create_import(self, session: AsyncSession, supplier_id: UUID, file_name: str, file_content: bytes, storage: StorageService):
        path = f"imports/{supplier_id}/{file_name}"
        storage.put(path, file_content)
        
        data = {
            "supplier_id": supplier_id,
            "file_name": file_name,
            "file_path": path,
            "file_size": len(file_content),
            "importer_type": "lehmox",
            "status": "UPLOADED"
        }
        return await self.repo.create_job(session, data)
        
    async def process_import(self, session: AsyncSession, job_id: UUID, storage: StorageService):
        """Synchronous process_import for tests or direct script invocation."""
        await self.process_import_background(job_id, storage)
        return await self.repo.get_job(session, job_id)

    async def process_import_background(self, job_id: UUID, storage: StorageService):
        """Background asynchronous process import with dedicated session, thread-pool extraction and batching."""
        import asyncio
        import re
        import math
        import logging
        from app.core.database import async_session_maker

        logger = logging.getLogger(__name__)

        async with async_session_maker() as session:
            try:
                job = await self.repo.get_job(session, job_id)
                if not job:
                    logger.error(f"Job {job_id} not found for background processing")
                    return

                await self.repo.update_job(session, job_id, {"status": "PROCESSING", "started_at": datetime.utcnow()})
                
                importer = LehmoxCatalogImporter()
                full_path = storage._get_full_path(job.file_path)

                # Run CPU-bound extraction in a thread pool so the asyncio event loop remains responsive
                extracted_items = await asyncio.to_thread(importer.extract, str(full_path), storage)

                items_data = []
                for idx, item in enumerate(extracted_items):
                    image_path = None
                    if item.image_data:
                        safe_code = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', item.normalized_code or 'img')[:50]
                        timestamp = int(datetime.utcnow().timestamp() * 1000)
                        ext = item.image_extension or 'jpg'
                        image_filename = f"products/{job.supplier_id}/{safe_code}_{timestamp}_{idx}.{ext}"
                        try:
                            storage.put(image_filename, item.image_data)
                            image_path = image_filename
                        except Exception as img_err:
                            logger.warning(f"Could not save product image {image_filename}: {img_err}")
                            image_path = None

                    is_out_of_stock = getattr(item, "is_out_of_stock", False)
                    item_status = "IGNORED" if is_out_of_stock else "DETECTED"
                    review_notes = "Produto esgotado no catálogo do fornecedor." if is_out_of_stock else None

                    # Sanitize price for JSON compliance (avoid NaN or Inf)
                    norm_price = None
                    if item.normalized_price is not None:
                        try:
                            p_float = float(item.normalized_price)
                            if not math.isnan(p_float) and not math.isinf(p_float):
                                norm_price = p_float
                        except (ValueError, TypeError):
                            norm_price = None

                    items_data.append({
                        "import_id": job.id,
                        "raw_data": {
                            "raw_code": item.raw_code[:200] if item.raw_code else None,
                            "raw_name": item.raw_name[:500] if item.raw_name else None,
                            "raw_price": item.raw_price[:100] if item.raw_price else None,
                            "raw_dimensions": item.raw_dimensions[:100] if item.raw_dimensions else None,
                            "raw_pcs_per_box": item.raw_pcs_per_box[:50] if item.raw_pcs_per_box else None,
                            "raw_color": item.raw_color[:100] if item.raw_color else None
                        },
                        "normalized_data": {
                            "normalized_code": item.normalized_code[:100] if item.normalized_code else None,
                            "normalized_name": item.normalized_name[:500] if item.normalized_name else None,
                            "normalized_price": norm_price,
                            "normalized_dimensions": item.normalized_dimensions[:100] if item.normalized_dimensions else None,
                            "normalized_pcs_per_box": item.normalized_pcs_per_box,
                            "normalized_color": item.normalized_color[:100] if item.normalized_color else None,
                            "is_out_of_stock": is_out_of_stock,
                            "warnings": item.warnings or [],
                        },
                        "confidence": float(item.confidence) if item.confidence is not None else 1.0,
                        "image_path": image_path,
                        "status": item_status,
                        "review_notes": review_notes,
                    })

                # Bulk insert in chunks of 50 to prevent parameter limit / lock issues
                CHUNK_SIZE = 50
                for i in range(0, len(items_data), CHUNK_SIZE):
                    chunk = items_data[i:i + CHUNK_SIZE]
                    instances = [ImportItem(**d) for d in chunk]
                    session.add_all(instances)
                    await session.flush()

                await session.commit()

                await self.repo.update_job(session, job_id, {
                    "status": "REVIEW_REQUIRED",
                    "total_detected": len(items_data),
                    "completed_at": datetime.utcnow()
                })
                logger.info(f"Successfully finished background import {job_id}: {len(items_data)} items detected")

            except Exception as e:
                logger.exception(f"Exception during background import {job_id}: {e}")
                await session.rollback()
                try:
                    await self.repo.update_job(session, job_id, {
                        "status": "FAILED",
                        "error_message": f"Erro na extração: {str(e)[:400]}",
                        "completed_at": datetime.utcnow()
                    })
                except Exception as update_err:
                    logger.exception(f"Failed to record FAILED status for job {job_id}: {update_err}")
        
    async def confirm_import(self, session: AsyncSession, job_id: UUID, approved_ids: Optional[List[UUID]] = None, rejected_ids: Optional[List[UUID]] = None, storage: StorageService = None):
        job = await self.repo.get_job(session, job_id)
        if not job:
            return None
            
        all_items = await self.repo.get_items_by_job(session, job_id)
        
        # If no explicit list is provided, approve all with status APPROVED or DETECTED
        if approved_ids is None:
            explicit_approved = [i.id for i in all_items if i.status == "APPROVED"]
            if explicit_approved:
                target_approved_ids = explicit_approved
            else:
                target_approved_ids = [i.id for i in all_items if i.status not in ["REJECTED", "IGNORED", "ERROR", "IMPORTED"]]
        else:
            target_approved_ids = approved_ids

        target_rejected_ids = rejected_ids or []
        imported_count = 0
        
        for item_id in target_approved_ids:
            item = await self.repo.get_item(session, item_id)
            if item and item.status != "IMPORTED":
                await self.product_svc.create_from_import(session, item, job.supplier_id)
                await self.repo.update_item(session, item_id, {"status": "IMPORTED"})
                imported_count += 1
                
        for item_id in target_rejected_ids:
            await self.repo.update_item(session, item_id, {"status": "REJECTED"})
            
        total = (job.total_imported or 0) + imported_count
        await self.repo.update_job(session, job_id, {
            "status": "IMPORTED",
            "total_imported": total
        })
        await session.commit()
        return await self.repo.get_job(session, job_id)
