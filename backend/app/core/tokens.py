from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from app.core.config import settings


def cipher():
    if not settings.TOKEN_ENCRYPTION_KEY:
        raise HTTPException(503, "Criptografia de tokens não configurada.")
    try:
        return Fernet(settings.TOKEN_ENCRYPTION_KEY.get_secret_value().encode())
    except ValueError:
        raise HTTPException(503, "Configuração de criptografia inválida.")


def encrypt_token(value: str) -> str:
    return "fernet:" + cipher().encrypt(value.encode()).decode()


def decrypt_token(value: str | None) -> str:
    if not value or not value.startswith("fernet:"):
        raise HTTPException(409, "Reconecte a conta para proteger suas credenciais.")
    try:
        return cipher().decrypt(value[7:].encode()).decode()
    except InvalidToken:
        raise HTTPException(409, "Credencial indisponível. Reconecte a conta.")
