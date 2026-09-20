from uuid import UUID
from sqlalchemy import select, delete, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pricing import PricingProfile, ProductChannelPrice
from app.schemas.pricing import PricingProfileCreate, PricingProfileUpdate


class PricingRepository:
    async def _reserve_default(self, session, channel, is_default, profile_id=None):
        if not is_default:
            return
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:channel))"), {"channel": channel})
        query = update(PricingProfile).where(PricingProfile.channel == channel, PricingProfile.is_default.is_(True))
        if profile_id:
            query = query.where(PricingProfile.id != profile_id)
        await session.execute(query.values(is_default=False))

    async def create_profile(
        self, session: AsyncSession, data: PricingProfileCreate
    ) -> PricingProfile:
        await self._reserve_default(session, data.channel, data.is_default)
        profile = PricingProfile(**data.model_dump())
        session.add(profile)
        await session.flush()
        await session.refresh(profile)
        return profile

    async def get_profile_by_id(
        self, session: AsyncSession, profile_id: UUID
    ) -> PricingProfile | None:
        stmt = select(PricingProfile).where(PricingProfile.id == profile_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_profiles(
        self, session: AsyncSession, active_only: bool = False
    ) -> list[PricingProfile]:
        stmt = select(PricingProfile)
        if active_only:
            stmt = stmt.where(PricingProfile.is_active.is_(True))
        stmt = stmt.order_by(PricingProfile.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_profile(
        self, session: AsyncSession, profile_id: UUID, data: PricingProfileUpdate
    ) -> PricingProfile | None:
        profile = await self.get_profile_by_id(session, profile_id)
        if not profile:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        merged = {key: getattr(profile, key) for key in PricingProfileCreate.model_fields}
        merged.update(update_dict)
        validated = PricingProfileCreate.model_validate(merged)
        await self._reserve_default(session, validated.channel, validated.is_default, profile_id)
        await session.execute(update(ProductChannelPrice).where(ProductChannelPrice.pricing_profile_id == profile_id).values(is_stale=True))
        for key, value in update_dict.items():
            setattr(profile, key, value)

        await session.flush()
        await session.refresh(profile)
        return profile

    async def delete_profile(self, session: AsyncSession, profile_id: UUID) -> bool:
        profile = await self.get_profile_by_id(session, profile_id)
        if not profile:
            return False
        profile.is_active = False
        profile.is_default = False
        await session.execute(update(ProductChannelPrice).where(ProductChannelPrice.pricing_profile_id == profile_id).values(is_stale=True))
        await session.flush()
        return True

    async def get_default_profile(
        self, session: AsyncSession, channel: str | None = None
    ) -> PricingProfile | None:
        stmt = select(PricingProfile).where(PricingProfile.is_default.is_(True))
        if channel:
            stmt = stmt.where(PricingProfile.channel == channel)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def upsert_product_price(
        self,
        session: AsyncSession,
        product_id: UUID,
        profile_id: UUID,
        calculated_data: dict,
    ) -> ProductChannelPrice:
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:identity))"), {"identity": f"price:{product_id}:{profile_id}"})
        stmt = (
            select(ProductChannelPrice)
            .where(
                ProductChannelPrice.product_id == product_id,
                ProductChannelPrice.pricing_profile_id == profile_id,
            )
            .options(selectinload(ProductChannelPrice.profile))
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            for key, val in calculated_data.items():
                setattr(record, key, val)
        else:
            record = ProductChannelPrice(
                product_id=product_id,
                pricing_profile_id=profile_id,
                **calculated_data,
            )
            session.add(record)

        await session.flush()
        await session.refresh(record)
        return record

    async def get_product_prices(
        self, session: AsyncSession, product_id: UUID
    ) -> list[ProductChannelPrice]:
        stmt = (
            select(ProductChannelPrice)
            .where(ProductChannelPrice.product_id == product_id)
            .options(selectinload(ProductChannelPrice.profile))
            .order_by(ProductChannelPrice.created_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_product_price(
        self, session: AsyncSession, product_id: UUID, profile_id: UUID
    ) -> ProductChannelPrice | None:
        stmt = (
            select(ProductChannelPrice)
            .where(
                ProductChannelPrice.product_id == product_id,
                ProductChannelPrice.pricing_profile_id == profile_id,
            )
            .options(selectinload(ProductChannelPrice.profile))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_product_price(
        self, session: AsyncSession, product_id: UUID, profile_id: UUID
    ) -> bool:
        stmt = delete(ProductChannelPrice).where(
            ProductChannelPrice.product_id == product_id,
            ProductChannelPrice.pricing_profile_id == profile_id,
        )
        res = await session.execute(stmt)
        await session.flush()
        return res.rowcount > 0
