"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useClonePreview, useCloneProduct } from "@/hooks/use-clone";
import { useSuppliers } from "@/hooks/use-suppliers";
import { ClonePreviewResponse } from "@/types";
import { errorMessage, formatCurrency } from "@/lib/utils";
import { toast } from "sonner";
import { Copy, Sparkles, Loader2, CheckCircle2, ArrowRight, ExternalLink } from "lucide-react";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CloneProductDialog({ open, onOpenChange }: Props) {
  const router = useRouter();
  const [urlInput, setUrlInput] = useState("");
  const [previewData, setPreviewData] = useState<ClonePreviewResponse | null>(null);
  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [costPriceInput, setCostPriceInput] = useState("");

  const previewMutation = useClonePreview();
  const cloneMutation = useCloneProduct();
  const suppliersQuery = useSuppliers(0, 100);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) {
      toast.warning("Insira o link ou código do anúncio no Mercado Livre.");
      return;
    }
    try {
      const data = await previewMutation.mutateAsync({ url_or_id: urlInput.trim() });
      setPreviewData(data);
      toast.success(`Anúncio identificado: "${data.name.slice(0, 45)}..."`);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const handleClone = async () => {
    if (!previewData) return;
    try {
      const cost = costPriceInput.trim() ? parseFloat(costPriceInput.replace(",", ".")) : null;
      const created = await cloneMutation.mutateAsync({
        url_or_id: previewData.mlb_id,
        supplier_id: selectedSupplierId || null,
        cost_price: cost,
        status: "ACTIVE",
      });

      toast.success(`Produto "${created.name}" clonado com sucesso! Redirecionando...`);
      onOpenChange(false);
      // Reset
      setUrlInput("");
      setPreviewData(null);
      setSelectedSupplierId("");
      setCostPriceInput("");
      // Navigate to product page
      router.push(`/products/${created.id}`);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <div className="h-8 w-8 rounded-lg bg-orange-500/10 text-orange-600 flex items-center justify-center">
              <Sparkles className="h-4 w-4" />
            </div>
            Clonar Anúncio do Mercado Livre
          </DialogTitle>
          <DialogDescription>
            Cole o link de qualquer anúncio do Mercado Livre para extrair fotos em alta resolução,
            especificações, dimensões e descrição diretamente para o AdapterFlow.
          </DialogDescription>
        </DialogHeader>

        {/* Input bar */}
        <form onSubmit={handleAnalyze} className="space-y-3 pt-1">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                placeholder="https://produto.mercadolivre.com.br/MLB-... ou código MLB"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                className="h-10 text-sm pr-10"
              />
              <Copy className="h-4 w-4 absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            </div>
            <Button
              type="submit"
              disabled={previewMutation.isPending || !urlInput.trim()}
              className="bg-amber-500 hover:bg-amber-600 text-black font-semibold h-10 px-4"
            >
              {previewMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analisando...
                </>
              ) : (
                "Analisar Anúncio"
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Exemplo: <span className="font-mono text-[11px]">https://produto.mercadolivre.com.br/MLB-123456789...</span>
          </p>
        </form>

        {/* Preview Section */}
        {previewData && (
          <div className="mt-4 rounded-xl border bg-muted/20 p-4 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Badge variant="outline" className="text-amber-700 dark:text-amber-400 border-amber-300">
                  {previewData.mlb_id}
                </Badge>
                <h3 className="font-semibold text-base mt-1 text-foreground">
                  {previewData.name}
                </h3>
                {previewData.permalink && (
                  <a
                    href={previewData.permalink}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mt-0.5"
                  >
                    Ver anúncio original <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
              {previewData.price !== undefined && previewData.price !== null && (
                <div className="text-right shrink-0">
                  <span className="text-xs text-muted-foreground block">Preço no ML</span>
                  <span className="font-bold text-lg text-emerald-600 dark:text-emerald-400">
                    {formatCurrency(previewData.price)}
                  </span>
                </div>
              )}
            </div>

            {/* Photos carousel / grid */}
            {previewData.pictures.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-medium text-muted-foreground">
                  Fotos detectadas ({previewData.pictures.length} imagens):
                </span>
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {previewData.pictures.map((picUrl, idx) => (
                    <div
                      key={idx}
                      className="relative h-20 w-20 shrink-0 rounded-lg border bg-white p-1 overflow-hidden shadow-xs"
                    >
                      <Image
                        src={picUrl}
                        alt={`Foto ${idx + 1}`}
                        fill
                        unoptimized
                        className="object-contain"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extracted Attributes Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
              <div className="p-2 rounded-md bg-background border">
                <span className="text-muted-foreground block">Marca:</span>
                <span className="font-medium text-foreground">{previewData.brand || "Não informada"}</span>
              </div>
              <div className="p-2 rounded-md bg-background border">
                <span className="text-muted-foreground block">Modelo:</span>
                <span className="font-medium text-foreground">{previewData.model || "Não informado"}</span>
              </div>
              <div className="p-2 rounded-md bg-background border">
                <span className="text-muted-foreground block">EAN / GTIN:</span>
                <span className="font-mono font-medium text-foreground">{previewData.ean || "Não informado"}</span>
              </div>
              <div className="p-2 rounded-md bg-background border">
                <span className="text-muted-foreground block">Cor:</span>
                <span className="font-medium text-foreground">{previewData.color || "Não informada"}</span>
              </div>
              <div className="p-2 rounded-md bg-background border">
                <span className="text-muted-foreground block">Dimensões:</span>
                <span className="font-medium text-foreground">{previewData.dimensions || "Não informadas"}</span>
              </div>
              <div className="p-2 rounded-md bg-background border">
                <span className="text-muted-foreground block">Peso:</span>
                <span className="font-medium text-foreground">
                  {previewData.weight ? `${previewData.weight} kg` : "Não informado"}
                </span>
              </div>
            </div>

            {/* Optional Supplier & Cost Association */}
            <div className="pt-2 border-t space-y-3">
              <span className="text-xs font-semibold text-foreground block">
                Origem & Custo (Opcional)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">
                    Vincular Fornecedor
                  </label>
                  <select
                    className="w-full border rounded-md p-2 text-xs bg-background"
                    value={selectedSupplierId}
                    onChange={(e) => setSelectedSupplierId(e.target.value)}
                  >
                    <option value="">Nenhum fornecedor agora</option>
                    {suppliersQuery.data?.items
                      ?.filter((s) => s.is_active)
                      .map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground block mb-1">
                    Custo de Compra (R$)
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="Ex: 25.00"
                    value={costPriceInput}
                    onChange={(e) => setCostPriceInput(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setPreviewData(null)}
              >
                Limpar
              </Button>
              <Button
                type="button"
                disabled={cloneMutation.isPending}
                onClick={handleClone}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
              >
                {cloneMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Baixando fotos e criando...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Clonar e Criar Produto
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
