import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import {
  ClonePreviewRequest,
  ClonePreviewResponse,
  CloneProductRequest,
  ProductWithDetails,
} from "@/types";

export function useClonePreview() {
  return useMutation({
    mutationFn: (data: ClonePreviewRequest) =>
      apiClient.post<ClonePreviewResponse>(
        "/api/v1/products/clone/preview",
        data
      ),
  });
}

export function useCloneProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CloneProductRequest) =>
      apiClient.post<ProductWithDetails>(
        "/api/v1/products/clone",
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
