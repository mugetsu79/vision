import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

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
    data: fleetOverview,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
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
}));

vi.mock("@/hooks/use-cameras", () => ({
  useCameras: () => ({
    data: [
      {
        id: "00000000-0000-0000-0000-000000000101",
        site_id: "00000000-0000-0000-0000-000000000301",
        edge_node_id: null,
        name: "Lobby",
        rtsp_url_masked: "rtsp://redacted@camera.local/live",
        processing_mode: "central",
        primary_model_id: "00000000-0000-0000-0000-000000000001",
        secondary_model_id: null,
        tracker_type: "bytetrack",
        active_classes: ["person"],
        attribute_rules: [],
        zones: [{ id: "entry-line", type: "line", points: [[0, 0], [1, 1]] }],
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
        frame_skip: 1,
        fps_cap: 25,
        created_at: "2026-05-09T07:00:00Z",
        updated_at: "2026-05-09T07:00:00Z",
      },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-sites", () => ({
  useSites: () => ({
    data: [
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

import { SettingsPage } from "@/pages/Settings";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SettingsPage operations workbench", () => {
  test("renders fleet operations instead of placeholder copy", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { name: /operations/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("operations-workspace")).toBeInTheDocument();
    const sceneMatrix = screen.getByTestId("scene-intelligence-matrix");
    expect(sceneMatrix).toBeInTheDocument();
    expect(
      within(sceneMatrix).getByText(/scene intelligence matrix/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("edge-fleet-grid")).toBeInTheDocument();
    expect(screen.getByTestId("worker-rail")).toBeInTheDocument();
    expect(screen.getByTestId("stream-diagnostics-rail")).toBeInTheDocument();
    expect(screen.getAllByText(/stream diagnostics/i).length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText(/delivery truth/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/native unavailable/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/desired state/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/camera workers/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/assigned cameras/i)).not.toBeInTheDocument();
    expect(screen.getByText(/scene workers/i)).toBeInTheDocument();
    expect(screen.getByText(/manual dev mode/i)).toBeInTheDocument();
    expect(screen.getAllByText(/planned workers/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/direct streams unavailable/i)).toBeInTheDocument();
    expect(screen.getAllByText(/direct stream unavailable/i).length).toBeGreaterThan(
      0,
    );
    expect(
      within(sceneMatrix).getByRole("link", {
        name: /inspect delivery for lobby/i,
      }),
    ).toHaveAttribute("href", "/settings");
    expect(
      screen.queryByText(/prompt 7 uses this route/i),
    ).not.toBeInTheDocument();
  });

  test("shows worker lifecycle and delivery diagnostics", () => {
    renderPage();

    expect(
      within(screen.getByTestId("worker-rail")).getByText("Lobby"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/argus.inference.engine --camera-id/i),
    ).toBeInTheDocument();
    expect(screen.getByText("jetson-1")).toBeInTheDocument();
    const diagnosticsRail = screen.getByTestId("stream-diagnostics-rail");
    expect(
      within(diagnosticsRail).getByText(/direct stream unavailable:/i),
    ).toBeInTheDocument();
    expect(
      within(diagnosticsRail).getByText(/privacy filtering required/i),
    ).toBeInTheDocument();
    expect(within(diagnosticsRail).getByText(/1280 x 720/i)).toBeInTheDocument();
  });

  test("generates bootstrap material with one-time warning", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/hostname/i), "edge-kit-01");
    await user.type(screen.getByLabelText(/version/i), "0.1.0");
    await user.click(
      screen.getByRole("button", { name: /generate bootstrap/i }),
    );

    expect(await screen.findByText(/edge_secret_once/i)).toBeInTheDocument();
    expect(screen.getByText(/shown once/i)).toBeInTheDocument();
    expect(screen.getByText(/docker compose/i)).toBeInTheDocument();
  });
});
