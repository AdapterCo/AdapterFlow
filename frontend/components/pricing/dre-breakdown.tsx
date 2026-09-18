import React from "react";
import { DREBreakdown } from "@/types";
import { TrendingUp, DollarSign, Percent, AlertCircle } from "lucide-react";

interface DREBreakdownProps {
  dre: DREBreakdown;
  suggestedPrice: string;
}

export function DREBreakdownCard({ dre, suggestedPrice }: DREBreakdownProps) {
  const priceNum = parseFloat(suggestedPrice) || 0;
  const netProfitNum = parseFloat(dre.net_profit_value) || 0;
  const isProfitable = netProfitNum > 0;
  const isLoss = netProfitNum < 0;

  const commissionNum = parseFloat(dre.marketplace_commission_value) || 0;
  const taxNum = parseFloat(dre.tax_value) || 0;
  const operatingNum =
    (parseFloat(dre.operating_cost_value) || 0) +
    (parseFloat(dre.fixed_cost) || 0);
  const fixedFeeNum = parseFloat(dre.marketplace_fixed_fee) || 0;
  const shippingNum = parseFloat(dre.shipping_cost) || 0;
  const costBasisNum = parseFloat(dre.cost_basis) || 0;

  const costPct = priceNum > 0 ? (costBasisNum / priceNum) * 100 : 0;
  const commPct = priceNum > 0 ? (commissionNum / priceNum) * 100 : 0;
  const taxPct = priceNum > 0 ? (taxNum / priceNum) * 100 : 0;
  const feePct = priceNum > 0 ? ((fixedFeeNum + shippingNum) / priceNum) * 100 : 0;
  const opPct = priceNum > 0 ? (operatingNum / priceNum) * 100 : 0;
  const profitPct = parseFloat(dre.net_margin_percent) || 0;

  return (
    <div className="rounded-xl border bg-card p-6 shadow-xs space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b pb-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Preço de Venda Sugerido
          </span>
          <div className="text-3xl font-extrabold text-foreground flex items-baseline gap-1">
            <span className="text-xl font-medium text-muted-foreground">R$</span>
            {parseFloat(suggestedPrice).toLocaleString("pt-BR", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Margem Líquida Real
            </span>
            <div
              className={`text-2xl font-bold flex items-center justify-end gap-1 ${
                isProfitable
                  ? "text-emerald-600 dark:text-emerald-400"
                  : isLoss
                  ? "text-rose-600 dark:text-rose-400"
                  : "text-amber-500"
              }`}
            >
              {parseFloat(dre.net_margin_percent).toFixed(2)}%
            </div>
          </div>

          <div className="text-right pl-4 border-l">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Markup Efetivo
            </span>
            <div className="text-2xl font-bold text-foreground">
              {parseFloat(dre.effective_markup).toFixed(2)}x
            </div>
          </div>
        </div>
      </div>

      {/* Visual Composition Bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-muted-foreground font-medium">
          <span>Composição do Preço</span>
          <span>100% da Receita Bruta</span>
        </div>
        <div className="h-3 w-full rounded-full overflow-hidden flex bg-muted/40 border">
          <div
            title={`Custo: ${costPct.toFixed(1)}%`}
            style={{ width: `${Math.max(0, Math.min(100, costPct))}%` }}
            className="bg-slate-400 dark:bg-slate-600"
          />
          <div
            title={`Comissão: ${commPct.toFixed(1)}%`}
            style={{ width: `${Math.max(0, Math.min(100, commPct))}%` }}
            className="bg-amber-400"
          />
          <div
            title={`Impostos: ${taxPct.toFixed(1)}%`}
            style={{ width: `${Math.max(0, Math.min(100, taxPct))}%` }}
            className="bg-blue-400"
          />
          <div
            title={`Taxas & Frete: ${feePct.toFixed(1)}%`}
            style={{ width: `${Math.max(0, Math.min(100, feePct))}%` }}
            className="bg-orange-400"
          />
          <div
            title={`Operacional: ${opPct.toFixed(1)}%`}
            style={{ width: `${Math.max(0, Math.min(100, opPct))}%` }}
            className="bg-purple-400"
          />
          {profitPct > 0 && (
            <div
              title={`Lucro: ${profitPct.toFixed(1)}%`}
              style={{ width: `${Math.max(0, Math.min(100, profitPct))}%` }}
              className="bg-emerald-500"
            />
          )}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground pt-1">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-slate-400" /> Custo Base
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400" /> Comissão
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-blue-400" /> Impostos
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-orange-400" /> Frete & Taxa Fixa
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-purple-400" /> Custos Operacionais
          </div>
          <div className="flex items-center gap-1.5 font-medium text-emerald-600 dark:text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Lucro Líquido
          </div>
        </div>
      </div>

      {/* DRE Unitária Detalhada */}
      <div className="border rounded-lg overflow-hidden divide-y divide-border text-sm">
        <div className="flex justify-between items-center px-4 py-2.5 bg-muted/40 font-semibold">
          <span>Receita Bruta (Preço de Venda)</span>
          <span className="font-mono text-base">R$ {parseFloat(dre.gross_revenue).toFixed(2)}</span>
        </div>

        <div className="flex justify-between items-center px-4 py-2 text-muted-foreground">
          <span className="pl-2">(-) Custo da Mercadoria (CMV / Custo Base)</span>
          <span className="font-mono text-foreground font-medium">
            R$ {parseFloat(dre.cost_basis).toFixed(2)}
          </span>
        </div>

        <div className="flex justify-between items-center px-4 py-2 text-muted-foreground">
          <span className="pl-2">
            (-) Comissão do Canal ({parseFloat(dre.marketplace_commission_percent).toFixed(1)}%)
          </span>
          <span className="font-mono text-foreground font-medium">
            R$ {parseFloat(dre.marketplace_commission_value).toFixed(2)}
          </span>
        </div>

        {fixedFeeNum > 0 && (
          <div className="flex justify-between items-center px-4 py-2 text-muted-foreground">
            <span className="pl-2">(-) Taxa Fixa do Marketplace</span>
            <span className="font-mono text-foreground font-medium">
              R$ {parseFloat(dre.marketplace_fixed_fee).toFixed(2)}
            </span>
          </div>
        )}

        {shippingNum > 0 && (
          <div className="flex justify-between items-center px-4 py-2 text-muted-foreground">
            <span className="pl-2">(-) Custo de Frete do Vendedor</span>
            <span className="font-mono text-foreground font-medium">
              R$ {parseFloat(dre.shipping_cost).toFixed(2)}
            </span>
          </div>
        )}

        <div className="flex justify-between items-center px-4 py-2 text-muted-foreground">
          <span className="pl-2">(-) Impostos ({parseFloat(dre.tax_percent).toFixed(1)}%)</span>
          <span className="font-mono text-foreground font-medium">
            R$ {parseFloat(dre.tax_value).toFixed(2)}
          </span>
        </div>

        <div className="flex justify-between items-center px-4 py-2 text-muted-foreground">
          <span className="pl-2">
            (-) Custo Operacional ({parseFloat(dre.operating_cost_percent).toFixed(1)}% + Embalagem R${" "}
            {parseFloat(dre.fixed_cost).toFixed(2)})
          </span>
          <span className="font-mono text-foreground font-medium">
            R$ {operatingNum.toFixed(2)}
          </span>
        </div>

        <div className="flex justify-between items-center px-4 py-2 bg-muted/20 text-muted-foreground font-medium">
          <span>Total de Deduções e Custos</span>
          <span className="font-mono text-foreground">
            R$ {parseFloat(dre.total_deductions).toFixed(2)}
          </span>
        </div>

        <div
          className={`flex justify-between items-center px-4 py-3 font-bold text-base ${
            isProfitable
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
              : isLoss
              ? "bg-rose-500/10 text-rose-700 dark:text-rose-400"
              : "bg-muted"
          }`}
        >
          <span className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Lucro Líquido Unitário Real
          </span>
          <span className="font-mono text-lg">
            R$ {parseFloat(dre.net_profit_value).toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
