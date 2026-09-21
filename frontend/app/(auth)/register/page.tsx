"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Eye, EyeOff, Lock, Mail, User, Building, ArrowRight, Loader2, Check } from "lucide-react";

const registerSchema = z
  .object({
    fullName: z.string().trim().min(3, "Nome completo deve ter no mínimo 3 caracteres."),
    storeName: z.string().trim().min(2, "Nome da loja ou empresa obrigatório."),
    email: z.string().trim().email("Informe um e-mail válido."),
    password: z.string().min(8, "A senha deve ter no mínimo 8 caracteres."),
    confirmPassword: z.string().min(8, "Confirmação de senha obrigatória."),
    terms: z.boolean().refine((val) => val === true, {
      message: "Você precisa aceitar os Termos e Política de Privacidade.",
    }),
  })

  .refine((data) => data.password === data.confirmPassword, {
    message: "As senhas digitadas não coincidem.",
    path: ["confirmPassword"],
  });

type RegisterValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      storeName: "",
      email: "",
      password: "",
      confirmPassword: "",
      terms: true,
    },
  });

  const password = useWatch({ control, name: "password" }) || "";

  // Password strength helper
  const hasMinLength = password.length >= 8;
  const hasNumber = /[0-9]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const strengthScore = [hasMinLength, hasNumber, hasUpper].filter(Boolean).length;

  const onSubmit = async (values: RegisterValues) => {
    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 900));
      toast.success(`Conta "${values.storeName}" cadastrada com sucesso! Redirecionando...`);
      router.push("/marketplaces");
    } catch {
      toast.error("Não foi possível criar a conta. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2 text-center sm:text-left">
        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Crie sua conta AdapterFlow
        </h2>
        <p className="text-sm text-muted-foreground">
          Comece a automatizar seus catálogos e publicações multicanal hoje mesmo.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <User className="h-3.5 w-3.5 text-muted-foreground" />
              Seu Nome
            </label>
            <Input
              placeholder="Carlos Silva"
              autoComplete="name"
              className="h-10"
              {...register("fullName")}
            />
            {errors.fullName && (
              <p className="text-xs text-destructive mt-1 font-medium">
                {errors.fullName.message}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Building className="h-3.5 w-3.5 text-muted-foreground" />
              Nome da Empresa / Loja
            </label>
            <Input
              placeholder="Minha Loja E-commerce"
              className="h-10"
              {...register("storeName")}
            />
            {errors.storeName && (
              <p className="text-xs text-destructive mt-1 font-medium">
                {errors.storeName.message}
              </p>
            )}
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <Mail className="h-3.5 w-3.5 text-muted-foreground" />
            E-mail Corporativo
          </label>
          <Input
            type="email"
            placeholder="contato@empresa.com.br"
            autoComplete="email"
            className="h-10"
            {...register("email")}
          />
          {errors.email && (
            <p className="text-xs text-destructive mt-1 font-medium">
              {errors.email.message}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-muted-foreground" />
              Senha (mín. 8 caracteres)
            </label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                className="h-10 pr-10"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-muted-foreground" />
              Confirmar Senha
            </label>
            <Input
              type={showPassword ? "text" : "password"}
              placeholder="••••••••"
              className="h-10"
              {...register("confirmPassword")}
            />
          </div>
        </div>

        {errors.password && (
          <p className="text-xs text-destructive font-medium">{errors.password.message}</p>
        )}
        {errors.confirmPassword && (
          <p className="text-xs text-destructive font-medium">{errors.confirmPassword.message}</p>
        )}

        {/* Indicador de força de senha */}
        {password.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Segurança da senha</span>
              <span className="font-semibold text-foreground">
                {strengthScore === 3 ? "Forte" : strengthScore === 2 ? "Média" : "Fraca"}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-1.5 h-1.5">
              <div
                className={`rounded-full ${
                  strengthScore >= 1 ? "bg-orange-500" : "bg-muted"
                }`}
              />
              <div
                className={`rounded-full ${
                  strengthScore >= 2 ? "bg-orange-500" : "bg-muted"
                }`}
              />
              <div
                className={`rounded-full ${
                  strengthScore === 3 ? "bg-emerald-500" : "bg-muted"
                }`}
              />
            </div>
            <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground pt-1">
              <span className={`flex items-center gap-1 ${hasMinLength ? "text-emerald-600 dark:text-emerald-400 font-medium" : ""}`}>
                <Check className="h-3 w-3" /> 8+ dígitos
              </span>
              <span className={`flex items-center gap-1 ${hasNumber ? "text-emerald-600 dark:text-emerald-400 font-medium" : ""}`}>
                <Check className="h-3 w-3" /> Número
              </span>
              <span className={`flex items-center gap-1 ${hasUpper ? "text-emerald-600 dark:text-emerald-400 font-medium" : ""}`}>
                <Check className="h-3 w-3" /> Letra maiúscula
              </span>
            </div>
          </div>
        )}

        <div className="flex items-start space-x-2 pt-2">
          <input
            type="checkbox"
            id="terms"
            className="h-4 w-4 mt-0.5 rounded border-input text-orange-600 focus:ring-orange-500 cursor-pointer"
            {...register("terms")}
          />
          <label htmlFor="terms" className="text-xs text-muted-foreground cursor-pointer select-none leading-normal">
            Concordo com os{" "}
            <span className="underline hover:text-foreground">Termos de Serviço</span> e com a{" "}
            <span className="underline hover:text-foreground">Política de Privacidade</span> do AdapterFlow.
          </label>
        </div>
        {errors.terms && (
          <p className="text-xs text-destructive font-medium">{errors.terms.message}</p>
        )}

        <Button
          type="submit"
          className="w-full h-10 bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white font-semibold shadow-md shadow-orange-500/20"
          disabled={loading}
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Criando sua conta...
            </>
          ) : (
            <>
              Criar Conta e Começar
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </form>

      <div className="text-center pt-2">
        <p className="text-xs text-muted-foreground">
          Já possui uma conta?{" "}
          <Link
            href="/login"
            className="font-semibold text-orange-600 hover:text-orange-700 dark:text-orange-400 hover:underline"
          >
            Fazer login
          </Link>
        </p>
      </div>
    </div>
  );
}
