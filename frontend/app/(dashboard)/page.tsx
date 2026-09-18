import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, Package, Truck, ArrowRight, DollarSign, Store, Send } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Bem-vindo ao AdapterFlow</h2>
        <p className="text-muted-foreground mt-1">
          Central de gerenciamento de produtos e publicação multicanal.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Upload className="h-5 w-5 text-blue-500" />
              Importar Catálogo
            </CardTitle>
            <CardDescription>
              Importe produtos de catálogos em PDF dos seus fornecedores.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="outline">
              <Link href="/imports">
                Acessar Importações
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Package className="h-5 w-5 text-orange-500" />
              Catálogo de Produtos
            </CardTitle>
            <CardDescription>
              Visualize e gerencie seu catálogo unificado de produtos e fotos.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="outline">
              <Link href="/products">
                Acessar Produtos
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <DollarSign className="h-5 w-5 text-emerald-500" />
              Motor de Precificação
            </CardTitle>
            <CardDescription>
              Simule e configure regras de margem, impostos e taxas por canal.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="outline">
              <Link href="/pricing">
                Configurar Regras
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Store className="h-5 w-5 text-yellow-500" />
              Marketplaces (Mercado Livre)
            </CardTitle>
            <CardDescription>
              Conecte suas contas OAuth 2.0 e gerencie integrações ativas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="outline">
              <Link href="/marketplaces">
                Gerenciar Contas
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Send className="h-5 w-5 text-purple-500" />
              Central de Publicações
            </CardTitle>
            <CardDescription>
              Acompanhe histórico, status de sincronização e anúncios no Meli.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="outline">
              <Link href="/publications">
                Ver Publicações
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Truck className="h-5 w-5 text-zinc-500" />
              Fornecedores
            </CardTitle>
            <CardDescription>
              Gerencie fornecedores parceiros, códigos e dados de contato.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="outline">
              <Link href="/suppliers">
                Acessar Fornecedores
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
