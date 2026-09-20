import secrets
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.core.config import settings

basic = HTTPBasic(auto_error=False)


def require_admin(request: Request, credentials: Annotated[HTTPBasicCredentials | None, Depends(basic)]) -> str:
    """Single-operator deployment; credentials are configured only on the server."""
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        raise HTTPException(503, "Acesso administrativo não configurado no servidor.")
    valid = False
    if credentials:
        valid_user = secrets.compare_digest(credentials.username.encode(), settings.ADMIN_USERNAME.encode())
        valid_password = secrets.compare_digest(credentials.password.encode(), settings.ADMIN_PASSWORD.get_secret_value().encode())
        valid = valid_user and valid_password
    if not valid:
        raise HTTPException(401, "Autenticação necessária.", headers={"WWW-Authenticate": 'Basic realm="AdapterFlow", charset="UTF-8"'})
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in settings.BACKEND_CORS_ORIGINS:
        raise HTTPException(403, "Origem não autorizada.")
    return credentials.username
