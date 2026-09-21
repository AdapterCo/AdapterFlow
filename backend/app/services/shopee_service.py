from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
import hashlib
import secrets
import logging
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.tokens import encrypt_token, decrypt_token
from app.models.marketplace import MarketplaceAccount, OAuthAttempt
from app.integrations.shopee.client import ShopeeClient
from app.repositories.marketplace_repository import MarketplaceRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.pricing_repository import PricingRepository
from app.schemas.marketplace import (
    MarketplaceAccountResponse,
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
        raise HTTPException(501, "Autorização Shopee indisponível até validação oficial do retorno de state. Nenhuma autorização foi iniciada.")

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
        raise HTTPException(501, "Publicação Shopee não implementada: logística, marca, atributos e reconciliação precisam de contrato oficial validado. Nenhum anúncio foi enviado.")
