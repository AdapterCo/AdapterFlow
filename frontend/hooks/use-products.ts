import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { ProductWithDetails, PaginatedResponse, Status } from "@/types";

export function useProducts(skip = 0, limit = 100, search?: string, status?: Status | "") {
  return useQuery({
    queryKey: ["products", skip, limit, search, status],
    queryFn: () => {
      const params = new URLSearchParams({ skip: skip.toString(), limit: limit.toString() });
      if (search) params.append("search", search);
      if (status) params.append("status", status);
      
      return apiClient.get<PaginatedResponse<ProductWithDetails>>(`/api/v1/products?${params.toString()}`);
    },
  });
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ["product", id],
    queryFn: () => apiClient.get<ProductWithDetails>(`/api/v1/products/${id}`),
    enabled: !!id,
  });
}
