"use client";
import { use, useState } from "react";
import { useIsMutating } from "@tanstack/react-query";
import Image from "next/image";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useImport, useImportItems, useUpdateImportItem, useConfirmImport } from "@/hooks/use-imports";
import { ImportItem } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pagination, QueryError } from "@/components/data-state";
import { errorMessage } from "@/lib/utils";
import { toast } from "sonner";
const editSchema = z.object({ normalized_name: z.string().trim().min(1), normalized_code: z.string().trim().min(1), normalized_price: z.string().regex(/^$|^\d+(\.\d{1,4})?$/, "Use decimal com ponto, até quatro casas.") });
export default function Review({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params); const [offset, setOffset] = useState(0); const [busy, setBusy] = useState(false);
  const pendingEdits = useIsMutating({ mutationKey: ["review-item"] });
  const job = useImport(id); const items = useImportItems(id, offset, ["UPLOADED", "PROCESSING"].includes(job.data?.status || "")); const update = useUpdateImportItem(); const confirm = useConfirmImport();
  if (job.isError || items.isError) return <QueryError error={job.error || items.error} retry={() => { job.refetch(); items.refetch(); }} />;
  if (!job.data || !items.data) return <p>Carregando revisão…</p>;
  const readOnly = job.data.status !== "REVIEW_REQUIRED" || busy || confirm.isPending;
  return <div className="space-y-4"><h2 className="text-xl font-bold">Revisão: {job.data.original_filename}</h2><p>Status: {job.data.status}</p>
    {job.data.error_message && <p role="alert">{job.data.error_message}</p>}
    {["UPLOADED", "PROCESSING"].includes(job.data.status) && <p>Extração em andamento. Os resultados serão atualizados automaticamente.</p>}
    <p>Aprove ou ignore todos os itens de todas as páginas antes de confirmar. Itens esgotados aprovados serão cadastrados inativos.</p>
    <Button disabled={readOnly || pendingEdits > 0 || update.isPending} onClick={async () => { setBusy(true); try { for (const item of items.data.items) if (item.status === "DETECTED" && !item.is_out_of_stock) await update.mutateAsync({ itemId: item.id, data: { status: "APPROVED" } }); toast.success("Aprovações desta página salvas."); } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); } }}>Aprovar disponíveis desta página</Button>
    {!items.data.items.length && job.data.status === "REVIEW_REQUIRED" && <p>Nenhum item detectado.</p>}
    {items.data.items.map(item => <Item key={`${item.id}:${item.updated_at}`} item={item} readOnly={readOnly} />)}
    <Pagination offset={offset} total={items.data.total} onChange={setOffset} />
    <Button disabled={readOnly || pendingEdits > 0 || update.isPending || !items.data.total} onClick={async () => { try { const result = await confirm.mutateAsync(id); toast.success(`${result.items_imported} produtos confirmados.`); } catch (e) { toast.error(errorMessage(e)); } }}>Confirmar itens aprovados</Button>
  </div>;
}
function Item({ item, readOnly }: { item: ImportItem; readOnly: boolean }) {
  const pendingEdits = useIsMutating({ mutationKey: ["review-item"] });
  const update = useUpdateImportItem();
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof editSchema>>({ resolver: zodResolver(editSchema), defaultValues: { normalized_name: item.normalized_name || item.raw_name || "", normalized_code: item.normalized_code || "", normalized_price: item.normalized_price ?? "" } });
  const save = handleSubmit(async values => { try { await update.mutateAsync({ itemId: item.id, data: { ...values, normalized_price: values.normalized_price || null } }); toast.success("Revisão salva."); } catch (e) { toast.error(errorMessage(e)); } });
  const disabled = readOnly || pendingEdits > 0 || update.isPending || item.status === "IMPORTED";
  return <div className="rounded border p-4 space-y-3"><p>{item.status}{item.is_out_of_stock ? " · Esgotado no catálogo" : ""}</p>
    {item.image_url && <Image src={item.image_url} alt={item.raw_name || "Imagem extraída"} width={160} height={160} unoptimized className="object-contain" />}
    <p>Fonte: {item.raw_code || "Sem código"} · {item.raw_price || "Sem preço"} · {item.raw_dimensions || "Sem dimensões"}</p>
    <form onSubmit={save} className="grid gap-3 sm:grid-cols-3"><label>Nome<Input disabled={disabled} {...register("normalized_name")} /></label><label>Código do fornecedor<Input disabled={disabled} {...register("normalized_code")} /></label><label>Custo unitário<Input disabled={disabled} inputMode="decimal" {...register("normalized_price")} /></label><Button disabled={disabled} type="submit">Salvar correções</Button>{Object.keys(errors).length > 0 && <p role="alert">Revise nome, código e formato do preço.</p>}</form>
    <div className="flex gap-2">{(["APPROVED", "IGNORED", "DETECTED"] as const).map(status => <Button key={status} disabled={disabled} variant="outline" onClick={async () => { try { await update.mutateAsync({ itemId: item.id, data: { status } }); } catch (e) { toast.error(errorMessage(e)); } }}>{status === "APPROVED" ? "Aprovar" : status === "IGNORED" ? "Ignorar" : "Voltar à revisão"}</Button>)}</div>
    {item.warnings?.map((warning, index) => <p className="text-amber-800" key={index}>{warning}</p>)}
  </div>;
}
