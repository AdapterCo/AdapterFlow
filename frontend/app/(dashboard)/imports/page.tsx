"use client";

import { Pagination, QueryError } from "@/components/data-state";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { useImports, useRetryImport, useUploadImport } from "@/hooks/use-imports";
import { useSuppliers } from "@/hooks/use-suppliers";
import { errorMessage, formatDate } from "@/lib/utils";

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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Loader2, Plus, UploadCloud, File, X } from "lucide-react";
import { toast } from "sonner";

const uploadSchema = z.object({ supplier: z.string().uuid("Selecione um fornecedor.") });

export default function ImportsPage() {
  const router = useRouter();
  const [offset, setOffset] = useState(0);
  const { data, isLoading, error, refetch } = useImports(offset, 50);
  const [supplierOffset, setSupplierOffset] = useState(0);
  const { data: suppliersData, error: supplierError, refetch: refetchSuppliers } = useSuppliers(supplierOffset, 50);
  const uploadImport = useUploadImport();
  const retryImport = useRetryImport();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const form = useForm<z.infer<typeof uploadSchema>>({ resolver: zodResolver(uploadSchema), defaultValues: { supplier: "" } });
  const selectedSupplier = form.watch("supplier");
  const setSelectedSupplier = (value: string) => form.setValue("supplier", value);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file && file.name.toLowerCase().endsWith(".pdf")) {
      if (file.size > 200 * 1024 * 1024) {
        toast.error("O arquivo excede o limite de 200MB.");
        return;
      }
      setSelectedFile(file);
    } else {
      toast.error("Por favor, selecione um arquivo PDF válido.");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    maxSize: 200 * 1024 * 1024,
    onDropRejected: () => toast.error("Selecione um único PDF de até 200 MB."),
  });

  const handleUpload = form.handleSubmit(() => {
    if (!selectedSupplier) {
      toast.error("Selecione um fornecedor.");
      return;
    }
    if (!selectedFile) {
      toast.error("Selecione um arquivo PDF.");
      return;
    }

    setUploadProgress(0);
    uploadImport.mutate(
      {
        file: selectedFile,
        supplierId: selectedSupplier,
        onProgress: (p) => setUploadProgress(p),
      },
      {
        onSuccess: (job) => {
          toast.success("Arquivo recebido. Acompanhe a leitura das páginas e revise os resultados.");
          setIsDialogOpen(false);
          setSelectedFile(null);
          setSelectedSupplier("");
          setUploadProgress(0);
          router.push(`/imports/${job.id}/review`);
        },
        onError: (err) => {
          toast.error(`Erro ao enviar: ${err.message}`);
          setUploadProgress(0);
        },
      }
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
      case "IMPORTED":
        return <Badge className="bg-green-500">Concluído</Badge>;
      case "UPLOADED":
        return <Badge variant="outline">Aguardando processamento</Badge>;
      case "PROCESSING":
        return (
          <Badge className="bg-blue-600 text-white flex items-center gap-1.5 animate-pulse">
            <Loader2 className="h-3 w-3 animate-spin" />
            Processando
          </Badge>
        );
      case "REVIEW_REQUIRED":
      case "REVIEW_NEEDED":
        return <Badge className="bg-orange-500">Revisão Necessária</Badge>;
      case "FAILED":
        return <Badge variant="destructive">Falha</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Importações</h2>
        <Button onClick={() => setIsDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nova Importação
        </Button>
      </div>

      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Arquivo</TableHead>
              <TableHead>Fornecedor</TableHead>
              <TableHead>Data</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-center">Itens (Det / Imp / Err)</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-zinc-500" />
                </TableCell>
              </TableRow>
            ) : error ? (<TableRow><TableCell colSpan={6}><QueryError error={error} retry={refetch} /></TableCell></TableRow>) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  Nenhuma importação realizada.
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((job) => (
                <TableRow 
                  key={job.id} 
                  className="cursor-pointer hover:bg-zinc-50"
                  onClick={() => router.push(`/imports/${job.id}/review`)}
                >
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <File className="h-4 w-4 text-zinc-400" />
                      {job.original_filename}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium text-zinc-800">
                      {job.supplier?.name || "Fornecedor não identificado"}
                    </span>
                  </TableCell>
                  <TableCell>{formatDate(job.created_at)}</TableCell>
                  <TableCell>
                    <div className="space-y-2">
                      {getStatusBadge(job.status)}
                      {job.total_pages != null && (
                        <p className="text-xs text-muted-foreground">{job.processed_pages ?? 0}/{job.total_pages} páginas processadas</p>
                      )}
                      {job.status === "FAILED" && job.error_message && (
                        <p className="max-w-xs text-xs text-destructive">{job.error_message}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-2 text-sm">
                      <span className="text-zinc-600 font-medium" title="Detectados">{job.items_detected}</span>
                      <span className="text-zinc-300">/</span>
                      <span className="text-green-600 font-medium" title="Importados">{job.items_imported}</span>
                      <span className="text-zinc-300">/</span>
                      <span className="text-red-600 font-medium" title="Erros">{job.items_failed}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex flex-wrap justify-end gap-2">
                    {job.status === "FAILED" && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={retryImport.isPending}
                        onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            await retryImport.mutateAsync(job.id);
                            toast.success("Importação recolocada na fila, sem reenviar o arquivo.");
                            router.push(`/imports/${job.id}/review`);
                          } catch (error) {
                            toast.error(errorMessage(error));
                          }
                        }}
                      >
                        {retryImport.isPending && retryImport.variables === job.id ? "Retomando..." : "Tentar novamente"}
                      </Button>
                    )}
                    <Button 
                      size="sm" 
                      variant={job.status === "IMPORTED" || job.status === "COMPLETED" ? "outline" : "default"}
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/imports/${job.id}/review`);
                      }}
                    >
                      {["UPLOADED", "PROCESSING"].includes(job.status)
                        ? "Acompanhar leitura"
                        : job.status === "IMPORTED" || job.status === "COMPLETED"
                        ? "Ver produtos"
                        : "Ver páginas e revisar"}
                    </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && <Pagination offset={offset} total={data.total} onChange={setOffset} />}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Nova Importação</DialogTitle>
            <DialogDescription>
              Envie um arquivo PDF do catálogo do fornecedor para extração automática.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 pt-4">
            <p className="text-sm text-muted-foreground">Envie o catálogo completo. A leitura percorre todas as páginas e preserva o conteúdo disponível. Os produtos identificados serão apresentados para revisão antes de entrar no cadastro.</p>
            <div className="space-y-2">
              <label className="text-sm font-medium">Fornecedor</label>
              {supplierError ? <QueryError error={supplierError} retry={refetchSuppliers} /> : (!suppliersData?.items || suppliersData.items.length === 0) ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/20 p-3 text-xs text-amber-800 dark:text-amber-300 space-y-1">
                  <p>Nenhum fornecedor cadastrado na plataforma.</p>
                  <p>
                    É obrigatório associar a importação a um fornecedor.
                    <Button
                      variant="link"
                      size="sm"
                      className="p-0 h-auto ml-1 text-xs font-semibold underline text-amber-900 dark:text-amber-200"
                      onClick={() => {
                        setIsDialogOpen(false);
                        router.push("/suppliers");
                      }}
                    >
                      Cadastrar fornecedor agora
                    </Button>
                  </p>
                </div>
              ) : (
                <Select value={selectedSupplier} onValueChange={setSelectedSupplier}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione um fornecedor" />
                  </SelectTrigger>
                  <SelectContent>
                    {suppliersData?.items
                      .filter((s) => s.is_active ?? (s.status === "ACTIVE"))
                      .map((supplier) => (
                        <SelectItem key={supplier.id} value={supplier.id}>
                          {supplier.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {suppliersData && <Pagination offset={supplierOffset} total={suppliersData.total} onChange={setSupplierOffset} />}
            <div className="space-y-2">
              <label className="text-sm font-medium">Arquivo PDF</label>
              {!selectedFile ? (
                <div 
                  {...getRootProps()} 
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                    ${isDragActive ? "border-primary bg-primary/5" : "border-zinc-200 hover:border-primary/50 hover:bg-zinc-50"}`}
                >
                  <input {...getInputProps()} />
                  <UploadCloud className="mx-auto h-10 w-10 text-zinc-400 mb-4" />
                  <p className="text-sm font-medium mb-1">
                    Arraste o arquivo PDF aqui ou clique para selecionar
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Apenas arquivos .pdf até 200 MB
                  </p>
                </div>
              ) : (
                <div className="border rounded-lg p-4 flex items-center justify-between bg-zinc-50">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <File className="h-8 w-8 text-blue-500 shrink-0" />
                    <div className="truncate">
                      <p className="text-sm font-medium truncate">{selectedFile.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    onClick={() => setSelectedFile(null)}
                    disabled={uploadImport.isPending}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>

            {uploadImport.isPending && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{uploadProgress < 100 ? "Enviando arquivo..." : "Aguardando confirmação do recebimento..."}</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            )}

            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button 
                variant="outline" 
                onClick={() => setIsDialogOpen(false)}
                disabled={uploadImport.isPending}
              >
                Cancelar
              </Button>
              <Button 
                onClick={handleUpload}
                disabled={!selectedSupplier || !selectedFile || uploadImport.isPending}
              >
                {uploadImport.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Enviando...
                  </>
                ) : (
                  "Iniciar Importação"
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
