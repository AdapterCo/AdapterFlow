import Decimal from "decimal.js";
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  try {
    const decimal = new Decimal(value);
    if (!decimal.isFinite()) return "—";
    const [whole, cents] = decimal.abs().toFixed(2, Decimal.ROUND_HALF_UP).split(".");
    return `${decimal.isNegative() ? "−" : ""}R$ ${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${cents}`;
  } catch { return "—"; }
}

export function formatDecimal(value: string | null | undefined, places = 2): string {
  if (value == null || value === "") return "—";
  try { return new Decimal(value).toFixed(places, Decimal.ROUND_HALF_UP).replace(".", ","); }
  catch { return "—"; }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Não foi possível concluir a operação.";
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "-";
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return "-";
    
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return "-";
  }
}
