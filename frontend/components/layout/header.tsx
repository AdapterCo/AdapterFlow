"use client";

import { usePathname } from "next/navigation";
import { Menu, LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Sidebar } from "./sidebar";
import { toast } from "sonner";

const getPageTitle = (pathname: string) => {
  if (pathname === "/") return "Dashboard";
  if (pathname.startsWith("/products")) return "Produtos";
  if (pathname.startsWith("/imports")) return "Importações";
  if (pathname.startsWith("/suppliers")) return "Fornecedores";
  if (pathname.startsWith("/pricing")) return "Precificação";
  if (pathname.startsWith("/marketplaces")) return "Marketplaces";
  if (pathname.startsWith("/publications")) return "Publicações";
  if (pathname.startsWith("/inventory")) return "Estoque";
  if (pathname.startsWith("/orders")) return "Pedidos";
  if (pathname.startsWith("/sales")) return "Vendas";
  if (pathname.startsWith("/reports")) return "Relatórios";
  if (pathname.startsWith("/settings")) return "Configurações";
  return "";
};

export function Header() {
  const pathname = usePathname();
  const title = getPageTitle(pathname);

  const handleLogout = async () => {
    try {
      await fetch("/api/v1/auth/logout", { method: "POST" });
      toast.success("Sessão encerrada com sucesso.");
      window.location.assign("/login");
    } catch {
      window.location.assign("/login");
    }
  };

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-white px-4 lg:px-6">
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden shrink-0">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="p-0 w-64">
          <Sidebar />
        </SheetContent>
      </Sheet>

      <div className="flex flex-1 items-center justify-between">
        <h1 className="text-lg font-semibold">{title}</h1>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground border rounded-full px-3 py-1 bg-zinc-50">
            <User className="h-3.5 w-3.5 text-zinc-500" />
            <span className="font-medium text-foreground">Operador</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 h-8 gap-1.5"
            title="Encerrar sessão"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Sair</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
