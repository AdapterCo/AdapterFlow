import React from "react";
import Link from "next/link";
import { Zap, ShieldCheck, ShoppingCart, Sparkles } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* Left panel: Auth Form */}
      <div className="flex flex-col justify-between p-6 sm:p-10 lg:p-12">
        <div className="flex items-center justify-between">
          <Link href="/login" className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-amber-500 via-orange-500 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-orange-500/20">
              <Zap className="h-5 w-5 fill-current" />
            </div>
            <div>
              <span className="font-bold text-xl tracking-tight text-foreground flex items-center gap-1.5">
                AdapterFlow
                <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded-full bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 border border-orange-200 dark:border-orange-800">
                  Pro
                </span>
              </span>
            </div>
          </Link>
        </div>

        <div className="w-full max-w-md mx-auto my-auto py-8">
          {children}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 text-xs text-muted-foreground pt-4 border-t border-border/40">
          <span>&copy; {new Date().getFullYear()} AdapterFlow Inc. Todos os direitos reservados.</span>
          <div className="flex items-center gap-4">
            <span className="hover:text-foreground transition-colors cursor-pointer">Termos</span>
            <span className="hover:text-foreground transition-colors cursor-pointer">Privacidade</span>
            <span className="hover:text-foreground transition-colors cursor-pointer">Suporte</span>
          </div>
        </div>
      </div>

      {/* Right panel: Brand Showcase (Desktop) */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-zinc-900 via-zinc-950 to-black text-white relative overflow-hidden">
        {/* Subtle glowing orbs */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-orange-500/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex items-center gap-2 text-xs font-medium tracking-wider text-orange-400 uppercase">
          <Sparkles className="h-4 w-4" />
          <span>Hub Multicanal de Alta Performance</span>
        </div>

        <div className="relative z-10 space-y-6 max-w-lg">
          <h1 className="text-4xl font-extrabold tracking-tight leading-tight">
            Automatize seu e-commerce do catálogo à publicação multicanal.
          </h1>
          <p className="text-zinc-400 text-base leading-relaxed">
            Importe tabelas em PDF, calcule margens reais com motor DRE integrado,
            clone anúncios instantaneamente e publique no Mercado Livre e Shopee em segundos.
          </p>

          <div className="grid grid-cols-2 gap-4 pt-4">
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-1">
              <div className="flex items-center gap-2 text-orange-400 font-semibold text-sm">
                <ShoppingCart className="h-4 w-4" />
                Multicanal Nativo
              </div>
              <p className="text-xs text-zinc-400">
                Mercado Livre e Shopee integrados via APIs oficiais com regras de precificação.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-1">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                <ShieldCheck className="h-4 w-4" />
                Segurança Bancária
              </div>
              <p className="text-xs text-zinc-400">
                Criptografia de tokens com chaves restritas e proteção contra vazamentos de dados.
              </p>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between text-xs text-zinc-500 pt-6 border-t border-white/10">
          <span>Infraestrutura Segura · Criptografia Fernet AES-128</span>
          <span>Versão 2.4</span>
        </div>
      </div>
    </div>
  );
}
