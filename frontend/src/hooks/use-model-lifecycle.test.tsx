import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    DELETE: vi.fn(),
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) =>
    new Error(fallbackMessage),
}));

import {
  useAssignDeploymentModel,
  useCreateRuntimeArtifactBuildJob,
  useRegisterCatalogModel,
  useUpdateEdgeConfiguration,
} from "@/hooks/use-model-lifecycle";
import { apiClient } from "@/lib/api";

describe("model lifecycle hooks", () => {
  beforeEach(() => {
    vi.mocked(apiClient.DELETE).mockReset();
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.POST).mockReset();
    vi.mocked(apiClient.PUT).mockReset();
  });

  it("registers catalog models and invalidates catalog plus model queries", async () => {
    const { invalidateQueries, result } = renderModelLifecycleHook(() =>
      useRegisterCatalogModel(),
    );
    vi.mocked(apiClient.POST).mockResolvedValueOnce(okResponse({ id: "job-1" }));

    await act(async () => {
      await result.current.mutateAsync("yolo26n-coco-onnx");
    });

    expect(apiClient.POST).toHaveBeenCalledWith(
      "/api/v1/model-catalog/{catalog_id}/register",
      { params: { path: { catalog_id: "yolo26n-coco-onnx" } } },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["model-catalog"] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["models"] });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["model-lifecycle", "model-import-jobs"],
    });
  });

  it("assigns a model to a deployment node and invalidates node assignment queries", async () => {
    const { invalidateQueries, result } = renderModelLifecycleHook(() =>
      useAssignDeploymentModel("node-1"),
    );
    vi.mocked(apiClient.POST).mockResolvedValueOnce(okResponse({ id: "assignment-1" }));

    await act(async () => {
      await result.current.mutateAsync({
        model_id: "model-1",
        desired_path: "/var/lib/vezor/models/yolo26n.onnx",
      });
    });

    expect(apiClient.POST).toHaveBeenCalledWith(
      "/api/v1/deployment/nodes/{node_id}/model-assignments",
      {
        params: { path: { node_id: "node-1" } },
        body: {
          model_id: "model-1",
          desired_path: "/var/lib/vezor/models/yolo26n.onnx",
        },
      },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: [
        "model-lifecycle",
        "deployment-nodes",
        "node-1",
        "model-assignments",
      ],
    });
  });

  it("starts an artifact build job and invalidates artifact job queries", async () => {
    const { invalidateQueries, result } = renderModelLifecycleHook(() =>
      useCreateRuntimeArtifactBuildJob("model-1"),
    );
    vi.mocked(apiClient.POST).mockResolvedValueOnce(okResponse({ id: "build-job-1" }));

    await act(async () => {
      await result.current.mutateAsync({
        deployment_node_id: "node-1",
        build_format: "tensorrt_engine",
        target_profile: "linux-aarch64-nvidia-jetson",
        precision: "fp16",
        input_shape: { width: 640, height: 640 },
      });
    });

    expect(apiClient.POST).toHaveBeenCalledWith(
      "/api/v1/models/{model_id}/runtime-artifact-build-jobs",
      {
        params: { path: { model_id: "model-1" } },
        body: {
          deployment_node_id: "node-1",
          build_format: "tensorrt_engine",
          target_profile: "linux-aarch64-nvidia-jetson",
          precision: "fp16",
          input_shape: { width: 640, height: 640 },
        },
      },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: [
        "model-lifecycle",
        "models",
        "model-1",
        "runtime-artifact-build-jobs",
      ],
    });
  });

  it("updates edge configuration and invalidates deployment node config", async () => {
    const { invalidateQueries, result } = renderModelLifecycleHook(() =>
      useUpdateEdgeConfiguration("node-1"),
    );
    vi.mocked(apiClient.PUT).mockResolvedValueOnce(okResponse({ id: "edge-config-1" }));

    await act(async () => {
      await result.current.mutateAsync({
        desired_config: {
          model_store_path: "/var/lib/vezor/models",
          artifact_store_path: "/var/lib/vezor/artifacts",
        },
      });
    });

    expect(apiClient.PUT).toHaveBeenCalledWith(
      "/api/v1/deployment/nodes/{node_id}/edge-configuration",
      {
        params: { path: { node_id: "node-1" } },
        body: {
          desired_config: {
            model_store_path: "/var/lib/vezor/models",
            artifact_store_path: "/var/lib/vezor/artifacts",
          },
        },
      },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: [
        "model-lifecycle",
        "deployment-nodes",
        "node-1",
        "edge-configuration",
      ],
    });
  });
});

function renderModelLifecycleHook<Result>(hook: () => Result) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  return {
    invalidateQueries,
    ...renderHook(hook, { wrapper }),
  };
}

function okResponse(data: unknown) {
  return {
    data,
    error: undefined,
    response: new Response(null, { status: 200 }),
  } as Awaited<ReturnType<typeof apiClient.POST>>;
}
