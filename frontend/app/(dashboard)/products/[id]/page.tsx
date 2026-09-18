"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useProduct } from "@/hooks/use-products";
import {
  useProductPrices,
  usePricingProfiles,
  useCalculateProductPrice,
  useDeleteProductPrice,
} from "@/hooks/use-pricing";
import { formatCurrency, formatDate } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  ArrowLeft,
  Loader2,
  Image as ImageIcon,
  DollarSign,
  Plus,
  Trash2,
  TrendingUp,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { toast } from "sonner";
import { DREBreakdownCard } from "@/components/pricing/dre-breakdown";
import { PublishDialog } from "@/components/marketplaces/publish-dialog";
import { ProductChannelPrice } from "@/types";
import { UploadCloud } from "lucide-react";

export default function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const router = useRouter();
  const productId = resolvedParams.id;

  const { data: product, isLoading } = useProduct(productId);
  const { data: channelPrices, isLoading: pricesLoading } = useProductPrices(productId);
  const { data: profiles } = usePricingProfiles(true);

  const calculateMutation = useCalculateProductPrice();
  const deletePriceMutation = useDeleteProductPrice();

  const [selectedProfileId, setSelectedProfileId] = useState<string>("");
  const [manualPriceInput, setManualPriceInput] = useState<string>("");
  const [expandedDreId, setExpandedDreId] = useState<string | null>(null);
  const [publishDialogOpen, setPublishDialogOpen] = useState<boolean>(false);
  const [selectedPriceForPublish, setSelectedPriceForPublish] = useState<ProductChannelPrice | null>(null);

  const handleCalculate = async () => {
    if (!selectedProfileId) {
      toast.error("Selecione um perfil de precificação.");
      return;
    }

    try {
      await calculateMutation.mutateAsync({
        productId,
        pricingProfileId: selectedProfileId,
        manualOverridePrice: manualPriceInput.trim() ? manualPriceInput.trim() : null,
      });
      toast.success("Preço de canal calculado com sucesso!");
      setManualPriceInput("");
    } catch (err: any) {
      toast.error(err.message || "Erro ao calcular preço.");
    }
  };

  const handleDeleteChannelPrice = async (profileId: string) => {
    try {
      await deletePriceMutation.mutateAsync({ productId, profileId });
      toast.success("Precificação de canal removida.");
    } catch (err: any) {
      toast.error(err.message || "Erro ao remover precificação.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="text-center py-10">
        <h2 className="text-xl font-semibold">Produto não encontrado</h2>
        <Button variant="link" onClick={() => router.push("/products")}>
          Voltar para produtos
        </Button>
      </div>
    );
  }

  const activeSupplierData = product.supplier_data?.find(
    (sd) => sd.current_cost !== null
  );

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/products")}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold tracking-tight">{product.name}</h2>
          <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
            <span>SKU: {product.sku}</span>
            <span>•</span>
            <Badge variant="outline">{product.status}</Badge>
            {activeSupplierData && (
              <>
                <span>•</span>
                <span>
                  Custo Base:{" "}
                  <strong className="text-foreground">
                    {formatCurrency(activeSupplierData.current_cost)}
                  </strong>
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      <Tabs defaultValue="geral" className="w-full">
        <TabsList className="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent">
          <TabsTrigger
            value="geral"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4"
          >
            Dados Gerais
          </TabsTrigger>
          <TabsTrigger
            value="fornecedor"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4"
          >
            Fornecedor
          </TabsTrigger>
          <TabsTrigger
            value="precificacao"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4"
          >
            Precificação Multicanal
          </TabsTrigger>
          <TabsTrigger
            value="imagens"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4"
          >
            Imagens
          </TabsTrigger>
          <TabsTrigger
            value="historico"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4"
          >
            Histórico de Custos
          </TabsTrigger>
        </TabsList>

        <TabsContent value="geral" className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-6 rounded-md border">
            <div className="space-y-4">
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  Nome do Produto
                </span>
                <span>{product.name || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  SKU
                </span>
                <span>{product.sku || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  Marca
                </span>
                <span>{product.brand || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  Modelo
                </span>
                <span>{product.model || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  EAN
                </span>
                <span>{product.ean || "-"}</span>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  Cor
                </span>
                <span>{product.color || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  Dimensões
                </span>
                <span>{product.dimensions || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  Peso
                </span>
                <span>{product.weight ? `${product.weight} kg` : "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  GTIN
                </span>
                <span>{product.gtin || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">
                  Criado em
                </span>
                <span>{formatDate(product.created_at)}</span>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="fornecedor" className="pt-6">
          <div className="space-y-6">
            {!product.supplier_data || product.supplier_data.length === 0 ? (
              <div className="text-center p-8 bg-white border rounded-md text-muted-foreground">
                Nenhum dado de fornecedor associado a este produto.
              </div>
            ) : (
              product.supplier_data.map((sd) => (
                <div
                  key={sd.id}
                  className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-6 rounded-md border"
                >
                  <div className="space-y-4">
                    <div>
                      <span className="text-sm font-medium text-muted-foreground block">
                        Fornecedor
                      </span>
                      <span>{sd.supplier?.name || "Desconhecido"}</span>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-muted-foreground block">
                        Código no Fornecedor
                      </span>
                      <span>{sd.supplier_code || "-"}</span>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <span className="text-sm font-medium text-muted-foreground block">
                        Custo Atual
                      </span>
                      <span className="font-medium text-lg">
                        {formatCurrency(sd.current_cost)}
                      </span>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-muted-foreground block">
                        Peças por Caixa (PCS/CX)
                      </span>
                      <span>{sd.pcs_per_box || "-"}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </TabsContent>

        {/* TAB PRECIFICAÇÃO MULTICANAL */}
        <TabsContent value="precificacao" className="pt-6 space-y-6">
          {/* Card de Cálculo Rápido */}
          <div className="rounded-xl border bg-card p-5 shadow-xs space-y-4">
            <h3 className="font-semibold text-base flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-primary" />
              Calcular Preço para Canal / Marketplace
            </h3>
            <div className="flex flex-col sm:flex-row gap-3 items-end">
              <div className="flex-1 space-y-1 w-full">
                <span className="text-xs font-medium text-muted-foreground">
                  Perfil de Canal
                </span>
                <select
                  value={selectedProfileId}
                  onChange={(e) => setSelectedProfileId(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="">Selecione um perfil de canal...</option>
                  {profiles?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.channel}) - Margem Alvo: {p.target_margin_percent}%
                    </option>
                  ))}
                </select>
              </div>

              <div className="w-full sm:w-44 space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Preço Manual (Opcional)
                </span>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="Ex: 89.90"
                  value={manualPriceInput}
                  onChange={(e) => setManualPriceInput(e.target.value)}
                />
              </div>

              <Button
                onClick={handleCalculate}
                disabled={calculateMutation.isPending || !selectedProfileId}
                className="w-full sm:w-auto"
              >
                {calculateMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                ) : (
                  <Plus className="h-4 w-4 mr-1.5" />
                )}
                Calcular Preço
              </Button>
            </div>
          </div>

          {/* Tabela de Preços Calculados */}
          <div className="rounded-xl border bg-card overflow-hidden shadow-xs">
            <div className="px-5 py-3 border-b bg-muted/30 font-semibold text-sm">
              Canais Precificados para este Produto
            </div>

            {pricesLoading ? (
              <div className="p-8 text-center text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                Carregando precificações...
              </div>
            ) : !channelPrices || channelPrices.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                Nenhuma precificação de canal gerada ainda. Selecione um perfil acima para calcular.
              </div>
            ) : (
              <div className="divide-y divide-border">
                {channelPrices.map((cp) => {
                  const isExpanded = expandedDreId === cp.id;
                  const netProfit = parseFloat(cp.net_margin_value) || 0;
                  const isProfitable = netProfit > 0;

                  return (
                    <div key={cp.id} className="p-4 space-y-3">
                      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-base text-foreground">
                              {cp.profile_name || "Canal"}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {cp.channel}
                            </Badge>
                            {cp.is_manual_override && (
                              <Badge className="bg-amber-500 text-xs">
                                Manual Override
                              </Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground flex gap-3">
                            <span>Custo Base: R$ {parseFloat(cp.cost_basis).toFixed(2)}</span>
                            <span>•</span>
                            <span>Comissão: R$ {parseFloat(cp.channel_commission).toFixed(2)}</span>
                            <span>•</span>
                            <span>Impostos: R$ {parseFloat(cp.taxes).toFixed(2)}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="text-lg font-bold text-foreground">
                              R$ {parseFloat(cp.calculated_price).toFixed(2)}
                            </div>
                            <div
                              className={`text-xs font-semibold ${
                                isProfitable
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : "text-rose-600"
                              }`}
                            >
                              Lucro: R$ {parseFloat(cp.net_margin_value).toFixed(2)} (
                              {parseFloat(cp.net_margin_percent).toFixed(2)}%)
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5">
                            {cp.channel === "MERCADO_LIVRE" && (
                              <Button
                                size="sm"
                                variant="default"
                                className="bg-yellow-500 hover:bg-yellow-600 text-black font-semibold h-8 text-xs"
                                onClick={() => {
                                  setSelectedPriceForPublish(cp);
                                  setPublishDialogOpen(true);
                                }}
                              >
                                <UploadCloud className="h-3.5 w-3.5 mr-1" />
                                Publicar no Meli
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                setExpandedDreId(isExpanded ? null : cp.id)
                              }
                            >
                              {isExpanded ? (
                                <>
                                  Ocultar DRE <ChevronUp className="h-4 w-4 ml-1" />
                                </>
                              ) : (
                                <>
                                  Ver DRE <ChevronDown className="h-4 w-4 ml-1" />
                                </>
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-rose-500 hover:text-rose-600 h-8 w-8"
                              onClick={() =>
                                handleDeleteChannelPrice(cp.pricing_profile_id)
                              }
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>

                      {/* DRE Expandida */}
                      {isExpanded && cp.breakdown && (
                        <div className="pt-2">
                          <DREBreakdownCard
                            dre={cp.breakdown}
                            suggestedPrice={cp.calculated_price}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="imagens" className="pt-6">
          {!product.images || product.images.length === 0 ? (
            <div className="text-center p-12 bg-white border rounded-md flex flex-col items-center">
              <ImageIcon className="h-12 w-12 text-zinc-300 mb-2" />
              <p className="text-muted-foreground">Nenhuma imagem disponível.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {product.images.map((img) => (
                <div
                  key={img.id}
                  className="border rounded-md overflow-hidden bg-white aspect-square relative group"
                >
                  <img
                    src={img.url}
                    alt={product.name}
                    className="w-full h-full object-contain p-2"
                  />
                  {img.is_primary && (
                    <div className="absolute top-2 left-2">
                      <Badge className="bg-blue-500">Principal</Badge>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="historico" className="pt-6">
          <div className="rounded-md border bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Preço</TableHead>
                  <TableHead>Importação ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!product.price_history || product.price_history.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={3}
                      className="h-24 text-center text-muted-foreground"
                    >
                      Nenhum histórico de custos disponível.
                    </TableCell>
                  </TableRow>
                ) : (
                  product.price_history.map((ph) => (
                    <TableRow key={ph.id}>
                      <TableCell>{formatDate(ph.date)}</TableCell>
                      <TableCell className="font-medium">
                        {formatCurrency(ph.price)}
                      </TableCell>
                      <TableCell className="text-muted-foreground font-mono text-xs">
                        {ph.import_job_id || "-"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      {/* Modal de Publicação no Mercado Livre */}
      <PublishDialog
        open={publishDialogOpen}
        onOpenChange={setPublishDialogOpen}
        product={product}
        selectedChannelPrice={selectedPriceForPublish}
      />
    </div>
  );
}

