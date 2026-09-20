from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.product_repository import ProductRepository
from app.models.product import ProductSupplierData, SupplierProductPrice
from app.models.product_image import ProductImage
from app.models.import_job import ImportItem
from uuid import UUID
from typing import Optional
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import update
from app.models.pricing import ProductChannelPrice

class ProductService:
    def __init__(self):
        self.repo = ProductRepository()
        
    async def create_from_import(self, session: AsyncSession, import_item: ImportItem, supplier_id: UUID):
        data = {**(import_item.normalized_data or {}), **(import_item.user_edits or {})}
        raw = import_item.raw_data or {}
        price_val = Decimal(str(data["normalized_price"])) if data.get("normalized_price") is not None else None
        if price_val is not None and (not price_val.is_finite() or price_val < 0):
            raise HTTPException(422, "Custo inválido.")
        sku_code = data.get("normalized_code")
        is_out_of_stock = bool(data.get("is_out_of_stock", False))
        product_status = "INACTIVE" if is_out_of_stock else "ACTIVE"
        
        name = data.get("normalized_name") or raw.get("raw_name")
        if not sku_code:
            sku_code = raw.get("raw_code") or f"ITEM-{import_item.id.hex[:8].upper()}"
        if not name:
            name = f"Produto {sku_code}"
        supplier_data = await self.repo.find_by_supplier_code(session, supplier_id, sku_code)
        product = await self.repo.get_by_id(session, supplier_data.product_id) if supplier_data else None
        if product is None:
            product_data = {
                "name": name,
                "sku": None,
                "status": product_status,
                "color": data.get("normalized_color"),
                "dimensions": data.get("normalized_dimensions"),
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
        
        supplier_code = sku_code
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
            if supplier_data.current_cost != price_val:
                await session.execute(update(ProductChannelPrice).where(ProductChannelPrice.product_id == product.id).values(is_stale=True))
            supplier_data.current_cost = price_val
            supplier_data.supplier_name = data.get("normalized_name") or supplier_data.supplier_name
            supplier_data.pcs_per_box = data.get("normalized_pcs_per_box")
            supplier_data.raw_cost_value = raw.get("raw_price")
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

    async def update_supplier_link(self, session, product_id, supplier_data_id, data):
        link = await self.repo.update_supplier_link(session, product_id, supplier_data_id, data.is_active, data.activation_reason)
        if not link:
            raise HTTPException(404, "Vínculo de fornecedor não encontrado para este produto.")
        return await self.repo.get_with_details(session, product_id)
