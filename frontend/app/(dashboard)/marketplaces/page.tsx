"use client";

import React from "react";
import {
  useMarketplacesOverview,
  useDisconnectAccount,
} from "@/hooks/use-marketplaces";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Store,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Unplug,
  ShieldCheck,
  RefreshCw,
  ShoppingBag,
} from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";

export default function MarketplacesPage() {
  const { data, isLoading, refetch } = useMarketplacesOverview();
  const disconnectMutation = useDisconnectAccount();

  const handleDisconnect = async (accountId: string, accountName: string) => {
    if (
      !confirm(
        `Deseja realmente desconectar a conta "${accountName}" do Mercado Livre?`
      )
    )
      return;

    try {
      await disconnectMutation.mutateAsync(accountId);
      toast.success("Conta desconectada com sucesso.");
    } catch (err: any) {
      toast.error(err.message || "Erro ao desconectar conta.");
    }
  };

  const getChannelColor = (channel: string) => {
    switch (channel) {
      case "MERCADO_LIVRE":
        return "border-yellow-400 bg-yellow-50/50 dark:bg-yellow-950/10";
      case "SHOPEE":
        return "border-orange-300 bg-orange-50/30 dark:bg-orange-950/10";
      case "AMAZON":
        return "border-blue-300 bg-blue-50/30 dark:bg-blue-950/10";
      case "TIKTOK":
        return "border-purple-300 bg-purple-50/30 dark:bg-purple-950/10";
      default:
        return "border-border bg-card";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Marketplaces & Canais</h1>
          <p className="text-sm text-muted-foreground">
            Gerenciamento centralizado de autenticações e publicação multicanal.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
          Atualizar Status
        </Button>
      </div>

      {/* Grid de Canais */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {data?.channels.map((ch) => {
          const isML = ch.marketplace === "MERCADO_LIVRE";

          return (
            <div
              key={ch.marketplace}
              className={`rounded-xl border p-6 shadow-xs flex flex-col justify-between space-y-5 transition-all ${getChannelColor(
                ch.marketplace
              )}`}
            >
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-background border flex items-center justify-center shadow-xs">
                      <Store className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-bold text-lg text-foreground">{ch.name}</h3>
                      <p className="text-xs text-muted-foreground">
                        {isML
                          ? "API Oficial Mercado Livre Brasil (MLB)"
                          : "Integração prevista no cronograma"}
                      </p>
                    </div>
                  </div>

                  {ch.is_connected ? (
                    <Badge className="bg-emerald-500 hover:bg-emerald-600 text-white flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" /> Conectado
                    </Badge>
                  ) : ch.is_configured ? (
                    <Badge variant="outline" className="text-amber-600 border-amber-300">
                      Pronto para Conectar
                    </Badge>
                  ) : isML ? (
                    <Badge variant="outline" className="text-zinc-500 border-zinc-300">
                      Requer Configuração
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-zinc-500">
                      Em Breve
                    </Badge>
                  )}
                </div>

                {/* Explicação de Status */}
                {isML ? (
                  !ch.is_configured ? (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/20 p-3.5 text-xs text-amber-900 dark:text-amber-200 space-y-1.5">
                      <div className="font-semibold flex items-center gap-1.5">
                        <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
                        Credenciais de Desenvolvedor Não Detectadas
                      </div>
                      <p className="opacity-90 leading-relaxed">
                        Para habilitar a autenticação OAuth oficial, informe as variáveis no arquivo <code>.env</code> do servidor:
                      </p>
                      <ul className="list-disc pl-4 space-y-0.5 font-mono text-[11px]">
                        <li>MERCADOLIVRE_APP_ID</li>
                        <li>MERCADOLIVRE_CLIENT_SECRET</li>
                        <li>MERCADOLIVRE_REDIRECT_URI</li>
                      </ul>
                    </div>
                  ) : ch.is_connected ? (
                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-emerald-600" />
                      <span>
                        Autenticado via OAuth 2.0. Sessão com renovação automática.
                      </span>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Credenciais validadas. Clique no botão abaixo para autorizar o acesso à sua conta de vendedor.
                    </p>
                  )
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Conforme as diretrizes de arquitetura, este canal será ativado nas próximas fases sem dados fictícios.
                  </p>
                )}
              </div>

              {/* Botões de Ação */}
              <div className="pt-3 border-t border-border/60 flex items-center justify-between">
                <span className="text-xs text-muted-foreground">
                  {ch.accounts_count > 0
                    ? `${ch.accounts_count} conta(s) ativa(s)`
                    : "0 contas conectadas"}
                </span>

                {isML && ch.is_configured && ch.auth_url && (
                  <Button
                    size="sm"
                    onClick={() => {
                      window.location.href = ch.auth_url!;
                    }}
                  >
                    <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                    Conectar Conta Mercado Livre
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Contas Conectadas */}
      <div className="rounded-xl border bg-card overflow-hidden shadow-xs space-y-0">
        <div className="px-6 py-4 border-b bg-muted/20 flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-base">Contas de Vendedores Conectadas</h3>
            <p className="text-xs text-muted-foreground">
              Tokens e credenciais armazenados com segurança.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary">
            {data?.accounts.length || 0} contas
          </span>
        </div>

        {data?.accounts.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground space-y-2">
            <ShoppingBag className="h-10 w-10 mx-auto opacity-40 mb-2" />
            <p className="font-medium text-foreground">Nenhuma conta de marketplace conectada</p>
            <p className="text-xs max-w-md mx-auto">
              Quando você autorizar sua conta do Mercado Livre via OAuth oficial, ela será exibida aqui para sincronização de anúncios e estoque.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {data?.accounts.map((acc) => (
              <div
                key={acc.id}
                className="p-5 flex flex-col sm:flex-row justify-between sm:items-center gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-base text-foreground">
                      {acc.account_name}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {acc.marketplace}
                    </Badge>
                    <Badge className="bg-emerald-500 text-[11px]">Ativa</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground flex flex-wrap gap-x-3 gap-y-1">
                    <span>Seller ID: {acc.seller_id}</span>
                    <span>•</span>
                    <span>Site: {acc.site_id}</span>
                    <span>•</span>
                    <span>Conectada em: {formatDate(acc.created_at)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/20"
                    disabled={disconnectMutation.isPending}
                    onClick={() => handleDisconnect(acc.id, acc.account_name)}
                  >
                    <Unplug className="h-4 w-4 mr-1.5" />
                    Desconectar
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
