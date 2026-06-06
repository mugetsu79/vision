import { useQuery } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";

export function useLinkSiteStatus(siteId?: string | null) {
  return useQuery({
    queryKey: ["link", "sites", siteId ?? "none", "status"],
    enabled: Boolean(siteId),
    queryFn: async () => {
      if (!siteId) {
        return null;
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/link/sites/{site_id}/status",
        { params: { path: { site_id: siteId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load link status.");
      }
      return data ?? null;
    },
  });
}

export function useLinkSiteQueue(siteId?: string | null) {
  return useQuery({
    queryKey: ["link", "sites", siteId ?? "none", "queue"],
    enabled: Boolean(siteId),
    queryFn: async () => {
      if (!siteId) {
        return [];
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/link/sites/{site_id}/queue",
        { params: { path: { site_id: siteId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load link queue.");
      }
      return data ?? [];
    },
  });
}
