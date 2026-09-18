from typing import Optional
from uuid import UUID
from fastapi import APIRouter, status, Query
from app.api.deps import DBSession
from app.schemas.marketplace import (
    MarketplacesOverviewResponse,
    MarketplaceAccountResponse,
    OAuthCallbackRequest,
    CategoryPredictionItem,
    PublishProductRequest,
    MarketplaceListingResponse,
    MarketplaceListingListResponse,
)
from app.services.mercadolivre_service import MercadoLivreService

router = APIRouter()
service = MercadoLivreService()


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
def get_mercadolivre_auth_url():
    """Gera a URL de autorização oficial do Mercado Livre para conectar uma conta."""
    url = service.client.get_authorization_url()
    return {"auth_url": url}


@router.post(
    "/mercadolivre/oauth/callback",
    response_model=MarketplaceAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def mercadolivre_oauth_callback(
    request: OAuthCallbackRequest, db: DBSession
):
    """Processa o código recebido do Mercado Livre e conclui a autenticação da conta."""
    return await service.handle_oauth_callback(db, request.code)


@router.get(
    "/mercadolivre/categories/predict",
    response_model=list[CategoryPredictionItem],
)
async def predict_category(q: str = Query(..., min_length=2)):
    """Sugere categorias no Mercado Livre a partir do título do produto."""
    return await service.predict_category(q)


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
    skip: int = 0,
    limit: int = 100,
):
    """Lista anúncios e publicações nos marketplaces."""
    return await service.list_listings(
        db, product_id, account_id, status, skip, limit
    )
