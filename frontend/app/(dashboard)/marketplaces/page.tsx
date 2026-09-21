"use client";

import { useState } from "react";
import Link from "next/link";
import { useMarketplacesOverview, useDisconnectAccount, useShopeeConfiguration } from "@/hooks/use-marketplaces";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { QueryError } from "@/components/data-state";
import { apiClient } from "@/lib/api";
import { formatDate, errorMessage } from "@/lib/utils";
import { toast } from "sonner";
import { useQuery } from "@tanstack/react-query";
import type { components } from "@/types/api.generated";
import {
  Store,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  PlusCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ShoppingBag,
  Send,
  Unlink,
  KeyRound,
} from "lucide-react";
import { MarketplaceCredentialsDialog } from "@/components/marketplaces/marketplace-credentials-dialog";

export default function MarketplacesPage() {
  const query = useMarketplacesOverview();
  const disconnect = useDisconnectAccount();
  const [connecting, setConnecting] = useState(false);
  const [showConfigDetails, setShowConfigDetails] = useState(false);

  const [connectingShopee, setConnectingShopee] = useState(false);
  const [showShopeeConfigDetails, setShowShopeeConfigDetails] = useState(false);
  const [credentialMarketplace, setCredentialMarketplace] = useState<"MERCADO_LIVRE" | "SHOPEE" | null>(null);

  const configuration = useQuery({
    queryKey: ["mercadolivre-configuration"],
    queryFn: () =>
      apiClient.get<components["schemas"]["MercadoLivreConfigurationResponse"]>(
        "/api/v1/marketplaces/mercadolivre/configuration"
      ),
  });

  const shopeeConfiguration = useShopeeConfiguration();

  const meliAccounts =
    query.data?.accounts.filter((acc) => acc.marketplace === "MERCADO_LIVRE" && acc.is_active) || [];
  const hasConnectedAccount = meliAccounts.length > 0;

  const shopeeAccounts =
    query.data?.accounts.filter((acc) => acc.marketplace === "SHOPEE" && acc.is_active) || [];
  const hasConnectedShopee = shopeeAccounts.length > 0;

  const handleAuthorize = async () => {
    setConnecting(true);
    try {
      const result = await apiClient.get<{ auth_url: string }>(
        "/api/v1/marketplaces/mercadolivre/auth-url"
      );
      window.location.assign(result.auth_url);
    } catch (e) {
      toast.error(errorMessage(e));
      setConnecting(false);
    }
  };

  const handleAuthorizeShopee = async () => {
    setConnectingShopee(true);
    try {
      const result = await apiClient.get<{ auth_url: string }>(
        "/api/v1/marketplaces/shopee/auth-url"
      );
      window.location.assign(result.auth_url);
    } catch (e) {
      toast.error(errorMessage(e));
      setConnectingShopee(false);
    }
  };

  const handleDisconnect = async (accountId: string, accountName: string) => {
    if (
      !confirm(
        `Desconectar a conta "${accountName}" localmente? O histórico será preservado e os anúncios continuarão existindo no Mercado Livre.`
      )
    ) {
      return;
    }
    try {
      await disconnect.mutateAsync(accountId);
      toast.success(`Conta "${accountName}" desconectada localmente.`);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Marketplaces & Integrações</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            Gerencie suas contas conectadas e canais de venda para publicação multicanal.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={query.isFetching}
          onClick={() => {
            query.refetch();
            toast.info("Verificando status das contas...");
          }}
          className="self-start sm:self-auto"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${query.isFetching ? "animate-spin" : ""}`} />
          Verificar Conexões
        </Button>
      </div>

      {query.isError && <QueryError error={query.error} retry={() => query.refetch()} />}

      {/* Seção Canal Mercado Livre */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Store className="h-5 w-5 text-amber-500" />
            Canal Mercado Livre
          </h3>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs flex items-center gap-1.5"
              onClick={() => setCredentialMarketplace("MERCADO_LIVRE")}
            >
              <KeyRound className="h-3.5 w-3.5 text-amber-500" />
              Credenciais da API
            </Button>
            {hasConnectedAccount && (
              <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Conectado
              </Badge>
            )}
          </div>
        </div>

        {hasConnectedAccount ? (
          /* Card de Contas Conectadas */
          <div className="grid gap-4">
            {meliAccounts.map((account) => (
              <Card key={account.id} className="border-emerald-200 bg-emerald-50/20 dark:bg-emerald-950/10">
                <CardHeader className="pb-3">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div>
                      <CardTitle className="text-xl flex items-center gap-2">
                        <span>{account.account_name}</span>
                        <Badge variant="outline" className="text-emerald-700 border-emerald-300">
                          {account.site_id || "MLB"}
                        </Badge>
                      </CardTitle>
                      <CardDescription className="mt-1">
                        Seller ID: <span className="font-mono">{account.seller_id}</span>
                        {account.verified_at && (
                          <> · Verificado em: {formatDate(account.verified_at)}</>
                        )}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button asChild size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                        <Link href="/publications">
                          <Send className="mr-2 h-4 w-4" />
                          Ver Publicações
                        </Link>
                      </Button>
                      <Button asChild size="sm" variant="outline">
                        <Link href="/products">
                          <ShoppingBag className="mr-2 h-4 w-4" />
                          Publicar Produtos
                        </Link>
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        disabled={disconnect.isPending}
                        onClick={() => handleDisconnect(account.id, account.account_name)}
                        title="Desconectar conta"
                      >
                        <Unlink className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                {account.connection_error && (
                  <CardContent className="pt-0 pb-3">
                    <div className="rounded-md bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      <span>{account.connection_error}</span>
                    </div>
                  </CardContent>
                )}
              </Card>
            ))}

            {/* Opção secundária e discreta para conectar outra conta ou ver config */}
            <div className="flex flex-wrap items-center justify-between text-xs text-muted-foreground pt-1 px-1">
              <span>Sua conta já está apta para publicar e validar anúncios no Mercado Livre.</span>
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setShowConfigDetails(!showConfigDetails)}
                >
                  {showConfigDetails ? <ChevronUp className="h-3 w-3 mr-1" /> : <ChevronDown className="h-3 w-3 mr-1" />}
                  {showConfigDetails ? "Ocultar detalhes técnicos" : "Ver dados da aplicação"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  disabled={connecting}
                  onClick={handleAuthorize}
                >
                  <PlusCircle className="h-3 w-3 mr-1" />
                  Conectar outra conta
                </Button>
              </div>
            </div>

            {/* Detalhes de Configuração Técnicos (Recolhível) */}
            {showConfigDetails && configuration.data && (
              <div className="rounded-lg border bg-muted/30 p-4 text-xs space-y-2 text-muted-foreground">
                <p className="font-semibold text-foreground">Configuração da Aplicação Mercado Livre:</p>
                <p>App ID: <span className="font-mono">{configuration.data.app_id || "Não informado"}</span></p>
                <p className="break-all">Redirect URI: <span className="font-mono">{configuration.data.redirect_uri || "Não informado"}</span></p>
                {configuration.data.issues.map((issue) => (
                  <p key={issue} className="text-destructive font-medium">{issue}</p>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* Card de Conexão quando NÃO tem conta vinculada */
          <Card className="border-dashed border-2">
            <CardHeader>
              <CardTitle className="text-lg">Conectar sua conta do Mercado Livre</CardTitle>
              <CardDescription>
                Vincule sua conta de vendedor para publicar anúncios automáticos e sincronizar preços.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {configuration.isError && (
                <QueryError error={configuration.error} retry={() => configuration.refetch()} />
              )}
              {configuration.data && configuration.data.issues.length > 0 && (
                <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800 space-y-1">
                  {configuration.data.issues.map((issue) => (
                    <p key={issue}>• {issue}</p>
                  ))}
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                A autorização é feita diretamente no site seguro do Mercado Livre via OAuth 2.0.
              </p>
            </CardContent>
            <CardFooter className="flex justify-between items-center gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <Button
                  disabled={connecting || (configuration.data && !configuration.data.ready)}
                  onClick={handleAuthorize}
                  className="bg-amber-500 hover:bg-amber-600 text-black font-semibold"
                >
                  <ExternalLink className="mr-2 h-4 w-4" />
                  {connecting ? "Redirecionando..." : "Autorizar Conta no Mercado Livre"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCredentialMarketplace("MERCADO_LIVRE")}
                >
                  <KeyRound className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
                  Configurar Credenciais
                </Button>
              </div>
              {configuration.data && (
                <span className="text-xs text-muted-foreground">
                  App ID: {configuration.data.app_id || "Não configurado"}
                </span>
              )}
            </CardFooter>
          </Card>
        )}
      </div>

      {/* Seção Canal Shopee */}
      <div className="space-y-4 pt-4 border-t">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <ShoppingBag className="h-5 w-5 text-orange-500" />
            Canal Shopee
          </h3>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs flex items-center gap-1.5"
              onClick={() => setCredentialMarketplace("SHOPEE")}
            >
              <KeyRound className="h-3.5 w-3.5 text-orange-500" />
              Credenciais da API
            </Button>
            {hasConnectedShopee && (
              <Badge className="bg-orange-600 hover:bg-orange-700 text-white flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Conectado
              </Badge>
            )}
          </div>
        </div>

        {hasConnectedShopee ? (
          <div className="grid gap-4">
            {shopeeAccounts.map((account) => (
              <Card key={account.id} className="border-orange-200 bg-orange-50/20 dark:bg-orange-950/10">
                <CardHeader className="pb-3">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div>
                      <CardTitle className="text-xl flex items-center gap-2">
                        <span>{account.account_name}</span>
                        <Badge variant="outline" className="text-orange-700 border-orange-300">
                          {account.site_id || "BR"}
                        </Badge>
                      </CardTitle>
                      <CardDescription className="mt-1">
                        Shop ID: <span className="font-mono">{account.seller_id}</span>
                        {account.verified_at && (
                          <> · Verificado em: {formatDate(account.verified_at)}</>
                        )}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button asChild size="sm" className="bg-orange-600 hover:bg-orange-700 text-white">
                        <Link href="/publications">
                          <Send className="mr-2 h-4 w-4" />
                          Ver Publicações
                        </Link>
                      </Button>
                      <Button asChild size="sm" variant="outline">
                        <Link href="/products">
                          <ShoppingBag className="mr-2 h-4 w-4" />
                          Publicar Produtos
                        </Link>
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        disabled={disconnect.isPending}
                        onClick={() => handleDisconnect(account.id, account.account_name)}
                        title="Desconectar loja"
                      >
                        <Unlink className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                {account.connection_error && (
                  <CardContent className="pt-0 pb-3">
                    <div className="rounded-md bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      <span>{account.connection_error}</span>
                    </div>
                  </CardContent>
                )}
              </Card>
            ))}

            <div className="flex flex-wrap items-center justify-between text-xs text-muted-foreground pt-1 px-1">
              <span>Sua loja Shopee está apta para publicar e validar anúncios multicanal.</span>
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setShowShopeeConfigDetails(!showShopeeConfigDetails)}
                >
                  {showShopeeConfigDetails ? <ChevronUp className="h-3 w-3 mr-1" /> : <ChevronDown className="h-3 w-3 mr-1" />}
                  {showShopeeConfigDetails ? "Ocultar detalhes técnicos" : "Ver dados da aplicação Shopee"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  disabled={connectingShopee}
                  onClick={handleAuthorizeShopee}
                >
                  <PlusCircle className="h-3 w-3 mr-1" />
                  Conectar outra loja
                </Button>
              </div>
            </div>

            {showShopeeConfigDetails && shopeeConfiguration.data && (
              <div className="rounded-lg border bg-muted/30 p-4 text-xs space-y-2 text-muted-foreground">
                <p className="font-semibold text-foreground">Configuração da Shopee Open API v2:</p>
                <p>Partner ID: <span className="font-mono">{shopeeConfiguration.data.partner_id || "Não informado"}</span></p>
                <p className="break-all">Redirect URI: <span className="font-mono">{shopeeConfiguration.data.redirect_uri || "Não informado"}</span></p>
                {shopeeConfiguration.data.issues.map((issue) => (
                  <p key={issue} className="text-destructive font-medium">{issue}</p>
                ))}
              </div>
            )}
          </div>
        ) : (
          <Card className="border-dashed border-2">
            <CardHeader>
              <CardTitle className="text-lg">Conectar sua loja da Shopee</CardTitle>
              <CardDescription>
                Vincule sua loja oficial na Shopee (Open API v2) para publicar anúncios automáticos e sincronizar preços.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {shopeeConfiguration.isError && (
                <QueryError error={shopeeConfiguration.error} retry={() => shopeeConfiguration.refetch()} />
              )}
              {shopeeConfiguration.data && shopeeConfiguration.data.issues.length > 0 && (
                <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800 space-y-1">
                  {shopeeConfiguration.data.issues.map((issue) => (
                    <p key={issue}>• {issue}</p>
                  ))}
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                A autorização é realizada com assinatura HMAC-SHA256 no portal seguro de parceiros da Shopee.
              </p>
            </CardContent>
            <CardFooter className="flex justify-between items-center gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <Button
                  disabled={connectingShopee || (shopeeConfiguration.data && !shopeeConfiguration.data.ready)}
                  onClick={handleAuthorizeShopee}
                  className="bg-orange-600 hover:bg-orange-700 text-white font-semibold"
                >
                  <ExternalLink className="mr-2 h-4 w-4" />
                  {connectingShopee ? "Redirecionando..." : "Autorizar Loja na Shopee"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCredentialMarketplace("SHOPEE")}
                >
                  <KeyRound className="mr-1.5 h-3.5 w-3.5 text-orange-500" />
                  Configurar Credenciais
                </Button>
              </div>
              {shopeeConfiguration.data && (
                <span className="text-xs text-muted-foreground">
                  Partner ID: {shopeeConfiguration.data.partner_id || "Não configurado"}
                </span>
              )}
            </CardFooter>
          </Card>
        )}
      </div>

      {/* Canais Futuros (Amazon, TikTok) */}
      <div className="space-y-4 pt-4 border-t">
        <h3 className="text-lg font-semibold text-muted-foreground">Outros Canais Multicanal</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <Card className="bg-muted/10 opacity-75">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold">Amazon Brasil</CardTitle>
                <Badge variant="outline" className="text-xs">Em breve</Badge>
              </div>
              <CardDescription className="text-xs mt-1">
                Fase 5 do planejamento multicanal.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Integração via Amazon Selling Partner API (SP-API).
            </CardContent>
          </Card>

          <Card className="bg-muted/10 opacity-75">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold">TikTok Shop</CardTitle>
                <Badge variant="outline" className="text-xs">Em breve</Badge>
              </div>
              <CardDescription className="text-xs mt-1">
                Fase 6 do planejamento multicanal.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Integração para catálogo e social commerce.
            </CardContent>
          </Card>
        </div>
      </div>

      {credentialMarketplace && (
        <MarketplaceCredentialsDialog
          marketplace={credentialMarketplace}
          open={!!credentialMarketplace}
          onOpenChange={(open) => !open && setCredentialMarketplace(null)}
        />
      )}
    </div>
  );
}
