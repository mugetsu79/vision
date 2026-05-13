import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type DeploymentNode = components["schemas"]["DeploymentNodeResponse"];
export type DeploymentSupportBundle =
  components["schemas"]["DeploymentSupportBundleResponse"];
export type NodePairingSessionCreate =
  components["schemas"]["NodePairingSessionCreate"];
export type NodePairingSessionResponse =
  components["schemas"]["NodePairingSessionResponse"];

export function deploymentNodesQueryOptions() {
  return queryOptions({
    queryKey: ["deployment", "nodes"],
    staleTime: 0,
    refetchInterval: 5_000,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/deployment/nodes");
      if (error || !data) {
        throw toApiError(error, "Failed to load deployment nodes.");
      }
      return data;
    },
  });
}

export function deploymentSupportBundleQueryOptions(nodeId: string | null) {
  return queryOptions({
    queryKey: ["deployment", "nodes", nodeId, "support-bundle"],
    enabled: Boolean(nodeId),
    queryFn: async () => {
      if (!nodeId) {
        throw new Error("Deployment node id is required.");
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/deployment/nodes/{node_id}/support-bundle",
        {
          params: { path: { node_id: nodeId } },
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to load deployment support bundle.");
      }
      return data;
    },
  });
}

export function useDeploymentNodes() {
  return useQuery(deploymentNodesQueryOptions());
}

export function useDeploymentSupportBundle(nodeId: string | null) {
  return useQuery(deploymentSupportBundleQueryOptions(nodeId));
}

export function useCreatePairingSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: NodePairingSessionCreate) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/deployment/pairing-sessions",
        { body: payload },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to create pairing session.");
      }
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["deployment", "nodes"],
      });
    },
  });
}
