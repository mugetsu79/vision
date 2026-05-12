import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type FleetOverview = components["schemas"]["FleetOverviewResponse"];
export type FleetBootstrapRequest = components["schemas"]["FleetBootstrapRequest"];
export type FleetBootstrapResponse = components["schemas"]["FleetBootstrapResponse"];
export type OperationalMemoryPattern =
  components["schemas"]["OperationalMemoryPatternResponse"];

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

export function operationalMemoryPatternsQueryOptions(params?: {
  incidentId?: string | null;
  cameraId?: string | null;
  siteId?: string | null;
  limit?: number;
}) {
  return queryOptions({
    queryKey: ["operations", "memory-patterns", params ?? {}],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/operations/memory-patterns",
        {
          params: {
            query: {
              incident_id: params?.incidentId ?? undefined,
              camera_id: params?.cameraId ?? undefined,
              site_id: params?.siteId ?? undefined,
              limit: params?.limit,
            },
          },
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to load operational memory.");
      }
      return data;
    },
  });
}

export function useFleetOverview() {
  return useQuery(fleetOverviewQueryOptions());
}

export function useOperationalMemoryPatterns(params?: {
  incidentId?: string | null;
  cameraId?: string | null;
  siteId?: string | null;
  limit?: number;
}) {
  return useQuery(operationalMemoryPatternsQueryOptions(params));
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
