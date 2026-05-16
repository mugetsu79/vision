import { describe, expect, test } from "vitest";

import {
  deriveAttentionItems,
  deriveDeploymentPosture,
  deriveFleetHealth,
  derivePrivacyPosture,
  deriveSceneReadinessRows,
  healthToTone,
} from "@/lib/operational-health";
import type { components } from "@/lib/api.generated";

type FleetOverview = components["schemas"]["FleetOverviewResponse"];
type Camera = components["schemas"]["CameraResponse"];
type Site = components["schemas"]["SiteResponse"];
type TelemetryFrame = components["schemas"]["TelemetryFrame"];

const edgeNodeId = "00000000-0000-0000-0000-000000000999";

const fleet: FleetOverview = {
  mode: "manual_dev",
  generated_at: "2026-05-09T08:00:00Z",
  summary: {
    desired_workers: 2,
    running_workers: 1,
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
      assigned_camera_ids: ["camera-1"],
      reported_camera_count: null,
    },
    {
      id: edgeNodeId,
      kind: "edge",
      hostname: "orin1",
      site_id: "site-1",
      status: "stale",
      version: "0.1.0",
      last_seen_at: "2026-05-09T07:58:00Z",
      assigned_camera_ids: ["camera-2"],
      reported_camera_count: null,
    },
  ],
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
      node_id: edgeNodeId,
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
      assigned_node_id: edgeNodeId,
      source_capability: { width: 1920, height: 1080, fps: 15 },
      default_profile: "native",
      available_profiles: [],
      native_status: { available: false, reason: "source_unavailable" },
      selected_stream_mode: "passthrough",
    },
  ],
};

function createCamera(overrides: Partial<Camera>): Camera {
  return {
    id: "camera-1",
    site_id: "site-1",
    edge_node_id: null,
    name: "North Gate",
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
    ...overrides,
  };
}

const cameras: Camera[] = [
  createCamera({ id: "camera-1", name: "North Gate" }),
  createCamera({
    id: "camera-2",
    name: "Depot Yard",
    processing_mode: "edge",
    edge_node_id: edgeNodeId,
    zones: [],
    browser_delivery: {
      default_profile: "native",
      allow_native_on_demand: true,
      profiles: [],
      unsupported_profiles: [],
      native_status: { available: false, reason: "source_unavailable" },
    },
  }),
];

const sites: Site[] = [
  {
    id: "site-1",
    tenant_id: "tenant-1",
    name: "Zurich Lab",
    description: null,
    tz: "Europe/Zurich",
    geo_point: null,
    created_at: "2026-05-09T07:00:00Z",
  },
];

const freshFrame: TelemetryFrame = {
  camera_id: "camera-1",
  ts: new Date().toISOString(),
  profile: "central-gpu",
  stream_mode: "annotated-whip",
  counts: {},
  tracks: [],
};

const staleFrame: TelemetryFrame = {
  ...freshFrame,
  ts: new Date(Date.now() - 60_000).toISOString(),
};

describe("operational health", () => {
  test("maps health to status tone badges", () => {
    expect(healthToTone("healthy")).toBe("healthy");
    expect(healthToTone("attention")).toBe("attention");
    expect(healthToTone("danger")).toBe("danger");
    expect(healthToTone("unknown")).toBe("muted");
  });

  test("derives fleet attention from existing summary fields", () => {
    const result = deriveFleetHealth(fleet);

    expect(result.health).toBe("attention");
    expect(result.label).toBe("Attention needed");
    expect(result.reasons).toEqual([
      "1 stale node",
      "1 worker missing",
      "1 direct stream unavailable",
    ]);
  });

  test("derives dashboard attention items ordered by severity", () => {
    const items = deriveAttentionItems({
      fleet,
      cameras,
      pendingIncidents: [{ id: "incident-1" }],
    });

    expect(items.map((item) => item.title)).toEqual([
      "Evidence waiting for review",
      "Edge or central workers need attention",
      "Direct streams unavailable",
      "Node heartbeats stale",
    ]);
    expect(items[0].href).toBe("/incidents");
  });

  test("derives deployment posture from existing sites cameras incidents and fleet", () => {
    const posture = deriveDeploymentPosture({
      sites,
      cameras,
      fleet,
      pendingIncidents: [{ id: "incident-1" }],
    });

    expect(posture).toMatchObject({
      siteCount: 1,
      sceneCount: 2,
      centralScenes: 1,
      edgeScenes: 1,
      hybridScenes: 0,
      assignedEdgeNodes: 1,
      pendingEvidence: 1,
      privacyConfiguredScenes: 2,
    });
  });

  test("derives privacy posture without making compliance claims", () => {
    expect(derivePrivacyPosture(cameras[0])).toMatchObject({
      health: "healthy",
      label: "Face/plate filtering configured",
    });
  });

  test("derives scene readiness rows from cameras, fleet records, and telemetry", () => {
    const rows = deriveSceneReadinessRows({
      cameras,
      sites,
      fleet,
      framesByCamera: { "camera-1": freshFrame },
    });

    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      cameraId: "camera-1",
      cameraName: "North Gate",
      siteName: "Zurich Lab",
      readiness: { health: "healthy", label: "Ready" },
      privacy: { health: "healthy", label: "Face/plate filtering configured" },
      worker: { health: "healthy", label: "Worker running" },
      delivery: { health: "healthy", label: "Native stream available" },
      transport: { health: "unknown", label: "Inherited transport" },
      liveRendition: {
        health: "healthy",
        label: "Native clean",
        detail: "passthrough stream",
      },
      telemetry: { health: "healthy", label: "Telemetry live" },
    });
    expect(rows[1]).toMatchObject({
      cameraId: "camera-2",
      cameraName: "Depot Yard",
      readiness: { health: "attention", label: "Needs setup" },
      worker: { health: "attention", label: "Worker stale" },
      delivery: { health: "danger", label: "Direct stream unavailable" },
      transport: { health: "unknown", label: "Inherited transport" },
      liveRendition: {
        health: "danger",
        label: "Native clean",
        detail: "source unavailable",
      },
      telemetry: { health: "unknown", label: "Awaiting telemetry" },
      actionHref: "/cameras",
      actionLabel: "Review setup",
    });
  });

  test("marks stale live telemetry as needing attention when setup is otherwise ready", () => {
    const rows = deriveSceneReadinessRows({
      cameras: [cameras[0]],
      sites,
      fleet,
      framesByCamera: { "camera-1": staleFrame },
    });

    expect(rows[0]).toMatchObject({
      readiness: { health: "attention", label: "Needs attention" },
      telemetry: { health: "attention", label: "Telemetry stale" },
      actionHref: "/live",
      actionLabel: "Inspect telemetry",
    });
  });

  test("routes delivery and worker issues to operations without treating fallback delivery as danger", () => {
    const fallbackCamera = createCamera({
      id: "camera-3",
      name: "Fallback Delivery",
      browser_delivery: {
        default_profile: "720p10",
        allow_native_on_demand: true,
        profiles: [],
        unsupported_profiles: [],
        native_status: { available: false, reason: "source_unavailable" },
      },
    });
    const fallbackFleet: FleetOverview = {
      ...fleet,
      camera_workers: [
        {
          camera_id: "camera-3",
          camera_name: "Fallback Delivery",
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
      ],
      delivery_diagnostics: [
        {
          camera_id: "camera-3",
          camera_name: "Fallback Delivery",
          processing_mode: "central",
          assigned_node_id: null,
          source_capability: { width: 1920, height: 1080, fps: 15 },
          default_profile: "720p10",
          available_profiles: [],
          native_status: { available: false, reason: "source_unavailable" },
          selected_stream_mode: "transcode",
        },
      ],
    };

    const rows = deriveSceneReadinessRows({
      cameras: [fallbackCamera],
      sites,
      fleet: fallbackFleet,
      framesByCamera: { "camera-3": freshFrame },
    });

    expect(rows[0]).toMatchObject({
      readiness: { health: "attention", label: "Needs attention" },
      delivery: { health: "attention", label: "Direct stream unavailable" },
      liveRendition: {
        health: "healthy",
        label: "720p / 10 fps",
        detail: "transcode stream",
      },
      actionHref: "/settings",
      actionLabel: "Inspect delivery",
    });
  });
});
