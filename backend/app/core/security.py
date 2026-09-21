import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.admin_session import AdminSession

basic = HTTPBasic(auto_error=False)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def credential_hash(token: str) -> str:
    return hmac.new(settings.ADMIN_PASSWORD.get_secret_value().encode(), token.encode(), hashlib.sha256).hexdigest()


def check_origin(request: Request):
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in settings.BACKEND_CORS_ORIGINS:
        raise HTTPException(403, "Origem não autorizada.")


async def require_admin(request: Request, credentials: Annotated[HTTPBasicCredentials | None, Depends(basic)],
                        db: Annotated[AsyncSession, Depends(get_db, scope="function")]) -> str:
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        raise HTTPException(503, "Acesso administrativo não configurado no servidor.")
    check_origin(request)
    if credentials:
        if (secrets.compare_digest(credentials.username.encode(), settings.ADMIN_USERNAME.encode())
                and secrets.compare_digest(credentials.password.encode(), settings.ADMIN_PASSWORD.get_secret_value().encode())):
            return settings.ADMIN_USERNAME
    token = request.cookies.get("adapterflow_session")
    if token and len(token) <= 200:
        session = await db.scalar(select(AdminSession).where(AdminSession.token_hash == token_hash(token)))
        if (session and session.expires_at > datetime.now(timezone.utc)
                and session.username == settings.ADMIN_USERNAME
                and hmac.compare_digest(session.credential_hash, credential_hash(token))):
            return session.username
    raise HTTPException(401, "Autenticação necessária.")
