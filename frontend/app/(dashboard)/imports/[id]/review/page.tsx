"use client";
import { use, useState } from "react";
import { useIsMutating } from "@tanstack/react-query";
import Image from "next/image";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  useImport,
  useImportItems,
  useUpdateImportItem,
  useConfirmImport,
  useApproveAllImportItems,
} from "@/hooks/use-imports";
import { ImportItem } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pagination, QueryError } from "@/components/data-state";
import { errorMessage } from "@/lib/utils";
import { toast } from "sonner";
import { CheckCircle2, CheckCheck, UploadCloud, AlertCircle } from "lucide-react";

const editSchema = z.object({
  normalized_name: z.string().trim().min(1, "Nome é obrigatório"),
  normalized_code: z.string().trim().min(1, "Código é obrigatório"),
  normalized_price: z.string().regex(/^$|^\d+(\.\d{1,4})?$/, "Use decimal com ponto, até quatro casas."),
});

export default function Review({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const pendingEdits = useIsMutating({ mutationKey: ["review-item"] });

  const job = useImport(id);
  const items = useImportItems(id, offset, ["UPLOADED", "PROCESSING"].includes(job.data?.status || ""));
  const update = useUpdateImportItem();
  const approveAll = useApproveAllImportItems();
  const confirm = useConfirmImport();

  if (job.isError || items.isError) {
    return <QueryError error={job.error || items.error} retry={() => { job.refetch(); items.refetch(); }} />;
  }

  if (!job.data || !items.data) {
    return (
      <div className="flex items-center justify-center p-12 text-muted-foreground">
        <p>Carregando revisão do catálogo...</p>
      </div>
    );
  }

  const isProcessing = ["UPLOADED", "PROCESSING"].includes(job.data.status);
  const isImported = job.data.status === "IMPORTED";
  const readOnly = job.data.status !== "REVIEW_REQUIRED" || busy || confirm.isPending || approveAll.isPending;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Revisão: {job.data.original_filename}</h2>
          <p className="text-sm text-muted-foreground">
            Status: <span className="font-semibold text-foreground">{job.data.status}</span>
            {job.data.total_detected ? ` · ${job.data.total_detected} produtos detectados` : ""}
            {isImported ? ` · ${job.data.total_imported || 0} cadastrados com sucesso` : ""}
          </p>
        </div>

        {job.data.status === "REVIEW_REQUIRED" && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="gap-2 border-emerald-600/30 text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-950/30"
              disabled={readOnly || pendingEdits > 0}
              onClick={async () => {
                try {
                  const res = await approveAll.mutateAsync(id);
                  toast.success(`${res.approved_count} produtos foram aprovados no catálogo inteiro.`);
                  items.refetch();
                } catch (e) {
                  toast.error(errorMessage(e));
                }
              }}
            >
              <CheckCheck className="h-4 w-4 text-emerald-600" />
              {approveAll.isPending ? "Aprovando..." : "Aprovar Todos os Disponíveis"}
            </Button>

            <Button
              className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
              disabled={readOnly || pendingEdits > 0 || !items.data.total}
              onClick={async () => {
                try {
                  const result = await confirm.mutateAsync(id);
                  toast.success(`${result.total_imported ?? result.items_imported ?? "Todos os"} produtos cadastrados com sucesso!`);
                } catch (e) {
                  toast.error(errorMessage(e));
                }
              }}
            >
              <CheckCircle2 className="h-4 w-4" />
              {confirm.isPending ? "Cadastrando..." : "Confirmar e Cadastrar"}
            </Button>
          </div>
        )}
      </div>

      {job.data.error_message && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-300" role="alert">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{job.data.error_message}</span>
        </div>
      )}

      {isProcessing && (
        <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/50 dark:text-blue-300">
          <UploadCloud className="h-5 w-5 animate-pulse shrink-0" />
          <p>A extração multi-páginas do PDF está em andamento. Os resultados aparecerão automaticamente aqui em instantes.</p>
        </div>
      )}

      {isImported && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/50 dark:text-emerald-300">
          <p className="font-medium">Importação concluída!</p>
          <p>Os produtos aprovados já foram cadastrados no sistema e estão disponíveis na aba de Produtos.</p>
        </div>
      )}

      {job.data.status === "REVIEW_REQUIRED" && (
        <div className="flex items-center justify-between bg-muted/40 p-3 rounded-lg border text-sm text-muted-foreground">
          <p>
            Dica: você pode aprovar todo o catálogo de uma vez pelo botão acima, ou aprovar/editar item por item abaixo.
          </p>
          <Button
            size="sm"
            variant="ghost"
            disabled={readOnly || pendingEdits > 0 || update.isPending}
            onClick={async () => {
              setBusy(true);
              try {
                for (const item of items.data.items) {
                  if (item.status === "DETECTED" && !item.is_out_of_stock) {
                    await update.mutateAsync({ itemId: item.id, data: { status: "APPROVED" } });
                  }
                }
                toast.success("Aprovações desta página salvas.");
              } catch (e) {
                toast.error(errorMessage(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            Aprovar apenas esta página
          </Button>
        </div>
      )}

      {!items.data.items.length && job.data.status === "REVIEW_REQUIRED" && (
        <div className="text-center py-12 border rounded-lg bg-card">
          <p className="text-muted-foreground">Nenhum item detectado neste arquivo.</p>
        </div>
      )}

      <div className="space-y-3">
        {items.data.items.map((item) => (
          <Item key={`${item.id}:${item.updated_at}`} item={item} readOnly={readOnly} />
        ))}
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pt-2">
        <Pagination offset={offset} total={items.data.total} onChange={setOffset} />
        {job.data.status === "REVIEW_REQUIRED" && (
          <Button
            className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
            disabled={readOnly || pendingEdits > 0 || update.isPending || !items.data.total}
            onClick={async () => {
              try {
                const result = await confirm.mutateAsync(id);
                toast.success(`${result.total_imported ?? result.items_imported ?? "Todos os"} produtos confirmados.`);
              } catch (e) {
                toast.error(errorMessage(e));
              }
            }}
          >
            <CheckCircle2 className="h-4 w-4" />
            {confirm.isPending ? "Cadastrando..." : "Confirmar e Cadastrar Aprovados"}
          </Button>
        )}
      </div>
    </div>
  );
}

function Item({ item, readOnly }: { item: ImportItem; readOnly: boolean }) {
  const pendingEdits = useIsMutating({ mutationKey: ["review-item"] });
  const update = useUpdateImportItem();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<z.infer<typeof editSchema>>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      normalized_name: item.normalized_name || item.raw_name || "",
      normalized_code: item.normalized_code || "",
      normalized_price: item.normalized_price != null ? String(item.normalized_price) : "",
    },
  });

  const save = handleSubmit(async (values) => {
    try {
      await update.mutateAsync({
        itemId: item.id,
        data: { ...values, normalized_price: values.normalized_price || null },
      });
      toast.success("Item atualizado.");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  });

  const disabled = readOnly || pendingEdits > 0 || update.isPending || item.status === "IMPORTED";

  const statusBadge = {
    APPROVED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-300",
    DETECTED: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-300",
    IGNORED: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400 border-zinc-300",
    IMPORTED: "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300 border-purple-300",
    ERROR: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300 border-red-300",
  }[item.status] || "bg-muted text-muted-foreground";

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${statusBadge}`}>
            {item.status === "APPROVED"
              ? "APROVADO"
              : item.status === "DETECTED"
              ? "PENDENTE"
              : item.status === "IGNORED"
              ? "IGNORADO"
              : item.status === "IMPORTED"
              ? "CADASTRADO"
              : item.status}
          </span>
          {item.is_out_of_stock && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              Esgotado no catálogo
            </span>
          )}
        </div>
        <div className="flex gap-1.5">
          {(["APPROVED", "IGNORED", "DETECTED"] as const).map((status) => (
            <Button
              key={status}
              disabled={disabled}
              size="sm"
              variant={item.status === status ? "default" : "outline"}
              className={item.status === status && status === "APPROVED" ? "bg-emerald-600 hover:bg-emerald-700 text-white" : ""}
              onClick={async () => {
                try {
                  await update.mutateAsync({ itemId: item.id, data: { status } });
                } catch (e) {
                  toast.error(errorMessage(e));
                }
              }}
            >
              {status === "APPROVED" ? "Aprovar" : status === "IGNORED" ? "Ignorar" : "Pendente"}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 items-start">
        {item.image_url ? (
          <div className="w-24 h-24 shrink-0 rounded border bg-muted/20 flex items-center justify-center overflow-hidden">
            <Image
              src={item.image_url}
              alt={item.raw_name || "Imagem extraída"}
              width={96}
              height={96}
              unoptimized
              className="object-contain max-h-24 w-auto"
            />
          </div>
        ) : (
          <div className="w-24 h-24 shrink-0 rounded border bg-muted/30 flex items-center justify-center text-xs text-muted-foreground">
            Sem imagem
          </div>
        )}

        <form onSubmit={save} className="flex-1 grid gap-3 sm:grid-cols-3 items-end">
          <label className="text-xs font-medium space-y-1">
            <span>Nome do Produto</span>
            <Input disabled={disabled} {...register("normalized_name")} className="h-9" />
          </label>
          <label className="text-xs font-medium space-y-1">
            <span>Código Fornecedor</span>
            <Input disabled={disabled} {...register("normalized_code")} className="h-9" />
          </label>
          <label className="text-xs font-medium space-y-1">
            <span>Custo Unitário (R$)</span>
            <Input disabled={disabled} inputMode="decimal" {...register("normalized_price")} className="h-9" />
          </label>
          {errors.normalized_name && <p className="text-xs text-red-500 sm:col-span-3">{errors.normalized_name.message}</p>}
          {errors.normalized_code && <p className="text-xs text-red-500 sm:col-span-3">{errors.normalized_code.message}</p>}
          {errors.normalized_price && <p className="text-xs text-red-500 sm:col-span-3">{errors.normalized_price.message}</p>}
          <div className="sm:col-span-3 flex justify-between items-center pt-1 text-xs text-muted-foreground">
            <span>
              Fonte: {item.raw_code || "Sem cód"} · {item.raw_price || "Sem preço"}
              {item.raw_dimensions ? ` · ${item.raw_dimensions}` : ""}
            </span>
            <Button disabled={disabled} type="submit" size="sm" variant="secondary">
              Salvar Alterações
            </Button>
          </div>
        </form>
      </div>

      {item.warnings && item.warnings.length > 0 && (
        <div className="text-xs text-amber-700 bg-amber-50 rounded p-2 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/50">
          {item.warnings.map((warning, index) => (
            <p key={index}>{warning}</p>
          ))}
        </div>
      )}
    </div>
  );
}
