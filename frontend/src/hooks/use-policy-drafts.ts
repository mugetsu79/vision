import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";
import { incidentRulesQueryKey } from "@/hooks/use-incident-rules";

export type PolicyDraft = components["schemas"]["PolicyDraftResponse"];
export type PolicyDraftCreate = components["schemas"]["PolicyDraftCreate"];

export function policyDraftsQueryKey(cameraId: string | null) {
  return ["policy-drafts", cameraId ?? "none"];
}

export function useCreatePolicyDraft(cameraId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: Omit<PolicyDraftCreate, "camera_id">) => {
      const { data, error } = await apiClient.POST("/api/v1/policy-drafts", {
        body: {
          ...payload,
          camera_id: cameraId,
        },
      });

      if (error) {
        throw toApiError(error, "Failed to create policy draft.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: policyDraftsQueryKey(cameraId),
      });
    },
  });
}

export function useApprovePolicyDraft(cameraId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (draftId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/policy-drafts/{draft_id}/approve",
        {
          params: { path: { draft_id: draftId } },
        },
      );

      if (error) {
        throw toApiError(error, "Failed to approve policy draft.");
      }

      return data;
    },
    onSuccess: async (draft) => {
      await invalidatePolicyDraftQueries(queryClient, cameraId, draft);
    },
  });
}

export function useRejectPolicyDraft(cameraId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (draftId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/policy-drafts/{draft_id}/reject",
        {
          params: { path: { draft_id: draftId } },
        },
      );

      if (error) {
        throw toApiError(error, "Failed to reject policy draft.");
      }

      return data;
    },
    onSuccess: async (draft) => {
      await invalidatePolicyDraftQueries(queryClient, cameraId, draft);
    },
  });
}

export function useApplyPolicyDraft(cameraId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (draftId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/policy-drafts/{draft_id}/apply",
        {
          params: { path: { draft_id: draftId } },
        },
      );

      if (error) {
        throw toApiError(error, "Failed to apply policy draft.");
      }

      return data;
    },
    onSuccess: async (draft) => {
      await invalidatePolicyDraftQueries(queryClient, cameraId, draft);
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
      await queryClient.invalidateQueries({
        queryKey: incidentRulesQueryKey(draft?.camera_id ?? cameraId),
      });
      await queryClient.invalidateQueries({ queryKey: ["configuration"] });
    },
  });
}

async function invalidatePolicyDraftQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  cameraId: string,
  draft: PolicyDraft | undefined,
) {
  await queryClient.invalidateQueries({
    queryKey: policyDraftsQueryKey(draft?.camera_id ?? cameraId),
  });
}
