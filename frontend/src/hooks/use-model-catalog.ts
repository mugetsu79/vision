import { useQuery } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export type ModelCatalogEntry = components["schemas"]["ModelCatalogEntryResponse"];

export function useModelCatalog() {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: ["model-catalog", accessToken ? "authenticated" : "anonymous"],
    enabled: Boolean(accessToken),
    staleTime: 30_000,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/model-catalog");

      if (error) {
        throw toApiError(error, "Failed to load model catalog.");
      }

      return data ?? [];
    },
  });
}
