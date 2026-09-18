import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import {
  MarketplacesOverviewResponse,
  MarketplaceAccount,
  MarketplaceListingListResponse,
  MarketplaceListing,
  CategoryPredictionItem,
  PublishProductRequest,
} from "@/types";

export function useMarketplacesOverview() {
  return useQuery({
    queryKey: ["marketplaces-overview"],
    queryFn: () =>
      apiClient.get<MarketplacesOverviewResponse>("/api/v1/marketplaces/overview"),
  });
}

export function useDisconnectAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (accountId: string) =>
      apiClient.delete(`/api/v1/marketplaces/accounts/${accountId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketplaces-overview"] });
    },
  });
}

export function useMarketplaceCallback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ code, state }: { code: string; state?: string }) =>
      apiClient.post<MarketplaceAccount>(
        "/api/v1/marketplaces/mercadolivre/oauth/callback",
        { code, state }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketplaces-overview"] });
    },
  });
}

export function usePredictCategory(title: string) {
  return useQuery({
    queryKey: ["category-prediction", title],
    queryFn: () =>
      apiClient.get<CategoryPredictionItem[]>(
        `/api/v1/marketplaces/mercadolivre/categories/predict?q=${encodeURIComponent(
          title
        )}`
      ),
    enabled: !!title && title.length >= 2,
  });
}

export function usePublishToMercadoLivre() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PublishProductRequest) =>
      apiClient.post<MarketplaceListing>(
        "/api/v1/marketplaces/mercadolivre/publish",
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketplace-listings"] });
      queryClient.invalidateQueries({ queryKey: ["marketplaces-overview"] });
    },
  });
}

export function useMarketplaceListings(
  productId?: string,
  accountId?: string,
  status?: string,
  skip = 0,
  limit = 50
) {
  let url = `/api/v1/marketplaces/listings?skip=${skip}&limit=${limit}`;
  if (productId) url += `&product_id=${productId}`;
  if (accountId) url += `&account_id=${accountId}`;
  if (status) url += `&status=${status}`;

  return useQuery({
    queryKey: ["marketplace-listings", productId, accountId, status, skip, limit],
    queryFn: () => apiClient.get<MarketplaceListingListResponse>(url),
  });
}
