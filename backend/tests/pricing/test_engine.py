from decimal import Decimal
import pytest

from app.pricing.engine import (
    RoundingRule,
    apply_rounding_rule,
    calculate_selling_price,
    generate_dre,
    round_cents,
)


def test_rounding_rules():
    # EXACT
    assert apply_rounding_rule(Decimal("45.321"), RoundingRule.EXACT) == Decimal("45.32")
    assert apply_rounding_rule(Decimal("45.326"), RoundingRule.EXACT) == Decimal("45.33")

    # ENDS_90
    assert apply_rounding_rule(Decimal("45.12"), RoundingRule.ENDS_90) == Decimal("45.90")
    assert apply_rounding_rule(Decimal("45.90"), RoundingRule.ENDS_90) == Decimal("45.90")
    assert apply_rounding_rule(Decimal("45.91"), RoundingRule.ENDS_90) == Decimal("46.90")

    # ENDS_99
    assert apply_rounding_rule(Decimal("45.12"), RoundingRule.ENDS_99) == Decimal("45.99")
    assert apply_rounding_rule(Decimal("45.99"), RoundingRule.ENDS_99) == Decimal("45.99")

    # ROUND_INTEGER
    assert apply_rounding_rule(Decimal("45.00"), RoundingRule.ROUND_INTEGER) == Decimal("45.00")
    assert apply_rounding_rule(Decimal("45.01"), RoundingRule.ROUND_INTEGER) == Decimal("46.00")


def test_simple_pricing_margin():
    # Custo 80.00, Margem pretendida 20.00%, sem comissões ou impostos
    # PV = 80 / (1 - 0.20) = 80 / 0.80 = 100.00
    res = calculate_selling_price(
        cost_basis=Decimal("80.00"),
        target_margin_percent=Decimal("20.00"),
        rounding_rule=RoundingRule.EXACT,
    )

    assert res["suggested_price"] == Decimal("100.00")
    assert res["net_margin_value"] == Decimal("20.00")
    assert res["net_margin_percent"] == Decimal("20.0000")
    assert res["breakdown"]["gross_revenue"] == "100.00"
    assert res["breakdown"]["cost_basis"] == "80.00"
    assert res["breakdown"]["net_profit_value"] == "20.00"
    assert res["breakdown"]["effective_markup"] == "1.25"


def test_marketplace_pricing_with_fixed_fee():
    # Item barato (< R$ 79)
    # Custo 20.00
    # Comissão: 14%
    # Imposto: 6%
    # Operacional: 3%
    # Margem pretendida: 15%
    # Custo fixo embalagem: R$ 2.00
    # Taxa fixa de marketplace: R$ 6.00 (limiar R$ 79)
    # Total de custos fixos: 20 + 2 + 6 = 28.00
    # Soma de taxas percentuais: 14 + 6 + 3 + 15 = 38% -> divisor = 0.62
    # Preço teórico = 28.00 / 0.62 = 45.16129...
    # Com ENDS_90 -> 45.90
    res = calculate_selling_price(
        cost_basis=Decimal("20.00"),
        marketplace_commission_percent=Decimal("14.00"),
        tax_percent=Decimal("6.00"),
        operating_cost_percent=Decimal("3.00"),
        target_margin_percent=Decimal("15.00"),
        fixed_cost=Decimal("2.00"),
        fixed_fee=Decimal("6.00"),
        fixed_fee_threshold=Decimal("79.00"),
        free_shipping_threshold=Decimal("79.00"),
        free_shipping_cost=Decimal("18.00"),
        rounding_rule=RoundingRule.ENDS_90,
    )

    assert res["suggested_price"] == Decimal("45.90")
    assert res["fixed_fee"] == Decimal("6.00")
    assert res["shipping_cost"] == Decimal("0.00")

    # DRE do preço adotado de 45.90:
    # Comissão (14%): 45.90 * 0.14 = 6.426 -> 6.43
    # Imposto (6%): 45.90 * 0.06 = 2.754 -> 2.75
    # Operacional (3% + 2.00 fixo): (45.90 * 0.03 = 1.377 -> 1.38) + 2.00 = 3.38
    # Taxa fixa: 6.00
    # Custo: 20.00
    # Total deduções: 20.00 + 6.43 + 2.75 + 3.38 + 6.00 = 38.56
    # Lucro Líquido: 45.90 - 38.56 = 7.34
    assert res["marketplace_commission"] == Decimal("6.43")
    assert res["taxes"] == Decimal("2.75")
    assert res["operating_costs"] == Decimal("3.38")
    assert res["net_margin_value"] == Decimal("7.34")
    assert res["breakdown"]["total_deductions"] == "38.56"
    assert res["breakdown"]["net_profit_value"] == "7.34"


def test_free_shipping_threshold_trigger():
    # Produto de alto valor onde o frete grátis deve ser ativado
    # Custo 100.00
    # Comissão: 14%, Imposto: 6%, Operacional: 3%, Margem: 15% -> divisor = 0.62
    # Custo fixo embalagem: R$ 3.00
    # Frete grátis: R$ 18.00 (threshold R$ 79.00)
    # Taxa fixa: R$ 6.00 (threshold R$ 79.00, então deve ser 0)
    # Total de custos fixos = 100.00 + 3.00 + 18.00 = 121.00
    # Preço teórico = 121.00 / 0.62 = 195.1612...
    # Com ENDS_90 -> 195.90
    res = calculate_selling_price(
        cost_basis=Decimal("100.00"),
        marketplace_commission_percent=Decimal("14.00"),
        tax_percent=Decimal("6.00"),
        operating_cost_percent=Decimal("3.00"),
        target_margin_percent=Decimal("15.00"),
        fixed_cost=Decimal("3.00"),
        fixed_fee=Decimal("6.00"),
        fixed_fee_threshold=Decimal("79.00"),
        free_shipping_threshold=Decimal("79.00"),
        free_shipping_cost=Decimal("18.00"),
        rounding_rule=RoundingRule.ENDS_90,
    )

    assert res["suggested_price"] == Decimal("195.90")
    assert res["fixed_fee"] == Decimal("0.00")
    assert res["shipping_cost"] == Decimal("18.00")
    assert res["net_margin_value"] > Decimal("0.00")


def test_manual_override_price():
    # Produto custa 50.00, vendedor força preço de 89.90
    res = calculate_selling_price(
        cost_basis=Decimal("50.00"),
        marketplace_commission_percent=Decimal("15.00"),
        tax_percent=Decimal("5.00"),
        operating_cost_percent=Decimal("2.00"),
        fixed_cost=Decimal("3.00"),
        fixed_fee=Decimal("6.00"),
        fixed_fee_threshold=Decimal("79.00"),
        free_shipping_threshold=Decimal("79.00"),
        free_shipping_cost=Decimal("15.00"),
        manual_override_price=Decimal("89.90"),
    )

    assert res["suggested_price"] == Decimal("89.90")
    # Como 89.90 >= 79.00, taxa fixa é 0 e frete é 15.00
    assert res["fixed_fee"] == Decimal("0.00")
    assert res["shipping_cost"] == Decimal("15.00")
    assert Decimal(res["breakdown"]["gross_revenue"]) == Decimal("89.90")


def test_invalid_parameters():
    # Custo negativo
    with pytest.raises(ValueError, match="não pode ser negativo"):
        calculate_selling_price(cost_basis=Decimal("-10.00"))

    # Taxas somando >= 100%
    with pytest.raises(ValueError, match="menor que 100%"):
        calculate_selling_price(
            cost_basis=Decimal("50.00"),
            marketplace_commission_percent=Decimal("40.00"),
            tax_percent=Decimal("20.00"),
            operating_cost_percent=Decimal("20.00"),
            target_margin_percent=Decimal("25.00"),  # Soma = 105%
        )

    # Preço manual inválido
    with pytest.raises(ValueError, match="maior que zero"):
        calculate_selling_price(
            cost_basis=Decimal("50.00"),
            manual_override_price=Decimal("0.00"),
        )
