"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useImport, useImportItems, useUpdateImportItem, useConfirmImport } from "@/hooks/use-imports";
import { formatCurrency } from "@/lib/utils";
import { ImportItem, ItemStatus } from "@/types";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Loader2, Image as ImageIcon, AlertTriangle, Check, X, Pencil, Save } from "lucide-react";
import { toast } from "sonner";

export default function ImportReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const router = useRouter();
  
  const { data: job, isLoading: isLoadingJob } = useImport(resolvedParams.id);
  const { data: itemsData, isLoading: isLoadingItems } = useImportItems(resolvedParams.id);
  const updateItem = useUpdateImportItem();
  const confirmImport = useConfirmImport();

  const handleConfirmJob = () => {
    confirmImport.mutate(resolvedParams.id, {
      onSuccess: () => {
        toast.success("Importação confirmada com sucesso!");
        router.push("/products");
      },
      onError: (err) => {
        toast.error(`Erro ao confirmar: ${err.message}`);
      }
    });
  };

  if (isLoadingJob || isLoadingItems) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (!job || !itemsData) return null;

  const isJobComplete = job.status === "COMPLETED" || job.status === "IMPORTED";
  const approvedCount = itemsData.items.filter(i => i.status === "APPROVED").length;
  const detectedCount = itemsData.items.filter(i => i.status === "DETECTED" || i.status === "PENDING").length;
  const outOfStockCount = itemsData.items.filter(i => i.is_out_of_stock).length;
  const eligibleCount = itemsData.items.filter(i => i.status !== "IGNORED" && i.status !== "REJECTED").length;
  const hasEligibleItems = eligibleCount > 0;

  const handleApproveAll = () => {
    itemsData.items.forEach(item => {
      // Don't auto-approve out of stock items in approve-all
      if ((item.status === "DETECTED" || item.status === "PENDING") && !item.is_out_of_stock) {
        updateItem.mutate({ itemId: item.id, data: { status: "APPROVED" } });
      }
    });
    toast.success("Itens válidos marcados como Aprovados!");
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-24">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/imports")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Revisão de Importação</h2>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <span>{job.original_filename}</span>
              <span>•</span>
              <span className="font-medium text-zinc-700">{job.supplier?.name || "Fornecedor"}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {!isJobComplete && detectedCount > 0 && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleApproveAll}
              disabled={updateItem.isPending}
            >
              <Check className="mr-1.5 h-4 w-4 text-green-600" />
              Aprovar Disponíveis
            </Button>
          )}

          <div className="flex items-center gap-4 bg-white p-3 rounded-md border shadow-sm">
            <div className="text-center px-4 border-r">
              <span className="block text-xs text-muted-foreground uppercase font-semibold">Total</span>
              <span className="font-bold text-lg">{itemsData.total}</span>
            </div>
            <div className="text-center px-4 border-r">
              <span className="block text-xs text-muted-foreground uppercase font-semibold text-green-600">Aprovados</span>
              <span className="font-bold text-lg text-green-600">{approvedCount}</span>
            </div>
            <div className="text-center px-4 border-r">
              <span className="block text-xs text-muted-foreground uppercase font-semibold text-amber-600">Pendentes</span>
              <span className="font-bold text-lg text-amber-600">{detectedCount}</span>
            </div>
            {outOfStockCount > 0 && (
              <div className="text-center px-4">
                <span className="block text-xs text-muted-foreground uppercase font-semibold text-rose-600">Esgotados</span>
                <span className="font-bold text-lg text-rose-600">{outOfStockCount}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4">
        {itemsData.items.map((item) => (
          <ReviewItemCard key={item.id} item={item} updateItem={updateItem.mutate} readOnly={isJobComplete} />
        ))}
        {itemsData.items.length === 0 && (
          <div className="text-center py-12 bg-white rounded-md border">
            Nenhum item detectado neste arquivo.
          </div>
        )}
      </div>

      {!isJobComplete && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] lg:pl-64 z-10">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Revise os itens extraídos do PDF. Clique em Confirmar para cadastrar no catálogo de produtos.
            </div>
            <Button 
              size="lg" 
              onClick={handleConfirmJob} 
              disabled={!hasEligibleItems || confirmImport.isPending}
              className="bg-zinc-900 hover:bg-zinc-800 text-white"
            >
              {confirmImport.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
              Confirmar e Cadastrar {eligibleCount} Produtos
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function ReviewItemCard({ 
  item, 
  updateItem, 
  readOnly 
}: { 
  item: ImportItem; 
  updateItem: any; 
  readOnly: boolean 
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedCode, setEditedCode] = useState(item.normalized_code || "");
  const [editedPrice, setEditedPrice] = useState(item.normalized_price || "");
  
  const handleSaveEdit = () => {
    updateItem({
      itemId: item.id,
      data: { normalized_code: editedCode, normalized_price: editedPrice }
    });
    setIsEditing(false);
  };

  const setStatus = (status: ItemStatus) => {
    updateItem({ itemId: item.id, data: { status } });
  };

  const isApproved = item.status === "APPROVED";
  const isIgnored = item.status === "IGNORED";
  const isPendingReview = item.status === "PENDING" || item.status === "DETECTED";
  const hasWarnings = item.warnings && item.warnings.length > 0;
  const isOutOfStock = Boolean(item.is_out_of_stock);

  return (
    <Card className={`p-4 transition-colors ${
      isOutOfStock ? "border-rose-300 bg-rose-50/20" : isIgnored ? "opacity-60 bg-zinc-50" : isApproved ? "border-green-200 bg-green-50/10" : ""
    }`}>
      <div className="flex flex-col md:flex-row gap-6">
        <div className="w-full md:w-32 h-32 shrink-0 bg-white border rounded-md overflow-hidden flex items-center justify-center relative">
          {item.image_path ? (
            <img src={item.image_path} alt="Extraído" className="w-full h-full object-contain p-2" />
          ) : (
            <ImageIcon className="h-8 w-8 text-zinc-300" />
          )}
          {isOutOfStock && (
            <div className="absolute inset-0 bg-rose-900/10 flex items-center justify-center pointer-events-none">
              <span className="bg-rose-600/90 text-white text-[10px] font-black px-2 py-0.5 rounded shadow rotate-[-12deg] tracking-wider uppercase">
                ESGOTADO
              </span>
            </div>
          )}
        </div>

        <div className="flex-1 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                {isEditing ? (
                  <Input 
                    value={editedCode} 
                    onChange={(e) => setEditedCode(e.target.value)} 
                    className="h-8 w-40 font-mono text-sm font-bold"
                  />
                ) : (
                  <h3 className="font-mono text-lg font-bold">
                    {item.normalized_code || item.raw_code || "Sem código"}
                  </h3>
                )}
                {isOutOfStock && (
                  <Badge variant="destructive" className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold">
                    ESGOTADO NO FORNECEDOR
                  </Badge>
                )}
                {item.confidence_score && (
                  <Badge variant={item.confidence_score > 0.8 ? "default" : "secondary"} className="text-[10px]">
                    {Math.round(item.confidence_score * 100)}% Confiança
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">{item.raw_name || "Nome não extraído"}</p>
            </div>
            
            <div className="flex gap-2">
              {isPendingReview && !readOnly && (
                <>
                  {isEditing ? (
                    <Button size="sm" variant="outline" onClick={handleSaveEdit}>
                      <Save className="h-4 w-4 mr-1" /> Salvar
                    </Button>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => setIsEditing(true)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                  )}
                  <Button size="sm" variant="outline" className="text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => setStatus("IGNORED")}>
                    Ignorar
                  </Button>
                  <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white" onClick={() => setStatus("APPROVED")}>
                    Aprovar
                  </Button>
                </>
              )}
              {!isPendingReview && (
                <div className="flex items-center gap-3">
                  <Badge variant={isApproved ? "default" : "secondary"} className={isApproved ? "bg-green-500 text-white" : ""}>
                    {isApproved ? "Aprovado" : item.status === "IGNORED" ? (isOutOfStock ? "Ignorado (Esgotado)" : "Ignorado") : item.status === "IMPORTED" ? "Cadastrado" : item.status}
                  </Badge>
                  {!readOnly && item.status !== "IMPORTED" && (
                    <div className="flex items-center gap-2">
                      {isIgnored && (
                        <Button size="sm" variant="outline" className="text-green-700 hover:bg-green-50" onClick={() => setStatus("APPROVED")}>
                          Aprovar (Inativo)
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" onClick={() => setStatus("DETECTED")}>
                        Desfazer
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm bg-zinc-50 p-3 rounded-md border">
            <div>
              <span className="block text-xs text-muted-foreground">Preço</span>
              {isEditing ? (
                <Input 
                  value={editedPrice} 
                  onChange={(e) => setEditedPrice(e.target.value)} 
                  className="h-7 w-full mt-1 px-2 py-1 text-sm"
                />
              ) : (
                <span className="font-semibold">{item.normalized_price ? formatCurrency(item.normalized_price) : (item.raw_price || "-")}</span>
              )}
            </div>
            <div>
              <span className="block text-xs text-muted-foreground">Dimensões</span>
              <span>{item.raw_dimensions || "-"}</span>
            </div>
            <div>
              <span className="block text-xs text-muted-foreground">PCS/CX</span>
              <span>{item.raw_pcs_cx || "-"}</span>
            </div>
            <div>
              <span className="block text-xs text-muted-foreground">Cor (Extraída)</span>
              <span>{item.normalized_color || "-"}</span>
            </div>
          </div>

          {hasWarnings && (
            <div className="bg-orange-50 border border-orange-200 text-orange-800 p-2 rounded-md flex items-start gap-2 text-sm">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <ul className="list-disc list-inside">
                {item.warnings?.map((w, idx) => <li key={idx}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
