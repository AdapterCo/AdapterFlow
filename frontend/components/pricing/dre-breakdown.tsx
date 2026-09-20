import { DREBreakdown } from "@/types";
import { formatCurrency, formatDecimal } from "@/lib/utils";
export function DREBreakdownCard({ dre, suggestedPrice }: { dre: DREBreakdown; suggestedPrice: string }) {
  const rows: [string, string][] = [["Receita", suggestedPrice], ["Custo base", dre.cost_basis], ["Comissão", dre.marketplace_commission_value], ["Impostos", dre.tax_value], ["Operacional", dre.operating_cost_value], ["Custo fixo", dre.fixed_cost], ["Taxa fixa", dre.marketplace_fixed_fee], ["Frete", dre.shipping_cost], ["Deduções", dre.total_deductions], ["Lucro líquido", dre.net_profit_value]];
  return <div className="rounded border p-4 space-y-2"><h3 className="font-semibold">DRE unitária</h3><dl>{rows.map(([label, value]) => <div className="flex justify-between py-1" key={label}><dt>{label}</dt><dd>{formatCurrency(value)}</dd></div>)}</dl><p>Margem líquida: {formatDecimal(dre.net_margin_percent)}%</p><p>Markup: {formatDecimal(dre.effective_markup)}×</p></div>;
}
