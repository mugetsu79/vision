import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type LinkConnectionCreateInput =
  components["schemas"]["LinkConnectionCreate"];
export type LinkConnectionPatchInput =
  components["schemas"]["LinkConnectionPatch"];
export type LinkBudgetUpdateInput = components["schemas"]["LinkBudgetUpdate"];
export type LinkPolicyUpdateInput = components["schemas"]["LinkPolicyUpdate"];
export type LinkProbeCreateInput = components["schemas"]["LinkProbeCreate"];
export type LinkSiteSummary = components["schemas"]["LinkSiteSummaryResponse"];

type LinkMutationContext = {
  siteId?: string | null;
  vesselId?: string | null;
};

export function useLinkSiteSummaries() {
  return useQuery({
    queryKey: ["link", "sites", "summary"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/link/sites/summary");
      if (error) {
        throw toApiError(error, "Failed to load link summaries.");
      }
      return data ?? [];
    },
  });
}

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

export function useLinkConnections(siteId?: string | null) {
  return useQuery({
    queryKey: ["link", "sites", siteId ?? "none", "connections"],
    enabled: Boolean(siteId),
    queryFn: async () => {
      if (!siteId) {
        return [];
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/link/sites/{site_id}/connections",
        { params: { path: { site_id: siteId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load link connections.");
      }
      return data ?? [];
    },
  });
}

export function useCreateLinkConnection({
  siteId,
  vesselId,
}: LinkMutationContext) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LinkConnectionCreateInput) => {
      if (!siteId) {
        throw new Error("A site is required to create a link connection.");
      }
      const { data, error } = await apiClient.POST(
        "/api/v1/link/sites/{site_id}/connections",
        { params: { path: { site_id: siteId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to create link connection.");
      }
      return data ?? null;
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
  });
}

export function useUpdateLinkConnection({
  siteId,
  vesselId,
}: LinkMutationContext) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      connectionId,
      payload,
    }: {
      connectionId: string;
      payload: LinkConnectionPatchInput;
    }) => {
      if (!siteId) {
        throw new Error("A site is required to update a link connection.");
      }
      const { data, error } = await apiClient.PATCH(
        "/api/v1/link/sites/{site_id}/connections/{connection_id}",
        {
          params: { path: { site_id: siteId, connection_id: connectionId } },
          body: payload,
        },
      );
      if (error) {
        throw toApiError(error, "Failed to update link connection.");
      }
      return data ?? null;
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
  });
}

export function useDeleteLinkConnection({
  siteId,
  vesselId,
}: LinkMutationContext) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (connectionId: string) => {
      if (!siteId) {
        throw new Error("A site is required to delete a link connection.");
      }
      const { error } = await apiClient.DELETE(
        "/api/v1/link/sites/{site_id}/connections/{connection_id}",
        { params: { path: { site_id: siteId, connection_id: connectionId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to delete link connection.");
      }
      return connectionId;
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
  });
}

export function useLinkSiteBudget(siteId?: string | null) {
  return useQuery({
    queryKey: ["link", "sites", siteId ?? "none", "budget"],
    enabled: Boolean(siteId),
    queryFn: async () => {
      if (!siteId) {
        return null;
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/link/sites/{site_id}/budget",
        { params: { path: { site_id: siteId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load link budget.");
      }
      return data ?? null;
    },
  });
}

export function useUpdateLinkBudget({ siteId, vesselId }: LinkMutationContext) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LinkBudgetUpdateInput) => {
      if (!siteId) {
        throw new Error("A site is required to update link budget.");
      }
      const { data, error } = await apiClient.PUT(
        "/api/v1/link/sites/{site_id}/budget",
        { params: { path: { site_id: siteId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to update link budget.");
      }
      return data ?? null;
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
  });
}

export function useLinkPolicies(siteId?: string | null) {
  return useQuery({
    queryKey: ["link", "sites", siteId ?? "none", "policies"],
    enabled: Boolean(siteId),
    queryFn: async () => {
      if (!siteId) {
        return {};
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/link/sites/{site_id}/policies",
        { params: { path: { site_id: siteId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load link policies.");
      }
      return data ?? {};
    },
  });
}

export function useUpdateLinkPolicies({
  siteId,
  vesselId,
}: LinkMutationContext) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LinkPolicyUpdateInput) => {
      if (!siteId) {
        throw new Error("A site is required to update link policies.");
      }
      const { data, error } = await apiClient.PUT(
        "/api/v1/link/sites/{site_id}/policies",
        { params: { path: { site_id: siteId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to update link policies.");
      }
      return data ?? {};
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
  });
}

export function useLinkProbes(siteId?: string | null) {
  return useQuery({
    queryKey: ["link", "sites", siteId ?? "none", "probes"],
    enabled: Boolean(siteId),
    queryFn: async () => {
      if (!siteId) {
        return [];
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/link/sites/{site_id}/probes",
        { params: { path: { site_id: siteId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load link probes.");
      }
      return data ?? [];
    },
  });
}

export function useCreateLinkProbe({ siteId, vesselId }: LinkMutationContext) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LinkProbeCreateInput) => {
      if (!siteId) {
        throw new Error("A site is required to create a link probe.");
      }
      const { data, error } = await apiClient.POST(
        "/api/v1/link/sites/{site_id}/probes",
        { params: { path: { site_id: siteId } }, body: payload },
      );
      if (error) {
        throw toApiError(error, "Failed to create link probe.");
      }
      return data ?? null;
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
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

export function useRetryLinkQueueItem({
  siteId,
  vesselId,
}: LinkMutationContext) {
  return useQueueItemMutation({
    siteId,
    vesselId,
    path: "/api/v1/link/queue/{queue_item_id}/retry",
    failureMessage: "Failed to retry queued link work.",
  });
}

export function usePauseLinkQueueItem({
  siteId,
  vesselId,
}: LinkMutationContext) {
  return useQueueItemMutation({
    siteId,
    vesselId,
    path: "/api/v1/link/queue/{queue_item_id}/pause",
    failureMessage: "Failed to pause queued link work.",
  });
}

export function useResumeLinkQueueItem({
  siteId,
  vesselId,
}: LinkMutationContext) {
  return useQueueItemMutation({
    siteId,
    vesselId,
    path: "/api/v1/link/queue/{queue_item_id}/resume",
    failureMessage: "Failed to resume queued link work.",
  });
}

type QueueMutationPath =
  | "/api/v1/link/queue/{queue_item_id}/retry"
  | "/api/v1/link/queue/{queue_item_id}/pause"
  | "/api/v1/link/queue/{queue_item_id}/resume";

function useQueueItemMutation({
  siteId,
  vesselId,
  path,
  failureMessage,
}: LinkMutationContext & {
  path: QueueMutationPath;
  failureMessage: string;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (queueItemId: string) => {
      const { data, error } = await apiClient.POST(path, {
        params: { path: { queue_item_id: queueItemId } },
      });
      if (error) {
        throw toApiError(error, failureMessage);
      }
      return data ?? null;
    },
    onSuccess: async () =>
      invalidateLinkSiteQueries(queryClient, { siteId, vesselId }),
  });
}

async function invalidateLinkSiteQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  { siteId, vesselId }: LinkMutationContext,
) {
  await queryClient.invalidateQueries({
    queryKey: ["link", "sites", "summary"],
  });
  if (siteId) {
    await queryClient.invalidateQueries({
      queryKey: ["link", "sites", siteId],
    });
  }
  if (vesselId) {
    await queryClient.invalidateQueries({
      queryKey: ["maritime", "vessels", vesselId, "link-status"],
    });
  }
}
