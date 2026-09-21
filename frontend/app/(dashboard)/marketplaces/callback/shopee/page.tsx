"use client";

import React, { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useShopeeCallback } from "@/hooks/use-marketplaces";
import { Loader2, CheckCircle2, AlertTriangle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

function ShopeeCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const shopIdStr = searchParams.get("shop_id");
  const state = searchParams.get("state") || "";
  const errorParam = searchParams.get("error");
  const errorDescription = searchParams.get("error_description") || searchParams.get("msg");

  const callbackMutation = useShopeeCallback();
  const hasStarted = useRef(false);

  useEffect(() => {
    if (errorParam) {
      toast.error(
        `Autorização da Shopee cancelada ou recusada: ${errorDescription || errorParam}`
      );
      return;
    }

    const shopId = shopIdStr ? parseInt(shopIdStr, 10) : null;

    if (code && shopId && !hasStarted.current) {
      hasStarted.current = true;
      callbackMutation.mutate(
        { code, shop_id: shopId, state },
        {
          onSuccess: (acc) => {
            toast.success(
              `Loja "${acc.account_name}" conectada com sucesso à Shopee!`
            );
            router.push("/marketplaces");
          },
          onError: (err: unknown) => {
            toast.error(
              (err instanceof Error ? err.message : "") || "Falha ao concluir autenticação com a Shopee."
            );
          },
        }
      );
    }
  }, [code, shopIdStr, state, errorParam, errorDescription, callbackMutation, router]);

  const shopId = shopIdStr ? parseInt(shopIdStr, 10) : null;
  const isInvalid = Boolean(errorParam) || !code || !shopId;

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center max-w-md mx-auto p-6 space-y-4">
      {isInvalid ? (
        <>
          <div className="h-14 w-14 rounded-full bg-rose-100 dark:bg-rose-950/40 flex items-center justify-center text-rose-600">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold text-foreground">
            {errorParam ? "Autorização não concluída na Shopee" : "Retorno incompleto da Shopee"}
          </h2>
          <p className="text-sm text-muted-foreground">
            {errorParam
              ? errorDescription || "A Shopee retornou um erro durante o processo de autorização."
              : "Não foram recebidos os parâmetros de autenticação da Shopee (code ou shop_id). Inicie novamente pelo botão Autorizar Loja na Shopee."}
          </p>
          <Button variant="outline" onClick={() => router.push("/marketplaces")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar para Marketplaces
          </Button>
        </>
      ) : callbackMutation.isPending || (!callbackMutation.isSuccess && !callbackMutation.isError) ? (
        <>
          <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto" />
          <h2 className="text-xl font-bold text-foreground">Conectando à Shopee</h2>
          <p className="text-sm text-muted-foreground">
            Validando assinatura HMAC-SHA256, gerando tokens da loja {shopIdStr}...
          </p>
        </>
      ) : callbackMutation.isSuccess ? (
        <>
          <div className="h-14 w-14 rounded-full bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold text-foreground">Loja Shopee Conectada!</h2>
          <p className="text-sm text-muted-foreground">
            Redirecionando para o painel de marketplaces...
          </p>
        </>
      ) : (
        <>
          <div className="h-14 w-14 rounded-full bg-rose-100 dark:bg-rose-950/40 flex items-center justify-center text-rose-600">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold text-foreground">Falha na Autenticação</h2>
          <p className="text-sm text-muted-foreground">
            {callbackMutation.error?.message ||
              "Não foi possível concluir a troca de tokens com a Shopee."}
          </p>
          <Button variant="outline" onClick={() => router.push("/marketplaces")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar para Marketplaces
          </Button>
        </>
      )}
    </div>
  );
}

export default function ShopeeCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center min-h-[50vh] text-center max-w-md mx-auto p-6 space-y-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto" />
          <p className="text-sm text-muted-foreground">Carregando retorno da Shopee...</p>
        </div>
      }
    >
      <ShopeeCallbackContent />
    </Suspense>
  );
}
