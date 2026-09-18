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
        raw = import_item.raw_data or {}
        price_val = data.get("normalized_price")
        sku_code = data.get("normalized_code")
        is_out_of_stock = bool(data.get("is_out_of_stock", False))
        product_status = "INACTIVE" if is_out_of_stock else "ACTIVE"
        
        product = None
        if sku_code:
            product = await self.repo.get_by_sku(session, sku_code)
            
        if product is None:
            product_data = {
                "name": data.get("normalized_name") or "Unnamed Product",
                "sku": sku_code,
                "status": product_status,
                "color": data.get("normalized_color"),
            }
            product = await self.repo.create(session, product_data)
        else:
            update_fields = {
                "name": data.get("normalized_name") or product.name,
                "color": data.get("normalized_color") or product.color,
            }
            if is_out_of_stock:
                update_fields["status"] = "INACTIVE"
            await self.repo.update(session, product.id, update_fields)
        
        supplier_code = sku_code or "UNKNOWN"
        supplier_data = await self.repo.find_by_supplier_code(session, supplier_id, supplier_code)
        if supplier_data is None:
            supplier_data = ProductSupplierData(
                product_id=product.id,
                supplier_id=supplier_id,
                supplier_code=supplier_code,
                supplier_name=data.get("normalized_name"),
                pcs_per_box=data.get("normalized_pcs_per_box"),
                current_cost=price_val,
                raw_cost_value=raw.get("raw_price"),
                is_active=not is_out_of_stock,
            )
            session.add(supplier_data)
            await session.flush()
        else:
            supplier_data.current_cost = price_val
            supplier_data.supplier_name = data.get("normalized_name") or supplier_data.supplier_name
            supplier_data.pcs_per_box = data.get("normalized_pcs_per_box") or supplier_data.pcs_per_box
            if is_out_of_stock:
                supplier_data.is_active = False
            await session.flush()
        
        if price_val is not None:
            price = SupplierProductPrice(
                product_supplier_data_id=supplier_data.id,
                price=price_val,
                raw_value=raw.get("raw_price"),
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
