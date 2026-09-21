import re
import uuid
from decimal import Decimal
from typing import Tuple
from pathlib import Path
import httpx
from fastapi import HTTPException
from sqlalchemy import select, text
from urllib.parse import urlsplit
import simplejson
from app.models.supplier import Supplier
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.marketplace import MarketplaceAccount
from app.models.product import Product, ProductSupplierData, SupplierProductPrice
from app.models.product_image import ProductImage
from app.repositories.product_repository import ProductRepository
from app.schemas.clone import ClonePreviewResponse, CloneProductRequest
from app.storage.service import StorageService


def parse_mlb_info(url_or_id: str) -> Tuple[str, bool]:
    """Extract and normalize MLB identifier from any Mercado Livre link or code.
    Returns (mlb_id, is_catalog).
    """
    cleaned = url_or_id.strip()
    is_catalog = "/P/MLB" in cleaned.upper()
    match = re.search(r"(MLB)[\s\-_]?([0-9]+)", cleaned, re.IGNORECASE)
    if not match:
        raise HTTPException(
            422,
            "Link ou identificador do Mercado Livre inválido. "
            "Forneça uma URL como https://produto.mercadolivre.com.br/MLB-... ou o código MLB."
        )
    return f"MLB{match.group(2)}", is_catalog


def parse_mlb_id(url_or_id: str) -> str:
    """Extract and normalize MLB identifier from any Mercado Livre link or code."""
    mlb_id, _ = parse_mlb_info(url_or_id)
    return mlb_id


class CloneService:
    def __init__(self):
        self.product_repo = ProductRepository()
        self.storage = StorageService(settings.STORAGE_PATH)

    async def _get_ml_token(self, session: AsyncSession | None = None) -> str | None:
        """Obtains an access token from either an active connected account or client credentials."""
        if session is not None:
            try:
                account = await session.scalar(
                    select(MarketplaceAccount)
                    .where(MarketplaceAccount.marketplace == "MERCADO_LIVRE", MarketplaceAccount.is_active == True)
                    .order_by(MarketplaceAccount.updated_at.desc())
                    .limit(1)
                )
                if account:
                    from app.services.mercadolivre_service import MercadoLivreService
                    meli_service = MercadoLivreService()
                    try:
                        token, _ = await meli_service.get_valid_access_token(session, account.id)
                    finally:
                        await meli_service.client.close()
                    if token:
                        return token
            except HTTPException:
                raise
            except Exception:
                pass

        if session is not None:
            try:
                from app.models.marketplace import MarketplacePlatformCredential
                from app.core.tokens import decrypt_token
                cred = await session.scalar(
                    select(MarketplacePlatformCredential)
                    .where(MarketplacePlatformCredential.marketplace == "MERCADO_LIVRE", MarketplacePlatformCredential.is_active == True)
                    .limit(1)
                )
                app_id = cred.app_id if cred and cred.app_id else settings.MERCADOLIVRE_APP_ID
                app_secret = decrypt_token(cred.app_secret_encrypted) if cred and cred.app_secret_encrypted else (
                    settings.MERCADOLIVRE_CLIENT_SECRET.get_secret_value() if hasattr(settings.MERCADOLIVRE_CLIENT_SECRET, "get_secret_value") else settings.MERCADOLIVRE_CLIENT_SECRET
                )
                if app_id and app_secret:
                    async with httpx.AsyncClient(timeout=15) as client:
                        token_res = await client.post(
                            "https://api.mercadolibre.com/oauth/token",
                            data={
                                "grant_type": "client_credentials",
                                "client_id": app_id,
                                "client_secret": app_secret,
                            },
                        )
                        if token_res.status_code == 200:
                            token_json = token_res.json()
                            return token_json.get("access_token")
            except Exception:
                pass

        return None

    async def _fetch_ml_data(
        self, mlb_id: str, is_catalog: bool = False, session: AsyncSession | None = None
    ) -> Tuple[dict, str]:
        """Fetch item or catalog product and description from Mercado Livre API."""
        token = await self._get_ml_token(session)

        headers = {"User-Agent": "AdapterFlow/1.0", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Determine URLs to query based on whether it is a catalog product (/p/MLB...) or regular item
        if is_catalog:
            urls = [
                f"https://api.mercadolibre.com/products/{mlb_id}",
                f"https://api.mercadolibre.com/items/{mlb_id}",
            ]
        else:
            urls = [
                f"https://api.mercadolibre.com/items/{mlb_id}",
                f"https://api.mercadolibre.com/products/{mlb_id}",
            ]

        item = None
        last_status = None

        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            for url in urls:
                try:
                    res = await client.get(url, headers=headers)
                    last_status = res.status_code
                    if res.status_code == 200:
                        item = simplejson.loads(res.content, use_decimal=True)
                        break
                    elif res.status_code in (401, 403):
                        # PolicyAgent or unauthorized
                        last_status = res.status_code
                        break
                except httpx.HTTPError:
                    raise HTTPException(502, "Falha de rede ao consultar Mercado Livre.") from None

            if item is None:
                if last_status in (401, 403):
                    if not token:
                        raise HTTPException(
                            400,
                            "Para clonar anúncios do Mercado Livre, conecte sua conta do Mercado Livre "
                            "no menu 'Marketplaces'. O Mercado Livre exige autenticação para leitura de anúncios."
                        )
                    else:
                        raise HTTPException(
                            400,
                            "Mercado Livre recusou a consulta (HTTP 403/401). A autorização da sua conta pode "
                            "ter expirado. Acesse o menu 'Marketplaces' para reconectar sua conta e tente novamente."
                        )
                if last_status == 404:
                    raise HTTPException(
                        404,
                        f"Anúncio ou produto '{mlb_id}' não encontrado no Mercado Livre. Verifique se o link ou código está correto."
                    )
                raise HTTPException(502, f"Mercado Livre retornou status HTTP {last_status or 500}.")

            # Fetch plain text description
            description_text = ""
            if isinstance(item.get("short_description"), dict) and item["short_description"].get("content"):
                description_text = item["short_description"]["content"].strip()
            elif item.get("description") and isinstance(item["description"], str):
                description_text = item["description"].strip()

            target_desc_id = (item.get("buy_box_winner") or {}).get("item_id") or item.get("id") or mlb_id
            if not description_text and str(target_desc_id).startswith("MLB"):
                try:
                    desc_res = await client.get(
                        f"https://api.mercadolibre.com/items/{target_desc_id}/description",
                        headers=headers,
                    )
                    if desc_res.status_code == 200:
                        desc_json = desc_res.json()
                        description_text = (desc_json.get("plain_text") or desc_json.get("text") or "").strip()
                except Exception:
                    pass

            return item, description_text

    def _extract_attributes(self, item: dict, description: str, mlb_id: str) -> dict:
        """Extract structured product fields from Mercado Livre item or catalog payload."""
        attrs = {a.get("id"): a.get("value_name") for a in item.get("attributes", []) if a.get("id")}

        brand = attrs.get("BRAND") or attrs.get("MARCA") or item.get("brand")
        model = attrs.get("MODEL") or attrs.get("MODELO") or item.get("model")
        ean = attrs.get("GTIN") or attrs.get("EAN")
        gtin = attrs.get("GTIN") or ean
        color = attrs.get("COLOR") or attrs.get("COR")

        # Dimensions / weight
        dimensions_parts = []
        for key, label in [("PACKAGE_LENGTH", "C"), ("PACKAGE_WIDTH", "L"), ("PACKAGE_HEIGHT", "A")]:
            if attrs.get(key):
                dimensions_parts.append(f"{label}: {attrs[key]}")
        dimensions = " x ".join(dimensions_parts) if dimensions_parts else attrs.get("DIMENSIONS")

        weight = None
        raw_weight = attrs.get("PACKAGE_WEIGHT") or attrs.get("WEIGHT")
        if raw_weight:
            match = re.search(r"([0-9]+(?:[\.,][0-9]+)?)", raw_weight)
            if match:
                try:
                    weight = Decimal(match.group(1).replace(",", "."))
                    if "g" in raw_weight.lower() and "k" not in raw_weight.lower():
                        weight = weight / Decimal("1000")  # convert grams to kg
                except Exception:
                    weight = None

        # Pictures (highest resolution available)
        pictures = []
        for pic in item.get("pictures", []):
            url = pic.get("secure_url") or pic.get("url")
            if url and url not in pictures:
                pictures.append(url)

        if not pictures and item.get("thumbnail"):
            pictures.append(item["thumbnail"])

        # Price extraction (supports both /items and /products catalog formats)
        price = None
        if item.get("price") is not None:
            try:
                price = Decimal(str(item["price"]))
            except Exception:
                pass
        elif item.get("buy_box_winner") and item["buy_box_winner"].get("price") is not None:
            try:
                price = Decimal(str(item["buy_box_winner"]["price"]))
            except Exception:
                pass

        original_price = None
        if item.get("original_price") is not None:
            try:
                original_price = Decimal(str(item["original_price"]))
            except Exception:
                pass
        elif item.get("buy_box_winner") and item["buy_box_winner"].get("original_price") is not None:
            try:
                original_price = Decimal(str(item["buy_box_winner"]["original_price"]))
            except Exception:
                pass

        name = (item.get("title") or item.get("name") or "").strip()[:500]

        return {
            "mlb_id": mlb_id,
            "name": name,
            "price": price,
            "original_price": original_price,
            "brand": brand[:255] if brand else None,
            "model": model[:255] if model else None,
            "ean": ean[:20] if ean else None,
            "gtin": gtin[:20] if gtin else None,
            "color": color[:100] if color else None,
            "dimensions": dimensions[:255] if dimensions else None,
            "weight": weight,
            "category_id": item.get("category_id"),
            "pictures": pictures,
            "description": description or None,
            "permalink": item.get("permalink"),
        }

    async def preview(self, url_or_id: str, session: AsyncSession | None = None) -> ClonePreviewResponse:
        """Parse link and return preview of Mercado Livre listing."""
        mlb_id, is_catalog = parse_mlb_info(url_or_id)
        item, description = await self._fetch_ml_data(mlb_id, is_catalog=is_catalog, session=session)
        extracted = self._extract_attributes(item, description, mlb_id)
        return ClonePreviewResponse(**extracted)

    async def clone_product(self, session: AsyncSession, request: CloneProductRequest) -> Product:
        """Download pictures and persist new Product from Mercado Livre listing."""
        mlb_id, is_catalog = parse_mlb_info(request.url_or_id)
        if request.supplier_id and not (request.supplier_code or "").strip():
            raise HTTPException(422, "Informe o código real do fornecedor para vincular este produto.")
        if request.supplier_id:
            supplier = await session.get(Supplier, request.supplier_id)
            if not supplier or not supplier.is_active:
                raise HTTPException(422, "Selecione um fornecedor ativo.")
        if request.cost_price is not None and not request.supplier_id:
            raise HTTPException(422, "Selecione o fornecedor responsável pelo custo informado.")
        item, description = await self._fetch_ml_data(mlb_id, is_catalog=is_catalog, session=session)
        extracted = self._extract_attributes(item, description, mlb_id)
        external_id = str(item.get("id") or mlb_id)
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"clone:MERCADO_LIVRE:{external_id}"})
        existing = await session.scalar(select(Product.id).where(Product.source_marketplace == "MERCADO_LIVRE", Product.source_external_id == external_id))
        if existing:
            return await self.product_repo.get_with_details(session, existing)
        if not extracted["name"]:
            raise HTTPException(422, "A origem não informou o nome do produto; não é possível cadastrar um nome presumido.")

        # 1. Create Product
        product_id = uuid.uuid4()

        product = Product(
            id=product_id,
            name=extracted["name"],
            sku=None,
            source_marketplace="MERCADO_LIVRE",
            source_external_id=external_id,
            brand=extracted["brand"],
            model=extracted["model"],
            ean=extracted["ean"],
            gtin=extracted["gtin"],
            color=extracted["color"],
            dimensions=extracted["dimensions"],
            weight=extracted["weight"],
            description=extracted["description"],
            status=request.status,
        )
        session.add(product)
        await session.flush()

        # 3. Optional supplier and cost linking
        if request.supplier_id:
            supplier_code = request.supplier_code.strip()
            supplier_data = ProductSupplierData(
                product_id=product.id,
                supplier_id=request.supplier_id,
                supplier_code=supplier_code,
                supplier_name=extracted["name"],
                pcs_per_box=None,
                current_cost=request.cost_price,
                raw_cost_value=str(request.cost_price) if request.cost_price is not None else None,
                is_active=True,
            )
            session.add(supplier_data)
            await session.flush()

            if request.cost_price is not None:
                price = SupplierProductPrice(
                    product_supplier_data_id=supplier_data.id,
                    price=request.cost_price,
                    raw_value=str(request.cost_price),
                )
                session.add(price)


        # 2. Download and persist pictures to local StorageService
        pictures = extracted.get("pictures", [])[:8]
        saved_paths = []
        async with httpx.AsyncClient(timeout=30) as client:
            for idx, pic_url in enumerate(pictures):
                try:
                    parts = urlsplit(pic_url)
                    if parts.scheme != "https" or not parts.hostname or not (parts.hostname == "mlstatic.com" or parts.hostname.endswith(".mlstatic.com")):
                        raise ValueError("Origem de imagem não permitida.")
                    async with client.stream("GET", pic_url) as stream:
                        stream.raise_for_status()
                        content = bytearray()
                        async for chunk in stream.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > 10 * 1024 * 1024:
                                raise ValueError("Imagem excede 10 MiB.")
                        res = httpx.Response(200, content=bytes(content), headers=stream.headers)
                    if not res.content:
                        raise ValueError("Imagem vazia.")
                    if res.content:
                        filename = f"img_{idx+1}_{Path(pic_url).name.split('?')[0]}"
                        if not filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
                            filename += ".jpg"
                        rel_path = f"products/{product.id}/{filename}"
                        self.storage.put(rel_path, res.content)
                        saved_paths.append(rel_path)

                        img_record = ProductImage(
                            product_id=product.id,
                            storage_path=rel_path,
                            original_filename=filename,
                            mime_type=res.headers.get("content-type", "image/jpeg"),
                            size_bytes=len(res.content),
                            position=idx,
                            source="ML_CLONE",
                        )
                        session.add(img_record)
                except Exception:
                    await session.rollback()
                    for path in saved_paths:
                        self.storage.delete(path)
                    raise HTTPException(422, "Falha ao baixar ou salvar uma foto. Nenhum produto foi cadastrado; tente novamente.") from None

        try:
            await session.commit()
        except Exception:
            await session.rollback()
            for path in saved_paths:
                self.storage.delete(path)
            raise
        return await self.product_repo.get_with_details(session, product.id)
