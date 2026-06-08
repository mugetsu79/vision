import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export type DeploymentModelAssignmentCreate =
  components["schemas"]["DeploymentModelAssignmentCreate"];
export type DeploymentModelAssignment =
  components["schemas"]["DeploymentModelAssignmentResponse"];
export type DeploymentModelInventoryReport =
  components["schemas"]["DeploymentModelInventoryReport"];
export type DeploymentModelSyncJob =
  components["schemas"]["DeploymentModelSyncJobResponse"];
export type EdgeConfiguration =
  components["schemas"]["EdgeConfigurationResponse"];
export type EdgeConfigurationUpdate =
  components["schemas"]["EdgeConfigurationUpdate"];
export type ModelImportJob = components["schemas"]["ModelImportJobResponse"];
export type ModelImportRequest = components["schemas"]["ModelImportRequest"];
export type RuntimeArtifactBuildJob =
  components["schemas"]["RuntimeArtifactBuildJobResponse"];
export type RuntimeArtifactBuildJobCreate =
  components["schemas"]["RuntimeArtifactBuildJobCreate"];

export const modelLifecycleQueryKeys = {
  modelImportJobs: ["model-lifecycle", "model-import-jobs"] as const,
  deploymentNode: (nodeId: string) =>
    ["model-lifecycle", "deployment-nodes", nodeId] as const,
  deploymentModelAssignments: (nodeId: string) =>
    [
      ...modelLifecycleQueryKeys.deploymentNode(nodeId),
      "model-assignments",
    ] as const,
  deploymentModelInventory: (nodeId: string) =>
    [...modelLifecycleQueryKeys.deploymentNode(nodeId), "model-inventory"] as const,
  edgeConfiguration: (nodeId: string) =>
    [
      ...modelLifecycleQueryKeys.deploymentNode(nodeId),
      "edge-configuration",
    ] as const,
  runtimeArtifactBuildJobs: (modelId: string) =>
    [
      "model-lifecycle",
      "models",
      modelId,
      "runtime-artifact-build-jobs",
    ] as const,
};

export function useRegisterCatalogModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (catalogId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/model-catalog/{catalog_id}/register",
        {
          params: { path: { catalog_id: catalogId } },
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to register catalog model.");
      }
      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["model-catalog"] }),
        queryClient.invalidateQueries({ queryKey: ["models"] }),
        queryClient.invalidateQueries({
          queryKey: modelLifecycleQueryKeys.modelImportJobs,
        }),
      ]);
    },
  });
}

export function useDownloadCatalogModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (catalogId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/model-catalog/{catalog_id}/download",
        {
          params: { path: { catalog_id: catalogId } },
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to queue catalog model download.");
      }
      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["model-catalog"] }),
        queryClient.invalidateQueries({ queryKey: ["models"] }),
        queryClient.invalidateQueries({
          queryKey: modelLifecycleQueryKeys.modelImportJobs,
        }),
      ]);
    },
  });
}

export function useImportModelFromUrl() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: ModelImportRequest) => {
      const { data, error } = await apiClient.POST("/api/v1/models/import-url", {
        body: payload,
      });
      if (error || !data) {
        throw toApiError(error, "Failed to import model from URL.");
      }
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: modelLifecycleQueryKeys.modelImportJobs,
      });
    },
  });
}

export function useModelImportJobs() {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: modelLifecycleQueryKeys.modelImportJobs,
    enabled: Boolean(accessToken),
    staleTime: 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/model-import-jobs");
      if (error) {
        throw toApiError(error, "Failed to load model import jobs.");
      }
      return data ?? [];
    },
  });
}

export function useDeploymentModelAssignments(nodeId: string | null) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: nodeScopedQueryKey(
      nodeId,
      modelLifecycleQueryKeys.deploymentModelAssignments,
    ),
    enabled: Boolean(accessToken && nodeId),
    staleTime: 0,
    queryFn: async () => {
      const resolvedNodeId = requireNodeId(nodeId);
      const { data, error } = await apiClient.GET(
        "/api/v1/deployment/nodes/{node_id}/model-assignments",
        {
          params: { path: { node_id: resolvedNodeId } },
        },
      );
      if (error) {
        throw toApiError(error, "Failed to load deployment model assignments.");
      }
      return data ?? [];
    },
  });
}

export function useAssignDeploymentModel(nodeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: DeploymentModelAssignmentCreate) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/deployment/nodes/{node_id}/model-assignments",
        {
          params: { path: { node_id: nodeId } },
          body: payload,
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to assign model to deployment node.");
      }
      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: modelLifecycleQueryKeys.deploymentModelAssignments(nodeId),
        }),
        queryClient.invalidateQueries({ queryKey: ["deployment", "nodes"] }),
      ]);
    },
  });
}

export function useRemoveDeploymentModelAssignment(nodeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (assignmentId: string) => {
      const { data, error } = await apiClient.DELETE(
        "/api/v1/deployment/nodes/{node_id}/model-assignments/{assignment_id}",
        {
          params: {
            path: {
              node_id: nodeId,
              assignment_id: assignmentId,
            },
          },
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to remove model assignment.");
      }
      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: modelLifecycleQueryKeys.deploymentModelAssignments(nodeId),
        }),
        queryClient.invalidateQueries({ queryKey: ["deployment", "nodes"] }),
      ]);
    },
  });
}

export function useCreateModelSyncJob(nodeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST(
        "/api/v1/deployment/nodes/{node_id}/model-sync-jobs",
        {
          params: { path: { node_id: nodeId } },
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to start model sync job.");
      }
      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: modelLifecycleQueryKeys.deploymentModelAssignments(nodeId),
        }),
        queryClient.invalidateQueries({
          queryKey: modelLifecycleQueryKeys.deploymentModelInventory(nodeId),
        }),
        queryClient.invalidateQueries({ queryKey: ["deployment", "nodes"] }),
      ]);
    },
  });
}

export function useDeploymentModelInventory(nodeId: string | null) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: nodeScopedQueryKey(
      nodeId,
      modelLifecycleQueryKeys.deploymentModelInventory,
    ),
    enabled: Boolean(accessToken && nodeId),
    staleTime: 0,
    queryFn: async () => {
      const resolvedNodeId = requireNodeId(nodeId);
      const { data, error } = await apiClient.GET(
        "/api/v1/deployment/nodes/{node_id}/model-inventory",
        {
          params: { path: { node_id: resolvedNodeId } },
        },
      );
      if (error) {
        throw toApiError(error, "Failed to load deployment model inventory.");
      }
      return data ?? { items: [] };
    },
  });
}

export function useRuntimeArtifactBuildJobs(modelId: string | null) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: modelScopedQueryKey(
      modelId,
      modelLifecycleQueryKeys.runtimeArtifactBuildJobs,
    ),
    enabled: Boolean(accessToken && modelId),
    staleTime: 0,
    queryFn: async () => {
      const resolvedModelId = requireModelId(modelId);
      const { data, error } = await apiClient.GET(
        "/api/v1/models/{model_id}/runtime-artifact-build-jobs",
        {
          params: { path: { model_id: resolvedModelId } },
        },
      );
      if (error) {
        throw toApiError(error, "Failed to load runtime artifact build jobs.");
      }
      return data ?? [];
    },
  });
}

export function useCreateRuntimeArtifactBuildJob(modelId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: RuntimeArtifactBuildJobCreate) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/models/{model_id}/runtime-artifact-build-jobs",
        {
          params: { path: { model_id: modelId } },
          body: payload,
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to create runtime artifact build job.");
      }
      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: modelLifecycleQueryKeys.runtimeArtifactBuildJobs(modelId),
        }),
        queryClient.invalidateQueries({ queryKey: ["model-runtime-artifacts"] }),
      ]);
    },
  });
}

export function useEdgeConfiguration(nodeId: string | null) {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: nodeScopedQueryKey(
      nodeId,
      modelLifecycleQueryKeys.edgeConfiguration,
    ),
    enabled: Boolean(accessToken && nodeId),
    staleTime: 0,
    queryFn: async () => {
      const resolvedNodeId = requireNodeId(nodeId);
      const { data, error } = await apiClient.GET(
        "/api/v1/deployment/nodes/{node_id}/edge-configuration",
        {
          params: { path: { node_id: resolvedNodeId } },
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to load edge configuration.");
      }
      return data;
    },
  });
}

export function useUpdateEdgeConfiguration(nodeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: EdgeConfigurationUpdate) => {
      const { data, error } = await apiClient.PUT(
        "/api/v1/deployment/nodes/{node_id}/edge-configuration",
        {
          params: { path: { node_id: nodeId } },
          body: payload,
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to update edge configuration.");
      }
      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: modelLifecycleQueryKeys.edgeConfiguration(nodeId),
        }),
        queryClient.invalidateQueries({ queryKey: ["deployment", "nodes"] }),
      ]);
    },
  });
}

function nodeScopedQueryKey<T extends readonly unknown[]>(
  nodeId: string | null,
  keyFor: (nodeId: string) => T,
) {
  return nodeId ? keyFor(nodeId) : ["model-lifecycle", "deployment-nodes", null];
}

function modelScopedQueryKey<T extends readonly unknown[]>(
  modelId: string | null,
  keyFor: (modelId: string) => T,
) {
  return modelId ? keyFor(modelId) : ["model-lifecycle", "models", null];
}

function requireNodeId(nodeId: string | null): string {
  if (!nodeId) {
    throw new Error("Deployment node id is required.");
  }
  return nodeId;
}

function requireModelId(modelId: string | null): string {
  if (!modelId) {
    throw new Error("Model id is required.");
  }
  return modelId;
}
