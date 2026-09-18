"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useProduct } from "@/hooks/use-products";
import { formatCurrency, formatDate } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ArrowLeft, Loader2, Image as ImageIcon } from "lucide-react";

export default function ProductDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const router = useRouter();
  const { data: product, isLoading } = useProduct(resolvedParams.id);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="text-center py-10">
        <h2 className="text-xl font-semibold">Produto não encontrado</h2>
        <Button variant="link" onClick={() => router.push("/products")}>Voltar para produtos</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push("/products")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold tracking-tight">{product.name}</h2>
          <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
            <span>SKU: {product.sku}</span>
            <span>•</span>
            <Badge variant="outline">{product.status}</Badge>
          </div>
        </div>
      </div>

      <Tabs defaultValue="geral" className="w-full">
        <TabsList className="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent">
          <TabsTrigger value="geral" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4">
            Dados Gerais
          </TabsTrigger>
          <TabsTrigger value="fornecedor" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4">
            Fornecedor
          </TabsTrigger>
          <TabsTrigger value="imagens" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4">
            Imagens
          </TabsTrigger>
          <TabsTrigger value="historico" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent py-3 px-4">
            Histórico de Custos
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="geral" className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-6 rounded-md border">
            <div className="space-y-4">
              <div>
                <span className="text-sm font-medium text-muted-foreground block">Nome do Produto</span>
                <span>{product.name || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">SKU</span>
                <span>{product.sku || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">Marca</span>
                <span>{product.brand || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">Modelo</span>
                <span>{product.model || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">EAN</span>
                <span>{product.ean || "-"}</span>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <span className="text-sm font-medium text-muted-foreground block">Cor</span>
                <span>{product.color || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">Dimensões</span>
                <span>{product.dimensions || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">Peso</span>
                <span>{product.weight ? `${product.weight} kg` : "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">GTIN</span>
                <span>{product.gtin || "-"}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground block">Criado em</span>
                <span>{formatDate(product.created_at)}</span>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="fornecedor" className="pt-6">
          <div className="space-y-6">
            {(!product.supplier_data || product.supplier_data.length === 0) ? (
              <div className="text-center p-8 bg-white border rounded-md text-muted-foreground">
                Nenhum dado de fornecedor associado a este produto.
              </div>
            ) : (
              product.supplier_data.map((sd) => (
                <div key={sd.id} className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-6 rounded-md border">
                  <div className="space-y-4">
                    <div>
                      <span className="text-sm font-medium text-muted-foreground block">Fornecedor</span>
                      <span>{sd.supplier?.name || "Desconhecido"}</span>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-muted-foreground block">Código no Fornecedor</span>
                      <span>{sd.supplier_code || "-"}</span>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <span className="text-sm font-medium text-muted-foreground block">Custo Atual</span>
                      <span className="font-medium text-lg">{formatCurrency(sd.current_cost)}</span>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-muted-foreground block">Peças por Caixa (PCS/CX)</span>
                      <span>{sd.pcs_per_box || "-"}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="imagens" className="pt-6">
          {(!product.images || product.images.length === 0) ? (
            <div className="text-center p-12 bg-white border rounded-md flex flex-col items-center">
              <ImageIcon className="h-12 w-12 text-zinc-300 mb-2" />
              <p className="text-muted-foreground">Nenhuma imagem disponível.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {product.images.map((img) => (
                <div key={img.id} className="border rounded-md overflow-hidden bg-white aspect-square relative group">
                  <img src={img.url} alt={product.name} className="w-full h-full object-contain p-2" />
                  {img.is_primary && (
                    <div className="absolute top-2 left-2">
                      <Badge className="bg-blue-500">Principal</Badge>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="historico" className="pt-6">
          <div className="rounded-md border bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Preço</TableHead>
                  <TableHead>Importação ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(!product.price_history || product.price_history.length === 0) ? (
                  <TableRow>
                    <TableCell colSpan={3} className="h-24 text-center text-muted-foreground">
                      Nenhum histórico de custos disponível.
                    </TableCell>
                  </TableRow>
                ) : (
                  product.price_history.map((ph) => (
                    <TableRow key={ph.id}>
                      <TableCell>{formatDate(ph.date)}</TableCell>
                      <TableCell className="font-medium">{formatCurrency(ph.price)}</TableCell>
                      <TableCell className="text-muted-foreground font-mono text-xs">
                        {ph.import_job_id || "-"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
