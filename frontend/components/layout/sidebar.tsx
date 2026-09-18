"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Package,
  Upload,
  Truck,
  DollarSign,
  Store,
  Send,
  Warehouse,
  ShoppingCart,
  TrendingUp,
  BarChart3,
  Settings,
} from "lucide-react";

const mainNavItems = [
  { title: "Dashboard", href: "/", icon: LayoutDashboard },
  { title: "Produtos", href: "/products", icon: Package },
  { title: "Importações", href: "/imports", icon: Upload },
  { title: "Fornecedores", href: "/suppliers", icon: Truck },
];

const futureNavItems = [
  { title: "Precificação", href: "/pricing", icon: DollarSign },
  { title: "Marketplaces", href: "/marketplaces", icon: Store },
  { title: "Publicações", href: "/publications", icon: Send },
  { title: "Estoque", href: "/inventory", icon: Warehouse },
  { title: "Pedidos", href: "/orders", icon: ShoppingCart },
  { title: "Vendas", href: "/sales", icon: TrendingUp },
  { title: "Relatórios", href: "/reports", icon: BarChart3 },
  { title: "Configurações", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-white">
      <div className="flex h-14 items-center border-b px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <div className="h-6 w-6 rounded-md bg-zinc-900 text-white flex items-center justify-center font-bold text-xs">
            A
          </div>
          AdapterFlow
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        <nav className="space-y-1 px-2">
          <div className="px-3 py-2 text-xs font-medium text-zinc-500 uppercase tracking-wider">
            Principal
          </div>
          {mainNavItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                pathname === item.href || (pathname.startsWith(item.href) && item.href !== "/")
                  ? "bg-zinc-100 text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.title}
            </Link>
          ))}

          <div className="mt-8 px-3 py-2 text-xs font-medium text-zinc-500 uppercase tracking-wider">
            Em Breve
          </div>
          {futureNavItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors opacity-60",
                pathname === item.href
                  ? "bg-zinc-100 text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
              )}
            >
              <div className="flex items-center gap-3">
                <item.icon className="h-4 w-4" />
                {item.title}
              </div>
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}
