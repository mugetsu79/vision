import { useQuery } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";
import { useMaritimeSupportDiagnostics } from "@/hooks/use-support";

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
