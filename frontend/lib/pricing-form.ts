import { z } from "zod";
import Decimal from "decimal.js";
const decimal = z.string().min(1, "Informe o valor real (zero quando aplicável).").refine(value => {
  try { return new Decimal(value).isFinite() && new Decimal(value).gte(0); } catch { return false; }
}, "Use um decimal não negativo com ponto.");
const optionalDecimal = z.union([z.literal(""), decimal]);
export const pricingInputSchema = z.object({
  marketplace_commission_percent: decimal,
  fixed_fee: decimal,
  fixed_fee_threshold: optionalDecimal,
  tax_percent: decimal,
  operating_cost_percent: decimal,
  fixed_cost: decimal,
  target_margin_percent: decimal,
  free_shipping_threshold: optionalDecimal,
  free_shipping_cost: optionalDecimal,
  rounding_rule: z.enum(["EXACT", "ENDS_90", "ENDS_99", "ROUND_INTEGER"]),
});
export const pricingFields = [
  ["marketplace_commission_percent", "Comissão (%)"], ["tax_percent", "Impostos (%)"],
  ["operating_cost_percent", "Operacional (%)"], ["target_margin_percent", "Margem alvo (%)"],
  ["fixed_fee", "Taxa fixa (R$)"], ["fixed_cost", "Custo fixo (R$)"],
  ["fixed_fee_threshold", "Taxa fixa abaixo de (opcional)"],
  ["free_shipping_threshold", "Frete a partir de (opcional)"], ["free_shipping_cost", "Custo real de frete (opcional)"],
] as const;
export const emptyPricing: z.infer<typeof pricingInputSchema> = {
  marketplace_commission_percent: "", fixed_fee: "", fixed_fee_threshold: "", tax_percent: "",
  operating_cost_percent: "", fixed_cost: "", target_margin_percent: "", free_shipping_threshold: "",
  free_shipping_cost: "", rounding_rule: "EXACT",
};
