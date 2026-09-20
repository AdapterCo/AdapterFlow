"""Motor Matemático Puro de Precificação para E-commerce e Marketplaces.

Todas as operações usam estritamente Decimal para evitar erros de ponto flutuante.
NUNCA utilizar float.
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from enum import Enum
from typing import TypedDict


class RoundingRule(str, Enum):
    EXACT = "EXACT"
    ENDS_90 = "ENDS_90"
    ENDS_99 = "ENDS_99"
    ROUND_INTEGER = "ROUND_INTEGER"


class DREBreakdown(TypedDict):
    gross_revenue: str
    cost_basis: str
    marketplace_commission_percent: str
    marketplace_commission_value: str
    marketplace_fixed_fee: str
    tax_percent: str
    tax_value: str
    operating_cost_percent: str
    operating_cost_value: str
    fixed_cost: str
    shipping_cost: str
    total_deductions: str
    net_profit_value: str
    net_margin_percent: str
    effective_markup: str


class PricingEngineResult(TypedDict):
    suggested_price: Decimal
    cost_basis: Decimal
    marketplace_commission: Decimal
    taxes: Decimal
    operating_costs: Decimal
    shipping_cost: Decimal
    fixed_fee: Decimal
    net_margin_value: Decimal
    net_margin_percent: Decimal
    breakdown: DREBreakdown


def to_decimal(value: int | str | Decimal | None, default: str = "0.00") -> Decimal:
    """Converte com segurança qualquer valor para Decimal."""
    if value is None:
        return Decimal(default)
    if isinstance(value, float):
        raise ValueError("Valores monetários devem ser Decimal ou texto decimal.")
    result = value if isinstance(value, Decimal) else Decimal(str(value))
    if not result.is_finite():
        raise ValueError("O valor deve ser finito.")
    return result


def round_cents(value: Decimal) -> Decimal:
    """Arredonda para exatamente 2 casas decimais usando ROUND_HALF_UP."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply_rounding_rule(raw_price: Decimal, rule: RoundingRule | str) -> Decimal:
    """
    Aplica regra de arredondamento comercial ao preço calculado:
    - EXACT: Apenas 2 casas decimais ROUND_HALF_UP
    - ENDS_90: Ajusta os centavos para .90 (garante cobertura de margem)
    - ENDS_99: Ajusta os centavos para .99
    - ROUND_INTEGER: Arredonda para cima no inteiro .00
    """
    if isinstance(rule, str):
        try:
            rule = RoundingRule(rule)
        except ValueError as exc:
            raise ValueError("Regra de arredondamento inválida.") from exc

    if rule == RoundingRule.EXACT:
        return round_cents(raw_price)

    integer_part = Decimal(int(raw_price))
    cents = raw_price - integer_part

    if rule == RoundingRule.ENDS_90:
        target = integer_part + Decimal("0.90")
        if target < raw_price:
            target += Decimal("1.00")
        return target

    if rule == RoundingRule.ENDS_99:
        target = integer_part + Decimal("0.99")
        if target < raw_price:
            target += Decimal("1.00")
        return target

    if rule == RoundingRule.ROUND_INTEGER:
        if cents > Decimal("0.00"):
            return integer_part + Decimal("1.00")
        return integer_part

    return raw_price


def generate_dre(
    sale_price: Decimal,
    cost_basis: Decimal,
    commission_percent: Decimal,
    tax_percent: Decimal,
    operating_percent: Decimal,
    fixed_cost: Decimal,
    fixed_fee: Decimal,
    shipping_cost: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, DREBreakdown]:
    """
    Gera a DRE unitária a partir do preço de venda final adotado.
    Retorna os componentes monetários e o dicionário formatado de DRE.
    """
    commission_val = round_cents(sale_price * (commission_percent / Decimal("100")))
    tax_val = round_cents(sale_price * (tax_percent / Decimal("100")))
    operating_val = round_cents(sale_price * (operating_percent / Decimal("100")))
    fixed_cost_val = round_cents(fixed_cost)
    fixed_fee_val = round_cents(fixed_fee)
    shipping_val = round_cents(shipping_cost)
    cost_basis_val = round_cents(cost_basis)

    total_operating = operating_val + fixed_cost_val
    total_deductions = (
        cost_basis_val
        + commission_val
        + tax_val
        + total_operating
        + fixed_fee_val
        + shipping_val
    )

    net_profit = sale_price - total_deductions

    if sale_price > Decimal("0.00"):
        net_margin_pct = (net_profit / sale_price) * Decimal("100")
        net_margin_pct = net_margin_pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    else:
        net_margin_pct = Decimal("0.0000")

    if cost_basis_val > Decimal("0.00"):
        effective_markup = (sale_price / cost_basis_val).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        effective_markup = Decimal("0.00")

    breakdown: DREBreakdown = {
        "gross_revenue": f"{sale_price:.2f}",
        "cost_basis": f"{cost_basis_val:.2f}",
        "marketplace_commission_percent": f"{commission_percent:.2f}",
        "marketplace_commission_value": f"{commission_val:.2f}",
        "marketplace_fixed_fee": f"{fixed_fee_val:.2f}",
        "tax_percent": f"{tax_percent:.2f}",
        "tax_value": f"{tax_val:.2f}",
        "operating_cost_percent": f"{operating_percent:.2f}",
        "operating_cost_value": f"{operating_val:.2f}",
        "fixed_cost": f"{fixed_cost_val:.2f}",
        "shipping_cost": f"{shipping_val:.2f}",
        "total_deductions": f"{total_deductions:.2f}",
        "net_profit_value": f"{net_profit:.2f}",
        "net_margin_percent": f"{net_margin_pct:.2f}",
        "effective_markup": f"{effective_markup:.2f}",
    }

    return (
        commission_val,
        tax_val,
        total_operating,
        shipping_val,
        fixed_fee_val,
        net_profit,
        breakdown,
    )


def calculate_selling_price(
    cost_basis: Decimal | str,
    marketplace_commission_percent: Decimal | str = "0.0",
    fixed_fee: Decimal | str = "0.0",
    fixed_fee_threshold: Decimal | str | None = None,
    tax_percent: Decimal | str = "0.0",
    operating_cost_percent: Decimal | str = "0.0",
    fixed_cost: Decimal | str = "0.0",
    target_margin_percent: Decimal | str = "0.0",
    free_shipping_threshold: Decimal | str | None = None,
    free_shipping_cost: Decimal | str | None = None,
    rounding_rule: RoundingRule | str = RoundingRule.EXACT,
    manual_override_price: Decimal | str | None = None,
) -> PricingEngineResult:
    """
    Calcula o preço de venda e a DRE completa com suporte a:
    - Markup Divisor Real (baseado em margem sobre venda)
    - Limiares dinâmicos de frete grátis e taxas fixas
    - Arredondamento comercial
    - Preço manual de override (calculando a margem real resultante)
    """
    cost_basis = to_decimal(cost_basis)
    comm_pct = to_decimal(marketplace_commission_percent)
    fixed_fee_val = to_decimal(fixed_fee)
    fixed_fee_thresh = to_decimal(fixed_fee_threshold) if fixed_fee_threshold is not None else None
    tax_pct = to_decimal(tax_percent)
    op_pct = to_decimal(operating_cost_percent)
    fixed_cost_val = to_decimal(fixed_cost)
    target_margin = to_decimal(target_margin_percent)
    shipping_thresh = to_decimal(free_shipping_threshold) if free_shipping_threshold is not None else None
    shipping_val = to_decimal(free_shipping_cost) if free_shipping_cost is not None else Decimal("0.00")

    for amount in (comm_pct, tax_pct, op_pct, fixed_fee_val, fixed_cost_val, shipping_val):
        if amount < 0:
            raise ValueError("Taxas e custos não podem ser negativos.")
    if any(v is not None and v < 0 for v in (fixed_fee_thresh, shipping_thresh)):
        raise ValueError("Limiares não podem ser negativos.")
    if (free_shipping_threshold is None) != (free_shipping_cost is None):
        raise ValueError("Informe conjuntamente limiar e custo real do frete.")
    if target_margin < -100 or target_margin >= 100:
        raise ValueError("A margem deve ser maior ou igual a -100 e menor que 100%.")
    RoundingRule(rounding_rule)

    if cost_basis < Decimal("0.00"):
        raise ValueError("O custo base do produto não pode ser negativo.")

    # Se foi fornecido um preço manual, calculamos a DRE com base nele diretamente
    if manual_override_price is not None:
        final_price = round_cents(to_decimal(manual_override_price))
        if final_price <= Decimal("0.00"):
            raise ValueError("O preço manual deve ser maior que zero.")

        # Avaliar taxas aplicáveis com base no preço manual
        app_fixed_fee = fixed_fee_val
        if fixed_fee_thresh is not None and final_price >= fixed_fee_thresh:
            app_fixed_fee = Decimal("0.00")

        app_shipping = Decimal("0.00")
        if shipping_thresh is not None and final_price >= shipping_thresh:
            app_shipping = shipping_val

        (
            comm,
            tax,
            op,
            ship,
            fee,
            net_val,
            breakdown,
        ) = generate_dre(
            sale_price=final_price,
            cost_basis=cost_basis,
            commission_percent=comm_pct,
            tax_percent=tax_pct,
            operating_percent=op_pct,
            fixed_cost=fixed_cost_val,
            fixed_fee=app_fixed_fee,
            shipping_cost=app_shipping,
        )

        net_pct = (net_val / final_price) * Decimal("100") if final_price > 0 else Decimal("0.00")

        return {
            "suggested_price": final_price,
            "cost_basis": cost_basis,
            "marketplace_commission": comm,
            "taxes": tax,
            "operating_costs": op,
            "shipping_cost": ship,
            "fixed_fee": fee,
            "net_margin_value": net_val,
            "net_margin_percent": net_pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            "breakdown": breakdown,
        }

    # Verificação do divisor de margem percentual
    percent_sum = comm_pct + tax_pct + op_pct + target_margin
    if percent_sum >= Decimal("100.0"):
        raise ValueError(
            f"A soma das taxas percentuais e da margem ({percent_sum}%) deve ser estritamente menor que 100%."
        )

    divisor = (Decimal("100.0") - percent_sum) / Decimal("100.0")

    # Enumerate every interval induced by the two thresholds. A candidate must
    # satisfy its own interval and its cent-rounded DRE, not a previous candidate.
    boundaries = sorted({Decimal("0"), *[v for v in (fixed_fee_thresh, shipping_thresh) if v is not None]})
    candidates = []
    for index, lower in enumerate(boundaries):
        upper = boundaries[index + 1] if index + 1 < len(boundaries) else None
        fee = fixed_fee_val if fixed_fee_thresh is None or lower < fixed_fee_thresh else Decimal("0")
        shipping = shipping_val if shipping_thresh is not None and lower >= shipping_thresh else Decimal("0")
        raw = (cost_basis + fixed_cost_val + fee + shipping) / divisor
        candidate = apply_rounding_rule(max(raw, lower, Decimal("0.01")), rounding_rule)
        if candidate < lower:
            candidate = apply_rounding_rule(lower.quantize(Decimal("0.01"), rounding=ROUND_CEILING), rounding_rule)
        for _ in range(32):
            if upper is not None and candidate >= upper:
                break
            profit = generate_dre(candidate, cost_basis, comm_pct, tax_pct, op_pct, fixed_cost_val, fee, shipping)[5]
            shortfall = candidate * target_margin / Decimal("100") - profit
            if shortfall <= 0:
                candidates.append((candidate, fee, shipping))
                break
            increase = max(Decimal("0.01"), (shortfall / divisor).quantize(Decimal("0.01"), rounding=ROUND_CEILING))
            candidate = apply_rounding_rule(candidate + increase, rounding_rule)
    if not candidates:
        raise ValueError("Não existe preço válido nas faixas e margem informadas.")
    chosen_price, applied_fee, applied_shipping = min(candidates, key=lambda entry: entry[0])

    (
        comm,
        tax,
        op,
        ship,
        fee,
        net_val,
        breakdown,
    ) = generate_dre(
        sale_price=chosen_price,
        cost_basis=cost_basis,
        commission_percent=comm_pct,
        tax_percent=tax_pct,
        operating_percent=op_pct,
        fixed_cost=fixed_cost_val,
        fixed_fee=applied_fee,
        shipping_cost=applied_shipping,
    )

    net_pct = (net_val / chosen_price) * Decimal("100") if chosen_price > 0 else Decimal("0.00")

    return {
        "suggested_price": chosen_price,
        "cost_basis": cost_basis,
        "marketplace_commission": comm,
        "taxes": tax,
        "operating_costs": op,
        "shipping_cost": ship,
        "fixed_fee": fee,
        "net_margin_value": net_val,
        "net_margin_percent": net_pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        "breakdown": breakdown,
    }
