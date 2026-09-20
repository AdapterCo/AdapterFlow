from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DBSession
from app.schemas.marketplace_notification import MercadoLivreNotification, NotificationReceipt
from app.services.marketplace_notification import receive_notification

router = APIRouter()


@router.post(
    "/marketplaces/mercadolivre/notifications",
    response_model=NotificationReceipt,
    tags=["Marketplace notifications"],
    description="Public durable receipt only. Does not verify origin or synchronize business data.",
    openapi_extra={"requestBody": {"required": True, "content": {"application/json": {"schema": MercadoLivreNotification.model_json_schema()}}}},
)
async def notifications(request: Request, session: DBSession):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "Envie application/json.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 16_384:
            raise HTTPException(413, "Notificação excede o limite de 16 KiB.")
        body.extend(chunk)
    try:
        notification = MercadoLivreNotification.model_validate_json(bytes(body))
    except ValidationError:
        raise HTTPException(422, "Formato de notificação inválido.") from None
    try:
        await receive_notification(session, notification)
        # Acknowledge only after durable commit, never before it succeeds.
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(503, "Não foi possível registrar a notificação. Tente novamente.") from None
    return NotificationReceipt()
