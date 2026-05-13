import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import type { components } from "@/lib/api.generated";
import { DashboardPage } from "@/pages/Dashboard";

type Camera = components["schemas"]["CameraResponse"];
type FleetOverview = components["schemas"]["FleetOverviewResponse"];

const baseCamera: Camera = {
  id: "camera-1",
  name: "North Gate",
  site_id: "site-1",
  edge_node_id: null,
  rtsp_url_masked: "rtsp://redacted@camera.local/live",
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
    default_profile: "native",
    allow_native_on_demand: true,
    profiles: [],
    unsupported_profiles: [],
    native_status: { available: true, reason: null },
  },
  source_capability: { width: 1920, height: 1080, fps: 15 },
  frame_skip: 1,
  fps_cap: 25,
  created_at: "2026-05-09T07:00:00Z",
  updated_at: "2026-05-09T07:00:00Z",
};

const fleet: FleetOverview = {
  mode: "manual_dev",
  generated_at: "2026-05-09T08:00:00Z",
  summary: {
    desired_workers: 2,
    running_workers: 1,
    stale_nodes: 0,
    offline_nodes: 0,
    native_unavailable_cameras: 1,
  },
  nodes: [],
  camera_workers: [
    {
      camera_id: "camera-1",
      camera_name: "North Gate",
      site_id: "site-1",
      node_id: null,
      node_hostname: null,
      processing_mode: "central",
      desired_state: "manual",
      runtime_status: "running",
      lifecycle_owner: "manual_dev",
      dev_run_command: null,
      detail: null,
      supervisor_mode: "disabled",
      restart_policy: "never",
    },
    {
      camera_id: "camera-2",
      camera_name: "Depot Yard",
      site_id: "site-1",
      node_id: "00000000-0000-0000-0000-000000000999",
      node_hostname: "orin1",
      processing_mode: "edge",
      desired_state: "supervised",
      runtime_status: "stale",
      lifecycle_owner: "edge_supervisor",
      dev_run_command: null,
      detail: "Edge heartbeat is stale.",
      supervisor_mode: "polling",
      restart_policy: "always",
    },
  ],
  delivery_diagnostics: [
    {
      camera_id: "camera-1",
      camera_name: "North Gate",
      processing_mode: "central",
      assigned_node_id: null,
      source_capability: { width: 1920, height: 1080, fps: 15 },
      default_profile: "native",
      available_profiles: [],
      native_status: { available: true, reason: null },
      selected_stream_mode: "passthrough",
    },
    {
      camera_id: "camera-2",
      camera_name: "Depot Yard",
      processing_mode: "edge",
      assigned_node_id: "00000000-0000-0000-0000-000000000999",
      source_capability: { width: 1920, height: 1080, fps: 15 },
      default_profile: "native",
      available_profiles: [],
      native_status: { available: false, reason: "source_unavailable" },
      selected_stream_mode: "passthrough",
    },
  ],
};

vi.mock("@/hooks/use-cameras", () => ({
  useCameras: () => ({
    data: [
      baseCamera,
      {
        ...baseCamera,
        id: "camera-2",
        name: "Depot Yard",
        processing_mode: "edge",
        edge_node_id: "00000000-0000-0000-0000-000000000999",
        browser_delivery: {
          ...baseCamera.browser_delivery,
          native_status: { available: false, reason: "source_unavailable" },
        },
      },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-incidents", () => ({
  useIncidents: () => ({
    data: [{ id: "incident-1", review_status: "pending", type: "ppe-missing" }],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-sites", () => ({
  useSites: () => ({
    data: [{ id: "site-1", name: "HQ", tz: "Europe/Zurich" }],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: fleet,
    isLoading: false,
    isError: false,
  }),
}));

describe("DashboardPage", () => {
  test("renders an OmniSight overview cockpit", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "OmniSight Overview" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("omnisight-lens")).toBeInTheDocument();
    expect(screen.getByText("Live scenes")).toBeInTheDocument();
    expect(screen.getByText("Evidence queue")).toBeInTheDocument();
    expect(screen.getByText("Edge workers")).toBeInTheDocument();
    expect(screen.getByTestId("deployment-posture-strip")).toBeInTheDocument();
    expect(screen.getByTestId("attention-stack")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /attention stack/i }),
    ).toBeInTheDocument();
    const attentionStack = screen.getByTestId("attention-stack");
    expect(
      within(attentionStack).getByText(/evidence waiting for review/i),
    ).toBeInTheDocument();
    expect(
      within(attentionStack).getByText(/direct streams unavailable/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Open Live Intelligence/i }),
    ).toHaveAttribute("href", "/live");
    expect(
      screen.getByRole("link", { name: /Review Evidence/i }),
    ).toHaveAttribute("href", "/incidents");
  });
});
