import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type IncidentRule = components["schemas"]["IncidentRuleResponse"];
export type IncidentRuleCreate = components["schemas"]["IncidentRuleCreate"];
export type IncidentRuleUpdate = components["schemas"]["IncidentRuleUpdate"];
export type IncidentRuleValidationRequest =
  components["schemas"]["IncidentRuleValidationRequest"];
export type IncidentRuleValidationResponse =
  components["schemas"]["IncidentRuleValidationResponse"];

export function incidentRulesQueryKey(cameraId: string | null) {
  return ["incident-rules", cameraId ?? "none"];
}

export function useIncidentRules(cameraId: string | null) {
  return useQuery({
    queryKey: incidentRulesQueryKey(cameraId),
    enabled: Boolean(cameraId),
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/cameras/{camera_id}/incident-rules",
        {
          params: { path: { camera_id: cameraId ?? "" } },
        },
      );

      if (error) {
        throw toApiError(error, "Failed to load incident rules.");
      }

      return data ?? [];
    },
  });
}

export function useCreateIncidentRule(cameraId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: IncidentRuleCreate) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/incident-rules",
        {
          params: { path: { camera_id: cameraId } },
          body: payload,
        },
      );

      if (error) {
        throw toApiError(error, "Failed to create incident rule.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: incidentRulesQueryKey(cameraId),
      });
    },
  });
}

export function useUpdateIncidentRule(cameraId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ruleId,
      payload,
    }: {
      ruleId: string;
      payload: IncidentRuleUpdate;
    }) => {
      const { data, error } = await apiClient.PATCH(
        "/api/v1/cameras/{camera_id}/incident-rules/{rule_id}",
        {
          params: { path: { camera_id: cameraId, rule_id: ruleId } },
          body: payload,
        },
      );

      if (error) {
        throw toApiError(error, "Failed to update incident rule.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: incidentRulesQueryKey(cameraId),
      });
    },
  });
}

export function useDeleteIncidentRule(cameraId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ruleId: string) => {
      const { error } = await apiClient.DELETE(
        "/api/v1/cameras/{camera_id}/incident-rules/{rule_id}",
        {
          params: { path: { camera_id: cameraId, rule_id: ruleId } },
        },
      );

      if (error) {
        throw toApiError(error, "Failed to delete incident rule.");
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: incidentRulesQueryKey(cameraId),
      });
    },
  });
}

export function useValidateIncidentRule(cameraId: string) {
  return useMutation({
    mutationFn: async (payload: IncidentRuleValidationRequest) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/incident-rules/validate",
        {
          params: { path: { camera_id: cameraId } },
          body: payload,
        },
      );

      if (error) {
        throw toApiError(error, "Failed to validate incident rule.");
      }

      return data;
    },
  });
}
