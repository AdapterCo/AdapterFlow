"use client";

import React, { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMarketplaceCallback } from "@/hooks/use-marketplaces";
import { Loader2, CheckCircle2, AlertTriangle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const state = searchParams.get("state") || undefined;
  const errorParam = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  const callbackMutation = useMarketplaceCallback();
  const hasStarted = useRef(false);

  useEffect(() => {
    if (errorParam) {
      toast.error(
        `Autorização cancelada ou recusada: ${errorDescription || errorParam}`
      );
      return;
    }

    if (code && state && !hasStarted.current) {
      hasStarted.current = true;
      callbackMutation.mutate(
        { code, state },
        {
          onSuccess: (acc) => {
            toast.success(
              `Conta "${acc.account_name}" conectada com sucesso ao Mercado Livre!`
            );
            router.push("/marketplaces");
          },
          onError: (err: unknown) => {
            toast.error(
              (err instanceof Error ? err.message : "") || "Falha ao concluir autenticação com o Mercado Livre."
            );
          },
        }
      );
    }
  }, [code, state, errorParam, errorDescription, callbackMutation, router]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center max-w-md mx-auto p-6 space-y-4">
      {errorParam || !code || !state ? (
        <>
          <div className="h-14 w-14 rounded-full bg-rose-100 dark:bg-rose-950/40 flex items-center justify-center text-rose-600">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold text-foreground">{errorParam ? "Autorização não concluída" : "Conexão não iniciada pelo AdapterFlow"}</h2>
          <p className="text-sm text-muted-foreground">
            {errorParam
              ? errorDescription || "O Mercado Livre retornou um erro na autorização. Inicie novamente pelo botão Autorizar conta."
              : "Este retorno está sem o código ou o identificador de segurança. A permissão pode existir no Mercado Livre, mas a conexão local não foi concluída. Volte para Marketplaces e clique em Autorizar conta; não use um link montado manualmente."}
          </p>
          <Button variant="outline" onClick={() => router.push("/marketplaces")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar para Marketplaces
          </Button>
        </>
      ) : callbackMutation.isPending || (Boolean(code) && Boolean(state) && !hasStarted.current) ? (
        <>
          <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto" />
          <h2 className="text-xl font-bold text-foreground">Conectando ao Mercado Livre</h2>
          <p className="text-sm text-muted-foreground">
            Trocando tokens de segurança e vinculando sua conta de vendedor...
          </p>
        </>
      ) : callbackMutation.isSuccess ? (
        <>
          <div className="h-14 w-14 rounded-full bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold text-foreground">Conta Conectada!</h2>
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
              "Não foi possível concluir a autenticação OAuth."}
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

export default function MarketplaceCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[40vh]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
