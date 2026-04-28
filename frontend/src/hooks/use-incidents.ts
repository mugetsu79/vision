import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type Incident = components["schemas"]["IncidentResponse"];
export type IncidentReviewStatus = Incident["review_status"];

export function useIncidents({
  cameraId,
  incidentType,
  reviewStatus,
  limit = 50,
}: {
  cameraId: string | null;
  incidentType: string | null;
  reviewStatus: IncidentReviewStatus | null;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["incidents", cameraId, incidentType, reviewStatus, limit],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/incidents", {
        params: {
          query: {
            camera_id: cameraId ?? undefined,
            type: incidentType ?? undefined,
            review_status: reviewStatus ?? undefined,
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

export function useUpdateIncidentReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      incidentId,
      reviewStatus,
    }: {
      incidentId: string;
      reviewStatus: IncidentReviewStatus;
    }) => {
      const { data, error } = await apiClient.PATCH(
        "/api/v1/incidents/{incident_id}/review",
        {
          params: { path: { incident_id: incidentId } },
          body: { review_status: reviewStatus },
        },
      );

      if (error) {
        throw toApiError(error, "Failed to update incident review state.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}
