import hmac
import hashlib
import time
import secrets
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.core.config import settings

basic = HTTPBasic(auto_error=False)


def sign_session(username: str) -> str:
    secret = (settings.ADMIN_PASSWORD.get_secret_value() if settings.ADMIN_PASSWORD else "adapterflow_secret").encode()
    ts = str(int(time.time()))
    sig = hmac.new(secret, f"{username}:{ts}".encode(), hashlib.sha256).hexdigest()
    return f"{username}:{ts}:{sig}"


def verify_session(token: str) -> str | None:
    if not token or not settings.ADMIN_PASSWORD:
        return None
    parts = token.split(":")
    if len(parts) != 3:
        return None
    username, ts, sig = parts
    try:
        ts_int = int(ts)
    except ValueError:
        return None
    # 30 days validity
    if time.time() - ts_int > 30 * 86400 or ts_int > time.time() + 300:
        return None
    secret = settings.ADMIN_PASSWORD.get_secret_value().encode()
    expected = hmac.new(secret, f"{username}:{ts}".encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected):
        return username
    return None


def require_admin(request: Request, credentials: Annotated[HTTPBasicCredentials | None, Depends(basic)]) -> str:
    """Authentication via either session cookie or HTTP Basic (backward compatibility)."""
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        raise HTTPException(503, "Acesso administrativo não configurado no servidor.")

    # 1. Check session cookie
    session_cookie = request.cookies.get("adapterflow_session")
    if session_cookie:
        verified_user = verify_session(session_cookie)
        if verified_user and secrets.compare_digest(verified_user.encode(), settings.ADMIN_USERNAME.encode()):
            origin = request.headers.get("origin")
            if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in settings.BACKEND_CORS_ORIGINS:
                raise HTTPException(403, "Origem não autorizada.")
            return verified_user

    # 2. Check HTTP Basic
    if credentials:
        valid_user = secrets.compare_digest(credentials.username.encode(), settings.ADMIN_USERNAME.encode())
        valid_password = secrets.compare_digest(credentials.password.encode(), settings.ADMIN_PASSWORD.get_secret_value().encode())
        if valid_user and valid_password:
            origin = request.headers.get("origin")
            if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in settings.BACKEND_CORS_ORIGINS:
                raise HTTPException(403, "Origem não autorizada.")
            return credentials.username

    # Neither valid: raise 401 without WWW-Authenticate header to prevent browser popup
    raise HTTPException(401, "Autenticação necessária.")
