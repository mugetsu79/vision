import { useQuery } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";

export function useFleetExceptions() {
  return useQuery({
    queryKey: ["fleet", "exceptions"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/fleet/exceptions");
      if (error) {
        throw toApiError(error, "Failed to load fleet exceptions.");
      }
      return data ?? { items: [] };
    },
  });
}

export function useFleetSiteGroups() {
  return useQuery({
    queryKey: ["fleet", "site-groups"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/fleet/site-groups");
      if (error) {
        throw toApiError(error, "Failed to load fleet site groups.");
      }
      return data ?? { items: [] };
    },
  });
}
