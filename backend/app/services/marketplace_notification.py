import hashlib
import json
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.marketplace_notification import save_notification
from app.schemas.marketplace_notification import MercadoLivreNotification


def notification_key(notification: MercadoLivreNotification) -> str:
    identity = notification.model_dump(mode="json", by_alias=True, exclude={"attempts", "sent"})
    if notification.notification_id:
        identity = {"application_id": notification.application_id, "_id": notification.notification_id}
    elif notification.received is None:
        # Without an event ID/time there is no safe way to merge distinct events.
        identity["receipt_nonce"] = str(uuid.uuid4())
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


async def receive_notification(session: AsyncSession, notification: MercadoLivreNotification) -> None:
    if not settings.MERCADOLIVRE_APP_ID:
        raise HTTPException(503, "Aplicação Mercado Livre não configurada.")
    if str(notification.application_id) != settings.MERCADOLIVRE_APP_ID:
        raise HTTPException(403, "Notificação de outra aplicação.")
    # App ID is routing validation, NOT proof of origin. Payload stays unverified.
    await save_notification(session, notification_key(notification), notification.model_dump(mode="json", by_alias=True))
