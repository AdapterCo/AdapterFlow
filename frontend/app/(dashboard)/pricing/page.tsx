"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { usePricingProfiles, useDeletePricingProfile, useSimulatePrice } from "@/hooks/use-pricing";
import { pricingInputSchema, pricingFields, emptyPricing } from "@/lib/pricing-form";
import { PricingProfile } from "@/types";
import { ProfileDialog } from "@/components/pricing/profile-dialog";
import { DREBreakdownCard } from "@/components/pricing/dre-breakdown";
import { QueryError } from "@/components/data-state";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/utils";
import { toast } from "sonner";
const schema = pricingInputSchema.extend({ cost_basis: z.string().min(1), manual_override_price: z.string() });
type Values = z.infer<typeof schema>;
export default function PricingPage() {
  const profiles = usePricingProfiles(); const simulate = useSimulatePrice(); const remove = useDeletePricingProfile();
  const [open, setOpen] = useState(false); const [editing, setEditing] = useState<PricingProfile | null>(null);
  const { register, handleSubmit, reset, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { ...emptyPricing, cost_basis: "", manual_override_price: "" } });
  const submit = handleSubmit(values => simulate.mutate({ ...values, fixed_fee_threshold: values.fixed_fee_threshold || null, free_shipping_threshold: values.free_shipping_threshold || null, free_shipping_cost: values.free_shipping_cost || null, manual_override_price: values.manual_override_price || null }));
  return <div className="space-y-6"><h2 className="text-2xl font-bold">Precificação</h2>
    <Button onClick={() => { setEditing(null); setOpen(true); }}>Novo perfil</Button>
    {profiles.isError ? <QueryError error={profiles.error} retry={() => profiles.refetch()} /> : profiles.isLoading ? <p>Carregando perfis…</p> : <div className="space-y-2">{!profiles.data?.length && <p>Nenhum perfil cadastrado.</p>}{profiles.data?.map(profile => <div key={profile.id} className="flex flex-wrap items-center gap-3 border p-3"><span>{profile.name} · {profile.channel} · {profile.is_active ? "Ativo" : "Inativo"}</span><Button variant="outline" onClick={() => { setEditing(profile); setOpen(true); }}>Editar</Button><Button variant="outline" onClick={() => { const values = { ...emptyPricing, cost_basis: "", manual_override_price: "" }; for (const [key] of pricingFields) values[key] = profile[key] ?? ""; values.rounding_rule = profile.rounding_rule as Values["rounding_rule"]; reset(values); simulate.reset(); }}>Usar na simulação</Button><Button variant="outline" disabled={!profile.is_active || remove.isPending} onClick={async () => { try { await remove.mutateAsync(profile.id); toast.success("Perfil desativado; histórico preservado."); } catch (e) { toast.error(errorMessage(e)); } }}>Desativar</Button></div>)}</div>}
    <form onSubmit={submit} className="rounded border p-4 space-y-3"><h3 className="font-semibold">Simulação com dados informados</h3><label className="block">Custo base real<Input inputMode="decimal" {...register("cost_basis")} /></label>
      <div className="grid gap-3 sm:grid-cols-2">{pricingFields.map(([key, label]) => <label key={key}>{label}<Input inputMode="decimal" {...register(key)} /></label>)}</div>
      <label className="block">Arredondamento<select className="block border p-2" {...register("rounding_rule")}>{["EXACT", "ENDS_90", "ENDS_99", "ROUND_INTEGER"].map(r => <option key={r}>{r}</option>)}</select></label>
      <label className="block">Preço manual opcional<Input inputMode="decimal" {...register("manual_override_price")} /></label>
      {!!Object.keys(errors).length && <p role="alert">Preencha os valores reais. Informe zero explicitamente quando não houver custo.</p>}
      <Button type="submit" disabled={simulate.isPending}>{simulate.isPending ? "Calculando…" : "Calcular"}</Button>
    </form>
    {simulate.isError && <QueryError error={simulate.error} retry={() => void submit()} />}
    {simulate.data && !simulate.isPending && !simulate.isError && <div><p className="text-sm">Resultado da última simulação enviada.</p><DREBreakdownCard dre={simulate.data.breakdown} suggestedPrice={simulate.data.suggested_price} /></div>}
    <ProfileDialog open={open} onOpenChange={setOpen} profileToEdit={editing} />
  </div>;
}
