import { useQuery } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";

export function useSupportBundles() {
  return useQuery({
    queryKey: ["support", "bundles"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/support/bundles");
      if (error) {
        throw toApiError(error, "Failed to load support bundles.");
      }
      return data?.items ?? [];
    },
  });
}

export function useSupportOnboardingChecks(siteId?: string | null) {
  return useQuery({
    queryKey: ["support", "onboarding-checks", siteId ?? "none"],
    enabled: Boolean(siteId),
    queryFn: async () => {
      if (!siteId) {
        return null;
      }
      const { data, error } = await apiClient.GET("/api/v1/support/onboarding-checks", {
        params: { query: { site_id: siteId } },
      });
      if (error) {
        throw toApiError(error, "Failed to load onboarding checks.");
      }
      return data ?? null;
    },
  });
}

export function useMaritimeSupportDiagnostics() {
  return useQuery({
    queryKey: ["maritime", "support", "diagnostics"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/maritime/support/diagnostics",
      );
      if (error) {
        throw toApiError(error, "Failed to load support diagnostics.");
      }
      return data ?? {};
    },
  });
}
