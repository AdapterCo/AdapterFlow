import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import {
  PricingProfile,
  PricingProfileCreate,
  PricingProfileUpdate,
  PriceSimulationRequest,
  PriceSimulationResponse,
  ProductChannelPrice,
} from "@/types";

export function usePricingProfiles(activeOnly = false) {
  return useQuery({
    queryKey: ["pricing-profiles", activeOnly],
    queryFn: () =>
      apiClient.get<PricingProfile[]>(
        `/api/v1/pricing/profiles?active_only=${activeOnly}`
      ),
  });
}

export function useCreatePricingProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PricingProfileCreate) =>
      apiClient.post<PricingProfile>("/api/v1/pricing/profiles", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pricing-profiles"] });
    },
  });
}

export function useUpdatePricingProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PricingProfileUpdate }) =>
      apiClient.put<PricingProfile>(`/api/v1/pricing/profiles/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pricing-profiles"] });
      queryClient.invalidateQueries({ queryKey: ["product-prices"] });
    },
  });
}

export function useDeletePricingProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`/api/v1/pricing/profiles/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pricing-profiles"] });
      queryClient.invalidateQueries({ queryKey: ["product-prices"] });
    },
  });
}

export function useSimulatePrice() {
  return useMutation({
    mutationFn: (data: PriceSimulationRequest) =>
      apiClient.post<PriceSimulationResponse>("/api/v1/pricing/simulate", data),
  });
}

export function useProductPrices(productId: string) {
  return useQuery({
    queryKey: ["product-prices", productId],
    queryFn: () =>
      apiClient.get<ProductChannelPrice[]>(
        `/api/v1/pricing/products/${productId}`
      ),
    enabled: !!productId,
  });
}

export function useCalculateProductPrice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      productId,
      pricingProfileId,
      supplierDataId,
      manualOverridePrice,
    }: {
      productId: string;
      pricingProfileId: string;
      supplierDataId: string;
      manualOverridePrice?: string | null;
    }) =>
      apiClient.post<ProductChannelPrice>(
        `/api/v1/pricing/products/${productId}/calculate`,
        {
          pricing_profile_id: pricingProfileId,
          supplier_data_id: supplierDataId,
          manual_override_price: manualOverridePrice || null,
        }
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["product-prices", variables.productId],
      });
    },
  });
}

export function useDeleteProductPrice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      productId,
      profileId,
    }: {
      productId: string;
      profileId: string;
    }) =>
      apiClient.delete(
        `/api/v1/pricing/products/${productId}/profiles/${profileId}`
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["product-prices", variables.productId],
      });
    },
  });
}
