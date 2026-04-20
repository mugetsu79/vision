import { useQuery } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export type Model = components["schemas"]["ModelResponse"];

export function useModels() {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: ["models", accessToken ? "authenticated" : "anonymous"],
    enabled: Boolean(accessToken),
    staleTime: 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/models");

      if (error) {
        throw toApiError(error, "Failed to load models.");
      }

      return data ?? [];
    },
  });
}
