"use client";

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useMarketplacesOverview,
  usePredictCategory,
  usePublishToMercadoLivre,
} from "@/hooks/use-marketplaces";
import { ProductWithDetails, ProductChannelPrice } from "@/types";
import { toast } from "sonner";
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { useRouter } from "next/navigation";

interface PublishDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  product: ProductWithDetails;
  selectedChannelPrice?: ProductChannelPrice | null;
}

export function PublishDialog({
  open,
  onOpenChange,
  product,
  selectedChannelPrice,
}: PublishDialogProps) {
  const router = useRouter();
  const { data: overview } = useMarketplacesOverview();
  const publishMutation = usePublishToMercadoLivre();

  const mlAccounts =
    overview?.accounts.filter((a) => a.marketplace === "MERCADO_LIVRE") || [];

  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [title, setTitle] = useState<string>("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [listingTypeId, setListingTypeId] = useState<string>("gold_special");
  const [availableQuantity, setAvailableQuantity] = useState<number>(1);
  const [condition, setCondition] = useState<string>("new");

  const { data: categoryPredictions, isLoading: predictingCategory } =
    usePredictCategory(title);

  useEffect(() => {
    if (open) {
      setTitle(product.name.slice(0, 60));
      if (mlAccounts.length > 0 && !selectedAccountId) {
        setSelectedAccountId(mlAccounts[0].id);
      }
    }
  }, [open, product, mlAccounts, selectedAccountId]);

  // Se houver predição de categoria e nenhuma categoria selecionada, seleciona a primeira
  useEffect(() => {
    if (categoryPredictions && categoryPredictions.length > 0 && !categoryId) {
      setCategoryId(categoryPredictions[0].category_id);
    }
  }, [categoryPredictions, categoryId]);

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedAccountId) {
      toast.error("Selecione uma conta do Mercado Livre conectada.");
      return;
    }
    if (!title.trim()) {
      toast.error("O título do anúncio é obrigatório.");
      return;
    }
    if (!categoryId.trim()) {
      toast.error("A categoria do Mercado Livre é obrigatória.");
      return;
    }

    try {
      const res = await publishMutation.mutateAsync({
        product_id: product.id,
        account_id: selectedAccountId,
        pricing_profile_id: selectedChannelPrice?.pricing_profile_id || null,
        title: title.trim(),
        category_id: categoryId.trim(),
        listing_type_id: listingTypeId,
        available_quantity: Number(availableQuantity) || 1,
        condition,
      });

      toast.success("Anúncio publicado com sucesso no Mercado Livre!");
      onOpenChange(false);
      router.push("/publications");
    } catch (err: any) {
      toast.error(err.message || "Erro ao publicar no Mercado Livre.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UploadCloud className="h-5 w-5 text-primary" />
            Publicar Produto no Mercado Livre
          </DialogTitle>
        </DialogHeader>

        {mlAccounts.length === 0 ? (
          <div className="py-6 text-center space-y-3">
            <AlertCircle className="h-10 w-10 text-amber-500 mx-auto" />
            <div className="space-y-1">
              <h3 className="font-semibold text-foreground">
                Nenhuma conta do Mercado Livre conectada
              </h3>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Para publicar produtos, é necessário autorizar sua conta de vendedor via OAuth oficial.
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => {
                onOpenChange(false);
                router.push("/marketplaces");
              }}
            >
              Ir para Conexão de Marketplaces
            </Button>
          </div>
        ) : (
          <form onSubmit={handlePublish} className="space-y-4 py-2">
            <div className="space-y-1">
              <Label htmlFor="ml_account">Conta Vendedora do Mercado Livre *</Label>
              <select
                id="ml_account"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
                required
              >
                {mlAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.account_name} (Seller ID: {acc.seller_id})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <Label htmlFor="ml_title">Título do Anúncio (Máx. 60 caracteres) *</Label>
                <span className={`text-xs ${title.length > 60 ? "text-rose-500 font-bold" : "text-muted-foreground"}`}>
                  {title.length}/60
                </span>
              </div>
              <Input
                id="ml_title"
                maxLength={60}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex: Fone De Ouvido Bluetooth Lehmox Com Microfone"
                required
              />
            </div>

            {/* Sugestões de Categoria */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <Label htmlFor="ml_category">Categoria do Mercado Livre *</Label>
                {predictingCategory && (
                  <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" /> Identificando categoria...
                  </span>
                )}
              </div>
              <Input
                id="ml_category"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                placeholder="Ex: MLB1055"
                required
              />

              {categoryPredictions && categoryPredictions.length > 0 && (
                <div className="space-y-1 pt-1">
                  <span className="text-[11px] text-muted-foreground block">
                    Categorias sugeridas pela inteligência do Mercado Livre:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {categoryPredictions.map((cp) => (
                      <button
                        key={cp.category_id}
                        type="button"
                        onClick={() => setCategoryId(cp.category_id)}
                        className={`text-xs px-2.5 py-1 rounded-md border text-left transition-colors ${
                          categoryId === cp.category_id
                            ? "bg-primary text-primary-foreground border-primary"
                            : "bg-muted/40 hover:bg-muted text-muted-foreground"
                        }`}
                      >
                        {cp.category_name} ({cp.category_id})
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label htmlFor="ml_type">Tipo de Anúncio</Label>
                <select
                  id="ml_type"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={listingTypeId}
                  onChange={(e) => setListingTypeId(e.target.value)}
                >
                  <option value="gold_special">Clássico (gold_special)</option>
                  <option value="gold_pro">Premium (gold_pro - parcelamento)</option>
                </select>
              </div>

              <div className="space-y-1">
                <Label htmlFor="ml_stock">Estoque Inicial (unidades)</Label>
                <Input
                  id="ml_stock"
                  type="number"
                  min={1}
                  value={availableQuantity}
                  onChange={(e) => setAvailableQuantity(Number(e.target.value))}
                  required
                />
              </div>
            </div>

            {/* Resumo de Preço da Fase 2 */}
            <div className="p-3.5 rounded-lg border bg-muted/30 flex justify-between items-center text-sm">
              <div>
                <span className="text-xs text-muted-foreground block">Preço de Venda a Publicar</span>
                <span className="font-bold text-lg text-foreground">
                  R${" "}
                  {selectedChannelPrice
                    ? parseFloat(selectedChannelPrice.calculated_price).toFixed(2)
                    : "0.00"}
                </span>
              </div>
              <div className="text-right text-xs text-muted-foreground">
                <span>Canal: Mercado Livre</span>
                {selectedChannelPrice && (
                  <span className="block text-emerald-600 font-medium">
                    Margem: {parseFloat(selectedChannelPrice.net_margin_percent).toFixed(1)}%
                  </span>
                )}
              </div>
            </div>

            <DialogFooter className="pt-4 border-t">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={publishMutation.isPending}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={publishMutation.isPending}>
                {publishMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Validando e Publicando...
                  </>
                ) : (
                  "Publicar no Mercado Livre"
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
