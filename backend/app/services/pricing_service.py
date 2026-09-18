from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.pricing.engine import calculate_selling_price, RoundingRule
from app.repositories.pricing_repository import PricingRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.pricing import (
    PriceSimulationRequest,
    PriceSimulationResponse,
    PricingProfileCreate,
    PricingProfileResponse,
    PricingProfileUpdate,
    ProductChannelPriceResponse,
)


class PricingService:
    def __init__(self) -> None:
        self.repo = PricingRepository()
        self.product_repo = ProductRepository()

    def simulate(self, request: PriceSimulationRequest) -> PriceSimulationResponse:
        try:
            result = calculate_selling_price(
                cost_basis=request.cost_basis,
                marketplace_commission_percent=request.marketplace_commission_percent,
                fixed_fee=request.fixed_fee,
                fixed_fee_threshold=request.fixed_fee_threshold,
                tax_percent=request.tax_percent,
                operating_cost_percent=request.operating_cost_percent,
                fixed_cost=request.fixed_cost,
                target_margin_percent=request.target_margin_percent,
                free_shipping_threshold=request.free_shipping_threshold,
                free_shipping_cost=request.free_shipping_cost,
                rounding_rule=request.rounding_rule,
                manual_override_price=request.manual_override_price,
            )
            return PriceSimulationResponse(**result)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

    async def create_profile(
        self, session: AsyncSession, data: PricingProfileCreate
    ) -> PricingProfileResponse:
        profile = await self.repo.create_profile(session, data)
        return PricingProfileResponse.model_validate(profile)

    async def list_profiles(
        self, session: AsyncSession, active_only: bool = False
    ) -> list[PricingProfileResponse]:
        profiles = await self.repo.list_profiles(session, active_only=active_only)
        return [PricingProfileResponse.model_validate(p) for p in profiles]

    async def get_profile(
        self, session: AsyncSession, profile_id: UUID
    ) -> PricingProfileResponse:
        profile = await self.repo.get_profile_by_id(session, profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Perfil de precificação {profile_id} não encontrado.",
            )
        return PricingProfileResponse.model_validate(profile)

    async def update_profile(
        self, session: AsyncSession, profile_id: UUID, data: PricingProfileUpdate
    ) -> PricingProfileResponse:
        profile = await self.repo.update_profile(session, profile_id, data)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Perfil de precificação {profile_id} não encontrado.",
            )
        return PricingProfileResponse.model_validate(profile)

    async def delete_profile(self, session: AsyncSession, profile_id: UUID) -> None:
        deleted = await self.repo.delete_profile(session, profile_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Perfil de precificação {profile_id} não encontrado.",
            )

    async def calculate_for_product(
        self,
        session: AsyncSession,
        product_id: UUID,
        profile_id: UUID,
        manual_override_price: Decimal | None = None,
    ) -> ProductChannelPriceResponse:
        product = await self.product_repo.get_with_details(session, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto {product_id} não encontrado.",
            )

        # Determinar custo base a partir dos dados do fornecedor
        cost_basis = None
        for sup in product.supplier_data:
            if sup.is_active and sup.current_cost is not None:
                cost_basis = sup.current_cost
                break

        if cost_basis is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O produto não possui custo base cadastrado em nenhum fornecedor ativo.",
            )

        profile = await self.repo.get_profile_by_id(session, profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Perfil de precificação {profile_id} não encontrado.",
            )

        try:
            calc = calculate_selling_price(
                cost_basis=cost_basis,
                marketplace_commission_percent=profile.marketplace_commission_percent,
                fixed_fee=profile.fixed_fee,
                fixed_fee_threshold=profile.fixed_fee_threshold,
                tax_percent=profile.tax_percent,
                operating_cost_percent=profile.operating_cost_percent,
                fixed_cost=profile.fixed_cost,
                target_margin_percent=profile.target_margin_percent,
                free_shipping_threshold=profile.free_shipping_threshold,
                free_shipping_cost=profile.free_shipping_cost,
                rounding_rule=profile.rounding_rule,
                manual_override_price=manual_override_price,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        saved = await self.repo.upsert_product_price(
            session=session,
            product_id=product_id,
            profile_id=profile_id,
            calculated_data={
                "calculated_price": calc["suggested_price"],
                "cost_basis": calc["cost_basis"],
                "channel_commission": calc["marketplace_commission"],
                "taxes": calc["taxes"],
                "operating_costs": calc["operating_costs"],
                "shipping_cost": calc["shipping_cost"],
                "fixed_fee": calc["fixed_fee"],
                "net_margin_value": calc["net_margin_value"],
                "net_margin_percent": calc["net_margin_percent"],
                "breakdown": calc["breakdown"],
                "is_manual_override": manual_override_price is not None,
                "manual_price": manual_override_price,
            },
        )

        return ProductChannelPriceResponse(
            id=saved.id,
            product_id=saved.product_id,
            pricing_profile_id=saved.pricing_profile_id,
            profile_name=profile.name,
            channel=profile.channel,
            calculated_price=saved.calculated_price,
            cost_basis=saved.cost_basis,
            channel_commission=saved.channel_commission,
            taxes=saved.taxes,
            operating_costs=saved.operating_costs,
            shipping_cost=saved.shipping_cost,
            fixed_fee=saved.fixed_fee,
            net_margin_value=saved.net_margin_value,
            net_margin_percent=saved.net_margin_percent,
            breakdown=saved.breakdown,
            is_manual_override=saved.is_manual_override,
            manual_price=saved.manual_price,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    async def get_product_prices(
        self, session: AsyncSession, product_id: UUID
    ) -> list[ProductChannelPriceResponse]:
        records = await self.repo.get_product_prices(session, product_id)
        output = []
        for r in records:
            output.append(
                ProductChannelPriceResponse(
                    id=r.id,
                    product_id=r.product_id,
                    pricing_profile_id=r.pricing_profile_id,
                    profile_name=r.profile.name if r.profile else None,
                    channel=r.profile.channel if r.profile else None,
                    calculated_price=r.calculated_price,
                    cost_basis=r.cost_basis,
                    channel_commission=r.channel_commission,
                    taxes=r.taxes,
                    operating_costs=r.operating_costs,
                    shipping_cost=r.shipping_cost,
                    fixed_fee=r.fixed_fee,
                    net_margin_value=r.net_margin_value,
                    net_margin_percent=r.net_margin_percent,
                    breakdown=r.breakdown,
                    is_manual_override=r.is_manual_override,
                    manual_price=r.manual_price,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
        return output

    async def delete_product_price(
        self, session: AsyncSession, product_id: UUID, profile_id: UUID
    ) -> None:
        deleted = await self.repo.delete_product_price(session, product_id, profile_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Precificação não encontrada para o produto e perfil especificados.",
            )
