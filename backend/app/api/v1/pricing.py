from uuid import UUID
from fastapi import APIRouter, status
from app.api.deps import DBSession
from app.schemas.pricing import (
    PriceSimulationRequest,
    PriceSimulationResponse,
    PricingProfileCreate,
    PricingProfileResponse,
    PricingProfileUpdate,
    ProductChannelPriceResponse,
    ProductPricingCalculateRequest,
)
from app.services.pricing_service import PricingService

router = APIRouter()
service = PricingService()


@router.post("/simulate", response_model=PriceSimulationResponse)
def simulate_price(request: PriceSimulationRequest):
    """Simula o cálculo de preço e gera a DRE completa sem persistir dados."""
    return service.simulate(request)


@router.get("/profiles", response_model=list[PricingProfileResponse])
async def list_profiles(db: DBSession, active_only: bool = False):
    """Lista todos os perfis de canais/taxas de precificação."""
    return await service.list_profiles(db, active_only=active_only)


@router.post(
    "/profiles",
    response_model=PricingProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(request: PricingProfileCreate, db: DBSession):
    """Cria um novo perfil de canal com regras de precificação."""
    return await service.create_profile(db, request)


@router.get("/profiles/{id}", response_model=PricingProfileResponse)
async def get_profile(id: UUID, db: DBSession):
    """Obtém detalhes de um perfil de precificação."""
    return await service.get_profile(db, id)


@router.put("/profiles/{id}", response_model=PricingProfileResponse)
async def update_profile(id: UUID, request: PricingProfileUpdate, db: DBSession):
    """Atualiza as taxas ou regras de um perfil de precificação."""
    return await service.update_profile(db, id, request)


@router.delete("/profiles/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(id: UUID, db: DBSession):
    """Remove um perfil de precificação."""
    await service.delete_profile(db, id)


@router.get(
    "/products/{product_id}",
    response_model=list[ProductChannelPriceResponse],
)
async def get_product_prices(product_id: UUID, db: DBSession):
    """Retorna todas as precificações calculadas para os canais de um produto."""
    return await service.get_product_prices(db, product_id)


@router.post(
    "/products/{product_id}/calculate",
    response_model=ProductChannelPriceResponse,
)
async def calculate_product_price(
    product_id: UUID, request: ProductPricingCalculateRequest, db: DBSession
):
    """Calcula e persiste o preço de venda e a DRE de um produto para um perfil de canal."""
    return await service.calculate_for_product(
        session=db,
        product_id=product_id,
        profile_id=request.pricing_profile_id,
        manual_override_price=request.manual_override_price,
    )


@router.delete(
    "/products/{product_id}/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product_price(product_id: UUID, profile_id: UUID, db: DBSession):
    """Remove a precificação de um canal específico para o produto."""
    await service.delete_product_price(db, product_id, profile_id)
