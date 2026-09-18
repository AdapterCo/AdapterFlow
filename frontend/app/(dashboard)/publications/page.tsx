"use client";

import React, { useState } from "react";
import { useMarketplaceListings } from "@/hooks/use-marketplaces";
import { Badge } from "@/components/ui/badge";
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
  ShoppingBag,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
} from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function PublicationsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const { data, isLoading, refetch } = useMarketplaceListings(
    undefined,
    undefined,
    statusFilter || undefined
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return (
          <Badge className="bg-emerald-500 hover:bg-emerald-600 text-white flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> Ativo
          </Badge>
        );
      case "ERROR":
        return (
          <Badge variant="destructive" className="flex items-center gap-1">
            <XCircle className="h-3 w-3" /> Erro de Publicação
          </Badge>
        );
      case "PAUSED":
        return (
          <Badge variant="secondary" className="flex items-center gap-1">
            <Clock className="h-3 w-3" /> Pausado
          </Badge>
        );
      case "CLOSED":
        return (
          <Badge variant="outline" className="text-zinc-500 flex items-center gap-1">
            Finalizado
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Publicações & Anúncios</h1>
          <p className="text-sm text-muted-foreground">
            Acompanhamento centralizado de anúncios publicados nos marketplaces.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="flex h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">Todos os Status</option>
            <option value="ACTIVE">Ativos</option>
            <option value="ERROR">Com Erro</option>
            <option value="PAUSED">Pausados</option>
            <option value="CLOSED">Finalizados</option>
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Tabela de Anúncios */}
      <div className="rounded-xl border bg-card overflow-hidden shadow-xs">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Produto / Anúncio</TableHead>
              <TableHead>Canal & Conta</TableHead>
              <TableHead>ID Externo</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Preço</TableHead>
              <TableHead>Estoque</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Última Sincronização</TableHead>
              <TableHead className="text-right">Ação</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="h-32 text-center text-muted-foreground">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
                  Carregando publicações...
                </TableCell>
              </TableRow>
            ) : !data || data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="h-32 text-center text-muted-foreground">
                  <ShoppingBag className="h-8 w-8 mx-auto opacity-40 mb-2" />
                  Nenhum anúncio publicado no momento.
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((listing) => (
                <TableRow key={listing.id}>
                  <TableCell className="max-w-xs">
                    <div className="font-semibold text-foreground truncate">
                      {listing.title}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">
                      {listing.product_name || "Produto interno"}
                    </div>
                    {listing.error_message && (
                      <div className="text-xs text-rose-600 dark:text-rose-400 mt-1 line-clamp-2">
                        {listing.error_message}
                      </div>
                    )}
                  </TableCell>

                  <TableCell>
                    <div className="font-medium text-xs">{listing.marketplace}</div>
                    <div className="text-xs text-muted-foreground">
                      {listing.account_name || "-"}
                    </div>
                  </TableCell>

                  <TableCell className="font-mono text-xs">
                    {listing.external_listing_id || "-"}
                  </TableCell>

                  <TableCell className="text-xs">
                    {listing.listing_type_id === "gold_pro"
                      ? "Premium"
                      : "Clássico"}
                  </TableCell>

                  <TableCell className="font-bold text-sm">
                    R$ {parseFloat(listing.price).toFixed(2)}
                  </TableCell>

                  <TableCell className="text-sm">
                    {listing.available_quantity} un
                  </TableCell>

                  <TableCell>{getStatusBadge(listing.status)}</TableCell>

                  <TableCell className="text-xs text-muted-foreground">
                    {listing.last_synced_at
                      ? formatDate(listing.last_synced_at)
                      : "-"}
                  </TableCell>

                  <TableCell className="text-right">
                    {listing.permalink ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        asChild
                        className="text-primary hover:text-primary/80"
                      >
                        <a
                          href={listing.permalink}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Ver no Meli <ExternalLink className="h-3.5 w-3.5 ml-1" />
                        </a>
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
