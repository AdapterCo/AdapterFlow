from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
from pathlib import Path
import hashlib
import secrets
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.tokens import cipher, encrypt_token, decrypt_token
from app.models.marketplace import MarketplaceAccount, MarketplaceListing, OAuthAttempt
from app.integrations.mercadolivre.client import MercadoLivreClient
from app.repositories.marketplace_repository import MarketplaceRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.pricing_repository import PricingRepository
from app.storage.service import StorageService
from app.schemas.marketplace import (
    MarketplaceAccountResponse, MarketplaceChannelStatus, MarketplacesOverviewResponse,
    MarketplaceListingResponse, MarketplaceListingListResponse, CategoryPredictionItem,
    MarketplaceCredentialUpsert, MarketplaceCredentialResponse,
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def safe_json(value):
    # PostgreSQL JSONB keeps decimal values as strings, never a float round trip.
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items() if k not in {"access_token", "refresh_token"}}
    if isinstance(value, list):
        return [safe_json(v) for v in value]
    return value


class MercadoLivreService:
    def __init__(self):
        self.client = MercadoLivreClient()
        self.repo = MarketplaceRepository()
        self.product_repo = ProductRepository()
        self.pricing_repo = PricingRepository()

    async def get_client(self, session: AsyncSession | None = None) -> MercadoLivreClient:
        if session is None:
            return self.client
        cred = await self.repo.get_platform_credential(session, "MERCADO_LIVRE")
        if cred and getattr(cred, "is_active", False) and getattr(cred, "app_id", None):
            client_secret = decrypt_token(cred.app_secret_encrypted) if getattr(cred, "app_secret_encrypted", None) else None
            return MercadoLivreClient(
                app_id=str(cred.app_id),
                client_secret=client_secret,
                redirect_uri=cred.redirect_uri or settings.MERCADOLIVRE_REDIRECT_URI,
            )
        return self.client

    async def list_credentials_safe(self, session: AsyncSession) -> list[MarketplaceCredentialResponse]:
        supported = ["SHOPEE", "MERCADO_LIVRE"]
        items = []
        for mp in supported:
            items.append(await self.get_credential_safe(session, mp))
        return items

    async def get_credential_safe(self, session: AsyncSession, marketplace: str) -> MarketplaceCredentialResponse:
        mp_norm = marketplace.upper()
        cred = await self.repo.get_platform_credential(session, mp_norm)

        app_id = cred.app_id if cred and cred.app_id else (
            settings.SHOPEE_PARTNER_ID if mp_norm == "SHOPEE" else settings.MERCADOLIVRE_APP_ID
        )
        app_id_str = str(app_id) if app_id is not None else None

        has_secret = False
        secret_preview = None
        if cred and cred.app_secret_encrypted:
            has_secret = True
            try:
                dec = decrypt_token(cred.app_secret_encrypted)
                secret_preview = f"••••••••{dec[-4:]}" if len(dec) >= 6 else "••••••••"
            except Exception:
                secret_preview = "••••••••"
        elif mp_norm == "SHOPEE" and settings.SHOPEE_PARTNER_KEY:
            has_secret = True
            secret_preview = f"••••••••{settings.SHOPEE_PARTNER_KEY[-4:]}"
        elif mp_norm == "MERCADO_LIVRE" and settings.MERCADOLIVRE_CLIENT_SECRET:
            has_secret = True
            secret_preview = f"••••••••{settings.MERCADOLIVRE_CLIENT_SECRET[-4:]}"

        redirect_uri = cred.redirect_uri if cred and cred.redirect_uri else (
            settings.SHOPEE_REDIRECT_URI if mp_norm == "SHOPEE" else settings.MERCADOLIVRE_REDIRECT_URI
        )
        api_url = cred.api_url if cred and cred.api_url else (
            settings.SHOPEE_API_URL if mp_norm == "SHOPEE" else "https://api.mercadolibre.com"
        )
        is_active = cred.is_active if cred else True
        updated_at = cred.updated_at or cred.created_at if cred else None

        return MarketplaceCredentialResponse(
            marketplace=mp_norm,
            app_id=app_id_str,
            has_secret=has_secret,
            secret_preview=secret_preview,
            redirect_uri=redirect_uri,
            api_url=api_url,
            is_active=is_active,
            updated_at=updated_at,
        )

    async def save_credential(
        self, session: AsyncSession, marketplace: str, payload: MarketplaceCredentialUpsert
    ) -> MarketplaceCredentialResponse:
        cipher()
        mp_norm = marketplace.upper()
        if mp_norm not in ("SHOPEE", "MERCADO_LIVRE"):
            raise HTTPException(400, f"Marketplace '{marketplace}' não suportado.")

        encrypted_secret = None
        if payload.app_secret and payload.app_secret.strip():
            encrypted_secret = encrypt_token(payload.app_secret.strip())

        await self.repo.upsert_platform_credential(
            session=session,
            marketplace=mp_norm,
            app_id=payload.app_id.strip(),
            app_secret_encrypted=encrypted_secret,
            redirect_uri=payload.redirect_uri.strip() if payload.redirect_uri else None,
            api_url=payload.api_url.strip() if payload.api_url else None,
        )
        await session.commit()
        return await self.get_credential_safe(session, mp_norm)

    async def delete_credential(self, session: AsyncSession, marketplace: str) -> None:
        mp_norm = marketplace.upper()
        cred = await self.repo.get_platform_credential(session, mp_norm)
        if cred:
            await session.delete(cred)
            await session.commit()

    async def start_oauth(self, session, owner):
        cipher()  # Fail before asking the seller to authorize insecure storage.
        client = await self.get_client(session)
        state, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        session.add(OAuthAttempt(state_hash=digest(state), browser_hash=digest(browser), owner=owner,
                                 expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
        await session.flush()
        return client.get_authorization_url(state), browser

    async def get_overview(self, session):
        from app.services.shopee_service import ShopeeService
        shopee_svc = ShopeeService()
        accounts = await self.repo.list_accounts(session)
        for account in accounts:
            if not account.is_active:
                continue
            if account.marketplace == "MERCADO_LIVRE":
                try:
                    token, _ = await self.get_valid_access_token(session, account.id)
                    client = await self.get_client(session)
                    user = await client.get_user_info(token)
                    if str(user.get("id")) != account.seller_id:
                        raise HTTPException(409, "Identidade da conta divergente.")
                    account.verified_at = datetime.now(timezone.utc)
                    account.connection_error = None
                except Exception:
                    account.verified_at = None
                    account.connection_error = "Não foi possível verificar a conexão. Reconecte ou tente novamente."
            elif account.marketplace == "SHOPEE":
                try:
                    token, shop_id, _ = await shopee_svc.get_valid_access_token(session, account.id)
                    client = await shopee_svc.get_client(session)
                    try:
                        await client.get_shop_info(token, shop_id)
                    finally:
                        await client.close()
                    account.verified_at = datetime.now(timezone.utc)
                    account.connection_error = None
                except Exception:
                    account.verified_at = None
                    account.connection_error = "Não foi possível verificar a conexão com a Shopee. Reconecte a conta."

        meli_connected = [a for a in accounts if a.marketplace == "MERCADO_LIVRE" and a.is_active and a.verified_at and not a.connection_error]
        shopee_connected = [a for a in accounts if a.marketplace == "SHOPEE" and a.is_active and a.verified_at and not a.connection_error]

        meli_cred = await self.repo.get_platform_credential(session, "MERCADO_LIVRE")
        shopee_cred = await self.repo.get_platform_credential(session, "SHOPEE")
        meli_client = await self.get_client(session)
        shopee_client = await shopee_svc.get_client(session)

        meli_is_configured = bool(settings.TOKEN_ENCRYPTION_KEY) and (meli_client.is_configured() or bool(meli_cred and getattr(meli_cred, "app_id", None) and getattr(meli_cred, "app_secret_encrypted", None)))
        shopee_is_configured = bool(settings.TOKEN_ENCRYPTION_KEY) and (shopee_client.is_configured() or bool(shopee_cred and getattr(shopee_cred, "app_id", None) and getattr(shopee_cred, "app_secret_encrypted", None)))

        channels = [
            MarketplaceChannelStatus(
                marketplace="MERCADO_LIVRE",
                name="Mercado Livre",
                is_configured=meli_is_configured,
                is_connected=bool(meli_connected),
                accounts_count=len(meli_connected),
                auth_url=None,
            ),
            MarketplaceChannelStatus(
                marketplace="SHOPEE",
                name="Shopee",
                is_configured=shopee_is_configured,
                is_connected=bool(shopee_connected),
                accounts_count=len(shopee_connected),
                auth_url=None,
            ),
            MarketplaceChannelStatus(marketplace="AMAZON", name="Amazon Brasil", is_configured=False, is_connected=False, accounts_count=0),
            MarketplaceChannelStatus(marketplace="TIKTOK", name="TikTok Shop", is_configured=False, is_connected=False, accounts_count=0),
        ]
        await session.flush()
        return MarketplacesOverviewResponse(channels=channels, accounts=[MarketplaceAccountResponse.model_validate(a) for a in accounts])

    async def handle_oauth_callback(self, session, code, state, browser, owner):
        attempt = await session.scalar(select(OAuthAttempt).where(OAuthAttempt.state_hash == digest(state)).with_for_update())
        if (not attempt or attempt.consumed_at or attempt.expires_at <= datetime.now(timezone.utc)
            or attempt.owner != owner or not browser or not secrets.compare_digest(attempt.browser_hash, digest(browser))):
            raise HTTPException(400, "Autorização expirada ou inválida. Inicie novamente.")
        attempt.consumed_at = datetime.now(timezone.utc)
        await session.commit()
        client = await self.get_client(session)
        token_data = await client.exchange_code_for_token(code)
        user = await client.get_user_info(token_data["access_token"])
        if not user.get("nickname") or user.get("site_id") != "MLB" or str(user.get("id")) != str(token_data["user_id"]):
            raise HTTPException(422, "A conta não possui identificação MLB confirmada.")
        account = await self.repo.upsert_account(session, "MERCADO_LIVRE", str(user["id"]), user["nickname"],
            encrypt_token(token_data["access_token"]), encrypt_token(token_data["refresh_token"]), token_data["token_expires_at"],
            site_id=user["site_id"], settings_dict={})
        account.settings = None
        account.verified_at = datetime.now(timezone.utc)
        account.connection_error = None
        await session.flush()
        return MarketplaceAccountResponse.model_validate(account)

    async def get_valid_access_token(self, session, account_id):
        account = await session.scalar(select(MarketplaceAccount).where(MarketplaceAccount.id == account_id)
                                       .with_for_update().execution_options(populate_existing=True))
        if not account or not account.is_active or account.marketplace != "MERCADO_LIVRE":
            raise HTTPException(404, "Conta ativa do Mercado Livre não encontrada.")
        if account.token_expires_at <= datetime.now(timezone.utc) + timedelta(seconds=30):
            try:
                data = await self.client.refresh_access_token(decrypt_token(account.refresh_token))
            except HTTPException as exc:
                if exc.status_code in (401, 422):
                    account.verified_at = None
                    account.connection_error = "Reautenticação necessária."
                    await session.commit()
                raise
            account.access_token = encrypt_token(data["access_token"])
            account.refresh_token = encrypt_token(data["refresh_token"])
            account.token_expires_at = data["token_expires_at"]
        token, name = decrypt_token(account.access_token), account.account_name
        await session.commit()  # Serialize rotation and release the account lock.
        return token, name

    async def predict_category(self, session, account_id, title):
        token, _ = await self.get_valid_access_token(session, account_id)
        return [CategoryPredictionItem.model_validate(p) for p in await self.client.predict_category(title, token)]

    async def category_attributes(self, session, account_id, category_id):
        token, _ = await self.get_valid_access_token(session, account_id)
        return await self.client.get_category_attributes(category_id, token)

    def listing_response(self, listing, product_name=None, account_name=None):
        data = MarketplaceListingResponse.model_validate(listing)
        return data.model_copy(update={"product_name": product_name, "account_name": account_name})

    async def publish_product(self, session, request):
        product = await self.product_repo.get_with_details(session, request.product_id)
        if not product or product.status != "ACTIVE":
            raise HTTPException(409, "Produto não encontrado ou inativo.")
        price = await self.pricing_repo.get_product_price(session, product.id, request.pricing_profile_id)
        if not price or price.is_stale or not price.profile.is_active or price.profile.channel != "MERCADO_LIVRE":
            raise HTTPException(409, "Calcule um preço atual com perfil ativo do Mercado Livre.")
        if price.profile.listing_type_id != request.listing_type_id or not price.profile.source_notes:
            raise HTTPException(422, "Informe a fonte das taxas e o tipo de anúncio no perfil de preço.")
        source = next((s for s in product.supplier_data if s.id == price.supplier_data_id), None)
        if not source or not source.is_active or not source.supplier.is_active or source.current_cost != price.cost_basis:
            raise HTTPException(409, "Custo de origem alterado ou indisponível; recalcule o preço.")
        if not product.images:
            raise HTTPException(422, "Cadastre imagens reais antes de publicar.")
        token, account_name = await self.get_valid_access_token(session, request.account_id)
        key = f"{request.account_id}:{product.id}"
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})
        same_request = await session.scalar(select(MarketplaceListing).where(MarketplaceListing.request_id == request.request_id))
        if same_request:
            if same_request.product_id != product.id or same_request.account_id != request.account_id:
                raise HTTPException(409, "Identificador de operação já utilizado.")
            if same_request.external_listing_id:
                return self.listing_response(same_request, product.name, account_name)
            raise HTTPException(409, "Operação já registrada. Consulte Publicações antes de tentar novamente.")
        existing = await session.scalar(select(MarketplaceListing.id).where(MarketplaceListing.product_id == product.id,
            MarketplaceListing.account_id == request.account_id, MarketplaceListing.status.not_in(["ERROR", "CLOSED"])).limit(1))
        if existing:
            raise HTTPException(409, "Existe anúncio ou publicação pendente para este produto/conta. Reconcilie antes de repetir.")
        listing = MarketplaceListing(product_id=product.id, account_id=request.account_id, request_id=request.request_id,
            marketplace="MERCADO_LIVRE", title=request.title.strip(), price=price.calculated_price,
            available_quantity=request.available_quantity, category_id=request.category_id,
            listing_type_id=request.listing_type_id, status="IN_PROGRESS")
        session.add(listing)
        await session.commit()
        external_started = False
        try:
            attributes = {a["id"]: a for a in (request.attributes or []) if a.get("id")}
            for key, value in (("BRAND", product.brand), ("MODEL", product.model), ("GTIN", product.gtin or product.ean)):
                if value and key not in attributes:
                    attributes[key] = {"id": key, "value_name": value}
            definitions = await self.client.get_category_attributes(request.category_id, token)
            required = [a["id"] for a in definitions if a.get("tags", {}).get("required") and not a.get("tags", {}).get("read_only")]
            missing = [key for key in required if key not in attributes]
            if missing:
                raise HTTPException(422, "Preencha os atributos obrigatórios: " + ", ".join(missing))
            storage = StorageService(settings.STORAGE_PATH)
            pictures = []
            for picture in product.images:
                if Path(picture.storage_path).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                    raise HTTPException(422, "Fotos para publicação devem estar em PNG ou JPEG.")
                picture_id = await self.client.upload_picture(storage.get(picture.storage_path), Path(picture.storage_path).name, token)
                pictures.append({"id": picture_id})
            payload = {"title": listing.title, "category_id": request.category_id, "price": price.calculated_price,
                "currency_id": "BRL", "available_quantity": request.available_quantity, "buying_mode": "buy_it_now",
                "condition": request.condition, "listing_type_id": request.listing_type_id,
                "attributes": list(attributes.values()), "pictures": pictures}
            await self.client.validate_item(payload, token)
            external_started = True
            response = await self.client.publish_item(payload, token)
            if not all(k in response for k in ("id", "status", "price", "available_quantity")):
                raise ValueError("Resposta incompleta")
            listing.external_listing_id = response["id"]
            listing.status = str(response["status"]).upper()
            listing.price = Decimal(str(response["price"]))
            listing.available_quantity = response["available_quantity"]
            listing.permalink = response.get("permalink")
            listing.raw_response = safe_json(response)
            listing.last_synced_at = datetime.now(timezone.utc)
            await session.commit()  # Save the external identity before optional description.
        except Exception as exc:
            await session.rollback()
            listing = await session.scalar(select(MarketplaceListing).where(MarketplaceListing.request_id == request.request_id))
            uncertain = external_started and not (isinstance(exc, HTTPException) and exc.status_code in (401, 422))
            listing.status = "UNKNOWN" if uncertain else "ERROR"
            listing.error_message = "Resultado incerto. Confira a conta no Mercado Livre antes de repetir." if uncertain else (str(exc.detail) if isinstance(exc, HTTPException) else "Falha anterior à publicação.")
            await session.commit()
            raise HTTPException(409 if uncertain else 422, listing.error_message)
        if product.description:
            try:
                await self.client.set_description(listing.external_listing_id, product.description, token)
            except Exception:
                listing.error_message = "Anúncio criado; descrição pendente. Não publique novamente."
                await session.commit()
        return self.listing_response(listing, product.name, account_name)

    async def reconcile(self, session, listing_id, external_id=None):
        listing = await session.get(MarketplaceListing, listing_id)
        if not listing:
            raise HTTPException(404, "Publicação não encontrada.")
        item_id = listing.external_listing_id or external_id
        if not item_id:
            raise HTTPException(422, "Informe o ID real encontrado na conta do Mercado Livre.")
        token, name = await self.get_valid_access_token(session, listing.account_id)
        response = await self.client.get_item(item_id, token)
        account = await session.get(MarketplaceAccount, listing.account_id)
        if str(response.get("seller_id")) != account.seller_id:
            raise HTTPException(422, "O anúncio não pertence à conta selecionada.")
        if not all(k in response for k in ("id", "status", "price", "available_quantity")):
            raise HTTPException(502, "Resposta de anúncio incompleta.")
        listing.external_listing_id = response["id"]
        listing.title = response.get("title") or listing.title
        listing.price = Decimal(str(response["price"]))
        listing.available_quantity = response["available_quantity"]
        listing.status = str(response["status"]).upper()
        listing.permalink = response.get("permalink")
        listing.raw_response = safe_json(response)
        listing.last_synced_at = datetime.now(timezone.utc)
        listing.error_message = None
        await session.flush()
        return self.listing_response(listing, account_name=name)

    async def list_listings(
        self,
        session: AsyncSession,
        product_id: UUID | None = None,
        account_id: UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> MarketplaceListingListResponse:
        """Lista anúncios de marketplaces com paginação."""
        listings = await self.repo.list_listings(
            session, product_id, account_id, status, skip, limit
        )
        total = await self.repo.count_listings(session, product_id, account_id, status)

        items = []
        for l in listings:
            items.append(
                MarketplaceListingResponse(
                    id=l.id,
                    product_id=l.product_id,
                    product_name=l.product.name if l.product else None,
                    account_id=l.account_id,
                    account_name=l.account.account_name if l.account else None,
                    marketplace=l.marketplace,
                    external_listing_id=l.external_listing_id,
                    title=l.title,
                    price=l.price,
                    available_quantity=l.available_quantity,
                    category_id=l.category_id,
                    listing_type_id=l.listing_type_id,
                    status=l.status,
                    permalink=l.permalink,
                    error_message=l.error_message,
                    last_synced_at=l.last_synced_at,
                    created_at=l.created_at,
                    updated_at=l.updated_at,
                )
            )

        return MarketplaceListingListResponse(items=items, total=total)

    async def delete_account(self, session: AsyncSession, account_id: UUID) -> None:
        """Remove/desconecta uma conta de marketplace."""
        deleted = await self.repo.delete_account(session, account_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Conta {account_id} não encontrada.",
            )
