import { useMutation, useQuery } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";
import type { components } from "@/lib/api.generated";

export type MasterBootstrapComplete =
  components["schemas"]["MasterBootstrapComplete"];
export type MasterBootstrapCompleteResponse =
  components["schemas"]["MasterBootstrapCompleteResponse"];
export type MasterBootstrapStatus =
  components["schemas"]["MasterBootstrapStatusResponse"];

export function useBootstrapStatus() {
  return useQuery({
    queryKey: ["deployment", "bootstrap", "status"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/deployment/bootstrap/status",
      );
      if (error || !data) {
        throw toApiError(error, "Failed to load first-run status.");
      }
      return data;
    },
    staleTime: 10_000,
    retry: false,
  });
}

export function useCompleteBootstrap() {
  return useMutation<
    MasterBootstrapCompleteResponse,
    Error,
    MasterBootstrapComplete
  >({
    mutationFn: async (payload) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/deployment/bootstrap/complete",
        { body: payload },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to complete first-run setup.");
      }
      return data;
    },
  });
}
