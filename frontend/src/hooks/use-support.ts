import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type SupportBundleCreateInput = components["schemas"]["SupportBundleCreate"];
export type SupportSessionCreateInput = components["schemas"]["SupportSessionCreate"];
export type SupportSessionCloseInput = components["schemas"]["SupportSessionClose"];
export type SupportTunnelCreateInput = components["schemas"]["SupportTunnelCreate"];
export type SupportTunnelRevokeInput = components["schemas"]["SupportTunnelRevoke"];
export type BreakGlassOpenInput = components["schemas"]["BreakGlassOpen"];
export type BreakGlassCloseInput = components["schemas"]["BreakGlassClose"];
export type OnboardingCheckRunInput = components["schemas"]["OnboardingCheckRunCreate"];

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

export function useCreateSupportBundle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SupportBundleCreateInput) => {
      const { data, error } = await apiClient.POST("/api/v1/support/bundles", {
        body: payload,
      });
      if (error) {
        throw toApiError(error, "Failed to create support bundle.");
      }
      return data ?? null;
    },
    onSuccess: async () => invalidateSupportQueries(queryClient),
  });
}

export function useCreateSupportSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SupportSessionCreateInput) => {
      const { data, error } = await apiClient.POST("/api/v1/support/sessions", {
        body: payload,
      });
      if (error) {
        throw toApiError(error, "Failed to create support session.");
      }
      return data ?? null;
    },
    onSuccess: async () => invalidateSupportQueries(queryClient),
  });
}

export function useCloseSupportSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sessionId,
      payload,
    }: {
      sessionId: string;
      payload: SupportSessionCloseInput;
    }) => {
      const { data, error } = await apiClient.PATCH(
        "/api/v1/support/sessions/{session_id}",
        { params: { path: { session_id: sessionId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to close support session.");
      }
      return data ?? null;
    },
    onSuccess: async () => invalidateSupportQueries(queryClient),
  });
}

export function useRequestSupportTunnel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SupportTunnelCreateInput) => {
      const { data, error } = await apiClient.POST("/api/v1/support/tunnels", {
        body: payload,
      });
      if (error) {
        throw toApiError(error, "Failed to request support tunnel.");
      }
      return data ?? null;
    },
    onSuccess: async () => invalidateSupportQueries(queryClient),
  });
}

export function useRevokeSupportTunnel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      tunnelId,
      payload,
    }: {
      tunnelId: string;
      payload: SupportTunnelRevokeInput;
    }) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/support/tunnels/{tunnel_id}/revoke",
        { params: { path: { tunnel_id: tunnelId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to revoke support tunnel.");
      }
      return data ?? null;
    },
    onSuccess: async () => invalidateSupportQueries(queryClient),
  });
}

export function useOpenBreakGlass() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: BreakGlassOpenInput) => {
      const { data, error } = await apiClient.POST("/api/v1/support/break-glass", {
        body: payload,
      });
      if (error) {
        throw toApiError(error, "Failed to open break-glass access.");
      }
      return data ?? null;
    },
    onSuccess: async () => invalidateSupportQueries(queryClient),
  });
}

export function useCloseBreakGlass() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      recordId,
      payload,
    }: {
      recordId: string;
      payload: BreakGlassCloseInput;
    }) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/support/break-glass/{record_id}/close",
        { params: { path: { record_id: recordId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to close break-glass access.");
      }
      return data ?? null;
    },
    onSuccess: async () => invalidateSupportQueries(queryClient),
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

export function useRunSupportOnboardingChecks(siteId?: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: OnboardingCheckRunInput) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/support/onboarding-checks/run",
        { body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to run onboarding checks.");
      }
      return data ?? null;
    },
    onSuccess: async () => {
      await invalidateSupportQueries(queryClient);
      if (siteId) {
        await queryClient.invalidateQueries({
          queryKey: ["support", "onboarding-checks", siteId],
        });
      }
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

async function invalidateSupportQueries(
  queryClient: ReturnType<typeof useQueryClient>,
) {
  await queryClient.invalidateQueries({ queryKey: ["support"] });
}
