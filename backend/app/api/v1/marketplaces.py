from typing import Optional
from uuid import UUID
from fastapi import APIRouter, status, Query, Depends, Request, Response, HTTPException
from urllib.parse import urlsplit
from app.api.deps import DBSession
from app.core.security import require_admin
from app.core.config import settings
from app.schemas.marketplace import (
    MarketplacesOverviewResponse,
    MarketplaceAccountResponse,
    OAuthCallbackRequest,
    CategoryPredictionItem,
    PublishProductRequest,
    MarketplaceListingResponse,
    MarketplaceListingListResponse,
    MercadoLivreConfigurationResponse,
    MarketplaceCredentialUpsert,
    MarketplaceCredentialResponse,
)
from app.services.mercadolivre_service import MercadoLivreService
from app.api.v1.shopee import router as shopee_router

router = APIRouter()
router.include_router(shopee_router)
service = MercadoLivreService()


@router.get("/mercadolivre/configuration", response_model=MercadoLivreConfigurationResponse)
async def mercadolivre_configuration(db: DBSession):
    """Authenticated diagnostics: public identifiers only, never credential values."""
    from app.core.tokens import cipher
    cred = await service.repo.get_platform_credential(db, "MERCADO_LIVRE") if db else None
    app_id = cred.app_id if cred and getattr(cred, "app_id", None) else service.client.app_id
    has_secret = bool(cred and getattr(cred, "app_secret_encrypted", None)) or bool(service.client.client_secret)
    redirect = cred.redirect_uri if cred and getattr(cred, "redirect_uri", None) else service.client.redirect_uri

    issues = []
    if not app_id or not app_id.isdigit():
        issues.append("Configure o App ID numérico da aplicação no menu Marketplaces.")
    if not has_secret:
        issues.append("Configure o Client Secret da aplicação no menu Marketplaces.")
    try:
        parts = urlsplit(redirect or "")
        redirect_valid = parts.scheme == "https" and parts.hostname and parts.path == "/marketplaces/callback" and not (parts.query or parts.fragment or parts.username or parts.password)
    except ValueError:
        redirect_valid = False
    if not redirect_valid:
        issues.append("Configure MERCADOLIVRE_REDIRECT_URI com HTTPS e o caminho /marketplaces/callback, igual ao painel do Mercado Livre.")
    try:
        cipher()
    except HTTPException as exc:
        issues.append(str(exc.detail))
    return {"app_id": app_id, "redirect_uri": redirect, "ready": not issues, "issues": issues}


@router.get("/overview", response_model=MarketplacesOverviewResponse)
async def get_marketplaces_overview(db: DBSession):
    """Retorna o panorama real das integrações de marketplaces e contas conectadas."""
    return await service.get_overview(db)


@router.get("/accounts", response_model=list[MarketplaceAccountResponse])
async def list_marketplace_accounts(
    db: DBSession, marketplace: Optional[str] = None
):
    """Lista as contas conectadas de marketplaces."""
    accounts = await service.repo.list_accounts(db, marketplace=marketplace)
    return [MarketplaceAccountResponse.model_validate(a) for a in accounts]


@router.delete("/accounts/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(id: UUID, db: DBSession):
    """Desconecta uma conta de marketplace."""
    await service.delete_account(db, id)


@router.get("/mercadolivre/auth-url")
async def get_mercadolivre_auth_url(db: DBSession, response: Response, owner: str = Depends(require_admin)):
    url, browser = await service.start_oauth(db, owner)
    response.set_cookie("ml_oauth", browser, max_age=600, httponly=True,
                        secure=bool(settings.MERCADOLIVRE_REDIRECT_URI and settings.MERCADOLIVRE_REDIRECT_URI.startswith("https://")),
                        samesite="lax", path="/api/v1/marketplaces/mercadolivre")
    return {"auth_url": url}


@router.post(
    "/mercadolivre/oauth/callback",
    response_model=MarketplaceAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def mercadolivre_oauth_callback(
    request: OAuthCallbackRequest, db: DBSession, http_request: Request, response: Response, owner: str = Depends(require_admin)
):
    """Processa o código recebido do Mercado Livre e conclui a autenticação da conta."""
    result = await service.handle_oauth_callback(db, request.code, request.state, http_request.cookies.get("ml_oauth"), owner)
    response.delete_cookie("ml_oauth", path="/api/v1/marketplaces/mercadolivre")
    return result


@router.get(
    "/mercadolivre/categories/predict",
    response_model=list[CategoryPredictionItem],
)
async def predict_category(db: DBSession, account_id: UUID, q: str = Query(..., min_length=2, max_length=60)):
    """Sugere categorias no Mercado Livre a partir do título do produto."""
    return await service.predict_category(db, account_id, q)


@router.post(
    "/mercadolivre/publish",
    response_model=MarketplaceListingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def publish_to_mercadolivre(
    request: PublishProductRequest, db: DBSession
):
    """Publica um produto no Mercado Livre com validação prévia e preço da Fase 2."""
    return await service.publish_product(db, request)


@router.get("/listings", response_model=MarketplaceListingListResponse)
async def list_marketplace_listings(
    db: DBSession,
    product_id: Optional[UUID] = None,
    account_id: Optional[UUID] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Lista anúncios e publicações nos marketplaces."""
    return await service.list_listings(
        db, product_id, account_id, status, skip, limit
    )


@router.get("/mercadolivre/categories/{category_id}/attributes")
async def category_attributes(category_id: str, account_id: UUID, db: DBSession):
    import re
    if not re.fullmatch(r"MLB[0-9]+", category_id):
        raise HTTPException(422, "Categoria inválida.")
    return await service.category_attributes(db, account_id, category_id)


@router.post("/listings/{listing_id}/reconcile", response_model=MarketplaceListingResponse)
async def reconcile_listing(listing_id: UUID, db: DBSession, external_id: str | None = Query(None, pattern=r"^MLB[0-9]+$")):
    return await service.reconcile(db, listing_id, external_id)


@router.get("/credentials", response_model=list[MarketplaceCredentialResponse])
async def list_marketplace_credentials(db: DBSession, user: str = Depends(require_admin)):
    """Lista as credenciais de plataformas de marketplaces configuradas (sem expor segredos)."""
    return await service.list_credentials_safe(db)


@router.get("/credentials/{marketplace}", response_model=MarketplaceCredentialResponse)
async def get_marketplace_credential(marketplace: str, db: DBSession, user: str = Depends(require_admin)):
    """Retorna o status de configuração de um marketplace específico (sem expor segredos)."""
    return await service.get_credential_safe(db, marketplace)


@router.put("/credentials/{marketplace}", response_model=MarketplaceCredentialResponse)
async def upsert_marketplace_credential(
    marketplace: str,
    payload: MarketplaceCredentialUpsert,
    db: DBSession,
    user: str = Depends(require_admin),
):
    """Salva/atualiza credenciais de um marketplace, encriptando a chave no banco de dados."""
    return await service.save_credential(db, marketplace, payload)


@router.delete("/credentials/{marketplace}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marketplace_credential(
    marketplace: str,
    db: DBSession,
    user: str = Depends(require_admin),
):
    """Remove as credenciais salvas no banco de dados para um marketplace."""
    await service.delete_credential(db, marketplace)
