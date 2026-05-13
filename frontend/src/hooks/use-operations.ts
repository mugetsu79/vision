import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type FleetOverview = components["schemas"]["FleetOverviewResponse"];
export type FleetBootstrapRequest = components["schemas"]["FleetBootstrapRequest"];
export type FleetBootstrapResponse = components["schemas"]["FleetBootstrapResponse"];
export type WorkerAssignmentCreate =
  components["schemas"]["WorkerAssignmentCreate"];
export type WorkerAssignmentResponse =
  components["schemas"]["WorkerAssignmentResponse"];
export type OperationsLifecycleRequestCreate =
  components["schemas"]["OperationsLifecycleRequestCreate"];
export type OperationsLifecycleRequestResponse =
  components["schemas"]["OperationsLifecycleRequestResponse"];
export type OperationalMemoryPattern =
  components["schemas"]["OperationalMemoryPatternResponse"];

export function fleetOverviewQueryOptions() {
  return queryOptions({
    queryKey: ["operations", "fleet"],
    staleTime: 0,
    refetchInterval: 5_000,
    refetchOnWindowFocus: true,
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

export function createWorkerAssignmentMutationOptions() {
  return {
    mutationFn: async (payload: WorkerAssignmentCreate) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/operations/worker-assignments",
        {
          body: payload,
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to update worker assignment.");
      }
      return data;
    },
  };
}

export function createLifecycleRequestMutationOptions() {
  return {
    mutationFn: async (payload: OperationsLifecycleRequestCreate) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/operations/lifecycle-requests",
        {
          body: payload,
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to create lifecycle request.");
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

export function useCreateWorkerAssignment() {
  const queryClient = useQueryClient();

  return useMutation({
    ...createWorkerAssignmentMutationOptions(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["operations", "fleet"] }),
        queryClient.invalidateQueries({ queryKey: ["cameras"] }),
      ]);
    },
  });
}

export function useCreateLifecycleRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    ...createLifecycleRequestMutationOptions(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["operations", "fleet"] });
    },
  });
}
