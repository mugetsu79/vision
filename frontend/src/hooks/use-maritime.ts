import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";
import { useMaritimeSupportDiagnostics } from "@/hooks/use-support";

export type MaritimeVesselCreateInput = components["schemas"]["VesselCreate"];
export type MaritimeVesselUpdateInput = components["schemas"]["VesselUpdate"];

type MaritimeQueryClient = ReturnType<typeof useQueryClient>;

export function useMaritimeRuntime() {
  return useQuery({
    queryKey: ["maritime", "runtime"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/maritime/runtime");
      if (error) {
        throw toApiError(error, "Failed to load maritime runtime.");
      }
      return data ?? {};
    },
  });
}

export function useMaritimeVessels() {
  return useQuery({
    queryKey: ["maritime", "vessels"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/maritime/vessels");
      if (error) {
        throw toApiError(error, "Failed to load vessels.");
      }
      return data ?? [];
    },
  });
}

export function useMaritimeVessel(vesselId?: string | null) {
  return useQuery({
    queryKey: ["maritime", "vessels", vesselId ?? "none"],
    enabled: Boolean(vesselId),
    queryFn: async () => {
      if (!vesselId) {
        return null;
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/maritime/vessels/{vessel_id}",
        { params: { path: { vessel_id: vesselId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load vessel.");
      }
      return data ?? null;
    },
  });
}

export function useCreateMaritimeVessel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: MaritimeVesselCreateInput) => {
      const { data, error } = await apiClient.POST("/api/v1/maritime/vessels", {
        body: payload,
      });
      if (error) {
        throw toApiError(error, "Failed to create vessel.");
      }
      return data ?? null;
    },
    onSuccess: async (created) => {
      const vesselId = typeof created?.id === "string" ? created.id : null;
      await invalidateMaritimeVesselCaches(queryClient, vesselId);
    },
  });
}

export function useUpdateMaritimeVessel(vesselId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: MaritimeVesselUpdateInput) => {
      const { data, error } = await apiClient.PATCH(
        "/api/v1/maritime/vessels/{vessel_id}",
        { params: { path: { vessel_id: vesselId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to update vessel.");
      }
      return data ?? null;
    },
    onSuccess: async () =>
      invalidateMaritimeVesselCaches(queryClient, vesselId),
  });
}

export function useDeactivateMaritimeVessel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (vesselId: string) => {
      const { error } = await apiClient.DELETE(
        "/api/v1/maritime/vessels/{vessel_id}",
        { params: { path: { vessel_id: vesselId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to deactivate vessel.");
      }
      return vesselId;
    },
    onSuccess: async (vesselId) =>
      invalidateMaritimeVesselCaches(queryClient, vesselId),
  });
}

async function invalidateMaritimeVesselCaches(
  queryClient: MaritimeQueryClient,
  vesselId?: string | null,
) {
  await queryClient.invalidateQueries({ queryKey: ["maritime", "vessels"] });
  await queryClient.invalidateQueries({ queryKey: ["sites"] });
  await queryClient.invalidateQueries({ queryKey: ["fleet"] });
  await queryClient.invalidateQueries({ queryKey: ["operations", "fleet"] });
  if (vesselId) {
    await queryClient.invalidateQueries({
      queryKey: ["maritime", "vessels", vesselId],
    });
  }
}

export function useMaritimeVesselTelemetry(vesselId?: string | null) {
  return useQuery({
    queryKey: ["maritime", "vessels", vesselId ?? "none", "telemetry"],
    enabled: Boolean(vesselId),
    queryFn: async () => {
      if (!vesselId) {
        return null;
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/maritime/vessels/{vessel_id}/telemetry",
        { params: { path: { vessel_id: vesselId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load vessel telemetry.");
      }
      return data ?? null;
    },
  });
}

export function useMaritimeVesselLinkStatus(vesselId?: string | null) {
  return useQuery({
    queryKey: ["maritime", "vessels", vesselId ?? "none", "link-status"],
    enabled: Boolean(vesselId),
    queryFn: async () => {
      if (!vesselId) {
        return null;
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/maritime/vessels/{vessel_id}/link-status",
        { params: { path: { vessel_id: vesselId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load vessel link status.");
      }
      return data ?? null;
    },
  });
}

export function useMaritimeEvidenceContext() {
  return useQuery({
    queryKey: ["maritime", "evidence-context"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/maritime/evidence-context");
      if (error) {
        throw toApiError(error, "Failed to load maritime evidence context.");
      }
      return data ?? {};
    },
  });
}

export function useMaritimeBillingUsage() {
  return useQuery({
    queryKey: ["maritime", "billing", "usage"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/maritime/billing/usage");
      if (error) {
        throw toApiError(error, "Failed to load maritime billing usage.");
      }
      return data ?? {};
    },
  });
}

export function useFleetOpsVesselDetail(vesselId?: string | null) {
  return {
    vessel: useMaritimeVessel(vesselId),
    telemetry: useMaritimeVesselTelemetry(vesselId),
    linkStatus: useMaritimeVesselLinkStatus(vesselId),
    evidenceContext: useMaritimeEvidenceContext(),
    billingUsage: useMaritimeBillingUsage(),
    supportDiagnostics: useMaritimeSupportDiagnostics(),
  };
}
