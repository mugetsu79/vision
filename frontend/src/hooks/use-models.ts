import { useQuery } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type Model = components["schemas"]["ModelResponse"];

export function useModels() {
  return useQuery({
    queryKey: ["models"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/models");

      if (error) {
        throw toApiError(error, "Failed to load models.");
      }

      return data ?? [];
    },
  });
}
