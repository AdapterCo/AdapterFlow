"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useProducts } from "@/hooks/use-products";
import { useDebounce } from "@/hooks/use-debounce";
import { formatCurrency } from "@/lib/utils";
import { Status } from "@/types";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Search, Loader2, Image as ImageIcon, AlertCircle, RefreshCw } from "lucide-react";

export default function ProductsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<Status | "">("");
  
  const debouncedSearch = useDebounce(search, 350);
  const { data, isLoading, isError, error, refetch } = useProducts(0, 50, debouncedSearch, statusFilter);

  const getStatusBadge = (status: Status) => {
    switch (status) {
      case "ACTIVE":
        return <Badge className="bg-green-500">Ativo</Badge>;
      case "DRAFT":
        return <Badge variant="secondary">Rascunho</Badge>;
      case "INACTIVE":
        return <Badge variant="destructive">Inativo</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Produtos</h2>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-500" />
          <Input
            placeholder="Buscar por nome ou SKU..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={(val: Status | "all") => setStatusFilter(val === "all" ? "" : val as Status)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Status: Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Status: Todos</SelectItem>
            <SelectItem value="ACTIVE">Ativo</SelectItem>
            <SelectItem value="DRAFT">Rascunho</SelectItem>
            <SelectItem value="INACTIVE">Inativo</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">Imagem</TableHead>
              <TableHead>Nome</TableHead>
              <TableHead>SKU</TableHead>
              <TableHead>Fornecedor</TableHead>
              <TableHead>Custo</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-zinc-500" />
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-red-600">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <AlertCircle className="h-6 w-6" />
                    <p className="text-sm font-medium">
                      {(error as Error)?.message || "Não foi possível carregar os produtos."}
                    </p>
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Tentar Novamente
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  Nenhum produto cadastrado. Importe um catálogo para começar.
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((product) => (
                <TableRow 
                  key={product.id}
                  className="cursor-pointer hover:bg-zinc-50"
                  onClick={() => router.push(`/products/${product.id}`)}
                >
                  <TableCell>
                    <div className="flex h-10 w-10 items-center justify-center rounded-md border bg-zinc-50 overflow-hidden">
                      {product.primary_image ? (
                        <img 
                          src={product.primary_image.url} 
                          alt={product.name}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <ImageIcon className="h-4 w-4 text-zinc-400" />
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-medium max-w-[300px] truncate" title={product.name}>
                    {product.name}
                  </TableCell>
                  <TableCell>{product.sku}</TableCell>
                  <TableCell>
                    {product.supplier_data && product.supplier_data.length > 0 
                      ? product.supplier_data[0].supplier?.name || "-" 
                      : "-"}
                  </TableCell>
                  <TableCell>
                    {product.supplier_data && product.supplier_data.length > 0
                      ? formatCurrency(product.supplier_data[0].current_cost)
                      : "-"}
                  </TableCell>
                  <TableCell>{getStatusBadge(product.status)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
