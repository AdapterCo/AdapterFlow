import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { ImportJob, ImportItem, ImportItemUpdate, PaginatedResponse } from "@/types";

export function useImports(skip = 0, limit = 100) {
  return useQuery({
    queryKey: ["imports", skip, limit],
    queryFn: () => apiClient.get<PaginatedResponse<ImportJob>>(`/api/v1/imports?skip=${skip}&limit=${limit}`),
  });
}

export function useImport(id: string) {
  return useQuery({
    queryKey: ["import", id],
    queryFn: () => apiClient.get<ImportJob>(`/api/v1/imports/${id}`),
    enabled: !!id,
  });
}

export function useImportItems(jobId: string) {
  return useQuery({
    queryKey: ["import-items", jobId],
    queryFn: () => apiClient.get<PaginatedResponse<ImportItem>>(`/api/v1/imports/${jobId}/items?limit=1000`), // Fetching all for review phase
    enabled: !!jobId,
  });
}

export function useUploadImport() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ file, supplierId, onProgress }: { file: File, supplierId: string, onProgress?: (p: number) => void }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("supplier_id", supplierId);
      
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
    mutationFn: ({ itemId, data }: { itemId: string; data: ImportItemUpdate }) => 
      apiClient.patch<ImportItem>(`/api/v1/imports/items/${itemId}`, data),
    onSuccess: (_, variables) => {
      // Invalidate specific item and its parent job's items list
      queryClient.invalidateQueries({ queryKey: ["import-items"] });
    },
  });
}

export function useConfirmImport() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (jobId: string) => apiClient.post<{ message: string }>(`/api/v1/imports/${jobId}/confirm`),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ["imports"] });
      queryClient.invalidateQueries({ queryKey: ["import", jobId] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
