"use client";
import { use, useState } from "react";
import Image from "next/image";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { useProduct } from "@/hooks/use-products";
import { useProductPrices, usePricingProfiles, useCalculateProductPrice } from "@/hooks/use-pricing";
import { apiClient } from "@/lib/api";
import { formatCurrency, formatDate, errorMessage } from "@/lib/utils";
import { ProductChannelPrice, ProductWithDetails, ProductSupplierData } from "@/types";
import { QueryError } from "@/components/data-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PublishDialog } from "@/components/marketplaces/publish-dialog";
import { DREBreakdownCard } from "@/components/pricing/dre-breakdown";
import { toast } from "sonner";
const calculationSchema = z.object({ supplierId: z.string().uuid(), profileId: z.string().uuid(), manual: z.string().regex(/^$|^\d+(\.\d{1,2})?$/, "Informe preço decimal com até duas casas.") });
const schema = z.object({ name: z.string().trim().min(1), sku: z.string(), brand: z.string(), model: z.string(), ean: z.string(), gtin: z.string(), color: z.string(), dimensions: z.string(), description: z.string(), status: z.enum(["ACTIVE", "INACTIVE", "DRAFT"]) });
const fields = [["name", "Nome"], ["sku", "SKU interno"], ["brand", "Marca"], ["model", "Modelo"], ["ean", "EAN"], ["gtin", "GTIN"], ["color", "Cor"], ["dimensions", "Dimensões/compatibilidade informadas"], ["description", "Descrição"]] as const;
export default function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params); const query = useProduct(id);
  if (query.isError) return <QueryError error={query.error} retry={() => query.refetch()} />;
  if (!query.data) return <p>Carregando produto…</p>;
  return <Detail key={`${id}:${query.data.updated_at}`} product={query.data} />;
}
function Detail({ product }: { product: ProductWithDetails }) {
  const queryClient = useQueryClient(); const profiles = usePricingProfiles(true); const prices = useProductPrices(product.id); const calculate = useCalculateProductPrice();
  const calculation = useForm<z.infer<typeof calculationSchema>>({ resolver: zodResolver(calculationSchema), defaultValues: { supplierId: "", profileId: "", manual: "" } });
  const [selected, setSelected] = useState<ProductChannelPrice | null>(null);
  const defaults = { name: product.name, sku: product.sku || "", brand: product.brand || "", model: product.model || "", ean: product.ean || "", gtin: product.gtin || "", color: product.color || "", dimensions: product.dimensions || "", description: product.description || "", status: product.status };
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: defaults });
  const save = handleSubmit(async values => { try { const payload = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value === "" ? null : value])); await apiClient.patch(`/api/v1/products/${product.id}`, payload); await queryClient.invalidateQueries({ queryKey: ["product", product.id] }); queryClient.invalidateQueries({ queryKey: ["products"] }); toast.success("Produto atualizado."); } catch (e) { toast.error(errorMessage(e)); } });
  return <div className="space-y-6"><h2 className="text-2xl font-bold">{product.name}</h2>
    <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">{fields.map(([key, label]) => <label key={key}>{label}<Input {...register(key)} /></label>)}<label>Status<select className="block border p-2" {...register("status")}>{["ACTIVE", "INACTIVE", "DRAFT"].map(status => <option key={status}>{status}</option>)}</select></label>{Object.keys(errors).length > 0 && <p role="alert">Confira os campos obrigatórios.</p>}<Button disabled={isSubmitting} type="submit">Salvar produto</Button></form>
    <h3 className="font-semibold">Fornecedores e custos</h3>{product.supplier_data.length ? product.supplier_data.map(s => <div key={s.id} className="border p-3"><p>{s.supplier?.name || "Fornecedor não informado"} · Código: {s.supplier_code} · {s.is_active && s.supplier?.is_active ? "Ativo" : "Inativo"}</p><SupplierLinkEditor productId={product.id} link={s} /><p>Custo: {formatCurrency(s.current_cost)} · Peças por caixa: {s.pcs_per_box ?? "Não informado"}</p><details><summary>Histórico de custos</summary>{s.prices.map(p => <p key={p.id}>{formatDate(p.effective_at)} · {formatCurrency(p.price)} · Importação: {p.import_id || "Não informada"}</p>)}</details></div>) : <p>Nenhum fornecedor associado.</p>}
    <div className="flex flex-wrap gap-3">{product.images.map(image => <Image key={image.id} src={image.url} width={180} height={180} unoptimized alt={product.name} className="object-contain" />)}{!product.images.length && <p>Nenhuma imagem cadastrada.</p>}</div>
    <h3 className="font-semibold">Calcular preço de canal</h3>{profiles.isError && <QueryError error={profiles.error} retry={() => profiles.refetch()} />}
    <form className="space-y-3" onSubmit={calculation.handleSubmit(async ({ supplierId, profileId, manual }) => { try { await calculate.mutateAsync({ productId: product.id, pricingProfileId: profileId, supplierDataId: supplierId, manualOverridePrice: manual || null }); toast.success("Preço calculado."); } catch (e) { toast.error(errorMessage(e)); } })}>
    <label className="block">Origem do custo<select className="block w-full border p-2" {...calculation.register("supplierId")}><option value="">Selecione explicitamente o fornecedor</option>{product.supplier_data.filter(s => s.is_active && s.supplier?.is_active && s.current_cost !== null).map(s => <option key={s.id} value={s.id}>{s.supplier?.name} · {formatCurrency(s.current_cost)}</option>)}</select></label>
    <label className="block">Perfil<select className="block w-full border p-2" {...calculation.register("profileId")}><option value="">Selecione um perfil</option>{profiles.data?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label className="block">Preço manual opcional<Input inputMode="decimal" {...calculation.register("manual")} /></label>
    <Button type="submit" disabled={calculate.isPending}>Calcular</Button>{Object.keys(calculation.formState.errors).length > 0 && <p role="alert">Selecione fornecedor, perfil e confira o preço manual.</p>}</form>
    {prices.isError && <QueryError error={prices.error} retry={() => prices.refetch()} />}{!prices.isLoading && !prices.isError && !prices.data?.length && <p>Nenhum preço calculado.</p>}
    {prices.data?.map(price => <div className="rounded border p-4 space-y-3" key={price.id}><p>{price.profile_name} · {formatCurrency(price.calculated_price)} {price.is_stale && "· DESATUALIZADO: recalcule"}</p>{price.breakdown && <DREBreakdownCard dre={price.breakdown} suggestedPrice={price.calculated_price} />}{price.channel === "MERCADO_LIVRE" && <Button disabled={price.is_stale || product.status !== "ACTIVE"} onClick={() => setSelected(price)}>Revisar publicação</Button>}</div>)}
    <PublishDialog open={!!selected} onOpenChange={open => { if (!open) setSelected(null); }} product={product} selectedChannelPrice={selected} />
  </div>;
}

const linkSchema = z.object({ is_active: z.boolean(), activation_reason: z.string().trim().min(1).max(2000) });
function SupplierLinkEditor({ productId, link }: { productId: string; link: ProductSupplierData }) {
  const cache = useQueryClient();
  const form = useForm<z.infer<typeof linkSchema>>({ resolver: zodResolver(linkSchema), defaultValues: { is_active: link.is_active, activation_reason: "" } });
  return <form className="my-2 flex flex-wrap gap-2" onSubmit={form.handleSubmit(async values => {
    try { await apiClient.patch(`/api/v1/products/${productId}/suppliers/${link.id}`, values); await cache.invalidateQueries({ queryKey: ["product", productId] }); cache.invalidateQueries({ queryKey: ["product-prices", productId] }); toast.success("Vínculo atualizado; recalcule o preço."); } catch (error) { toast.error(errorMessage(error)); }
  })}><label><input type="checkbox" {...form.register("is_active")} /> Vínculo ativo</label><label>Motivo/fonte da revisão<Input {...form.register("activation_reason")} /></label><Button type="submit" disabled={form.formState.isSubmitting}>Salvar vínculo</Button>{form.formState.errors.activation_reason && <p role="alert">Informe a fonte que justifica a alteração.</p>}</form>;
}
