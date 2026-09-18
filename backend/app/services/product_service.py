from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.product_repository import ProductRepository
from app.models.product import ProductSupplierData, SupplierProductPrice
from app.models.product_image import ProductImage
from app.models.import_job import ImportItem
from uuid import UUID
from typing import Optional

class ProductService:
    def __init__(self):
        self.repo = ProductRepository()
        
    async def create_from_import(self, session: AsyncSession, import_item: ImportItem, supplier_id: UUID):
        data = import_item.user_edits or import_item.normalized_data or {}
        
        product_data = {
            "name": data.get("normalized_name") or "Unnamed Product",
            "status": "ACTIVE",
            "color": data.get("normalized_color")
        }
        
        product = await self.repo.create(session, product_data)
        
        supplier_data = ProductSupplierData(
            product_id=product.id,
            supplier_id=supplier_id,
            supplier_code=data.get("normalized_code") or "UNKNOWN",
            pcs_per_box=data.get("normalized_pcs_per_box")
        )
        session.add(supplier_data)
        await session.flush()
        
        price_val = data.get("normalized_price")
        if price_val is not None:
            price = SupplierProductPrice(
                product_supplier_data_id=supplier_data.id,
                price=price_val,
                import_id=import_item.import_id
            )
            session.add(price)
            
        if import_item.image_path:
            image = ProductImage(
                product_id=product.id,
                storage_path=import_item.image_path,
                source="IMPORT"
            )
            session.add(image)
            
        await session.flush()
        
        import_item.product_id = product.id
        import_item.status = "IMPORTED"
        
        return product
        
    async def get_product_with_details(self, session: AsyncSession, id: UUID):
        return await self.repo.get_with_details(session, id)
        
    async def list_products(self, session: AsyncSession, skip: int = 0, limit: int = 100, search: Optional[str] = None, status: Optional[str] = None):
        items = await self.repo.list_all(session, skip, limit, search, status)
        total = await self.repo.count(session, search, status)
        return {"items": items, "total": total}
