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
        job = await self.repo.get_job(session, job_id)
        if not job:
            return None
            
        await self.repo.update_job(session, job_id, {"status": "PROCESSING", "started_at": datetime.utcnow()})
        
        try:
            importer = LehmoxCatalogImporter()
            # The file_path is relative to storage base path, let's assume we can get absolute path or pass storage
            # Since our storage uses local files, we can get the full path
            full_path = storage._get_full_path(job.file_path)
            extracted_items = importer.extract(full_path, storage)
            
            items_data = []
            for item in extracted_items:
                image_path = None
                if item.image_data:
                    image_filename = f"products/{job.supplier_id}/{item.normalized_code or 'img'}_{datetime.utcnow().timestamp()}.{item.image_extension or 'jpg'}"
                    storage.put(image_filename, item.image_data)
                    image_path = image_filename
                
                is_out_of_stock = getattr(item, "is_out_of_stock", False)
                item_status = "IGNORED" if is_out_of_stock else "DETECTED"
                review_notes = "Produto esgotado no catálogo do fornecedor." if is_out_of_stock else None

                items_data.append({
                    "import_id": job.id,
                    "raw_data": {
                        "raw_code": item.raw_code,
                        "raw_name": item.raw_name,
                        "raw_price": item.raw_price,
                        "raw_dimensions": item.raw_dimensions,
                        "raw_pcs_per_box": item.raw_pcs_per_box,
                        "raw_color": item.raw_color
                    },
                    "normalized_data": {
                        "normalized_code": item.normalized_code,
                        "normalized_name": item.normalized_name,
                        "normalized_price": float(item.normalized_price) if item.normalized_price else None,
                        "normalized_dimensions": item.normalized_dimensions,
                        "normalized_pcs_per_box": item.normalized_pcs_per_box,
                        "normalized_color": item.normalized_color,
                        "is_out_of_stock": is_out_of_stock,
                        "warnings": item.warnings or [],
                    },
                    "confidence": item.confidence,
                    "image_path": image_path,
                    "status": item_status,
                    "review_notes": review_notes,
                })
                
            await self.repo.create_items_bulk(session, items_data)
            
            await self.repo.update_job(session, job_id, {
                "status": "REVIEW_REQUIRED",
                "total_detected": len(items_data),
                "completed_at": datetime.utcnow()
            })
            
        except Exception as e:
            await self.repo.update_job(session, job_id, {
                "status": "FAILED",
                "error_message": str(e),
                "completed_at": datetime.utcnow()
            })
            
        return await self.repo.get_job(session, job_id)
        
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
