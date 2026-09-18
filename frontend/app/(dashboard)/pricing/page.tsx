"use client";

import React, { useState, useEffect } from "react";
import {
  usePricingProfiles,
  useDeletePricingProfile,
  useSimulatePrice,
} from "@/hooks/use-pricing";
import { PricingProfile, PriceSimulationRequest } from "@/types";
import { DREBreakdownCard } from "@/components/pricing/dre-breakdown";
import { ProfileDialog } from "@/components/pricing/profile-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Calculator,
  Layers,
  Plus,
  Edit2,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

export default function PricingPage() {
  const [activeTab, setActiveTab] = useState<"simulator" | "profiles">("simulator");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<PricingProfile | null>(null);

  const { data: profiles, isLoading: profilesLoading } = usePricingProfiles();
  const deleteMutation = useDeletePricingProfile();
  const simulateMutation = useSimulatePrice();

  // Estados do Simulador
  const [selectedProfileId, setSelectedProfileId] = useState<string>("custom");
  const [costBasis, setCostBasis] = useState<string>("35.00");
  const [commission, setCommission] = useState<string>("14.0");
  const [fixedFee, setFixedFee] = useState<string>("6.00");
  const [fixedFeeThreshold, setFixedFeeThreshold] = useState<string>("79.00");
  const [taxPercent, setTaxPercent] = useState<string>("6.0");
  const [operatingCost, setOperatingCost] = useState<string>("3.0");
  const [fixedCost, setFixedCost] = useState<string>("3.50");
  const [targetMargin, setTargetMargin] = useState<string>("15.0");
  const [freeShippingThreshold, setFreeShippingThreshold] = useState<string>("79.00");
  const [freeShippingCost, setFreeShippingCost] = useState<string>("18.00");
  const [roundingRule, setRoundingRule] = useState<string>("ENDS_90");
  const [manualPrice, setManualPrice] = useState<string>("");
  const [useManualPrice, setUseManualPrice] = useState<boolean>(false);

  // Quando seleciona um perfil no simulador, preenche as variáveis
  const handleProfileSelect = (profileId: string) => {
    setSelectedProfileId(profileId);
    if (profileId === "custom") return;

    const profile = profiles?.find((p) => p.id === profileId);
    if (profile) {
      setCommission(profile.marketplace_commission_percent || "0");
      setFixedFee(profile.fixed_fee || "0");
      setFixedFeeThreshold(profile.fixed_fee_threshold || "");
      setTaxPercent(profile.tax_percent || "0");
      setOperatingCost(profile.operating_cost_percent || "0");
      setFixedCost(profile.fixed_cost || "0");
      setTargetMargin(profile.target_margin_percent || "15.0");
      setFreeShippingThreshold(profile.free_shipping_threshold || "");
      setFreeShippingCost(profile.free_shipping_cost || "");
      setRoundingRule(profile.rounding_rule || "ENDS_90");
    }
  };

  // Dispara a simulação sempre que um parâmetro relevante mudar
  useEffect(() => {
    const costNum = parseFloat(costBasis);
    if (isNaN(costNum) || costNum < 0) return;

    const payload: PriceSimulationRequest = {
      cost_basis: costBasis,
      marketplace_commission_percent: commission || "0",
      fixed_fee: fixedFee || "0",
      fixed_fee_threshold: fixedFeeThreshold.trim() ? fixedFeeThreshold.trim() : null,
      tax_percent: taxPercent || "0",
      operating_cost_percent: operatingCost || "0",
      fixed_cost: fixedCost || "0",
      target_margin_percent: targetMargin || "0",
      free_shipping_threshold: freeShippingThreshold.trim() ? freeShippingThreshold.trim() : null,
      free_shipping_cost: freeShippingCost.trim() ? freeShippingCost.trim() : null,
      rounding_rule: roundingRule,
      manual_override_price: useManualPrice && manualPrice ? manualPrice : null,
    };

    simulateMutation.mutate(payload);
  }, [
    costBasis,
    commission,
    fixedFee,
    fixedFeeThreshold,
    taxPercent,
    operatingCost,
    fixedCost,
    targetMargin,
    freeShippingThreshold,
    freeShippingCost,
    roundingRule,
    useManualPrice,
    manualPrice,
  ]);

  const handleDeleteProfile = async (id: string, name: string) => {
    if (!confirm(`Deseja realmente remover o perfil "${name}"?`)) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Perfil removido com sucesso!");
    } catch (err: any) {
      toast.error(err.message || "Erro ao remover perfil.");
    }
  };

  const getChannelBadge = (channel: string) => {
    switch (channel) {
      case "MERCADO_LIVRE":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
      case "SHOPEE":
        return "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300";
      case "AMAZON":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300";
      case "TIKTOK":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300";
      default:
        return "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300";
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Motor de Precificação</h1>
          <p className="text-sm text-muted-foreground">
            Formação de preço por margem líquida real, cálculo de DRE e gestão de perfis de canais.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border bg-muted p-1">
            <button
              onClick={() => setActiveTab("simulator")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                activeTab === "simulator"
                  ? "bg-background text-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Calculator className="h-4 w-4" />
              Simulador Interativo
            </button>
            <button
              onClick={() => setActiveTab("profiles")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                activeTab === "profiles"
                  ? "bg-background text-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Layers className="h-4 w-4" />
              Perfis de Canais ({profiles?.length || 0})
            </button>
          </div>

          {activeTab === "profiles" && (
            <Button
              size="sm"
              onClick={() => {
                setEditingProfile(null);
                setDialogOpen(true);
              }}
            >
              <Plus className="h-4 w-4 mr-1.5" />
              Novo Perfil
            </Button>
          )}
        </div>
      </div>

      {/* TAB 1: SIMULADOR INTERATIVO */}
      {activeTab === "simulator" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Coluna Esquerda: Formulário de Parâmetros */}
          <div className="lg:col-span-6 space-y-6">
            <div className="rounded-xl border bg-card p-5 shadow-xs space-y-5">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="font-semibold text-base flex items-center gap-2">
                  <Calculator className="h-4 w-4 text-primary" />
                  Parâmetros de Precificação
                </h3>
                {selectedProfileId !== "custom" && (
                  <span className="text-xs text-muted-foreground">
                    Carregado do perfil
                  </span>
                )}
              </div>

              {/* Seletor de Perfil Modelo */}
              <div className="space-y-1.5">
                <Label htmlFor="profile_selector">Perfil Base do Canal</Label>
                <select
                  id="profile_selector"
                  value={selectedProfileId}
                  onChange={(e) => handleProfileSelect(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="custom">Personalizado (Manual)</option>
                  {profiles?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.channel})
                    </option>
                  ))}
                </select>
              </div>

              {/* Custo Base */}
              <div className="space-y-1.5 p-3 rounded-lg bg-primary/5 border border-primary/20">
                <div className="flex justify-between items-center">
                  <Label htmlFor="cost_basis" className="font-semibold text-foreground">
                    Custo de Aquisição do Produto (R$) *
                  </Label>
                  <span className="text-xs text-muted-foreground">CMV Unitário</span>
                </div>
                <Input
                  id="cost_basis"
                  type="number"
                  step="0.01"
                  value={costBasis}
                  onChange={(e) => setCostBasis(e.target.value)}
                  className="font-mono text-lg font-bold bg-background"
                />
              </div>

              {/* Grid de Taxas Principais */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label htmlFor="sim_margin">Margem Líquida Alvo (%)</Label>
                  <Input
                    id="sim_margin"
                    type="number"
                    step="0.01"
                    value={targetMargin}
                    onChange={(e) => setTargetMargin(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_comm">Comissão Canal (%)</Label>
                  <Input
                    id="sim_comm"
                    type="number"
                    step="0.01"
                    value={commission}
                    onChange={(e) => setCommission(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_tax">Impostos sobre Venda (%)</Label>
                  <Input
                    id="sim_tax"
                    type="number"
                    step="0.01"
                    value={taxPercent}
                    onChange={(e) => setTaxPercent(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_op">Custo Operacional (%)</Label>
                  <Input
                    id="sim_op"
                    type="number"
                    step="0.01"
                    value={operatingCost}
                    onChange={(e) => setOperatingCost(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_fixed_cost">Embalagem / Fixo (R$)</Label>
                  <Input
                    id="sim_fixed_cost"
                    type="number"
                    step="0.01"
                    value={fixedCost}
                    onChange={(e) => setFixedCost(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_rounding">Arredondamento</Label>
                  <select
                    id="sim_rounding"
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={roundingRule}
                    onChange={(e) => setRoundingRule(e.target.value)}
                  >
                    <option value="ENDS_90">Final .90 (R$ XX,90)</option>
                    <option value="ENDS_99">Final .99 (R$ XX,99)</option>
                    <option value="ROUND_INTEGER">Inteiro (R$ XX,00)</option>
                    <option value="EXACT">Exato (Centavos Naturais)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_fixed_fee">Taxa Fixa Canal (R$)</Label>
                  <Input
                    id="sim_fixed_fee"
                    type="number"
                    step="0.01"
                    value={fixedFee}
                    onChange={(e) => setFixedFee(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_fixed_thresh">Limiar Taxa Fixa (R$)</Label>
                  <Input
                    id="sim_fixed_thresh"
                    type="number"
                    step="0.01"
                    value={fixedFeeThreshold}
                    onChange={(e) => setFixedFeeThreshold(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_ship_thresh">Limiar Frete Grátis (R$)</Label>
                  <Input
                    id="sim_ship_thresh"
                    type="number"
                    step="0.01"
                    value={freeShippingThreshold}
                    onChange={(e) => setFreeShippingThreshold(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="sim_ship_cost">Custo Frete Grátis (R$)</Label>
                  <Input
                    id="sim_ship_cost"
                    type="number"
                    step="0.01"
                    value={freeShippingCost}
                    onChange={(e) => setFreeShippingCost(e.target.value)}
                  />
                </div>
              </div>

              {/* Seção de Override Manual */}
              <div className="pt-3 border-t space-y-3">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="use_manual"
                    checked={useManualPrice}
                    onChange={(e) => setUseManualPrice(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-primary"
                  />
                  <Label htmlFor="use_manual" className="cursor-pointer font-medium">
                    Testar Preço Manual de Venda (Simulação Reversa)
                  </Label>
                </div>

                {useManualPrice && (
                  <div className="space-y-1 pl-6">
                    <Label htmlFor="manual_price" className="text-xs text-muted-foreground">
                      Digite o preço que deseja cobrar para ver a margem resultante:
                    </Label>
                    <Input
                      id="manual_price"
                      type="number"
                      step="0.01"
                      placeholder="Ex: 89.90"
                      value={manualPrice}
                      onChange={(e) => setManualPrice(e.target.value)}
                      className="font-mono text-base"
                    />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Coluna Direita: Resultado em Tempo Real & DRE */}
          <div className="lg:col-span-6 space-y-4">
            {simulateMutation.isError && (
              <div className="rounded-xl border border-rose-300 bg-rose-50 dark:bg-rose-950/20 p-4 text-rose-800 dark:text-rose-300 flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-semibold">Erro no cálculo de precificação</p>
                  <p className="text-xs opacity-90 mt-1">
                    {(simulateMutation.error as any)?.message ||
                      "A soma das deduções percentuais ultrapassa 100% ou os parâmetros são inválidos."}
                  </p>
                </div>
              </div>
            )}

            {simulateMutation.data ? (
              <DREBreakdownCard
                dre={simulateMutation.data.breakdown}
                suggestedPrice={simulateMutation.data.suggested_price}
              />
            ) : simulateMutation.isPending ? (
              <div className="rounded-xl border bg-card p-12 text-center text-muted-foreground flex flex-col items-center justify-center space-y-3">
                <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm">Calculando viabilidade econômica...</p>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed bg-muted/20 p-12 text-center text-muted-foreground">
                Informe o custo do produto para calcular a precificação e a DRE.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: GESTÃO DE PERFIS */}
      {activeTab === "profiles" && (
        <div className="space-y-4">
          {profilesLoading ? (
            <div className="text-center py-12 text-muted-foreground">Carregando perfis...</div>
          ) : profiles && profiles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {profiles.map((profile) => (
                <div
                  key={profile.id}
                  className="rounded-xl border bg-card p-5 shadow-xs flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-2">
                    <div className="flex justify-between items-start">
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${getChannelBadge(
                          profile.channel
                        )}`}
                      >
                        {profile.channel}
                      </span>
                      {profile.is_default && (
                        <span className="text-[11px] font-medium text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" /> Padrão
                        </span>
                      )}
                    </div>

                    <div>
                      <h3 className="font-semibold text-base text-foreground">
                        {profile.name}
                      </h3>
                      {profile.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                          {profile.description}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t text-muted-foreground">
                      <div>
                        <span>Comissão:</span>{" "}
                        <strong className="text-foreground">
                          {profile.marketplace_commission_percent}%
                        </strong>
                      </div>
                      <div>
                        <span>Margem Alvo:</span>{" "}
                        <strong className="text-foreground">
                          {profile.target_margin_percent}%
                        </strong>
                      </div>
                      <div>
                        <span>Imposto:</span>{" "}
                        <strong className="text-foreground">
                          {profile.tax_percent}%
                        </strong>
                      </div>
                      <div>
                        <span>Taxa Fixa:</span>{" "}
                        <strong className="text-foreground">
                          R$ {profile.fixed_fee}
                        </strong>
                      </div>
                      <div>
                        <span>Frete Grátis:</span>{" "}
                        <strong className="text-foreground">
                          {profile.free_shipping_threshold
                            ? `R$ ${profile.free_shipping_threshold}`
                            : "N/A"}
                        </strong>
                      </div>
                      <div>
                        <span>Arredondamento:</span>{" "}
                        <strong className="text-foreground">
                          {profile.rounding_rule}
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        handleProfileSelect(profile.id);
                        setActiveTab("simulator");
                      }}
                    >
                      <Calculator className="h-3.5 w-3.5 mr-1" />
                      Simular
                    </Button>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => {
                          setEditingProfile(profile);
                          setDialogOpen(true);
                        }}
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-rose-500 hover:text-rose-600"
                        onClick={() =>
                          handleDeleteProfile(profile.id, profile.name)
                        }
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed bg-muted/20 p-12 text-center space-y-3">
              <Layers className="h-10 w-10 mx-auto text-muted-foreground" />
              <div className="space-y-1">
                <h3 className="font-semibold text-foreground">
                  Nenhum perfil de canal cadastrado
                </h3>
                <p className="text-sm text-muted-foreground">
                  Cadastre perfis de precificação para calcular automaticamente margens e preços para Mercado Livre, Shopee, Amazon e outros.
                </p>
              </div>
              <Button
                onClick={() => {
                  setEditingProfile(null);
                  setDialogOpen(true);
                }}
              >
                <Plus className="h-4 w-4 mr-2" />
                Criar Primeiro Perfil
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Dialog de Criação / Edição de Perfil */}
      <ProfileDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        profileToEdit={editingProfile}
      />
    </div>
  );
}
