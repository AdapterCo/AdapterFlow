"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  useMarketplaceCredential,
  useUpdateMarketplaceCredential,
  useDeleteMarketplaceCredential,
} from "@/hooks/use-marketplaces";
import { toast } from "sonner";
import { errorMessage } from "@/lib/utils";
import { ShieldCheck, Eye, EyeOff, KeyRound, Trash2, CheckCircle2, Lock } from "lucide-react";

interface MarketplaceCredentialsDialogProps {
  marketplace: "MERCADO_LIVRE" | "SHOPEE";
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MarketplaceCredentialsDialog({
  marketplace,
  open,
  onOpenChange,
}: MarketplaceCredentialsDialogProps) {
  const isShopee = marketplace === "SHOPEE";
  const channelName = isShopee ? "Shopee" : "Mercado Livre";

  const { data: cred, isLoading, refetch } = useMarketplaceCredential(marketplace);
  const updateMutation = useUpdateMarketplaceCredential();
  const deleteMutation = useDeleteMarketplaceCredential();

  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [redirectUri, setRedirectUri] = useState("");
  const [apiUrl, setApiUrl] = useState("");
  const [showSecret, setShowSecret] = useState(false);

  useEffect(() => {
    if (open && cred) {
      setAppId(cred.app_id || "");
      setAppSecret("");
      setRedirectUri(
        cred.redirect_uri ||
          (typeof window !== "undefined"
            ? `${window.location.origin}/marketplaces/callback${isShopee ? "/shopee" : ""}`
            : "")
      );
      setApiUrl(cred.api_url || (isShopee ? "https://partner.shopeemobile.com" : ""));
    } else if (open && !cred) {
      setAppId("");
      setAppSecret("");
      setRedirectUri(
        typeof window !== "undefined"
          ? `${window.location.origin}/marketplaces/callback${isShopee ? "/shopee" : ""}`
          : ""
      );
      setApiUrl(isShopee ? "https://partner.shopeemobile.com" : "");
    }
  }, [open, cred, isShopee]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!appId.trim()) {
      toast.error(`Informe o ${isShopee ? "Partner ID" : "App ID"}.`);
      return;
    }
    if (!cred?.has_secret && !appSecret.trim()) {
      toast.error(`Informe a chave secreta (${isShopee ? "Partner Key" : "Client Secret"}).`);
      return;
    }

    try {
      await updateMutation.mutateAsync({
        marketplace,
        data: {
          app_id: appId.trim(),
          app_secret: appSecret.trim() ? appSecret.trim() : undefined,
          redirect_uri: redirectUri.trim() || undefined,
          api_url: isShopee ? apiUrl.trim() || undefined : undefined,
        },
      });
      toast.success(`Credenciais de ${channelName} salvas e criptografadas com sucesso!`);
      refetch();
      onOpenChange(false);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const handleDelete = async () => {
    if (
      !confirm(
        `Remover as credenciais de ${channelName}? A conexão com as lojas será interrompida até novas chaves serem configuradas.`
      )
    ) {
      return;
    }
    try {
      await deleteMutation.mutateAsync(marketplace);
      toast.success(`Credenciais de ${channelName} removidas.`);
      refetch();
      onOpenChange(false);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center justify-between pr-4">
            <DialogTitle className="flex items-center gap-2 text-xl">
              <KeyRound className="h-5 w-5 text-primary" />
              Credenciais da Aplicação ({channelName})
            </DialogTitle>
            {cred?.has_secret && (
              <Badge variant="outline" className="text-emerald-600 border-emerald-300 bg-emerald-50 text-xs flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Criptografada
              </Badge>
            )}
          </div>
          <DialogDescription className="text-xs text-muted-foreground mt-1.5">
            Configure as chaves de integração da sua aplicação {channelName}. Os dados são gravados com
            criptografia AES-256 no banco de dados e usados <strong>apenas no backend</strong>, sem necessidade de editar arquivos .env.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSave} className="space-y-4 py-2">
          <div className="rounded-md border border-amber-200 bg-amber-50/60 dark:bg-amber-950/20 p-3 text-xs text-amber-900 dark:text-amber-200 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold">
              <Lock className="h-3.5 w-3.5 text-amber-600" />
              <span>Segurança e Privacidade</span>
            </div>
            <p>
              O segredo da sua aplicação nunca é enviado ou exposto ao navegador. O sistema armazena apenas um hash/preview mascarado.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="app_id">
              {isShopee ? "Partner ID (Shopee Open API)" : "App ID (Mercado Livre)"}
            </Label>
            <Input
              id="app_id"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
              placeholder={isShopee ? "Ex: 1002345" : "Ex: 1234567890123456"}
              required
              disabled={isLoading || updateMutation.isPending}
            />
            <p className="text-[11px] text-muted-foreground">
              {isShopee
                ? "ID numérico de parceiro obtido no Shopee Open Platform Console."
                : "Client ID público da sua aplicação no portal de desenvolvedores do Mercado Livre."}
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="app_secret">
                {isShopee ? "Partner Key (Chave Secreta)" : "Client Secret"}
              </Label>
              {cred?.has_secret && (
                <span className="text-[11px] font-mono text-muted-foreground">
                  Atual: {cred.secret_preview || "••••••••"}
                </span>
              )}
            </div>
            <div className="relative">
              <Input
                id="app_secret"
                type={showSecret ? "text" : "password"}
                value={appSecret}
                onChange={(e) => setAppSecret(e.target.value)}
                placeholder={
                  cred?.has_secret
                    ? "Deixe em branco para manter o segredo atual"
                    : "Cole sua chave secreta aqui"
                }
                className="pr-10 font-mono text-sm"
                disabled={isLoading || updateMutation.isPending}
              />
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                onClick={() => setShowSecret(!showSecret)}
              >
                {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground">
              {cred?.has_secret
                ? "Uma chave secreta já está salva e protegida. Preencha apenas se quiser alterá-la."
                : "Chave secreta privada. Será criptografada imediatamente no banco de dados."}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="redirect_uri">Redirect URI (URL de Retorno)</Label>
            <Input
              id="redirect_uri"
              value={redirectUri}
              onChange={(e) => setRedirectUri(e.target.value)}
              placeholder="https://seudominio.com/marketplaces/callback"
              disabled={isLoading || updateMutation.isPending}
            />
            <p className="text-[11px] text-muted-foreground">
              Deve corresponder exatamente à URL cadastrada na aplicação no portal de desenvolvedores.
            </p>
          </div>

          {isShopee && (
            <div className="space-y-2">
              <Label htmlFor="api_url">URL da API Shopee</Label>
              <Input
                id="api_url"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="https://partner.shopeemobile.com"
                disabled={isLoading || updateMutation.isPending}
              />
              <p className="text-[11px] text-muted-foreground">
                Produção: https://partner.shopeemobile.com | Testes: https://partner.test-stable.shopeemobile.com
              </p>
            </div>
          )}

          <DialogFooter className="flex flex-row items-center justify-between sm:justify-between gap-2 pt-2">
            <div>
              {cred?.has_secret && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive hover:bg-destructive/10 text-xs"
                  disabled={deleteMutation.isPending}
                  onClick={handleDelete}
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1" />
                  Remover
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
                disabled={updateMutation.isPending}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                size="sm"
                className="bg-primary text-primary-foreground"
                disabled={updateMutation.isPending}
              >
                <ShieldCheck className="h-4 w-4 mr-1.5" />
                {updateMutation.isPending ? "Salvando..." : "Salvar com Segurança"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
