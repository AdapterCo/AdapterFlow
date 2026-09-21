"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

export interface CurrentUser {
  authenticated: boolean;
  username: string;
  role: string;
}

export function useCurrentUser() {
  return useQuery<CurrentUser>({
    queryKey: ["auth-me"],
    queryFn: async () => {
      return await apiClient.get<CurrentUser>("/api/v1/auth/me");
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
