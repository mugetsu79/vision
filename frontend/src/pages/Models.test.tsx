import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { workspaceNavGroups } from "@/components/layout/workspace-nav";
import { ModelsPage } from "@/pages/Models";

const modelPageMocks = vi.hoisted(() => ({
  assignModel: vi.fn(),
  buildArtifact: vi.fn(),
  catalog: [] as unknown[],
  deploymentNodes: [] as unknown[],
  downloadCatalogModel: vi.fn(),
  edgeConfiguration: null as unknown,
  importJobs: [] as unknown[],
  inventory: { items: [] } as unknown,
  modelAssignments: [] as unknown[],
  models: [] as unknown[],
  registerCatalogModel: vi.fn(),
  runtimeArtifactBuildJobs: [] as unknown[],
  runtimeArtifactsByModelId: {} as Record<string, unknown[]>,
  startSyncJob: vi.fn(),
  updateEdgeConfiguration: vi.fn(),
  urlImport: vi.fn(),
  cameras: [] as unknown[],
}));

vi.mock("@/hooks/use-model-catalog", () => ({
  useModelCatalog: () => ({
    data: modelPageMocks.catalog,
    isError: false,
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-models", () => ({
  useModels: () => ({
    data: modelPageMocks.models,
    isError: false,
    isLoading: false,
  }),
  useRuntimeArtifactsByModelId: () => ({
    data: modelPageMocks.runtimeArtifactsByModelId,
    isError: false,
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-deployment", () => ({
  useDeploymentNodes: () => ({
    data: modelPageMocks.deploymentNodes,
    isError: false,
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-cameras", () => ({
  useCameras: () => ({
    data: modelPageMocks.cameras,
    isError: false,
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-model-lifecycle", () => ({
  useAssignDeploymentModel: () => ({
    isPending: false,
    mutateAsync: modelPageMocks.assignModel,
  }),
  useCreateModelSyncJob: () => ({
    isPending: false,
    mutateAsync: modelPageMocks.startSyncJob,
  }),
  useCreateRuntimeArtifactBuildJob: () => ({
    isPending: false,
    mutateAsync: modelPageMocks.buildArtifact,
  }),
  useDeploymentModelAssignments: () => ({
    data: modelPageMocks.modelAssignments,
    isError: false,
    isLoading: false,
  }),
  useDeploymentModelInventory: () => ({
    data: modelPageMocks.inventory,
    isError: false,
    isLoading: false,
  }),
  useDownloadCatalogModel: () => ({
    isPending: false,
    mutateAsync: modelPageMocks.downloadCatalogModel,
  }),
  useEdgeConfiguration: () => ({
    data: modelPageMocks.edgeConfiguration,
    isError: false,
    isLoading: false,
  }),
  useImportModelFromUrl: () => ({
    isPending: false,
    mutateAsync: modelPageMocks.urlImport,
  }),
  useModelImportJobs: () => ({
    data: modelPageMocks.importJobs,
    isError: false,
    isLoading: false,
  }),
  useRegisterCatalogModel: () => ({
    isPending: false,
    mutateAsync: modelPageMocks.registerCatalogModel,
  }),
  useRuntimeArtifactBuildJobs: () => ({
    data: modelPageMocks.runtimeArtifactBuildJobs,
    isError: false,
    isLoading: false,
  }),
  useUpdateEdgeConfiguration: () => ({
    isPending: false,
    mutateAsync: modelPageMocks.updateEdgeConfiguration,
  }),
}));

describe("ModelsPage", () => {
  beforeEach(() => {
    modelPageMocks.assignModel.mockReset();
    modelPageMocks.buildArtifact.mockReset();
    modelPageMocks.downloadCatalogModel.mockReset();
    modelPageMocks.registerCatalogModel.mockReset();
    modelPageMocks.startSyncJob.mockReset();
    modelPageMocks.updateEdgeConfiguration.mockReset();
    modelPageMocks.urlImport.mockReset();
    modelPageMocks.catalog = [catalogEntry("yolo26n-coco-onnx", "YOLO26n COCO")];
    modelPageMocks.models = [registeredModel("model-1", "YOLO26n COCO")];
    modelPageMocks.deploymentNodes = [jetsonNode];
    modelPageMocks.runtimeArtifactsByModelId = { "model-1": [] };
    modelPageMocks.runtimeArtifactBuildJobs = [];
    modelPageMocks.importJobs = [];
    modelPageMocks.modelAssignments = [];
    modelPageMocks.inventory = { items: [] };
    modelPageMocks.edgeConfiguration = {
      id: "edge-config-1",
      deployment_node_id: "node-1",
      revision: 3,
      apply_status: "applied",
      applied_revision: 3,
      desired_config: {},
      tenant_id: "tenant-1",
      created_at: "2026-06-08T09:00:00Z",
      updated_at: "2026-06-08T09:00:00Z",
      last_applied_at: "2026-06-08T09:01:00Z",
      error: null,
    };
    modelPageMocks.cameras = [
      {
        id: "camera-1",
        name: "Office",
        primary_model_id: "model-1",
        runtime_vocabulary: ["person", "laptop"],
      },
    ];
  });

  it("is available from the Control navigation group", () => {
    const controlItems = workspaceNavGroups.find(
      (group) => group.label === "Control",
    )?.items;

    expect(controlItems).toContainEqual(
      expect.objectContaining({
        label: "Models",
        to: "/models",
      }),
    );
  });

  it("shows yolo26 catalog entries with register actions", async () => {
    const user = userEvent.setup();
    modelPageMocks.catalog = [
      catalogEntry("yolo26n-coco-onnx", "YOLO26n COCO"),
      catalogEntry("yolo26s-coco-onnx", "YOLO26s COCO"),
    ];

    render(<ModelsPage />);

    expect(screen.getByText("YOLO26n COCO")).toBeInTheDocument();
    expect(screen.getByText("YOLO26s COCO")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /register YOLO26n COCO/i }),
    );

    expect(modelPageMocks.registerCatalogModel).toHaveBeenCalledWith(
      "yolo26n-coco-onnx",
    );
  });

  it("shows missing artifact state without marking it passed", () => {
    modelPageMocks.catalog = [
      {
        ...catalogEntry("yolo26s-coco-onnx", "YOLO26s COCO"),
        artifact_exists: false,
        registration_state: "missing_artifact",
        note: "Bundled artifact is missing.",
      },
    ];

    render(<ModelsPage />);

    expect(screen.getAllByText(/missing artifact/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/^pass$/i)).not.toBeInTheDocument();
  });

  it("starts an edge model assignment from the edge distribution tab", async () => {
    const user = userEvent.setup();

    render(<ModelsPage />);

    await user.click(screen.getByRole("button", { name: /edge distribution/i }));
    await user.click(screen.getByRole("button", { name: /assign model to node/i }));

    expect(modelPageMocks.assignModel).toHaveBeenCalledWith({
      model_id: "model-1",
      desired_path: null,
    });
  });

  it("starts a TensorRT artifact build for a Jetson target", async () => {
    const user = userEvent.setup();

    render(<ModelsPage />);

    await user.click(screen.getByRole("button", { name: /runtime artifacts/i }));
    await user.click(
      screen.getByRole("button", { name: /build TensorRT artifact/i }),
    );

    expect(modelPageMocks.buildArtifact).toHaveBeenCalledWith({
      build_format: "tensorrt_engine",
      deployment_node_id: "node-1",
      input_shape: { width: 640, height: 640 },
      precision: "fp16",
      target_profile: "linux-aarch64-nvidia-jetson",
    });
  });

  it("shows actual validated edge-built TensorRT artifact instead of stale static engine path", async () => {
    const user = userEvent.setup();
    modelPageMocks.catalog = [
      {
        ...catalogEntry("yolo26n-coco-onnx", "YOLO26n COCO"),
        path_hint: "models/yolo26n.onnx",
      },
      {
        ...catalogEntry("yolo26n-coco-tensorrt-engine", "YOLO26n TensorRT"),
        format: "engine",
        path_hint: "models/yolo26n.engine",
        artifact_exists: false,
        registration_state: "missing_artifact",
      },
    ];
    modelPageMocks.models = [
      {
        ...registeredModel("model-1", "YOLO26n COCO"),
        path: "models/yolo26n.onnx",
      },
    ];
    modelPageMocks.runtimeArtifactsByModelId = {
      "model-1": [
        runtimeArtifact({
          path: "/models/runtime-artifacts/model-1/yolo26n.engine",
          validation_status: "valid",
        }),
      ],
    };

    render(<ModelsPage />);

    expect(screen.queryByText("models/yolo26n.engine")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /runtime artifacts/i }));

    expect(screen.getByText("Runtime artifact ready")).toBeInTheDocument();
    expect(
      screen.getByText("/models/runtime-artifacts/model-1/yolo26n.engine"),
    ).toBeInTheDocument();
  });

  it("labels built edge artifacts that are still awaiting validation", async () => {
    const user = userEvent.setup();
    modelPageMocks.runtimeArtifactsByModelId = {
      "model-1": [
        runtimeArtifact({
          path: "/models/runtime-artifacts/model-1/yolo26n.engine",
          validation_status: "unvalidated",
        }),
      ],
    };

    render(<ModelsPage />);

    await user.click(screen.getByRole("button", { name: /runtime artifacts/i }));

    expect(
      screen.getByText("Built on edge, awaiting validation"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("/models/runtime-artifacts/model-1/yolo26n.engine"),
    ).toBeInTheDocument();
  });

  it("shows failed import and failed build errors with concrete text", async () => {
    const user = userEvent.setup();
    modelPageMocks.importJobs = [
      {
        id: "import-job-1",
        catalog_id: null,
        source: "url",
        status: "failed",
        target_path: "/var/lib/vezor/models/yolo26s.onnx",
        error: "Hash check failed for yolo26s.onnx",
        actor_subject: "admin-1",
        tenant_id: "tenant-1",
        created_at: "2026-06-08T09:00:00Z",
        updated_at: "2026-06-08T09:00:00Z",
      },
    ];
    modelPageMocks.runtimeArtifactBuildJobs = [
      {
        id: "build-job-1",
        tenant_id: "tenant-1",
        deployment_node_id: "node-1",
        model_id: "model-1",
        camera_id: null,
        artifact_id: null,
        status: "failed",
        build_format: "tensorrt_engine",
        target_profile: "linux-aarch64-nvidia-jetson",
        precision: "fp16",
        payload: {},
        error: "TensorRT builder is not available on this Jetson",
        created_at: "2026-06-08T09:00:00Z",
        updated_at: "2026-06-08T09:00:00Z",
      },
    ];

    render(<ModelsPage />);

    await user.click(screen.getByRole("button", { name: /imports/i }));
    expect(
      within(screen.getByTestId("model-import-jobs")).getByText(
        /Hash check failed for yolo26s.onnx/i,
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /runtime artifacts/i }));
    expect(
      within(screen.getByTestId("runtime-artifact-build-jobs")).getByText(
        /TensorRT builder is not available on this Jetson/i,
      ),
    ).toBeInTheDocument();
  });
});

function catalogEntry(id: string, name: string) {
  return {
    id,
    name,
    version: "2026.1",
    task: "detect",
    path_hint: `models/${id}.onnx`,
    format: "onnx",
    capability: "fixed_vocab",
    capability_config: {},
    classes: ["person"],
    input_shape: { width: 640, height: 640 },
    sha256: "a".repeat(64),
    size_bytes: 12345678,
    license: "AGPL-3.0",
    registration_state: "unregistered",
    registered_model_id: null,
    artifact_exists: true,
    note: "Bundled model artifact available.",
  };
}

function registeredModel(id: string, name: string) {
  return {
    id,
    name,
    version: "2026.1",
    task: "detect",
    path: `/var/lib/vezor/models/${id}.onnx`,
    format: "onnx",
    capability: "fixed_vocab",
    capability_config: {},
    classes: ["person"],
    input_shape: { width: 640, height: 640 },
    sha256: "a".repeat(64),
    size_bytes: 12345678,
    license: "AGPL-3.0",
    created_at: "2026-06-08T09:00:00Z",
    updated_at: "2026-06-08T09:00:00Z",
  };
}

function runtimeArtifact({
  path,
  validation_status,
}: {
  path: string;
  validation_status: string;
}) {
  return {
    id: "artifact-1",
    model_id: "model-1",
    camera_id: null,
    scope: "model",
    kind: "tensorrt_engine",
    capability: "fixed_vocab",
    runtime_backend: "tensorrt_engine",
    path,
    target_profile: "linux-aarch64-nvidia-jetson",
    precision: "fp16",
    input_shape: { width: 640, height: 640 },
    classes: ["person"],
    source_model_sha256: "a".repeat(64),
    sha256: "b".repeat(64),
    size_bytes: 8327412,
    builder: {},
    runtime_versions: {},
    validation_status,
    validation_error: null,
    build_duration_seconds: 12.5,
    validation_duration_seconds: null,
    validated_at: validation_status === "valid" ? "2026-06-08T09:00:00Z" : null,
    created_at: "2026-06-08T09:00:00Z",
    updated_at: "2026-06-08T09:00:00Z",
  };
}

const jetsonNode = {
  id: "node-1",
  tenant_id: "tenant-1",
  node_kind: "edge",
  edge_node_id: "edge-node-1",
  supervisor_id: "jetson-supervisor-1",
  hostname: "jetson-orin",
  install_status: "healthy",
  credential_status: "active",
  service_manager: "systemd",
  service_status: "running",
  version: "0.21.0",
  os_name: "linux",
  host_profile: "linux-aarch64-nvidia-jetson",
  last_service_reported_at: "2026-06-08T09:00:00Z",
  diagnostics: {},
  created_at: "2026-06-08T09:00:00Z",
  updated_at: "2026-06-08T09:00:00Z",
};
