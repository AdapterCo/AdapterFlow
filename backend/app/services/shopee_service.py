from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
from pathlib import Path
import hashlib
import secrets
import logging
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.tokens import cipher, encrypt_token, decrypt_token
from app.models.marketplace import MarketplaceAccount, MarketplaceListing, OAuthAttempt
from app.integrations.shopee.client import ShopeeClient
from app.repositories.marketplace_repository import MarketplaceRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.pricing_repository import PricingRepository
from app.storage.service import StorageService
from app.schemas.marketplace import (
    MarketplaceAccountResponse, MarketplaceListingResponse,
)

logger = logging.getLogger(__name__)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def safe_json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items() if k not in {"access_token", "refresh_token"}}
    if isinstance(value, list):
        return [safe_json(v) for v in value]
    return value


class ShopeeService:
    def __init__(self):
        self.client = ShopeeClient()
        self.repo = MarketplaceRepository()
        self.product_repo = ProductRepository()
        self.pricing_repo = PricingRepository()

    async def start_oauth(self, session: AsyncSession, owner: str):
        cipher()
        state = secrets.token_urlsafe(32)
        browser = secrets.token_urlsafe(32)
        session.add(
            OAuthAttempt(
                state_hash=digest(state),
                browser_hash=digest(browser),
                owner=owner,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        await session.flush()
        return self.client.get_authorization_url(state), browser

    async def handle_oauth_callback(
        self, session: AsyncSession, code: str, shop_id: int, state: str, browser: str | None, owner: str
    ):
        attempt = await session.scalar(
            select(OAuthAttempt).where(OAuthAttempt.state_hash == digest(state)).with_for_update()
        )
        if (
            not attempt
            or attempt.consumed_at
            or attempt.expires_at <= datetime.now(timezone.utc)
            or attempt.owner != owner
            or not browser
            or not secrets.compare_digest(attempt.browser_hash, digest(browser))
        ):
            raise HTTPException(400, "Autorização expirada ou inválida. Inicie novamente.")

        attempt.consumed_at = datetime.now(timezone.utc)
        await session.commit()

        token_data = await self.client.exchange_token(code, shop_id)
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expire_in = token_data.get("expire_in", 14400)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expire_in)

        # Query shop profile to display human-readable account name
        shop_info = await self.client.get_shop_info(access_token, shop_id)
        shop_name = shop_info.get("shop_name") or f"Loja Shopee {shop_id}"
        region = shop_info.get("region") or "BR"

        account = await self.repo.upsert_account(
            session,
            "SHOPEE",
            str(shop_id),
            shop_name,
            encrypt_token(access_token),
            encrypt_token(refresh_token),
            expires_at,
            site_id=region,
            settings_dict={"region": region, "shop_id": shop_id},
        )
        account.verified_at = datetime.now(timezone.utc)
        account.connection_error = None
        await session.flush()
        return MarketplaceAccountResponse.model_validate(account)

    async def get_valid_access_token(self, session: AsyncSession, account_id: UUID):
        account = await session.scalar(
            select(MarketplaceAccount)
            .where(MarketplaceAccount.id == account_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not account or not account.is_active or account.marketplace != "SHOPEE":
            raise HTTPException(404, "Conta ativa da Shopee não encontrada.")

        shop_id = int(account.seller_id)

        # Refresh if close to expiration (within 5 minutes)
        if account.token_expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
            try:
                data = await self.client.refresh_token(decrypt_token(account.refresh_token), shop_id)
                access_token = data["access_token"]
                refresh_token = data["refresh_token"]
                expire_in = data.get("expire_in", 14400)
                account.access_token = encrypt_token(access_token)
                account.refresh_token = encrypt_token(refresh_token)
                account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expire_in)
                account.verified_at = datetime.now(timezone.utc)
                account.connection_error = None
            except HTTPException as exc:
                if exc.status_code in (401, 422):
                    account.verified_at = None
                    account.connection_error = "Reautenticação necessária na Shopee."
                    await session.commit()
                raise

        token = decrypt_token(account.access_token)
        account_name = account.account_name
        await session.commit()
        return token, shop_id, account_name

    async def list_categories(self, session: AsyncSession, account_id: UUID):
        token, shop_id, _ = await self.get_valid_access_token(session, account_id)
        return await self.client.get_categories(token, shop_id)

    async def get_category_attributes(self, session: AsyncSession, account_id: UUID, category_id: int):
        token, shop_id, _ = await self.get_valid_access_token(session, account_id)
        return await self.client.get_category_attributes(token, shop_id, category_id)

    async def publish_product(self, session: AsyncSession, request):
        product = await self.product_repo.get_with_details(session, request.product_id)
        if not product or product.status != "ACTIVE":
            raise HTTPException(409, "Produto não encontrado ou inativo.")

        price = await self.pricing_repo.get_product_price(session, product.id, request.pricing_profile_id)
        if not price or price.is_stale or not price.profile.is_active or price.profile.channel != "SHOPEE":
            raise HTTPException(409, "Calcule um preço atualizado com perfil ativo da Shopee.")

        source = next((s for s in product.supplier_data if s.id == price.supplier_data_id), None)
        if not source or not source.is_active or not source.supplier.is_active or source.current_cost != price.cost_basis:
            raise HTTPException(409, "Custo de origem alterado ou indisponível; recalcule o preço.")

        if not product.images:
            raise HTTPException(422, "Cadastre fotos reais do produto antes de publicar na Shopee.")

        token, shop_id, account_name = await self.get_valid_access_token(session, request.account_id)

        key = f"shopee:{request.account_id}:{product.id}"
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})

        same_request = await session.scalar(
            select(MarketplaceListing).where(MarketplaceListing.request_id == request.request_id)
        )
        if same_request:
            if same_request.product_id != product.id or same_request.account_id != request.account_id:
                raise HTTPException(409, "Identificador de operação já utilizado.")
            if same_request.external_listing_id:
                return MarketplaceListingResponse.model_validate(same_request).model_copy(
                    update={"product_name": product.name, "account_name": account_name}
                )
            raise HTTPException(409, "Operação já registrada. Consulte Publicações antes de tentar novamente.")

        existing = await session.scalar(
            select(MarketplaceListing.id).where(
                MarketplaceListing.product_id == product.id,
                MarketplaceListing.account_id == request.account_id,
                MarketplaceListing.status.not_in(["ERROR", "CLOSED"]),
            ).limit(1)
        )
        if existing:
            raise HTTPException(409, "Existe anúncio ou publicação ativa para este produto nesta loja Shopee.")

        listing = MarketplaceListing(
            product_id=product.id,
            account_id=request.account_id,
            request_id=request.request_id,
            marketplace="SHOPEE",
            title=request.title.strip(),
            price=price.calculated_price,
            available_quantity=request.available_quantity,
            category_id=str(request.category_id),
            listing_type_id="default",
            status="IN_PROGRESS",
        )
        session.add(listing)
        await session.commit()

        try:
            storage = StorageService(settings.STORAGE_PATH)
            image_id_list = []
            for picture in product.images[:9]:  # Shopee permits up to 9 images
                image_bytes = storage.get(picture.storage_path)
                filename = Path(picture.storage_path).name
                image_id = await self.client.upload_image(token, shop_id, image_bytes, filename)
                image_id_list.append(image_id)

            # Build Shopee Add Item payload
            weight = float(product.weight) if product.weight and product.weight > 0 else 0.3
            payload = {
                "original_price": float(price.calculated_price),
                "description": product.description or product.name,
                "item_name": request.title.strip(),
                "normal_stock": request.available_quantity,
                "category_id": int(request.category_id),
                "weight": weight,
                "item_status": "NORMAL",
                "image": {"image_id_list": image_id_list},
                "brand": {"brand_id": 0, "original_brand_name": product.brand or "NoBrand"},
                "logistic_info": [
                    {
                        "logistic_id": 0,
                        "enabled": True,
                    }
                ],
            }

            response = await self.client.add_item(token, shop_id, payload)
            item_id = response.get("item_id")
            if not item_id:
                raise ValueError("Identificador do item não retornado pela Shopee.")

            listing.external_listing_id = str(item_id)
            listing.status = "ACTIVE"
            listing.raw_response = safe_json(response)
            listing.last_synced_at = datetime.now(timezone.utc)
            await session.commit()

        except Exception as exc:
            await session.rollback()
            listing = await session.scalar(
                select(MarketplaceListing).where(MarketplaceListing.request_id == request.request_id)
            )
            if listing:
                listing.status = "ERROR"
                listing.error_message = (
                    str(exc.detail) if isinstance(exc, HTTPException) else f"Falha na publicação: {str(exc)}"
                )
                await session.commit()
            raise HTTPException(422, listing.error_message if listing else str(exc))

        return MarketplaceListingResponse.model_validate(listing).model_copy(
            update={"product_name": product.name, "account_name": account_name}
        )
