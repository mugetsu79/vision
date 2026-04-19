import { useQuery } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type Incident = components["schemas"]["IncidentResponse"];

export function useIncidents({
  cameraId,
  incidentType,
  limit = 50,
}: {
  cameraId: string | null;
  incidentType: string | null;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["incidents", cameraId, incidentType, limit],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/incidents", {
        params: {
          query: {
            camera_id: cameraId ?? undefined,
            type: incidentType ?? undefined,
            limit,
          },
        },
      });

      if (error) {
        throw toApiError(error, "Failed to load incidents.");
      }

      return data ?? [];
    },
  });
}
