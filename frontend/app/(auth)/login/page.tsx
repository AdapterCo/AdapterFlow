"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Eye, EyeOff, Lock, Mail, ArrowRight, Loader2 } from "lucide-react";

const loginSchema = z.object({
  username: z.string().trim().min(1, "Informe seu usuário ou e-mail cadastrado."),
  password: z.string().min(1, "Informe sua senha."),
  rememberMe: z.boolean().optional(),
});

type LoginValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
      password: "",
      rememberMe: true,
    },
  });

  const onSubmit = async (values: LoginValues) => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: values.username,
          password: values.password,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || "Nome de usuário ou senha incorretos.");
      }

      toast.success("Login realizado com sucesso! Redirecionando...");
      window.location.assign("/");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha na autenticação.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2 text-center sm:text-left">
        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Bem-vindo de volta
        </h2>
        <p className="text-sm text-muted-foreground">
          Entre com suas credenciais para acessar sua central multicanal.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <Mail className="h-3.5 w-3.5 text-muted-foreground" />
            Usuário ou E-mail
          </label>
          <div className="relative">
            <Input
              type="text"
              placeholder="adaptercobr ou seu@empresa.com"
              autoComplete="username"
              className="h-10"
              {...register("username")}
            />
          </div>
          {errors.username && (
            <p className="text-xs text-destructive mt-1 font-medium">
              {errors.username.message}
            </p>
          )}
        </div>


        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-muted-foreground" />
              Senha
            </label>
            <Link
              href="/login"
              onClick={(e) => {
                e.preventDefault();
                toast.info("Recuperação de senha via e-mail configurada no servidor.");
              }}
              className="text-xs text-orange-600 hover:text-orange-700 dark:text-orange-400 hover:underline font-medium"
            >
              Esqueceu a senha?
            </Link>
          </div>
          <div className="relative">
            <Input
              type={showPassword ? "text" : "password"}
              placeholder="••••••••"
              autoComplete="current-password"
              className="h-10 pr-10"
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              tabIndex={-1}
              title={showPassword ? "Ocultar senha" : "Ver senha"}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
          {errors.password && (
            <p className="text-xs text-destructive mt-1 font-medium">
              {errors.password.message}
            </p>
          )}
        </div>

        <div className="flex items-center space-x-2 pt-1">
          <input
            type="checkbox"
            id="rememberMe"
            className="h-4 w-4 rounded border-input text-orange-600 focus:ring-orange-500 cursor-pointer"
            {...register("rememberMe")}
          />
          <label
            htmlFor="rememberMe"
            className="text-xs text-muted-foreground cursor-pointer select-none"
          >
            Lembrar desta máquina por 30 dias
          </label>
        </div>

        <Button
          type="submit"
          className="w-full h-10 bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white font-semibold shadow-md shadow-orange-500/20"
          disabled={loading}
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Entrando...
            </>
          ) : (
            <>
              Acessar Painel
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </form>

      <div className="text-center pt-2">
        <p className="text-xs text-muted-foreground">
          Não tem uma conta ainda?{" "}
          <Link
            href="/register"
            className="font-semibold text-orange-600 hover:text-orange-700 dark:text-orange-400 hover:underline"
          >
            Criar conta gratuita
          </Link>
        </p>
      </div>
    </div>
  );
}
