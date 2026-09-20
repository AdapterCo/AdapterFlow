import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { ImportJob, ImportItem, ImportItemUpdate, PaginatedResponse } from "@/types";

// These fields are part of the page-by-page import API and will be generated
// from OpenAPI together with the backend migration.
export type ImportJobWithProgress = ImportJob & {
  total_pages?: number | null;
  processed_pages?: number;
  last_progress_at?: string | null;
  original_file_url?: string | null;
};

export interface ImportPage {
  id: string;
  import_id: string;
  page_number: number;
  status: string;
  raw_text: string | null;
  text_blocks: unknown[] | null;
  image_paths: string[] | null;
  warnings: string[] | null;
  product_count: number;
  error_message: string | null;
  width: number | null;
  height: number | null;
}

export function useImports(skip = 0, limit = 100) {
  return useQuery({
    queryKey: ["imports", skip, limit],
    queryFn: () => apiClient.get<PaginatedResponse<ImportJobWithProgress>>(`/api/v1/imports?skip=${skip}&limit=${limit}`),
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasProcessing = data?.items?.some((i) => i.status === "PROCESSING" || i.status === "UPLOADED");
      return hasProcessing ? 3000 : false;
    },
  });
}

export function useImport(id: string) {
  return useQuery({
    queryKey: ["import", id],
    queryFn: () => apiClient.get<ImportJobWithProgress>(`/api/v1/imports/${id}`),
    enabled: !!id,
    refetchInterval: query => ["UPLOADED", "PROCESSING"].includes(query.state.data?.status || "") ? 3000 : false,
  });
}

export function useImportItems(jobId: string, skip = 0, processing = false) {
  return useQuery({
    queryKey: ["import-items", jobId, skip, processing],
    queryFn: () => apiClient.get<PaginatedResponse<ImportItem>>(`/api/v1/imports/${jobId}/items?skip=${skip}&limit=50`),
    enabled: !!jobId,
    refetchInterval: processing ? 3000 : false,
  });
}

export function useImportPages(jobId: string, skip = 0, processing = false) {
  return useQuery({
    queryKey: ["import-pages", jobId, skip, processing],
    queryFn: () => apiClient.get<PaginatedResponse<ImportPage>>(`/api/v1/imports/${jobId}/pages?skip=${skip}&limit=1`),
    enabled: !!jobId,
    refetchInterval: processing ? 3000 : false,
  });
}

export function useRetryImport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => apiClient.post<ImportJobWithProgress>(`/api/v1/imports/${jobId}/retry`),
    onSuccess: (job, jobId) => {
      queryClient.setQueryData(["import", jobId], job);
      queryClient.invalidateQueries({ queryKey: ["imports"] });
      queryClient.invalidateQueries({ queryKey: ["import-items", jobId] });
      queryClient.invalidateQueries({ queryKey: ["import-pages", jobId] });
    },
  });
}

export function useUploadImport() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ file, supplierId, onProgress }: { file: File, supplierId: string, onProgress?: (p: number) => void }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("supplier_id", supplierId);
      formData.append("importer_type", "lehmox");
      
      return apiClient.upload<ImportJob>("/api/v1/imports/upload", formData, onProgress);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["imports"] });
    },
  });
}

export function useUpdateImportItem() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationKey: ["review-item"],
    mutationFn: ({ itemId, data }: { itemId: string; data: ImportItemUpdate }) => 
      apiClient.patch<ImportItem>(`/api/v1/imports/items/${itemId}`, data),
    onSuccess: () => {
      // Invalidate specific item and its parent job's items list
      queryClient.invalidateQueries({ queryKey: ["import-items"] });
    },
  });
}

export function useApproveAllImportItems() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => apiClient.post<{ approved_count: number; skipped_count?: number }>(`/api/v1/imports/${jobId}/approve-all`),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ["import-items"] });
      queryClient.invalidateQueries({ queryKey: ["import", jobId] });
    },
  });
}

export function useConfirmImport() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (jobId: string) => apiClient.post<ImportJob>(`/api/v1/imports/${jobId}/confirm`),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ["imports"] });
      queryClient.invalidateQueries({ queryKey: ["import", jobId] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product"] });
      queryClient.invalidateQueries({ queryKey: ["product-prices"] });
      queryClient.invalidateQueries({ queryKey: ["import-items"] });
    },
  });
}


