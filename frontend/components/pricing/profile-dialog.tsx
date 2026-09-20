"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PricingProfile } from "@/types";
import { useCreatePricingProfile, useUpdatePricingProfile } from "@/hooks/use-pricing";
import { pricingInputSchema, pricingFields, emptyPricing } from "@/lib/pricing-form";
import { errorMessage } from "@/lib/utils";
import { toast } from "sonner";
const schema = pricingInputSchema.extend({ name: z.string().trim().min(1), description: z.string(), source_notes: z.string().trim().min(1, "Informe a origem das taxas e custos."), channel: z.enum(["CUSTOM", "MERCADO_LIVRE", "SHOPEE", "AMAZON", "TIKTOK"]), listing_type_id: z.enum(["", "gold_special", "gold_pro"]), is_default: z.boolean(), is_active: z.boolean() });
type Values = z.infer<typeof schema>;
type Props = { open: boolean; onOpenChange: (open: boolean) => void; profileToEdit?: PricingProfile | null };
export function ProfileDialog(props: Props) { return props.open ? <Editor key={props.profileToEdit?.id || "new"} {...props} /> : null; }
function Editor({ open, onOpenChange, profileToEdit: profile }: Props) {
  const create = useCreatePricingProfile(); const update = useUpdatePricingProfile();
  const defaults: Values = { ...emptyPricing, name: profile?.name || "", description: profile?.description || "", source_notes: profile?.source_notes || "", channel: profile?.channel || "CUSTOM", listing_type_id: profile?.listing_type_id || "", is_default: profile?.is_default || false, is_active: profile?.is_active ?? true };
  for (const [key] of pricingFields) defaults[key] = profile?.[key] ?? "";
  if (profile) defaults.rounding_rule = profile.rounding_rule as Values["rounding_rule"];
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: defaults });
  const submit = handleSubmit(async values => {
    try {
      const payload = { ...values, fixed_fee_threshold: values.fixed_fee_threshold || null, free_shipping_threshold: values.free_shipping_threshold || null, free_shipping_cost: values.free_shipping_cost || null, listing_type_id: values.listing_type_id || null };
      if (profile) await update.mutateAsync({ id: profile.id, data: payload }); else await create.mutateAsync(payload);
      toast.success("Perfil salvo. Recalcule os preços afetados."); onOpenChange(false);
    } catch (error) { toast.error(errorMessage(error)); }
  });
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>{profile ? "Editar perfil" : "Novo perfil"}</DialogTitle><DialogDescription>Informe somente taxas e custos com fonte conhecida. Nenhum valor é presumido.</DialogDescription></DialogHeader>
    <form onSubmit={submit} className="space-y-3">
      <label className="flex gap-2"><input type="checkbox" {...register("is_active")} />Perfil ativo</label>
      <label className="block">Nome<Input {...register("name")} /></label>
      <label className="block">Canal<select className="block w-full border p-2" {...register("channel")}>{["CUSTOM", "MERCADO_LIVRE", "SHOPEE", "AMAZON", "TIKTOK"].map(c => <option key={c}>{c}</option>)}</select></label>
      <label className="block">Tipo de anúncio Mercado Livre<select className="block w-full border p-2" {...register("listing_type_id")}><option value="">Não informado</option><option value="gold_special">Clássico</option><option value="gold_pro">Premium</option></select></label>
      {pricingFields.map(([key, label]) => <label className="block" key={key}>{label}<Input inputMode="decimal" {...register(key)} />{errors[key] && <span role="alert" className="text-red-700">{errors[key]?.message}</span>}</label>)}
      <label className="block">Arredondamento<select className="block w-full border p-2" {...register("rounding_rule")}>{["EXACT", "ENDS_90", "ENDS_99", "ROUND_INTEGER"].map(r => <option key={r}>{r}</option>)}</select></label>
      <label className="block">Fonte e data das taxas/custos<Input {...register("source_notes")} /></label>
      <label className="block">Notas<Input {...register("description")} /></label>
      <label><input type="checkbox" {...register("is_default")} /> Perfil padrão do canal</label>
      {Object.keys(errors).length > 0 && <p role="alert">Revise os campos obrigatórios e decimais (com ponto).</p>}
      <Button disabled={isSubmitting} type="submit">Salvar</Button>
    </form></DialogContent></Dialog>;
}
