import { useQuery } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export type Model = components["schemas"]["ModelResponse"];
export type RuntimeArtifact = components["schemas"]["RuntimeArtifactResponse"];

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

export function useRuntimeArtifactsByModelId(modelIds: string[]) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const uniqueModelIds = Array.from(new Set(modelIds)).sort();

  return useQuery({
    queryKey: [
      "model-runtime-artifacts",
      accessToken ? "authenticated" : "anonymous",
      uniqueModelIds.join("|"),
    ],
    enabled: Boolean(accessToken) && uniqueModelIds.length > 0,
    staleTime: 0,
    queryFn: async () => {
      const entries = await Promise.all(
        uniqueModelIds.map(async (modelId) => {
          const { data, error } = await apiClient.GET(
            "/api/v1/models/{model_id}/runtime-artifacts",
            {
              params: { path: { model_id: modelId } },
            },
          );

          if (error) {
            throw toApiError(error, "Failed to load runtime artifacts.");
          }

          return [modelId, data ?? []] as const;
        }),
      );

      return Object.fromEntries(entries) as Record<string, RuntimeArtifact[]>;
    },
  });
}
