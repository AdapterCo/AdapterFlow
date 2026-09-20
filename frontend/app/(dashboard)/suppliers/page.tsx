"use client";

import { Pagination } from "@/components/data-state";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useSuppliers, useCreateSupplier, useUpdateSupplier } from "@/hooks/use-suppliers";
import { formatDate } from "@/lib/utils";
import { Supplier, SupplierCreate } from "@/types";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Badge } from "@/components/ui/badge";
import { Loader2, Plus, Pencil, AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const formSchema = z.object({
  name: z.string().trim().min(2, "O nome deve ter pelo menos 2 caracteres"),
  code: z.string().optional(),
  is_active: z.boolean(),
});

export default function SuppliersPage() {
  const [offset, setOffset] = useState(0);
  const { data, isLoading, isError, error, refetch } = useSuppliers(offset, 50);
  const createSupplier = useCreateSupplier();
  const updateSupplier = useUpdateSupplier();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      code: "",
      is_active: true,
    },
  });

  const handleOpenDialog = (supplier?: Supplier) => {
    if (supplier) {
      setEditingSupplier(supplier);
      form.reset({
        name: supplier.name,
        code: supplier.code || "",
        is_active: supplier.is_active ?? false,
      });
    } else {
      setEditingSupplier(null);
      form.reset({
        name: "",
        code: "",
      is_active: true,
      });
    }
    setIsDialogOpen(true);
  };

  const onSubmit = (values: z.infer<typeof formSchema>) => {
    const payload: SupplierCreate = {
      name: values.name.trim(),
      code: values.code?.trim() || null,
    };

    if (editingSupplier) {
      updateSupplier.mutate(
        { id: editingSupplier.id, data: { ...payload, is_active: values.is_active } },
        {
          onSuccess: () => {
            toast.success("Fornecedor atualizado com sucesso!");
            setIsDialogOpen(false);
          },
          onError: (error) => toast.error(`Erro: ${error.message}`),
        }
      );
    } else {
      createSupplier.mutate(payload, {
        onSuccess: () => {
          toast.success("Fornecedor criado com sucesso!");
          setIsDialogOpen(false);
        },
        onError: (error) => toast.error(`Erro: ${error.message}`),
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Fornecedores</h2>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="mr-2 h-4 w-4" />
          Novo Fornecedor
        </Button>
      </div>

      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>Código</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Data de Criação</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-zinc-500" />
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center text-red-600">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <AlertCircle className="h-6 w-6" />
                    <p className="text-sm font-medium">
                      {(error as Error)?.message || "Não foi possível carregar os fornecedores."}
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
                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                  Nenhum fornecedor cadastrado.
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((supplier) => (
                <TableRow key={supplier.id}>
                  <TableCell className="font-medium">{supplier.name}</TableCell>
                  <TableCell>{supplier.code || "-"}</TableCell>
                  <TableCell>
                    <Badge variant={(supplier.is_active ?? (supplier.status === "ACTIVE")) ? "default" : "secondary"}>
                      {(supplier.is_active ?? (supplier.status === "ACTIVE")) ? "Ativo" : "Inativo"}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatDate(supplier.created_at)}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleOpenDialog(supplier)}
                    >
                      <Pencil className="h-4 w-4" />
                      <span className="sr-only">Editar</span>
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && <Pagination offset={offset} total={data.total} onChange={setOffset} />}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingSupplier ? "Editar Fornecedor" : "Novo Fornecedor"}
            </DialogTitle>
            <DialogDescription>
              Insira os dados do fornecedor abaixo.
            </DialogDescription>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nome</FormLabel>
                    <FormControl>
                      <Input placeholder="Nome do fornecedor" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Código (Opcional)</FormLabel>
                    <FormControl>
                      <Input placeholder="Ex: FORN-001" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {editingSupplier && <label className="flex gap-2"><input type="checkbox" {...form.register("is_active")} />Fornecedor ativo</label>}
              <DialogFooter className="pt-4">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setIsDialogOpen(false)}
                >
                  Cancelar
                </Button>
                <Button 
                  type="submit" 
                  disabled={createSupplier.isPending || updateSupplier.isPending}
                >
                  {(createSupplier.isPending || updateSupplier.isPending) && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Salvar
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
