"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMarketplaceCredentials } from "@/hooks/use-marketplaces";
import { MarketplaceCredentialsDialog } from "@/components/marketplaces/marketplace-credentials-dialog";
import { KeyRound, ShieldCheck, Lock, Store, ShoppingBag, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  const { data: credentials, refetch, isFetching } = useMarketplaceCredentials();
  const [activeDialogMp, setActiveDialogMp] = useState<"MERCADO_LIVRE" | "SHOPEE" | null>(null);

  const meliCred = credentials?.find((c) => c.marketplace === "MERCADO_LIVRE");
  const shopeeCred = credentials?.find((c) => c.marketplace === "SHOPEE");

  return (
    <div className="space-y-8 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Configurações do Sistema</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            Gerencie credenciais de plataformas de vendas, criptografia de dados e parâmetros de integração.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={isFetching}
          onClick={() => {
            refetch();
            toast.info("Atualizando status das credenciais...");
          }}
          className="self-start sm:self-auto"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          Atualizar Status
        </Button>
      </div>

      {/* Banner de Segurança */}
      <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 dark:bg-emerald-950/20 p-4 flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-emerald-600 mt-0.5 shrink-0" />
        <div className="text-xs space-y-1 text-emerald-950 dark:text-emerald-200">
          <p className="font-semibold text-sm">Armazenamento Seguro e Criptografado (AES-256)</p>
          <p className="text-muted-foreground">
            Todas as chaves secretas (Client Secret do Mercado Livre e Partner Key da Shopee) são criptografadas com AES-256 (Fernet) antes de serem gravadas no banco de dados.
            O backend nunca retorna chaves em texto plano para o frontend, garantindo que nenhum dado sensível seja exposto na rede ou nos navegadores.
          </p>
        </div>
      </div>

      {/* Seção Credenciais de Marketplaces */}
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-primary" />
            Credenciais de Aplicações de Venda
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Configure suas aplicações para permitir que o sistema conecte contas e publique anúncios sem precisar editar o arquivo <code>.env</code>.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Card Mercado Livre */}
          <Card className={meliCred?.has_secret ? "border-emerald-200" : "border-dashed"}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Store className="h-5 w-5 text-amber-500" />
                  Mercado Livre
                </CardTitle>
                {meliCred?.has_secret ? (
                  <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Configurado no Banco
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-amber-600 border-amber-300 text-xs flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    Pendente
                  </Badge>
                )}
              </div>
              <CardDescription className="text-xs">
                Integração via OAuth 2.0 oficial para catálogo, atributos e publicações.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">App ID:</span>
                <span className="font-mono font-medium">{meliCred?.app_id || "Não configurado"}</span>
              </div>
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">Client Secret:</span>
                <span className="font-mono">{meliCred?.has_secret ? (meliCred.secret_preview || "••••••••") : "Não configurado"}</span>
              </div>
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">Redirect URI:</span>
                <span className="font-mono truncate max-w-[200px]" title={meliCred?.redirect_uri || ""}>
                  {meliCred?.redirect_uri || "Padrão do sistema"}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground">Criptografia:</span>
                <span className="text-emerald-600 font-medium flex items-center gap-1">
                  <Lock className="h-3 w-3" />
                  AES-256 Fernet
                </span>
              </div>
            </CardContent>
            <CardFooter>
              <Button
                variant={meliCred?.has_secret ? "outline" : "default"}
                size="sm"
                className="w-full text-xs"
                onClick={() => setActiveDialogMp("MERCADO_LIVRE")}
              >
                <KeyRound className="mr-1.5 h-3.5 w-3.5" />
                {meliCred?.has_secret ? "Alterar Credenciais" : "Configurar Mercado Livre"}
              </Button>
            </CardFooter>
          </Card>

          {/* Card Shopee */}
          <Card className={shopeeCred?.has_secret ? "border-orange-200" : "border-dashed"}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <ShoppingBag className="h-5 w-5 text-orange-500" />
                  Shopee Open API v2
                </CardTitle>
                {shopeeCred?.has_secret ? (
                  <Badge className="bg-orange-600 hover:bg-orange-700 text-white text-xs flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Configurado no Banco
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-amber-600 border-amber-300 text-xs flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    Pendente
                  </Badge>
                )}
              </div>
              <CardDescription className="text-xs">
                Integração com assinatura HMAC-SHA256 para lojas Shopee Brasil.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">Partner ID:</span>
                <span className="font-mono font-medium">{shopeeCred?.app_id || "Não configurado"}</span>
              </div>
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">Partner Key:</span>
                <span className="font-mono">{shopeeCred?.has_secret ? (shopeeCred.secret_preview || "••••••••") : "Não configurado"}</span>
              </div>
              <div className="flex justify-between py-1 border-b">
                <span className="text-muted-foreground">API URL:</span>
                <span className="font-mono truncate max-w-[200px]" title={shopeeCred?.api_url || ""}>
                  {shopeeCred?.api_url || "https://partner.shopeemobile.com"}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground">Criptografia:</span>
                <span className="text-emerald-600 font-medium flex items-center gap-1">
                  <Lock className="h-3 w-3" />
                  AES-256 Fernet
                </span>
              </div>
            </CardContent>
            <CardFooter>
              <Button
                variant={shopeeCred?.has_secret ? "outline" : "default"}
                size="sm"
                className="w-full text-xs"
                onClick={() => setActiveDialogMp("SHOPEE")}
              >
                <KeyRound className="mr-1.5 h-3.5 w-3.5" />
                {shopeeCred?.has_secret ? "Alterar Credenciais" : "Configurar Shopee"}
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>

      {activeDialogMp && (
        <MarketplaceCredentialsDialog
          marketplace={activeDialogMp}
          open={!!activeDialogMp}
          onOpenChange={(open) => !open && setActiveDialogMp(null)}
        />
      )}
    </div>
  );
}
