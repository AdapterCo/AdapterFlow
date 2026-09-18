from datetime import datetime
from uuid import UUID
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marketplace import MarketplaceAccount, MarketplaceListing


class MarketplaceRepository:
    async def upsert_account(
        self,
        session: AsyncSession,
        marketplace: str,
        seller_id: str,
        account_name: str,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime,
        site_id: str = "MLB",
        settings_dict: dict | None = None,
    ) -> MarketplaceAccount:
        stmt = select(MarketplaceAccount).where(
            MarketplaceAccount.marketplace == marketplace,
            MarketplaceAccount.seller_id == str(seller_id),
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if account:
            account.account_name = account_name
            account.access_token = access_token
            account.refresh_token = refresh_token
            account.token_expires_at = token_expires_at
            account.site_id = site_id
            account.is_active = True
            if settings_dict:
                account.settings = settings_dict
        else:
            account = MarketplaceAccount(
                marketplace=marketplace,
                seller_id=str(seller_id),
                account_name=account_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                site_id=site_id,
                settings=settings_dict,
                is_active=True,
            )
            session.add(account)

        await session.commit()
        await session.refresh(account)
        return account

    async def get_account_by_id(
        self, session: AsyncSession, account_id: UUID
    ) -> MarketplaceAccount | None:
        stmt = select(MarketplaceAccount).where(MarketplaceAccount.id == account_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_accounts(
        self,
        session: AsyncSession,
        marketplace: str | None = None,
        active_only: bool = False,
    ) -> list[MarketplaceAccount]:
        stmt = select(MarketplaceAccount)
        if marketplace:
            stmt = stmt.where(MarketplaceAccount.marketplace == marketplace)
        if active_only:
            stmt = stmt.where(MarketplaceAccount.is_active.is_(True))
        stmt = stmt.order_by(MarketplaceAccount.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_account(self, session: AsyncSession, account_id: UUID) -> bool:
        account = await self.get_account_by_id(session, account_id)
        if not account:
            return False
        await session.delete(account)
        await session.commit()
        return True

    async def create_or_update_listing(
        self, session: AsyncSession, listing_data: dict
    ) -> MarketplaceListing:
        account_id = listing_data["account_id"]
        external_id = listing_data.get("external_listing_id")

        listing = None
        if external_id:
            stmt = select(MarketplaceListing).where(
                MarketplaceListing.account_id == account_id,
                MarketplaceListing.external_listing_id == external_id,
            )
            result = await session.execute(stmt)
            listing = result.scalar_one_or_none()

        if listing:
            for key, val in listing_data.items():
                setattr(listing, key, val)
        else:
            listing = MarketplaceListing(**listing_data)
            session.add(listing)

        await session.commit()
        await session.refresh(listing)
        return listing

    async def list_listings(
        self,
        session: AsyncSession,
        product_id: UUID | None = None,
        account_id: UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MarketplaceListing]:
        stmt = (
            select(MarketplaceListing)
            .options(
                selectinload(MarketplaceListing.product),
                selectinload(MarketplaceListing.account),
            )
            .order_by(MarketplaceListing.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if product_id:
            stmt = stmt.where(MarketplaceListing.product_id == product_id)
        if account_id:
            stmt = stmt.where(MarketplaceListing.account_id == account_id)
        if status:
            stmt = stmt.where(MarketplaceListing.status == status)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_listings(
        self,
        session: AsyncSession,
        product_id: UUID | None = None,
        account_id: UUID | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count(MarketplaceListing.id))
        if product_id:
            stmt = stmt.where(MarketplaceListing.product_id == product_id)
        if account_id:
            stmt = stmt.where(MarketplaceListing.account_id == account_id)
        if status:
            stmt = stmt.where(MarketplaceListing.status == status)

        result = await session.execute(stmt)
        return result.scalar() or 0
