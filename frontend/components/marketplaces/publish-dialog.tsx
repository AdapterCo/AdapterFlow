"use client";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { QueryError } from "@/components/data-state";
import { useMarketplacesOverview, usePredictCategory, usePublishToMercadoLivre, useCategoryAttributes } from "@/hooks/use-marketplaces";
import { useDebounce } from "@/hooks/use-debounce";
import { ProductWithDetails, ProductChannelPrice } from "@/types";
import { errorMessage, formatCurrency } from "@/lib/utils";
import { toast } from "sonner";
import Link from "next/link";
const schema = z.object({ account_id: z.string().uuid(), title: z.string().trim().min(1).max(60), category_id: z.string().regex(/^MLB[0-9]+$/), listing_type_id: z.enum(["gold_special", "gold_pro"]), available_quantity: z.string().regex(/^[1-9][0-9]*$/), condition: z.enum(["new", "used", "not_specified"]), attributes: z.record(z.string(), z.string()) });
type Values = z.infer<typeof schema>;
type Props = { open: boolean; onOpenChange: (open: boolean) => void; product: ProductWithDetails; selectedChannelPrice?: ProductChannelPrice | null };
export function PublishDialog(props: Props) { return props.open ? <Editor {...props} /> : null; }
function Editor({ open, onOpenChange, product, selectedChannelPrice: price }: Props) {
  const overview = useMarketplacesOverview(); const publish = usePublishToMercadoLivre(); const [requestId] = useState(() => crypto.randomUUID());
  const { register, control, setValue, handleSubmit, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { account_id: "", title: product.name.slice(0, 60), category_id: "", available_quantity: "", attributes: {} } });
  const title = useWatch({ control, name: "title" }); const account = useWatch({ control, name: "account_id" }); const category = useWatch({ control, name: "category_id" });
  const debouncedTitle = useDebounce(title || "", 500); const predictions = usePredictCategory(debouncedTitle, account || ""); const attributes = useCategoryAttributes(category || "", account || "");
  const submit = handleSubmit(async values => {
    if (!price || price.is_stale) { toast.error("Recalcule o preço antes de publicar."); return; }
    try {
      const result = await publish.mutateAsync({ ...values, product_id: product.id, pricing_profile_id: price.pricing_profile_id, request_id: requestId, available_quantity: Number(values.available_quantity), attributes: Object.entries(values.attributes).filter(([, value]) => value.trim()).map(([id, value_name]) => ({ id, value_name: value_name.trim() })) });
      toast.success(`Resposta do Mercado Livre registrada: ${result.status}.`);
      if (result.error_message) toast.warning(result.error_message);
      onOpenChange(false);
    } catch (e) { toast.error(errorMessage(e)); }
  });
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>Revisar anúncio Mercado Livre</DialogTitle><DialogDescription>Confirme estoque, condição e classificação com dados reais. Preço: {formatCurrency(price?.calculated_price)}</DialogDescription></DialogHeader>
    {overview.isError ? <QueryError error={overview.error} retry={() => overview.refetch()} /> : <form onSubmit={submit} className="space-y-3">
      <label className="block">Conta verificada<select className="block w-full border p-2" {...register("account_id")}><option value="">Selecione</option>{overview.data?.accounts.filter(a => a.marketplace === "MERCADO_LIVRE" && a.is_active && a.verified_at && !a.connection_error).map(a => <option key={a.id} value={a.id}>{a.account_name}</option>)}</select></label>
      <label className="block">Título<Input maxLength={60} {...register("title")} /></label>
      <label className="block">Categoria confirmada<Input {...register("category_id")} /></label>
      {predictions.isError && <p role="alert">Não foi possível consultar sugestões: {errorMessage(predictions.error)}</p>}
      {predictions.data?.map(p => <Button key={p.category_id} type="button" variant="outline" onClick={() => { setValue("category_id", p.category_id); setValue("attributes", {}); }}>Selecionar {p.category_name}</Button>)}
      <label className="block">Tipo de anúncio (deve corresponder ao perfil)<select className="block w-full border p-2" {...register("listing_type_id")}><option value="">Selecione</option><option value="gold_special">Clássico</option><option value="gold_pro">Premium</option></select></label>
      <label className="block">Estoque disponível confirmado<Input inputMode="numeric" {...register("available_quantity")} /></label>
      <label className="block">Condição real<select className="block w-full border p-2" {...register("condition")}><option value="">Selecione</option><option value="new">Novo</option><option value="used">Usado</option><option value="not_specified">Não especificada</option></select></label>
      {attributes.isError && <QueryError error={attributes.error} retry={() => attributes.refetch()} />}
      {attributes.data?.filter(a => !a.tags?.read_only).map(a => <label className="block" key={a.id}>{a.name}{a.tags?.required ? " *" : ""}<Input {...register(`attributes.${a.id}`)} list={`attribute-${a.id}`} /><datalist id={`attribute-${a.id}`}>{a.values?.map(v => <option key={v.id} value={v.name} />)}</datalist></label>)}
      {!!Object.keys(errors).length && <p role="alert">Preencha conta, categoria, tipo, quantidade e condição.</p>}
      {publish.isError && <p role="alert">{errorMessage(publish.error)} <Link className="underline" href="/publications">Consultar tentativas</Link></p>}
      <Button type="submit" disabled={publish.isPending || publish.isSuccess || attributes.isFetching || attributes.isError || !attributes.data || !price || price.is_stale}>{publish.isPending ? "Validando e publicando…" : "Publicar dados revisados"}</Button>
    </form>}
  </DialogContent></Dialog>;
}
