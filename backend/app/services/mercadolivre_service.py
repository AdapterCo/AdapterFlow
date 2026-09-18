from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.mercadolivre.client import MercadoLivreClient
from app.repositories.marketplace_repository import MarketplaceRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.pricing_repository import PricingRepository
from app.schemas.marketplace import (
    MarketplaceAccountResponse,
    MarketplaceChannelStatus,
    MarketplacesOverviewResponse,
    MarketplaceListingResponse,
    MarketplaceListingListResponse,
    PublishProductRequest,
    CategoryPredictionItem,
)


class MercadoLivreService:
    def __init__(self) -> None:
        self.client = MercadoLivreClient()
        self.repo = MarketplaceRepository()
        self.product_repo = ProductRepository()
        self.pricing_repo = PricingRepository()

    async def get_overview(self, session: AsyncSession) -> MarketplacesOverviewResponse:
        """Retorna o panorama real de integrações e contas conectadas."""
        accounts = await self.repo.list_accounts(session)
        ml_accounts = [a for a in accounts if a.marketplace == "MERCADO_LIVRE" and a.is_active]

        is_ml_configured = self.client.is_configured()
        auth_url = None
        if is_ml_configured:
            try:
                auth_url = self.client.get_authorization_url()
            except Exception:
                auth_url = None

        channels: list[MarketplaceChannelStatus] = [
            MarketplaceChannelStatus(
                marketplace="MERCADO_LIVRE",
                name="Mercado Livre",
                is_configured=is_ml_configured,
                is_connected=len(ml_accounts) > 0,
                accounts_count=len(ml_accounts),
                auth_url=auth_url,
            ),
            MarketplaceChannelStatus(
                marketplace="SHOPEE",
                name="Shopee",
                is_configured=False,
                is_connected=False,
                accounts_count=0,
                auth_url=None,
            ),
            MarketplaceChannelStatus(
                marketplace="AMAZON",
                name="Amazon Brasil",
                is_configured=False,
                is_connected=False,
                accounts_count=0,
                auth_url=None,
            ),
            MarketplaceChannelStatus(
                marketplace="TIKTOK",
                name="TikTok Shop",
                is_configured=False,
                is_connected=False,
                accounts_count=0,
                auth_url=None,
            ),
        ]

        account_responses = [
            MarketplaceAccountResponse.model_validate(acc) for acc in accounts
        ]

        return MarketplacesOverviewResponse(
            channels=channels,
            accounts=account_responses,
        )

    async def handle_oauth_callback(
        self, session: AsyncSession, code: str
    ) -> MarketplaceAccountResponse:
        """Conclui a troca de tokens do Mercado Livre e persiste a conta."""
        token_data = await self.client.exchange_code_for_token(code)
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        seller_id = str(token_data["user_id"])
        token_expires_at = token_data["token_expires_at"]

        # Busca dados do usuário no Mercado Livre
        user_info = await self.client.get_user_info(access_token)
        account_name = (
            user_info.get("nickname")
            or f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
            or f"Vendedor {seller_id}"
        )

        account = await self.repo.upsert_account(
            session=session,
            marketplace="MERCADO_LIVRE",
            seller_id=seller_id,
            account_name=account_name,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            site_id="MLB",
            settings_dict={"user_info": user_info},
        )

        return MarketplaceAccountResponse.model_validate(account)

    async def get_valid_access_token(
        self, session: AsyncSession, account_id: UUID
    ) -> tuple[str, str]:
        """Obtém um access_token válido, renovando automaticamente se estiver próximo de expirar."""
        account = await self.repo.get_account_by_id(session, account_id)
        if not account or not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conta do Mercado Livre não encontrada ou inativa.",
            )

        now = datetime.now(timezone.utc)
        # Se expira em menos de 10 minutos, renova
        if account.token_expires_at <= now + timedelta(minutes=10):
            token_data = await self.client.refresh_access_token(account.refresh_token)
            account.access_token = token_data["access_token"]
            account.refresh_token = token_data["refresh_token"]
            account.token_expires_at = token_data["token_expires_at"]
            await session.commit()
            await session.refresh(account)

        return account.access_token, account.account_name

    async def predict_category(
        self, title: str
    ) -> list[CategoryPredictionItem]:
        """Prediz categorias no Mercado Livre a partir do título."""
        predictions = await self.client.predict_category(title)
        items = []
        for p in predictions:
            items.append(
                CategoryPredictionItem(
                    category_id=p.get("category_id", ""),
                    category_name=p.get("category_name", ""),
                    domain_id=p.get("domain_id"),
                    domain_name=p.get("domain_name"),
                )
            )
        return items

    async def publish_product(
        self, session: AsyncSession, request: PublishProductRequest
    ) -> MarketplaceListingResponse:
        """Publica um produto no Mercado Livre com validação e preço da Fase 2."""
        product = await self.product_repo.get_with_details(session, request.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto {request.product_id} não encontrado.",
            )

        # Determinar preço de venda
        price = None
        if request.pricing_profile_id:
            channel_price = await self.pricing_repo.get_product_price(
                session, request.product_id, request.pricing_profile_id
            )
            if channel_price:
                price = channel_price.calculated_price

        if price is None:
            # Tentar buscar qualquer preço de canal calculado para o produto
            existing_prices = await self.pricing_repo.get_product_prices(
                session, request.product_id
            )
            if existing_prices:
                price = existing_prices[0].calculated_price

        if price is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O produto ainda não possui precificação calculada para canal de venda. Calcule o preço na aba de Precificação antes de publicar.",
            )

        access_token, account_name = await self.get_valid_access_token(
            session, request.account_id
        )

        title = (request.title or product.name).strip()[:60]

        attributes = request.attributes or []
        if product.brand:
            attributes.append({"id": "BRAND", "value_name": product.brand})
        if product.model:
            attributes.append({"id": "MODEL", "value_name": product.model})
        if product.ean:
            attributes.append({"id": "GTIN", "value_name": product.ean})

        item_payload = {
            "title": title,
            "category_id": request.category_id,
            "price": float(price),
            "currency_id": "BRL",
            "available_quantity": request.available_quantity,
            "buying_mode": "buy_it_now",
            "condition": request.condition,
            "listing_type_id": request.listing_type_id,
            "attributes": attributes,
        }

        if product.description:
            item_payload["description"] = {"plain_text": product.description}

        listing_record = None
        try:
            # Chama a API oficial do Mercado Livre
            meli_response = await self.client.publish_item(item_payload, access_token)
            external_id = meli_response.get("id")
            permalink = meli_response.get("permalink")

            listing_record = await self.repo.create_or_update_listing(
                session=session,
                listing_data={
                    "product_id": request.product_id,
                    "account_id": request.account_id,
                    "marketplace": "MERCADO_LIVRE",
                    "external_listing_id": external_id,
                    "title": title,
                    "price": price,
                    "available_quantity": request.available_quantity,
                    "category_id": request.category_id,
                    "listing_type_id": request.listing_type_id,
                    "status": "ACTIVE",
                    "permalink": permalink,
                    "raw_response": meli_response,
                    "error_message": None,
                    "last_synced_at": datetime.now(timezone.utc),
                },
            )
        except Exception as exc:
            err_text = getattr(exc, "detail", str(exc))
            # Registra a tentativa com status ERROR
            listing_record = await self.repo.create_or_update_listing(
                session=session,
                listing_data={
                    "product_id": request.product_id,
                    "account_id": request.account_id,
                    "marketplace": "MERCADO_LIVRE",
                    "external_listing_id": None,
                    "title": title,
                    "price": price,
                    "available_quantity": request.available_quantity,
                    "category_id": request.category_id,
                    "listing_type_id": request.listing_type_id,
                    "status": "ERROR",
                    "permalink": None,
                    "raw_response": None,
                    "error_message": err_text,
                    "last_synced_at": datetime.now(timezone.utc),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Falha ao publicar anúncio: {err_text}",
            )

        return MarketplaceListingResponse(
            id=listing_record.id,
            product_id=listing_record.product_id,
            product_name=product.name,
            account_id=listing_record.account_id,
            account_name=account_name,
            marketplace=listing_record.marketplace,
            external_listing_id=listing_record.external_listing_id,
            title=listing_record.title,
            price=listing_record.price,
            available_quantity=listing_record.available_quantity,
            category_id=listing_record.category_id,
            listing_type_id=listing_record.listing_type_id,
            status=listing_record.status,
            permalink=listing_record.permalink,
            error_message=listing_record.error_message,
            last_synced_at=listing_record.last_synced_at,
            created_at=listing_record.created_at,
            updated_at=listing_record.updated_at,
        )

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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conta {account_id} não encontrada.",
            )
