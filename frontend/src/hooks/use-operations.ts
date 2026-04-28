import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type FleetOverview = components["schemas"]["FleetOverviewResponse"];
export type FleetBootstrapRequest = components["schemas"]["FleetBootstrapRequest"];
export type FleetBootstrapResponse = components["schemas"]["FleetBootstrapResponse"];

export function fleetOverviewQueryOptions() {
  return queryOptions({
    queryKey: ["operations", "fleet"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/operations/fleet");
      if (error || !data) {
        throw toApiError(error, "Failed to load fleet operations.");
      }
      return data;
    },
  });
}

export function createBootstrapMutationOptions() {
  return {
    mutationFn: async (payload: FleetBootstrapRequest) => {
      const { data, error } = await apiClient.POST("/api/v1/operations/bootstrap", {
        body: payload,
      });
      if (error || !data) {
        throw toApiError(error, "Failed to create edge bootstrap material.");
      }
      return data;
    },
  };
}

export function useFleetOverview() {
  return useQuery(fleetOverviewQueryOptions());
}

export function useCreateBootstrapMaterial() {
  const queryClient = useQueryClient();

  return useMutation({
    ...createBootstrapMutationOptions(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["operations", "fleet"] });
    },
  });
}
