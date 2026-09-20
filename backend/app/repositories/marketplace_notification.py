from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketplace_notification import MarketplaceNotification


async def save_notification(session: AsyncSession, key: str, payload: dict) -> None:
    await session.execute(
        insert(MarketplaceNotification)
        .values(deduplication_key=key, payload=payload)
        .on_conflict_do_nothing(index_elements=[MarketplaceNotification.deduplication_key])
    )
