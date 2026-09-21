import secrets
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import sign_session, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(request_data: LoginRequest, response: Response, request: Request):
    """Autentica o operador administrativo e cria cookie de sessão seguro."""
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        raise HTTPException(503, "Acesso administrativo não configurado no servidor.")

    input_user = request_data.username.strip()
    input_pass = request_data.password

    # Permite login por nome de usuário exato ou se o e-mail começar com o username configurado
    user_match = secrets.compare_digest(input_user.encode(), settings.ADMIN_USERNAME.encode())
    if not user_match and "@" in input_user:
        prefix = input_user.split("@")[0]
        user_match = secrets.compare_digest(prefix.encode(), settings.ADMIN_USERNAME.encode())

    pass_match = secrets.compare_digest(input_pass.encode(), settings.ADMIN_PASSWORD.get_secret_value().encode())

    if not (user_match and pass_match):
        raise HTTPException(401, "Nome de usuário ou senha incorretos.")

    session_token = sign_session(settings.ADMIN_USERNAME)
    is_secure = request.url.scheme == "https" or "https" in request.headers.get("x-forwarded-proto", "")

    response.set_cookie(
        key="adapterflow_session",
        value=session_token,
        max_age=30 * 86400,  # 30 dias
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/",
    )

    return {"success": True, "username": settings.ADMIN_USERNAME}


@router.post("/logout")
async def logout(response: Response):
    """Encerra a sessão do usuário removendo o cookie de autenticação."""
    response.delete_cookie(
        key="adapterflow_session",
        path="/",
    )
    return {"success": True}


@router.get("/me")
async def get_current_user(user: str = Depends(require_admin)):
    """Retorna os dados do operador atualmente autenticado."""
    return {"authenticated": True, "username": user}
