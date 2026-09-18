import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Supplier, SupplierCreate, SupplierUpdate, PaginatedResponse } from "@/types";

export function useSuppliers(skip = 0, limit = 100) {
  return useQuery({
    queryKey: ["suppliers", skip, limit],
    queryFn: () => apiClient.get<PaginatedResponse<Supplier>>(`/api/v1/suppliers/?skip=${skip}&limit=${limit}`),
  });
}

export function useSupplier(id: string) {
  return useQuery({
    queryKey: ["supplier", id],
    queryFn: () => apiClient.get<Supplier>(`/api/v1/suppliers/${id}`),
    enabled: !!id,
  });
}

export function useCreateSupplier() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: SupplierCreate) => apiClient.post<Supplier>("/api/v1/suppliers/", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    },
  });
}

export function useUpdateSupplier() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: SupplierUpdate }) => 
      apiClient.patch<Supplier>(`/api/v1/suppliers/${id}`, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["supplier", variables.id] });
    },
  });
}
