"use client";
import { use, useState } from "react";
import { useIsMutating, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
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
  useImportPages,
  useRetryImport,
  type ImportPage,
} from "@/hooks/use-imports";
import { ImportItem } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Pagination, QueryError } from "@/components/data-state";
import { errorMessage, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import { CheckCircle2, CheckCheck, UploadCloud, AlertCircle } from "lucide-react";

const editSchema = z.object({
  normalized_dimensions: z.string().max(255),
  normalized_color: z.string().max(100),
  normalized_pcs_per_box: z.string().regex(/^$|^[1-9]\d*$/, "Quantidade inteira positiva."),
  normalized_name: z.string().trim().min(1, "Nome é obrigatório"),
  normalized_code: z.string().trim().min(1, "Código é obrigatório"),
  normalized_price: z.string().regex(/^$|^\d+(\.\d{1,4})?$/, "Use decimal com ponto, até quatro casas."),
});

export default function Review({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [offset, setOffset] = useState(0);
  const [pageOffset, setPageOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const pendingEdits = useIsMutating({ mutationKey: ["review-item"] });

  const job = useImport(id);
  const items = useImportItems(id, offset, ["UPLOADED", "PROCESSING"].includes(job.data?.status || ""));
  const pages = useImportPages(id, pageOffset, ["UPLOADED", "PROCESSING"].includes(job.data?.status || ""));
  const update = useUpdateImportItem();
  const approveAll = useApproveAllImportItems();
  const confirm = useConfirmImport();
  const retry = useRetryImport();

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
  const readOnly = !["REVIEW_REQUIRED", "IMPORTED"].includes(job.data.status) || busy || confirm.isPending || approveAll.isPending;
  const totalPages = job.data.total_pages;
  const processedPages = job.data.processed_pages ?? 0;

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
          {job.data.original_file_url && (
            <a href={job.data.original_file_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm underline underline-offset-4">Abrir PDF original</a>
          )}
        </div>

        {!isProcessing && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="gap-2 border-emerald-600/30 text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-950/30"
              disabled={readOnly || pendingEdits > 0 || !items.data.total}
              onClick={async () => {
                try {
                  const res = await approveAll.mutateAsync(id);
                  toast.success(`${res.approved_count} produtos foram aprovados no catálogo inteiro.`);
                  if (res.skipped_count) toast.warning(`${res.skipped_count} itens precisam de revisão e não foram aprovados.`);
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

      {job.data.status === "FAILED" && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border p-4 text-sm">
          <p className="flex-1">O arquivo já enviado pode ser processado novamente. As páginas concluídas e suas revisões serão preservadas.</p>
          <Button
            disabled={retry.isPending}
            onClick={async () => {
              try {
                await retry.mutateAsync(id);
                toast.success("Importação recolocada na fila. O progresso será atualizado aqui.");
              } catch (e) {
                toast.error(errorMessage(e));
              }
            }}
          >
            {retry.isPending ? "Retomando..." : "Tentar novamente sem reenviar"}
          </Button>
        </div>
      )}

      <div className="rounded-lg border p-4 space-y-2 text-sm" aria-live="polite">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-medium">Leitura das páginas do PDF</p>
          <p>{totalPages != null ? `${processedPages} de ${totalPages} páginas processadas` : "Total de páginas ainda não identificado"}</p>
        </div>
        {totalPages != null && totalPages > 0 && (
          <Progress value={Math.min(100, (processedPages / totalPages) * 100)} aria-label="Páginas processadas" />
        )}
        {job.data.last_progress_at && (
          <p className="text-xs text-muted-foreground">Último progresso: {formatDate(job.data.last_progress_at)}</p>
        )}
      </div>

      {isProcessing && (
        <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/50 dark:text-blue-300">
          <UploadCloud className="h-5 w-5 animate-pulse shrink-0" />
          <p>{job.data.status === "UPLOADED" ? "O arquivo está na fila de processamento." : "O PDF está sendo lido página por página. O conteúdo salvo e os itens identificados aparecem abaixo conforme o processamento avança."}</p>
        </div>
      )}

      <section className="rounded-lg border bg-card p-4 space-y-3" aria-labelledby="pdf-pages-title">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="pdf-pages-title" className="font-semibold">Conteúdo preservado do PDF</h3>
          {pages.data && pages.data.total > 0 && (
            <nav aria-label="Navegação entre páginas extraídas">
              <Pagination offset={pageOffset} total={pages.data.total} pageSize={1} onChange={setPageOffset} />
            </nav>
          )}
        </div>
        <p className="text-sm text-muted-foreground">Consulte o texto, as imagens e os avisos de cada página, inclusive quando nenhum produto foi identificado.</p>
        {pages.isError ? (
          <QueryError error={pages.error} retry={() => { pages.refetch(); }} />
        ) : pages.isPending ? (
          <p className="text-sm text-muted-foreground">Carregando páginas...</p>
        ) : pages.data.items.length ? (
          pages.data.items.map((page) => <ExtractedPage key={page.id} page={page} readOnly={readOnly} />)
        ) : (
          <p className="text-sm text-muted-foreground">Nenhuma página preservada disponível{isProcessing ? " ainda. A lista será atualizada durante a leitura." : "."}</p>
        )}
      </section>

      {isImported && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/50 dark:text-emerald-300">
          <p className="font-medium">Importação concluída!</p>
          <p>
            {job.data.total_imported || 0} produtos cadastrados no sistema. Caso existam itens ignorados ou pendentes que você deseje cadastrar, basta clicar em &quot;Aprovar&quot; no item e confirmar novamente.
          </p>
        </div>
      )}

      {!isProcessing && (
        <div className="flex items-center justify-between bg-muted/40 p-3 rounded-lg border text-sm text-muted-foreground">
          <p>
            Revise os dados antes de cadastrar. Corrija os itens incompletos ou marque como Ignorar aqueles que não devem entrar no cadastro.
          </p>
          <Button
            size="sm"
            variant="ghost"
            disabled={readOnly || pendingEdits > 0 || update.isPending}
            onClick={async () => {
              setBusy(true);
              try {
                for (const item of items.data.items) {
                  if (item.status === "DETECTED" && !item.is_out_of_stock && item.normalized_code && item.normalized_name) {
                    await update.mutateAsync({ itemId: item.id, data: { status: "APPROVED" } });
                  }
                }
                  toast.success("Aprovações do lote exibido salvas.");
              } catch (e) {
                toast.error(errorMessage(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            Aprovar os itens exibidos
          </Button>
        </div>
      )}

      {!items.data.items.length && !isProcessing && (
        <div className="text-center py-12 border rounded-lg bg-card">
          <p className="text-muted-foreground">Nenhum produto identificado neste lote. Consulte o conteúdo preservado das páginas acima.</p>
        </div>
      )}

      <div className="space-y-3">
        {!!items.data.total && <h3 className="font-semibold">Produtos identificados para revisão</h3>}
        {items.data.items.map((item) => (
          <Item key={`${item.id}:${item.updated_at}`} item={item} readOnly={readOnly} />
        ))}
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pt-2">
        <Pagination offset={offset} total={items.data.total} onChange={setOffset} />
        {!isProcessing && (
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

function ExtractedPage({ page, readOnly }: { page: ImportPage; readOnly: boolean }) {
  const cache = useQueryClient();
  const [working, setWorking] = useState(false);
  async function action(kind: string) {
    setWorking(true);
    try {
      const path = `/api/v1/imports/${page.import_id}/pages/${page.page_number}`;
      await apiClient.post(path + (kind === "manual" ? "/items" : `/retry?ocr=${kind === "ocr"}`), kind === "manual" ? {} : undefined);
      await Promise.all(["import", "imports", "import-items", "import-pages"].map(key => cache.invalidateQueries({ queryKey: [key] })));
      toast.success(kind === "manual" ? "Item criado para preenchimento e revisão na lista de produtos." : "Página enviada para releitura.");
    } catch (error) { toast.error(errorMessage(error)); }
    finally { setWorking(false); }
  }
  const pageStatus = {
    EXTRACTED: "Conteúdo extraído",
    NEEDS_REVIEW: "Conteúdo precisa de revisão",
    EMPTY: "Sem conteúdo extraído",
    FAILED: "Falha nesta página",
  }[page.status] || page.status;

  return (
    <div className="space-y-3 border-t pt-3">
      <div className="flex flex-wrap gap-2">
        <Button disabled={readOnly || working} variant="outline" onClick={() => action("retry")}>Reler página sem decisões</Button>
        <Button disabled={readOnly || working} variant="outline" onClick={() => action("ocr")}>Reler página com OCR</Button>
        <Button disabled={readOnly || working} variant="outline" onClick={() => action("manual")}>Adicionar produto desta página</Button>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <h4 className="font-semibold">Página {page.page_number}</h4>
        <span>{pageStatus}</span>
        <span className="text-muted-foreground">{page.product_count} produtos identificados</span>
      </div>
      {page.error_message && <p role="alert" className="text-sm text-destructive">{page.error_message}</p>}
      {!!page.warnings?.length && (
        <ul className="list-disc space-y-1 rounded-lg border border-amber-200 bg-amber-50 py-2 pl-7 pr-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
          {page.warnings.map((warning, index) => <li key={index}>{warning}</li>)}
        </ul>
      )}
      {page.product_count === 0 && (
        <p className="text-sm text-muted-foreground">Esta página não gerou produtos. O conteúdo disponível permanece abaixo para consulta.</p>
      )}
      <details className="rounded border p-3" open>
        <summary className="cursor-pointer text-sm font-medium">Texto extraído da página</summary>
        {page.raw_text?.trim() ? (
          <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded bg-muted/40 p-3 text-xs leading-relaxed">{page.raw_text}</pre>
        ) : (
          <p className="mt-3 text-sm text-muted-foreground">Nenhum texto foi extraído desta página.</p>
        )}
      </details>
      {!!page.text_blocks?.length && (
        <details className="rounded border p-3">
          <summary className="cursor-pointer text-sm font-medium">Blocos de texto e posições ({page.text_blocks.length})</summary>
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded bg-muted/40 p-3 text-xs">{JSON.stringify(page.text_blocks, null, 2)}</pre>
        </details>
      )}
      {!!page.image_paths?.length && (
        <details className="rounded border p-3">
          <summary className="cursor-pointer text-sm font-medium">Imagens preservadas ({page.image_paths.length})</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {page.image_paths.map((path, index) => {
              const url = `/api/v1/storage/${path.split("/").map(encodeURIComponent).join("/")}`;
              return (
                <a key={`${path}:${index}`} href={url} target="_blank" rel="noopener noreferrer" className="rounded border p-2 hover:bg-muted/40">
                  <Image src={url} width={320} height={320} alt={`Imagem ${index + 1} extraída da página ${page.page_number}`} unoptimized className="max-h-64 w-full object-contain" />
                  <span className="mt-2 block text-xs text-muted-foreground">Abrir imagem {index + 1}</span>
                </a>
              );
            })}
          </div>
        </details>
      )}
    </div>
  );
}

function Item({ item, readOnly }: { item: ImportItem; readOnly: boolean }) {
  const cache = useQueryClient();
  const pendingEdits = useIsMutating({ mutationKey: ["review-item"] });
  const update = useUpdateImportItem();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<z.infer<typeof editSchema>>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      normalized_dimensions: item.normalized_dimensions || "",
      normalized_color: item.normalized_color || "",
      normalized_pcs_per_box: item.normalized_pcs_per_box == null ? "" : String(item.normalized_pcs_per_box),
      normalized_name: item.normalized_name || item.raw_name || "",
      normalized_code: item.normalized_code || "",
      normalized_price: item.normalized_price != null ? String(item.normalized_price) : "",
    },
  });

  const save = handleSubmit(async (values) => {
    try {
      await update.mutateAsync({
        itemId: item.id,
        data: { ...values, normalized_pcs_per_box: values.normalized_pcs_per_box ? Number(values.normalized_pcs_per_box) : null, normalized_color: values.normalized_color || null, normalized_dimensions: values.normalized_dimensions || null, normalized_price: values.normalized_price || null },
      });
      toast.success("Item atualizado.");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  });

  const disabled = readOnly || pendingEdits > 0 || update.isPending || item.status === "IMPORTED";
  const sourcePage = item.raw_data?.page_number;

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
          {typeof sourcePage === "number" && <span className="text-xs text-muted-foreground">Página {sourcePage} do PDF</span>}
        </div>
        <div className="flex gap-1.5">
          {item.is_out_of_stock && <Button disabled={disabled} variant="outline" size="sm" onClick={async () => {
            try {
              await apiClient.post(`/api/v1/imports/${item.import_id}/items/${item.id}/unavailable`);
              await cache.invalidateQueries({queryKey: ["import-items"]});
              await cache.invalidateQueries({queryKey: ["import"]});
              toast.success("Fornecedor marcado como indisponível para este produto.");
            } catch (error) { toast.error(errorMessage(error)); }
          }}>Atualizar disponibilidade</Button>}
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
          <label className="text-xs">Cor<Input disabled={disabled} {...register("normalized_color")} /></label>
          <label className="text-xs">Dimensões<Input disabled={disabled} {...register("normalized_dimensions")} /></label>
          <label className="text-xs">Peças por caixa<Input disabled={disabled} inputMode="numeric" {...register("normalized_pcs_per_box")} /></label>
          {errors.normalized_pcs_per_box && <p role="alert">{errors.normalized_pcs_per_box.message}</p>}
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
      {item.error_message && <p role="alert" className="text-sm text-destructive">{item.error_message}</p>}
    </div>
  );
}
