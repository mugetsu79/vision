import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const settingsMocks = vi.hoisted(() => ({
  fleetOverview: null as unknown,
  cameras: null as unknown,
  sites: null as unknown,
  models: null as unknown,
  memoryPatterns: null as unknown,
  framesByCamera: null as unknown,
}));

const fleetOverview = {
  mode: "manual_dev",
  generated_at: "2026-04-28T07:00:00Z",
  summary: {
    desired_workers: 2,
    running_workers: 0,
    stale_nodes: 1,
    offline_nodes: 0,
    native_unavailable_cameras: 1,
  },
  nodes: [
    {
      id: null,
      kind: "central",
      hostname: "central",
      site_id: null,
      status: "unknown",
      version: null,
      last_seen_at: null,
      assigned_camera_ids: ["00000000-0000-0000-0000-000000000101"],
      reported_camera_count: null,
    },
    {
      id: "00000000-0000-0000-0000-000000000201",
      kind: "edge",
      hostname: "jetson-1",
      site_id: "00000000-0000-0000-0000-000000000301",
      status: "stale",
      version: "0.1.0",
      last_seen_at: "2026-04-28T06:50:00Z",
      assigned_camera_ids: ["00000000-0000-0000-0000-000000000102"],
      reported_camera_count: null,
    },
  ],
  camera_workers: [
    {
      camera_id: "00000000-0000-0000-0000-000000000101",
      camera_name: "Lobby",
      site_id: "00000000-0000-0000-0000-000000000301",
      node_id: null,
      node_hostname: null,
      processing_mode: "central",
      desired_state: "manual",
      runtime_status: "not_reported",
      lifecycle_owner: "manual_dev",
      dev_run_command:
        "python3 -m uv run python -m argus.inference.engine --camera-id 00000000-0000-0000-0000-000000000101",
      detail: "Start this worker manually in local development.",
      runtime_passport: {
        id: "00000000-0000-0000-0000-000000000901",
        passport_hash:
          "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        selected_backend: "tensorrt_engine",
        model_hash:
          "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        runtime_artifact_id: "00000000-0000-0000-0000-000000000902",
        runtime_artifact_hash:
          "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
        target_profile: "linux-aarch64-nvidia-jetson",
        precision: "fp16",
        validated_at: "2026-05-11T10:00:00Z",
        fallback_reason: null,
        runtime_selection_profile_id: "00000000-0000-0000-0000-000000000903",
        runtime_selection_profile_name: "Jetson runtime",
        runtime_selection_profile_hash:
          "9999999999999999999999999999999999999999999999999999999999999999",
        provider_versions: { tensorrt: "10.0.0" },
      },
      rule_runtime: {
        configured_rule_count: 2,
        effective_rule_hash:
          "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        latest_rule_event_at: "2026-05-12T09:30:00Z",
        load_status: "loaded",
      },
      latest_hardware_report: null,
      latest_model_admission: null,
    },
    {
      camera_id: "00000000-0000-0000-0000-000000000102",
      camera_name: "Driveway",
      site_id: "00000000-0000-0000-0000-000000000301",
      node_id: "00000000-0000-0000-0000-000000000201",
      node_hostname: "jetson-1",
      processing_mode: "edge",
      desired_state: "supervised",
      runtime_status: "stale",
      lifecycle_owner: "edge_supervisor",
      dev_run_command: null,
      detail: "Edge supervisor owns this worker process.",
      rule_runtime: {
        configured_rule_count: 0,
        effective_rule_hash: null,
        latest_rule_event_at: null,
        load_status: "not_configured",
      },
      assignment: {
        id: "00000000-0000-0000-0000-000000000401",
        tenant_id: "tenant-1",
        camera_id: "00000000-0000-0000-0000-000000000102",
        edge_node_id: "00000000-0000-0000-0000-000000000201",
        desired_state: "supervised",
        active: true,
        supersedes_assignment_id: null,
        assigned_by_subject: "operator-1",
        created_at: "2026-05-13T08:00:00Z",
        updated_at: "2026-05-13T08:00:00Z",
      },
      runtime_report: {
        id: "00000000-0000-0000-0000-000000000501",
        tenant_id: "tenant-1",
        camera_id: "00000000-0000-0000-0000-000000000102",
        edge_node_id: "00000000-0000-0000-0000-000000000201",
        assignment_id: "00000000-0000-0000-0000-000000000401",
        heartbeat_at: "2026-05-13T08:01:00Z",
        runtime_state: "running",
        restart_count: 3,
        last_error: "previous restart recovered",
        runtime_artifact_id: "00000000-0000-0000-0000-000000000601",
        scene_contract_hash:
          "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        created_at: "2026-05-13T08:01:00Z",
      },
      latest_lifecycle_request: {
        id: "00000000-0000-0000-0000-000000000701",
        tenant_id: "tenant-1",
        camera_id: "00000000-0000-0000-0000-000000000102",
        edge_node_id: "00000000-0000-0000-0000-000000000201",
        assignment_id: "00000000-0000-0000-0000-000000000401",
        action: "restart",
        status: "requested",
        requested_by_subject: "operator-1",
        requested_at: "2026-05-13T08:02:00Z",
        acknowledged_at: null,
        claimed_by_supervisor: null,
        claimed_at: null,
        completed_at: null,
        admission_report_id: null,
        error: null,
        request_payload: { reason: "operator_test" },
        created_at: "2026-05-13T08:02:00Z",
        updated_at: "2026-05-13T08:02:00Z",
      },
      latest_hardware_report: {
        id: "00000000-0000-0000-0000-000000000801",
        tenant_id: "tenant-1",
        edge_node_id: "00000000-0000-0000-0000-000000000201",
        supervisor_id: "edge-supervisor-1",
        reported_at: "2026-05-13T08:03:00Z",
        host_profile: "macos-x86_64-intel",
        os_name: "darwin",
        machine_arch: "x86_64",
        cpu_model: "Intel Core i7",
        cpu_cores: 8,
        memory_total_mb: 32768,
        accelerators: ["coreml"],
        provider_capabilities: { CoreMLExecutionProvider: true },
        observed_performance: [
          {
            model_id: "00000000-0000-0000-0000-000000000803",
            model_name: "YOLO26n COCO",
            runtime_backend: "CoreMLExecutionProvider",
            input_width: 1280,
            input_height: 720,
            target_fps: 10,
            observed_fps: 10,
            stage_p95_ms: { total: 92 },
            stage_p99_ms: { total: 118 },
            captured_at: "2026-05-13T08:03:00Z",
          },
        ],
        thermal_state: "nominal",
        report_hash:
          "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        created_at: "2026-05-13T08:03:00Z",
      },
      latest_model_admission: {
        id: "00000000-0000-0000-0000-000000000811",
        tenant_id: "tenant-1",
        camera_id: "00000000-0000-0000-0000-000000000102",
        edge_node_id: "00000000-0000-0000-0000-000000000201",
        assignment_id: "00000000-0000-0000-0000-000000000401",
        hardware_report_id: "00000000-0000-0000-0000-000000000801",
        model_id: "00000000-0000-0000-0000-000000000803",
        model_name: "YOLO26n COCO",
        model_capability: "fixed_vocab",
        runtime_artifact_id: null,
        runtime_selection_profile_id: null,
        stream_profile: { width: 1280, height: 720, fps: 10 },
        status: "recommended",
        selected_backend: "CoreMLExecutionProvider",
        recommended_model_id: null,
        recommended_model_name: null,
        recommended_runtime_profile_id: null,
        recommended_backend: "CoreMLExecutionProvider",
        rationale: "CoreML p95 total fits the frame budget.",
        constraints: { frame_budget_ms: 100 },
        evaluated_at: "2026-05-13T08:04:00Z",
        created_at: "2026-05-13T08:04:00Z",
      },
      supervisor_mode: "polling",
      restart_policy: "always",
      allowed_lifecycle_actions: ["start", "stop", "restart", "drain"],
      last_error: "previous restart recovered",
    },
  ],
  delivery_diagnostics: [
    {
      camera_id: "00000000-0000-0000-0000-000000000101",
      camera_name: "Lobby",
      processing_mode: "central",
      assigned_node_id: null,
      source_capability: { width: 1280, height: 720, fps: 10, codec: "h264" },
      default_profile: "720p10",
      available_profiles: [{ id: "720p10", kind: "transcode" }],
      native_status: { available: false, reason: "privacy_filtering_required" },
      selected_stream_mode: "transcode",
    },
  ],
};

vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: settingsMocks.fleetOverview ?? fleetOverview,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useOperationalMemoryPatterns: () => ({
    data: settingsMocks.memoryPatterns ?? [
      {
        id: "00000000-0000-0000-0000-000000000901",
        tenant_id: "tenant-1",
        site_id: "00000000-0000-0000-0000-000000000301",
        camera_id: "00000000-0000-0000-0000-000000000101",
        pattern_type: "event_burst",
        severity: "warning",
        summary: "Observed pattern: 3 incidents in one zone.",
        window_started_at: "2026-05-12T08:00:00Z",
        window_ended_at: "2026-05-12T08:15:00Z",
        source_incident_ids: ["00000000-0000-0000-0000-000000000701"],
        source_contract_hashes: [
          "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ],
        dimensions: { zone_id: "server-room" },
        evidence: { incident_count: 3 },
        pattern_hash:
          "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        created_at: "2026-05-12T08:20:00Z",
      },
    ],
    isLoading: false,
  }),
  useCreateBootstrapMaterial: () => ({
    mutateAsync: vi.fn(() =>
      Promise.resolve({
        edge_node_id: "00000000-0000-0000-0000-000000000999",
        api_key: "edge_secret_once",
        nats_nkey_seed: "nats_secret_once",
        subjects: [],
        mediamtx_url: "http://mediamtx:9997",
        overlay_network_hints: {},
        dev_compose_command:
          "docker compose -f infra/docker-compose.edge.yml up inference-worker",
        supervisor_environment: {
          ARGUS_EDGE_NODE_ID: "00000000-0000-0000-0000-000000000999",
        },
      }),
    ),
    isPending: false,
  }),
  useCreateLifecycleRequest: () => ({
    mutateAsync: vi.fn(() => Promise.resolve({})),
    isPending: false,
  }),
  useCreateWorkerAssignment: () => ({
    mutateAsync: vi.fn(() => Promise.resolve({})),
    isPending: false,
  }),
}));

vi.mock("@/hooks/use-cameras", () => ({
  useCameras: () => ({
    data: settingsMocks.cameras ?? [
      {
        id: "00000000-0000-0000-0000-000000000101",
        site_id: "00000000-0000-0000-0000-000000000301",
        edge_node_id: null,
        name: "Lobby",
        rtsp_url_masked: "rtsp://redacted@camera.local/live",
        camera_source: {
          kind: "rtsp",
          uri: "rtsp://redacted@camera.local/live",
        },
        processing_mode: "central",
        primary_model_id: "00000000-0000-0000-0000-000000000001",
        secondary_model_id: null,
        tracker_type: "bytetrack",
        active_classes: ["person"],
        attribute_rules: [],
        zones: [
          {
            id: "entry-line",
            type: "line",
            points: [
              [0, 0],
              [1, 1],
            ],
          },
        ],
        homography: { src: [], dst: [], ref_distance_m: 1 },
        privacy: {
          blur_faces: true,
          blur_plates: true,
          method: "gaussian",
          strength: 7,
        },
        browser_delivery: {
          default_profile: "720p10",
          allow_native_on_demand: true,
          profiles: [],
          unsupported_profiles: [],
          native_status: {
            available: false,
            reason: "privacy_filtering_required",
          },
        },
        source_capability: { width: 1280, height: 720, fps: 10, codec: "h264" },
        recording_policy: {
          enabled: true,
          mode: "event_clip",
          pre_seconds: 6,
          post_seconds: 10,
          fps: 12,
          max_duration_seconds: 16,
          storage_profile: "cloud",
          snapshot_enabled: false,
          snapshot_offset_seconds: 0,
          snapshot_quality: 85,
        },
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-05-09T07:00:00Z",
        updated_at: "2026-05-09T07:00:00Z",
      },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-live-telemetry", () => ({
  useLiveTelemetry: () => ({
    connectionState: "open",
    framesByCamera: settingsMocks.framesByCamera ?? {},
  }),
}));

vi.mock("@/hooks/use-sites", () => ({
  useSites: () => ({
    data: settingsMocks.sites ?? [
      {
        id: "00000000-0000-0000-0000-000000000301",
        tenant_id: "tenant-1",
        name: "Zurich Lab",
        description: null,
        tz: "Europe/Zurich",
        geo_point: null,
        created_at: "2026-05-09T07:00:00Z",
      },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-models", () => ({
  useModels: () => ({
    data: settingsMocks.models ?? [
      {
        id: "00000000-0000-0000-0000-000000000001",
        name: "YOLO26n",
        version: "2026.1",
        task: "detect",
        path: "/models/yolo26n.onnx",
        format: "onnx",
        capability: "fixed_vocab",
        capability_config: { runtime_backend: "onnxruntime" },
        classes: ["person", "car"],
        input_shape: { width: 640, height: 640 },
        sha256: "a".repeat(64),
        size_bytes: 1024,
        license: "AGPL-3.0",
      },
    ],
    isLoading: false,
  }),
  useRuntimeArtifactsByModelId: () => ({
    data: {
      "00000000-0000-0000-0000-000000000001": [
        {
          id: "00000000-0000-0000-0000-000000000401",
          model_id: "00000000-0000-0000-0000-000000000001",
          camera_id: null,
          scope: "model",
          kind: "tensorrt_engine",
          capability: "fixed_vocab",
          runtime_backend: "tensorrt_engine",
          path: "/models/yolo26n.jetson.fp16.engine",
          target_profile: "linux-aarch64-nvidia-jetson",
          precision: "fp16",
          input_shape: { width: 640, height: 640 },
          classes: ["person", "car"],
          vocabulary_hash: null,
          vocabulary_version: null,
          source_model_sha256: "a".repeat(64),
          sha256: "b".repeat(64),
          size_bytes: 2048,
          builder: {},
          runtime_versions: {},
          validation_status: "valid",
          validation_error: null,
          build_duration_seconds: 2.5,
          validation_duration_seconds: null,
          validated_at: "2026-05-10T08:00:00Z",
          created_at: "2026-05-10T08:00:00Z",
          updated_at: "2026-05-10T08:00:00Z",
        },
      ],
    },
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-configuration", () => ({
  useConfigurationCatalog: () => ({
    data: {
      kinds: [
        { kind: "evidence_storage", label: "Evidence storage" },
        { kind: "stream_delivery", label: "Transport profile" },
        { kind: "runtime_selection", label: "Runtime" },
        { kind: "privacy_policy", label: "Privacy and retention" },
        { kind: "llm_provider", label: "LLM and policy" },
        { kind: "operations_mode", label: "Operations" },
      ],
    },
    isLoading: false,
  }),
  useConfigurationProfiles: () => ({
    data: [
      {
        id: "profile-minio",
        tenant_id: "tenant-1",
        kind: "evidence_storage",
        scope: "tenant",
        name: "Central MinIO",
        slug: "central-minio",
        enabled: true,
        is_default: true,
        config: {
          provider: "minio",
          storage_scope: "central",
          endpoint: "localhost:9000",
          bucket: "incidents",
          secure: false,
        },
        secret_state: { secret_key: "present" },
        validation_status: "unvalidated",
        validation_message: null,
        validated_at: null,
        config_hash: "a".repeat(64),
        created_at: "2026-05-11T10:00:00Z",
        updated_at: "2026-05-11T10:00:00Z",
      },
    ],
    isLoading: false,
  }),
  useConfigurationBindings: () => ({
    data: [],
    isLoading: false,
  }),
  useConfigurationProfileImpact: () => ({
    data: null,
    isLoading: false,
  }),
  useCreateConfigurationProfile: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateConfigurationProfile: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteConfigurationProfile: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteConfigurationBinding: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useTestConfigurationProfile: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpsertConfigurationBinding: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useResolvedConfiguration: () => ({ data: null, isLoading: false }),
}));

import { SettingsPage } from "@/pages/Settings";
import { TestMemoryRouter } from "@/test/router";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TestMemoryRouter>
        <SettingsPage />
      </TestMemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SettingsPage operations workbench", () => {
  beforeEach(() => {
    settingsMocks.fleetOverview = null;
    settingsMocks.cameras = null;
    settingsMocks.sites = null;
    settingsMocks.models = null;
    settingsMocks.memoryPatterns = null;
    settingsMocks.framesByCamera = null;
  });

  test("renders fleet operations with attention-first order and deferred configuration details", async () => {
    const user = userEvent.setup();

    renderPage();

    expect(
      screen.getByRole("heading", { name: /operations/i }),
    ).toBeInTheDocument();
    const workspace = screen.getByTestId("operations-workspace");
    expect(workspace).toBeInTheDocument();
    const attentionOverview = screen.getByTestId("attention-stack");
    const sceneMatrix = screen.getByTestId("scene-intelligence-matrix");
    const sectionNav = within(workspace).getByRole("navigation", {
      name: /operations sections/i,
    });
    const workerRail = screen.getByTestId("worker-rail");
    const configurationSection = screen.getByTestId("configuration-section");

    expect(attentionOverview).toBeInTheDocument();
    expect(
      attentionOverview.compareDocumentPosition(sceneMatrix) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      attentionOverview.compareDocumentPosition(workerRail) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      sceneMatrix.compareDocumentPosition(sectionNav) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      sectionNav.compareDocumentPosition(workerRail) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      workerRail.compareDocumentPosition(configurationSection) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      within(sectionNav).getByRole("link", { name: /workers/i }),
    ).toHaveAttribute("href", "#workers");
    expect(
      within(sectionNav).getByRole("link", { name: /stream diagnostics/i }),
    ).toHaveAttribute("href", "#stream-diagnostics");
    expect(
      within(sectionNav).getByRole("link", { name: /deployment nodes/i }),
    ).toHaveAttribute("href", "#deployment-nodes");
    expect(
      within(sectionNav).getByRole("link", { name: /configuration/i }),
    ).toHaveAttribute("href", "#configuration");
    expect(
      within(sectionNav).getByRole("link", { name: /installer guidance/i }),
    ).toHaveAttribute("href", "#installer-guidance");
    const configurationToggle = within(configurationSection).getByRole(
      "button",
      { name: /show configuration/i },
    );
    expect(configurationToggle).toHaveAttribute("aria-expanded", "false");
    expect(configurationToggle).toHaveAttribute(
      "aria-controls",
      "configuration-content",
    );
    const configurationContent = document.getElementById(
      "configuration-content",
    );
    expect(configurationContent).toBeInTheDocument();
    expect(configurationContent).not.toBeVisible();
    expect(
      screen.queryByTestId("configuration-workspace"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("runtime-artifact-rail"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("No scenes focused")).toBeInTheDocument();
    await user.type(
      screen.getByLabelText(/search operations scenes/i),
      "lobby",
    );
    expect(screen.getByText("1 matching")).toBeInTheDocument();
    expect(sceneMatrix).toBeInTheDocument();
    expect(
      within(sceneMatrix).getByText(/scene readiness/i),
    ).toBeInTheDocument();
    expect(
      within(sceneMatrix).getByText(/2 active rules/i),
    ).toBeInTheDocument();
    expect(
      within(sceneMatrix).getByText(/awaiting telemetry/i),
    ).toBeInTheDocument();
    expect(within(sceneMatrix).getByText(/ffffffffffff/i)).toBeInTheDocument();
    const memoryPanel = screen.getByTestId("operational-memory-panel");
    expect(
      within(memoryPanel).getByText(/observed patterns/i),
    ).toBeInTheDocument();
    expect(
      within(memoryPanel).getByText(
        /observed pattern: 3 incidents in one zone/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId("edge-fleet-grid")).toBeInTheDocument();
    expect(screen.getByTestId("worker-rail")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getAllByText(
        /runtime diagnostics/i,
      ).length,
    ).toBeGreaterThan(0);
    expect(screen.getByTestId("stream-diagnostics-rail")).toBeInTheDocument();
    expect(screen.getAllByText(/stream diagnostics/i).length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText(/native unavailable/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/desired state/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/camera workers/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/assigned cameras/i)).not.toBeInTheDocument();
    expect(screen.getByText(/scene workers/i)).toBeInTheDocument();
    expect(screen.getByText(/manual dev mode/i)).toBeInTheDocument();
    expect(
      screen.getByText(/rotated credentials must be picked up/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/planned workers/i).length).toBeGreaterThan(0);
    expect(
      within(screen.getByTestId("edge-fleet-grid")).getByText(
        /direct streams unavailable/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(/direct stream unavailable/i).length,
    ).toBeGreaterThan(0);
    expect(
      within(sceneMatrix).getByRole("link", {
        name: /inspect operations for lobby/i,
      }),
    ).toHaveAttribute("href", "/settings");
    expect(
      screen.queryByText(/prompt 7 uses this route/i),
    ).not.toBeInTheDocument();

    await user.click(configurationToggle);

    expect(
      within(configurationSection).getByRole("button", {
        name: /hide configuration/i,
      }),
    ).toHaveAttribute("aria-expanded", "true");
    const configurationWorkspace = screen.getByTestId(
      "configuration-workspace",
    );
    expect(configurationWorkspace).toBeVisible();
    expect(screen.getByTestId("runtime-artifact-rail")).toBeVisible();

    await user.click(
      within(configurationSection).getByRole("button", {
        name: /hide configuration/i,
      }),
    );

    expect(
      within(configurationSection).getByRole("button", {
        name: /show configuration/i,
      }),
    ).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("configuration-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("configuration-workspace")).not.toBeVisible();

    await user.click(
      within(configurationSection).getByRole("button", {
        name: /show configuration/i,
      }),
    );

    expect(screen.getByTestId("configuration-workspace")).toBeVisible();
    expect(screen.getByTestId("runtime-artifact-rail")).toBeVisible();
  });

  test("shows live telemetry status when operations receives retained live frames", async () => {
    const user = userEvent.setup();
    settingsMocks.framesByCamera = {
      "00000000-0000-0000-0000-000000000101": {
        camera_id: "00000000-0000-0000-0000-000000000101",
        ts: new Date().toISOString(),
        profile: "central-gpu",
        stream_mode: "annotated-whip",
        counts: {},
        tracks: [],
      },
    };

    renderPage();

    await user.type(
      screen.getByLabelText(/search operations scenes/i),
      "lobby",
    );
    const sceneMatrix = screen.getByTestId("scene-intelligence-matrix");
    expect(
      within(sceneMatrix).getByText(/telemetry live/i),
    ).toBeInTheDocument();
  });

  test("does not show operations detail until an operator searches or selects scenes", async () => {
    const user = userEvent.setup();
    settingsMocks.cameras = [
      {
        id: "00000000-0000-0000-0000-000000000101",
        site_id: "00000000-0000-0000-0000-000000000301",
        edge_node_id: null,
        name: "Lobby",
        rtsp_url_masked: "rtsp://redacted@camera.local/live",
        camera_source: {
          kind: "rtsp",
          uri: "rtsp://redacted@camera.local/live",
        },
        processing_mode: "central",
        primary_model_id: "00000000-0000-0000-0000-000000000001",
        secondary_model_id: null,
        tracker_type: "bytetrack",
        active_classes: ["person"],
        attribute_rules: [],
        zones: [],
        homography: null,
        privacy: {
          blur_faces: true,
          blur_plates: true,
          method: "gaussian",
          strength: 7,
        },
        browser_delivery: {
          default_profile: "720p10",
          allow_native_on_demand: true,
          profiles: [],
          unsupported_profiles: [],
          native_status: {
            available: false,
            reason: "privacy_filtering_required",
          },
        },
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-05-09T07:00:00Z",
        updated_at: "2026-05-09T07:00:00Z",
      },
      {
        id: "00000000-0000-0000-0000-000000000102",
        site_id: "00000000-0000-0000-0000-000000000301",
        edge_node_id: "00000000-0000-0000-0000-000000000201",
        name: "Driveway",
        rtsp_url_masked: "rtsp://redacted@driveway.local/live",
        camera_source: {
          kind: "rtsp",
          uri: "rtsp://redacted@driveway.local/live",
        },
        processing_mode: "edge",
        primary_model_id: "00000000-0000-0000-0000-000000000001",
        secondary_model_id: null,
        tracker_type: "botsort",
        active_classes: ["car"],
        attribute_rules: [],
        zones: [],
        homography: null,
        privacy: {
          blur_faces: true,
          blur_plates: true,
          method: "gaussian",
          strength: 7,
        },
        browser_delivery: {
          default_profile: "540p5",
          allow_native_on_demand: true,
          profiles: [],
          unsupported_profiles: [],
          native_status: { available: true, reason: null },
        },
        recording_policy: {
          enabled: true,
          mode: "event_clip",
          pre_seconds: 6,
          post_seconds: 10,
          fps: 12,
          max_duration_seconds: 16,
          storage_profile: "cloud",
          snapshot_enabled: false,
          snapshot_offset_seconds: 0,
          snapshot_quality: 85,
        },
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-05-09T07:00:00Z",
        updated_at: "2026-05-09T07:00:00Z",
      },
    ];
    settingsMocks.fleetOverview = {
      ...fleetOverview,
      delivery_diagnostics: [
        ...fleetOverview.delivery_diagnostics,
        {
          camera_id: "00000000-0000-0000-0000-000000000102",
          camera_name: "Driveway",
          processing_mode: "edge",
          assigned_node_id: "00000000-0000-0000-0000-000000000201",
          source_capability: { width: 1920, height: 1080, fps: 15 },
          default_profile: "540p5",
          available_profiles: [{ id: "540p5", kind: "transcode" }],
          native_status: { available: true, reason: null },
          selected_stream_mode: "transcode",
        },
      ],
    };
    settingsMocks.memoryPatterns = [
      {
        id: "00000000-0000-0000-0000-000000000901",
        tenant_id: "tenant-1",
        site_id: "00000000-0000-0000-0000-000000000301",
        camera_id: "00000000-0000-0000-0000-000000000101",
        pattern_type: "event_burst",
        severity: "warning",
        summary: "Lobby pattern: 3 incidents in one zone.",
        window_started_at: "2026-05-12T08:00:00Z",
        window_ended_at: "2026-05-12T08:15:00Z",
        source_incident_ids: ["00000000-0000-0000-0000-000000000701"],
        source_contract_hashes: ["a".repeat(64)],
        dimensions: { zone_id: "lobby" },
        evidence: { incident_count: 3 },
        pattern_hash: "b".repeat(64),
        created_at: "2026-05-12T08:20:00Z",
      },
      {
        id: "00000000-0000-0000-0000-000000000902",
        tenant_id: "tenant-1",
        site_id: "00000000-0000-0000-0000-000000000301",
        camera_id: "00000000-0000-0000-0000-000000000102",
        pattern_type: "zone_hotspot",
        severity: "critical",
        summary: "Driveway pattern: 5 incidents at the gate.",
        window_started_at: "2026-05-12T09:00:00Z",
        window_ended_at: "2026-05-12T09:15:00Z",
        source_incident_ids: ["00000000-0000-0000-0000-000000000702"],
        source_contract_hashes: ["c".repeat(64)],
        dimensions: { zone_id: "gate" },
        evidence: { incident_count: 5 },
        pattern_hash: "d".repeat(64),
        created_at: "2026-05-12T09:20:00Z",
      },
    ];

    renderPage();

    const sceneMatrix = screen.getByTestId("scene-intelligence-matrix");
    const workerRail = screen.getByTestId("worker-rail");
    const diagnosticsRail = screen.getByTestId("stream-diagnostics-rail");
    const memoryPanel = screen.getByTestId("operational-memory-panel");

    expect(screen.getByText("No scenes focused")).toBeInTheDocument();
    expect(
      within(sceneMatrix).getByText(
        /select or search scenes to review readiness/i,
      ),
    ).toBeInTheDocument();
    expect(within(sceneMatrix).queryByText("Lobby")).not.toBeInTheDocument();
    expect(within(sceneMatrix).queryByText("Driveway")).not.toBeInTheDocument();
    expect(
      within(workerRail).getByText(
        /select or search scenes to review workers/i,
      ),
    ).toBeInTheDocument();
    expect(within(workerRail).queryByText("Lobby")).not.toBeInTheDocument();
    expect(within(workerRail).queryByText("Driveway")).not.toBeInTheDocument();
    expect(
      within(diagnosticsRail).getByText(
        /select or search scenes to review stream diagnostics/i,
      ),
    ).toBeInTheDocument();
    expect(
      within(diagnosticsRail).queryByText(/Lobby scene delivery/i),
    ).not.toBeInTheDocument();
    expect(
      within(diagnosticsRail).queryByText(/Driveway scene delivery/i),
    ).not.toBeInTheDocument();
    expect(
      within(memoryPanel).queryByText(/Lobby pattern/i),
    ).not.toBeInTheDocument();
    expect(
      within(memoryPanel).queryByText(/Driveway pattern/i),
    ).not.toBeInTheDocument();

    await user.type(
      screen.getByLabelText(/search operations scenes/i),
      "drive",
    );

    expect(screen.getByText("1 matching")).toBeInTheDocument();
    expect(within(sceneMatrix).getByText("Driveway")).toBeInTheDocument();
    expect(within(sceneMatrix).queryByText("Lobby")).not.toBeInTheDocument();
    expect(within(workerRail).getByText("Driveway")).toBeInTheDocument();
    expect(within(workerRail).queryByText("Lobby")).not.toBeInTheDocument();
    expect(
      within(diagnosticsRail).getByText(/Driveway scene delivery/i),
    ).toBeInTheDocument();
    expect(
      within(diagnosticsRail).queryByText(/Lobby scene delivery/i),
    ).not.toBeInTheDocument();
    expect(
      within(memoryPanel).getByText(/Driveway pattern/i),
    ).toBeInTheDocument();
    expect(
      within(memoryPanel).queryByText(/Lobby pattern/i),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: "Driveway" }));

    expect(screen.getByText("1 selected")).toBeInTheDocument();
    expect(within(sceneMatrix).getByText("Driveway")).toBeInTheDocument();
  });

  test("paginates large focused operations result panels", async () => {
    const user = userEvent.setup();
    const siteId = "00000000-0000-0000-0000-000000000301";
    const cameras = Array.from({ length: 12 }, (_, index) => {
      const number = index + 1;
      return {
        id: `00000000-0000-0000-0000-${String(100 + number).padStart(12, "0")}`,
        site_id: siteId,
        edge_node_id: null,
        name: `Batch Scene ${String(number).padStart(2, "0")}`,
        rtsp_url_masked: "rtsp://redacted@camera.local/live",
        camera_source: {
          kind: "rtsp",
          uri: "rtsp://redacted@camera.local/live",
        },
        processing_mode: "central",
        primary_model_id: "00000000-0000-0000-0000-000000000001",
        secondary_model_id: null,
        tracker_type: "bytetrack",
        active_classes: ["person"],
        attribute_rules: [],
        zones: [],
        homography: null,
        privacy: {
          blur_faces: true,
          blur_plates: true,
          method: "gaussian",
          strength: 7,
        },
        browser_delivery: {
          default_profile: "720p10",
          allow_native_on_demand: true,
          profiles: [],
          unsupported_profiles: [],
          native_status: {
            available: false,
            reason: "privacy_filtering_required",
          },
        },
        source_capability: {
          width: 1280,
          height: 720,
          fps: 10,
          codec: "h264",
        },
        recording_policy: {
          enabled: true,
          mode: "event_clip",
          pre_seconds: 6,
          post_seconds: 10,
          fps: 12,
          max_duration_seconds: 16,
          storage_profile: "cloud",
          snapshot_enabled: false,
          snapshot_offset_seconds: 0,
          snapshot_quality: 85,
        },
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-05-09T07:00:00Z",
        updated_at: "2026-05-09T07:00:00Z",
      };
    });
    settingsMocks.cameras = cameras;
    settingsMocks.fleetOverview = {
      ...fleetOverview,
      summary: {
        desired_workers: cameras.length,
        running_workers: 0,
        stale_nodes: 0,
        offline_nodes: 0,
        native_unavailable_cameras: cameras.length,
      },
      nodes: fleetOverview.nodes,
      camera_workers: cameras.map((camera) => ({
        camera_id: camera.id,
        camera_name: camera.name,
        site_id: siteId,
        node_id: null,
        node_hostname: null,
        processing_mode: "central",
        desired_state: "manual",
        runtime_status: "not_reported",
        lifecycle_owner: "manual_dev",
        dev_run_command: null,
        detail: null,
      })),
      delivery_diagnostics: cameras.map((camera) => ({
        camera_id: camera.id,
        camera_name: camera.name,
        processing_mode: "central",
        assigned_node_id: null,
        source_capability: {
          width: 1280,
          height: 720,
          fps: 10,
          codec: "h264",
        },
        default_profile: "720p10",
        available_profiles: [{ id: "720p10", kind: "transcode" }],
        native_status: {
          available: false,
          reason: "privacy_filtering_required",
        },
        selected_stream_mode: "transcode",
      })),
    };
    settingsMocks.memoryPatterns = [];

    renderPage();
    await user.type(
      screen.getByLabelText(/search operations scenes/i),
      "batch",
    );

    const sceneMatrix = screen.getByTestId("scene-intelligence-matrix");
    expect(within(sceneMatrix).getByText("Batch Scene 10")).toBeInTheDocument();
    expect(
      within(sceneMatrix).queryByText("Batch Scene 11"),
    ).not.toBeInTheDocument();
    await user.selectOptions(
      screen.getByLabelText(/scene readiness per page/i),
      "25",
    );
    expect(within(sceneMatrix).getByText("Batch Scene 11")).toBeInTheDocument();

    const workerRail = screen.getByTestId("worker-rail");
    expect(within(workerRail).getByText("Batch Scene 10")).toBeInTheDocument();
    expect(
      within(workerRail).queryByText("Batch Scene 11"),
    ).not.toBeInTheDocument();
    await user.selectOptions(
      within(workerRail).getByLabelText(/scene workers per page/i),
      "25",
    );
    expect(within(workerRail).getByText("Batch Scene 11")).toBeInTheDocument();

    const diagnosticsRail = screen.getByTestId("stream-diagnostics-rail");
    expect(
      within(diagnosticsRail).getByText(/Batch Scene 10 scene delivery/i),
    ).toBeInTheDocument();
    expect(
      within(diagnosticsRail).queryByText(/Batch Scene 11 scene delivery/i),
    ).not.toBeInTheDocument();
    await user.selectOptions(
      within(diagnosticsRail).getByLabelText(/stream diagnostics per page/i),
      "25",
    );
    expect(
      within(diagnosticsRail).getByText(/Batch Scene 11 scene delivery/i),
    ).toBeInTheDocument();
  });

  test("guides a fresh tenant to configure sites, scenes, and deployment", () => {
    settingsMocks.fleetOverview = {
      ...fleetOverview,
      mode: "supervised",
      summary: {
        desired_workers: 0,
        running_workers: 0,
        stale_nodes: 0,
        offline_nodes: 0,
        native_unavailable_cameras: 0,
      },
      nodes: [],
      camera_workers: [],
      delivery_diagnostics: [],
    };
    settingsMocks.cameras = [];
    settingsMocks.sites = [];
    settingsMocks.models = [];
    settingsMocks.memoryPatterns = [];

    renderPage();

    const workspace = screen.getByTestId("operations-workspace");
    expect(
      within(workspace).getByRole("heading", {
        name: /configure sites, scenes, and deployment/i,
      }),
    ).toBeInTheDocument();
    expect(
      within(workspace).queryByText(/failed to load fleet operations/i),
    ).not.toBeInTheDocument();
    expect(
      within(workspace).getByRole("link", { name: /open sites/i }),
    ).toHaveAttribute("href", "/sites");
    expect(
      within(workspace).getByRole("link", { name: /open scenes/i }),
    ).toHaveAttribute("href", "/cameras");
    expect(
      within(workspace)
        .getAllByRole("link", { name: /open deployment/i })
        .some((link) => link.getAttribute("href") === "/deployment"),
    ).toBe(true);
    expect(
      within(workspace).getByText(/no deployment nodes yet/i),
    ).toBeInTheDocument();
    expect(
      within(workspace).getByText(/no scene workers yet/i),
    ).toBeInTheDocument();
  });

  test("shows worker lifecycle and delivery diagnostics", async () => {
    const user = userEvent.setup();

    renderPage();
    await user.type(
      screen.getByLabelText(/search operations scenes/i),
      "lobby",
    );

    expect(
      within(screen.getByTestId("worker-rail")).getByText("Lobby"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/argus.inference.engine --camera-id/i),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getByText(
        /installable supervisors own production worker launch/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("jetson-1").length).toBeGreaterThan(0);
    expect(
      within(screen.getByTestId("worker-rail")).getByText(/rtsp source/i),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getByText(
        /event clips: cloud storage/i,
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getByText("tensorrt_engine"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getByText(
        /linux-aarch64-nvidia-jetson/i,
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getByText("Jetson runtime"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getAllByText(/^rules$/i).length,
    ).toBeGreaterThan(0);
    expect(
      within(screen.getByTestId("worker-rail")).getByText(/2 active/i),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getAllByText(/ffffffffffff/i)
        .length,
    ).toBeGreaterThan(0);
    expect(
      within(screen.getByTestId("worker-rail")).getByText(/loaded/i),
    ).toBeInTheDocument();
    const diagnosticsRail = screen.getByTestId("stream-diagnostics-rail");
    expect(
      within(diagnosticsRail).getByText(/direct stream unavailable:/i),
    ).toBeInTheDocument();
    expect(
      within(diagnosticsRail).getByText(/privacy filtering required/i),
    ).toBeInTheDocument();
    expect(
      within(diagnosticsRail).getByText(/1280 x 720/i),
    ).toBeInTheDocument();

    await user.clear(screen.getByLabelText(/search operations scenes/i));
    await user.type(
      screen.getByLabelText(/search operations scenes/i),
      "drive",
    );
    expect(screen.getByText("1 matching")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getByText("Driveway"),
    ).toBeInTheDocument();
    const supervisorControls = screen.getAllByTestId(
      "supervisor-lifecycle-controls",
    );
    expect(supervisorControls.length).toBeGreaterThan(0);
    expect(
      screen
        .getAllByRole("button", { name: /^start$/i })
        .some((button) => !button.hasAttribute("disabled")),
    ).toBe(true);
    expect(
      screen
        .getAllByRole("button", { name: /^stop$/i })
        .some((button) => !button.hasAttribute("disabled")),
    ).toBe(true);
    expect(
      screen
        .getAllByRole("button", { name: /^restart$/i })
        .some((button) => !button.hasAttribute("disabled")),
    ).toBe(true);
    expect(
      screen
        .getAllByRole("button", { name: /^drain$/i })
        .some((button) => !button.hasAttribute("disabled")),
    ).toBe(true);
    expect(
      within(screen.getByTestId("worker-rail")).getByText(/3 restarts/i),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getByText(
        /previous restart recovered/i,
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getByText(/aaaaaaaaaaaa/i),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("worker-rail")).getAllByLabelText(
        /desired worker location/i,
      ).length,
    ).toBeGreaterThan(0);
  });

  test("surfaces removed worker assignments with a re-enable path", async () => {
    settingsMocks.fleetOverview = {
      ...fleetOverview,
      summary: {
        ...fleetOverview.summary,
        desired_workers: 1,
        running_workers: 0,
      },
      nodes: fleetOverview.nodes.map((node) =>
        node.id === "00000000-0000-0000-0000-000000000201"
          ? { ...node, assigned_camera_ids: [] }
          : node,
      ),
      camera_workers: fleetOverview.camera_workers.map((worker) =>
        worker.camera_id === "00000000-0000-0000-0000-000000000102"
          ? {
              ...worker,
              node_id: null,
              node_hostname: null,
              desired_state: "not_desired",
              runtime_status: "not_reported",
              lifecycle_owner: "none",
              detail:
                "Worker assignment removed. Assign a worker location to enable processing again.",
              runtime_report: null,
              latest_lifecycle_request: null,
              latest_hardware_report: null,
              latest_model_admission: null,
              allowed_lifecycle_actions: [],
              assignment: {
                ...worker.assignment,
                edge_node_id: null,
                desired_state: "not_desired",
              },
            }
          : worker,
      ),
    };

    const user = userEvent.setup();

    renderPage();

    await user.type(
      screen.getByLabelText(/search operations scenes/i),
      "drive",
    );

    const workerRail = screen.getByTestId("worker-rail");
    expect(within(workerRail).getByText("Driveway")).toBeInTheDocument();
    expect(within(workerRail).getByText(/not_desired/i)).toBeInTheDocument();

    const drivewayControls = screen.getByRole("region", {
      name: /supervisor controls for driveway/i,
    });
    expect(
      within(drivewayControls).getByText(/worker assignment removed/i),
    ).toBeInTheDocument();
    expect(
      within(drivewayControls).getByRole("button", { name: /^start$/i }),
    ).toBeDisabled();
    expect(
      within(drivewayControls).getByRole("button", { name: /worker removed/i }),
    ).toBeDisabled();
    expect(
      within(drivewayControls).getByRole("button", { name: /assign worker/i }),
    ).not.toBeDisabled();
  });

  test("shows model runtime artifact status", async () => {
    const user = userEvent.setup();

    renderPage();

    await user.click(
      within(screen.getByTestId("configuration-section")).getByRole("button", {
        name: /show configuration/i,
      }),
    );

    const artifactRail = screen.getByTestId("runtime-artifact-rail");
    expect(within(artifactRail).getByText("YOLO26n")).toBeInTheDocument();
    expect(
      within(artifactRail).getByText(/TensorRT artifact: valid/i),
    ).toBeInTheDocument();
    expect(
      within(artifactRail).getByText(/linux-aarch64-nvidia-jetson/i),
    ).toBeInTheDocument();
  });

  test("routes node pairing through deployment", () => {
    renderPage();

    expect(screen.getByText(/pair jetson edge nodes/i)).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: /open deployment/i }),
    ).toHaveLength(2);
    expect(
      screen.queryByRole("button", { name: /generate bootstrap/i }),
    ).not.toBeInTheDocument();
  });
});
