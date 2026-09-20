"use client";
import { useState } from "react";
import { useMarketplacesOverview, useDisconnectAccount } from "@/hooks/use-marketplaces";
import { Button } from "@/components/ui/button";
import { QueryError } from "@/components/data-state";
import { apiClient } from "@/lib/api";
import { formatDate, errorMessage } from "@/lib/utils";
import { toast } from "sonner";
export default function MarketplacesPage() {
  const query = useMarketplacesOverview(); const disconnect = useDisconnectAccount(); const [connecting, setConnecting] = useState(false);
  return <div className="space-y-4"><h2 className="text-2xl font-bold">Marketplaces</h2><Button disabled={query.isFetching} onClick={() => query.refetch()}>Verificar conexões</Button>
    {query.isLoading && <p>Verificando contas no Mercado Livre…</p>}{query.isError && <QueryError error={query.error} retry={() => query.refetch()} />}
    {query.data?.channels.map(channel => <div className="rounded border p-4 space-y-2" key={channel.marketplace}><h3>{channel.name}</h3><p>{channel.marketplace !== "MERCADO_LIVRE" ? "NOT_IMPLEMENTED" : channel.is_connected ? "Conexão verificada nesta consulta" : channel.is_configured ? "Configurado; nenhuma conexão verificada" : "Configuração do servidor pendente"}</p>{channel.marketplace === "MERCADO_LIVRE" && channel.is_configured && <Button disabled={connecting} onClick={async () => { setConnecting(true); try { const result = await apiClient.get<{ auth_url: string }>("/api/v1/marketplaces/mercadolivre/auth-url"); window.location.assign(result.auth_url); } catch (e) { toast.error(errorMessage(e)); setConnecting(false); } }}>Autorizar conta</Button>}</div>)}
    {query.data && !query.data.accounts.length && <p>Nenhuma conta cadastrada.</p>}{query.data?.accounts.map(account => <div className="border p-4" key={account.id}><h3>{account.account_name}</h3><p>{!account.is_active ? "Desconectada" : account.connection_error || `Verificada em ${formatDate(account.verified_at)}`}</p><Button disabled={!account.is_active || disconnect.isPending} variant="outline" onClick={async () => { if (!confirm("Desconectar localmente? O histórico será preservado e os anúncios externos continuarão existindo.")) return; try { await disconnect.mutateAsync(account.id); toast.success("Conta desconectada localmente."); } catch (e) { toast.error(errorMessage(e)); } }}>Desconectar</Button></div>)}
  </div>;
}
