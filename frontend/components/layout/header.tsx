"use client";

import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Sidebar } from "./sidebar";

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
        <div className="flex items-center gap-4">
          {/* Add user profile or other actions here later */}
        </div>
      </div>
    </header>
  );
}
