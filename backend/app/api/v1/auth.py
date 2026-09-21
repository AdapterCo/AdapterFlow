import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete
from app.api.deps import DBSession
from app.models.admin_session import AdminSession
from app.core.config import settings
from app.core.security import require_admin, token_hash, credential_hash, check_origin

router = APIRouter(prefix="/auth", tags=["auth"])
login_attempts = deque(maxlen=20)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    success: bool
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(request_data: LoginRequest, response: Response, request: Request, db: DBSession):
    """Autentica o operador administrativo e cria cookie de sessão seguro."""
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        raise HTTPException(503, "Acesso administrativo não configurado no servidor.")

    check_origin(request)
    now = time.monotonic()
    while login_attempts and now - login_attempts[0] >= 60:
        login_attempts.popleft()
    if len(login_attempts) >= 20:
        raise HTTPException(429, "Muitas tentativas de login. Aguarde um minuto.", headers={"Retry-After": "60"})
    login_attempts.append(now)
    input_user = request_data.username.strip()
    input_pass = request_data.password

    user_match = secrets.compare_digest(input_user.encode(), settings.ADMIN_USERNAME.encode())

    pass_match = secrets.compare_digest(input_pass.encode(), settings.ADMIN_PASSWORD.get_secret_value().encode())

    if not (user_match and pass_match):
        raise HTTPException(401, "Nome de usuário ou senha incorretos.")

    session_token = secrets.token_urlsafe(48)
    await db.execute(delete(AdminSession).where(AdminSession.expires_at <= datetime.now(timezone.utc)))
    db.add(AdminSession(token_hash=token_hash(session_token), username=settings.ADMIN_USERNAME,
                       credential_hash=credential_hash(session_token), expires_at=datetime.now(timezone.utc) + timedelta(hours=12)))
    await db.flush()
    is_secure = request.url.scheme == "https" or "https" in request.headers.get("x-forwarded-proto", "")

    response.set_cookie(
        key="adapterflow_session",
        value=session_token,
        max_age=12 * 3600,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/",
    )

    return {"success": True, "username": settings.ADMIN_USERNAME}


@router.post("/logout")
async def logout(response: Response, request: Request, db: DBSession):
    """Encerra a sessão do usuário removendo o cookie de autenticação."""
    check_origin(request)
    token = request.cookies.get("adapterflow_session")
    if token:
        await db.execute(delete(AdminSession).where(AdminSession.token_hash == token_hash(token)))
    response.delete_cookie(
        key="adapterflow_session",
        path="/",
    )
    return {"success": True}


@router.get("/me")
async def get_current_user(user: str = Depends(require_admin)):
    """Retorna os dados do usuário atualmente autenticado."""
    return {"authenticated": True, "username": user, "role": "Administrador"}
