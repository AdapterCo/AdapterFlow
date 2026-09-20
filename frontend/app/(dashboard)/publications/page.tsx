"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMarketplaceListings } from "@/hooks/use-marketplaces";
import { MarketplaceListing } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pagination, QueryError } from "@/components/data-state";
import { apiClient } from "@/lib/api";
import { formatCurrency, formatDate, errorMessage } from "@/lib/utils";
import { toast } from "sonner";
export default function Publications() {
  const [offset, setOffset] = useState(0); const query = useMarketplaceListings(undefined, undefined, undefined, offset);
  return <div className="space-y-4"><h2 className="text-2xl font-bold">Publicações e tentativas</h2><p>Dados da última resposta externa. Atualizar a lista não consulta os anúncios no marketplace.</p><Button onClick={() => query.refetch()}>Atualizar lista local</Button>{query.isError ? <QueryError error={query.error} retry={() => query.refetch()} /> : query.isLoading ? <p>Carregando…</p> : <>{!query.data?.items.length && <p>Nenhuma tentativa registrada.</p>}{query.data?.items.map(listing => <Listing key={listing.id} listing={listing} refresh={() => query.refetch()} />)}<Pagination offset={offset} total={query.data?.total || 0} onChange={setOffset} /></>}</div>;
}
const reconciliationSchema = z.object({ externalId: z.string().trim().regex(/^MLB[0-9]+$/, "Informe o ID real do anúncio, iniciado por MLB.") });
function Listing({ listing, refresh }: { listing: MarketplaceListing; refresh: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof reconciliationSchema>>({ resolver: zodResolver(reconciliationSchema), defaultValues: { externalId: listing.external_listing_id || "" } });
  const reconcile = handleSubmit(async ({ externalId }) => {
    try {
      await apiClient.post(`/api/v1/marketplaces/listings/${listing.id}/reconcile${listing.external_listing_id ? "" : `?external_id=${encodeURIComponent(externalId)}`}`);
      toast.success("Resposta externa atualizada.");
      refresh();
    } catch (error) { toast.error(errorMessage(error)); }
  });
  return <div className="rounded border p-4 space-y-2"><h3>{listing.title}</h3><p>{listing.status} · {formatCurrency(listing.price)} · Quantidade: {listing.available_quantity}</p><p>Última confirmação externa: {formatDate(listing.last_synced_at)}</p>{listing.error_message && <p role="alert">{listing.error_message}</p>}{listing.permalink && <a href={listing.permalink} target="_blank" rel="noopener noreferrer" className="underline">Abrir anúncio no Mercado Livre</a>}
    <form onSubmit={reconcile} className="space-y-2">
      {!listing.external_listing_id && <label className="block">ID real encontrado na sua conta (para reconciliar resultado incerto)<Input {...register("externalId")} /></label>}
      {errors.externalId && <p role="alert">{errors.externalId.message}</p>}
      <Button type="submit" variant="outline" disabled={isSubmitting}>Consultar anúncio real</Button>
    </form>
  </div>;
}
