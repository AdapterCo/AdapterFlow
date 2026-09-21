from typing import Optional
from uuid import UUID
from urllib.parse import urlsplit
from fastapi import APIRouter, status, Query, Depends, Request, Response, HTTPException

from app.api.deps import DBSession
from app.core.security import require_admin
from app.core.config import settings
from app.schemas.marketplace import (
    MarketplaceAccountResponse,
    MarketplaceListingResponse,
    ShopeeConfigurationResponse,
    ShopeeOAuthCallbackRequest,
    PublishShopeeProductRequest,
)
from app.services.shopee_service import ShopeeService

router = APIRouter(prefix="/shopee", tags=["shopee"])
service = ShopeeService()


@router.get("/configuration", response_model=ShopeeConfigurationResponse)
async def shopee_configuration():
    """Diagnóstico de configuração da Shopee Open API v2."""
    from app.core.tokens import cipher

    issues = []
    if not settings.SHOPEE_PARTNER_ID:
        issues.append("Defina SHOPEE_PARTNER_ID com o Partner ID numérico fornecido pela Shopee.")
    if not settings.SHOPEE_PARTNER_KEY:
        issues.append("Defina SHOPEE_PARTNER_KEY com a Partner Key secreta.")
    redirect = settings.SHOPEE_REDIRECT_URI
    if not redirect:
        issues.append("Configure SHOPEE_REDIRECT_URI apontando para /marketplaces/callback/shopee.")
    else:
        try:
            parts = urlsplit(redirect)
            if parts.scheme != "https" or not parts.hostname or not parts.path.endswith("/marketplaces/callback/shopee"):
                issues.append("SHOPEE_REDIRECT_URI deve usar HTTPS e terminar com /marketplaces/callback/shopee.")
        except Exception:
            issues.append("SHOPEE_REDIRECT_URI inválida.")

    try:
        cipher()
    except HTTPException as exc:
        issues.append(str(exc.detail))

    return {
        "partner_id": settings.SHOPEE_PARTNER_ID,
        "redirect_uri": redirect,
        "ready": len(issues) == 0,
        "issues": issues,
    }


@router.get("/auth-url")
async def get_shopee_auth_url(db: DBSession, response: Response, owner: str = Depends(require_admin)):
    """Gera URL oficial de autorização da Shopee com state protegido contra CSRF."""
    url, browser = await service.start_oauth(db, owner)
    is_https = bool(settings.SHOPEE_REDIRECT_URI and settings.SHOPEE_REDIRECT_URI.startswith("https://"))
    response.set_cookie(
        "shopee_oauth",
        browser,
        max_age=600,
        httponly=True,
        secure=is_https,
        samesite="lax",
        path="/api/v1/marketplaces/shopee",
    )
    return {"auth_url": url}


@router.post(
    "/oauth/callback",
    response_model=MarketplaceAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def shopee_oauth_callback(
    request: ShopeeOAuthCallbackRequest,
    db: DBSession,
    http_request: Request,
    response: Response,
    owner: str = Depends(require_admin),
):
    """Processa o código e shop_id retornados pela Shopee e cadastra a conta."""
    browser = http_request.cookies.get("shopee_oauth")
    result = await service.handle_oauth_callback(
        db,
        code=request.code,
        shop_id=request.shop_id,
        state=request.state,
        browser=browser,
        owner=owner,
    )
    response.delete_cookie("shopee_oauth", path="/api/v1/marketplaces/shopee")
    return result


@router.get("/categories")
async def list_shopee_categories(account_id: UUID, db: DBSession):
    """Lista as categorias ativas disponíveis para a loja Shopee."""
    return await service.list_categories(db, account_id)


@router.get("/categories/{category_id}/attributes")
async def get_shopee_category_attributes(category_id: int, account_id: UUID, db: DBSession):
    """Retorna os atributos obrigatórios e opcionais da categoria na Shopee."""
    return await service.get_category_attributes(db, account_id, category_id)


@router.post(
    "/publish",
    response_model=MarketplaceListingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def publish_to_shopee(
    request: PublishShopeeProductRequest,
    db: DBSession,
):
    """Publica um produto na Shopee com validação prévia de margens e custos da Fase 2."""
    return await service.publish_product(db, request)
