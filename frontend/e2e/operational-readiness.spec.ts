import { expect, test, type Page } from "@playwright/test";

const cameraId = "11111111-1111-1111-1111-111111111111";
const edgeCameraId = "22222222-2222-2222-2222-222222222222";
const siteId = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const edgeNodeId = "33333333-3333-3333-3333-333333333333";

function cameraPayload({
  id,
  name,
  mode,
  nativeAvailable,
}: {
  id: string;
  name: string;
  mode: "central" | "edge";
  nativeAvailable: boolean;
}) {
  return {
    id,
    site_id: siteId,
    edge_node_id: mode === "edge" ? edgeNodeId : null,
    name,
    rtsp_url_masked: "rtsp://***",
    processing_mode: mode,
    primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    secondary_model_id: null,
    tracker_type: "bytetrack",
    active_classes: ["person", "car"],
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
      default_profile: nativeAvailable ? "native" : "720p10",
      allow_native_on_demand: true,
      profiles: [],
      unsupported_profiles: [],
      native_status: {
        available: nativeAvailable,
        reason: nativeAvailable ? null : "source_unavailable",
      },
    },
    source_capability: { width: 1920, height: 1080, fps: 15 },
    frame_skip: 1,
    fps_cap: 25,
    created_at: "2026-05-09T07:00:00Z",
    updated_at: "2026-05-09T07:00:00Z",
  };
}

function fleetPayload() {
  return {
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
        assigned_camera_ids: [cameraId],
        reported_camera_count: null,
      },
      {
        id: edgeNodeId,
        kind: "edge",
        hostname: "orin-lab",
        site_id: siteId,
        status: "stale",
        version: "0.1.0",
        last_seen_at: "2026-05-09T07:58:00Z",
        assigned_camera_ids: [edgeCameraId],
        reported_camera_count: null,
      },
    ],
    camera_workers: [
      {
        camera_id: cameraId,
        camera_name: "North Gate",
        site_id: siteId,
        node_id: null,
        node_hostname: null,
        processing_mode: "central",
        desired_state: "manual",
        runtime_status: "running",
        lifecycle_owner: "manual_dev",
        dev_run_command: null,
        detail: null,
      },
      {
        camera_id: edgeCameraId,
        camera_name: "Depot Yard",
        site_id: siteId,
        node_id: edgeNodeId,
        node_hostname: "orin-lab",
        processing_mode: "edge",
        desired_state: "supervised",
        runtime_status: "stale",
        lifecycle_owner: "edge_supervisor",
        dev_run_command: null,
        detail: "Edge heartbeat is stale.",
      },
    ],
    delivery_diagnostics: [
      {
        camera_id: cameraId,
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
        camera_id: edgeCameraId,
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
}

async function installOperationalReadinessFixtures(page: Page) {
  await page.addInitScript(() => {
    const authority = "http://127.0.0.1:8080/realms/argus-dev";
    const clientId = "argus-frontend";
    const expiresAt = Math.floor(Date.now() / 1000) + 60 * 60;

    window.localStorage.setItem(
      `oidc.user:${authority}:${clientId}`,
      JSON.stringify({
        id_token: "e2e-id-token",
        session_state: "e2e-session",
        access_token: "e2e-access-token",
        token_type: "Bearer",
        scope: "openid profile email",
        expires_at: expiresAt,
        profile: {
          sub: "e2e-admin",
          email: "admin@example.test",
          iss: authority,
          tenant_id: "tenant-1",
          realm_access: { roles: ["admin"] },
        },
      }),
    );

    class QuietWebSocket {
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onmessage: ((event: { data: string }) => void) | null = null;
      readyState = 1;

      constructor() {
        window.setTimeout(() => this.onopen?.(), 0);
      }

      close() {
        this.readyState = 3;
        this.onclose?.();
      }

      send() {}
    }

    Object.defineProperty(window, "WebSocket", {
      value: QuietWebSocket,
      configurable: true,
    });

    Object.defineProperty(window, "RTCPeerConnection", {
      value: class UnavailablePeerConnection {
        constructor() {
          throw new Error("E2E smoke uses mocked stream transport.");
        }
      },
      configurable: true,
    });
  });

  await page.route("**/api/v1/cameras", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        cameraPayload({
          id: cameraId,
          name: "North Gate",
          mode: "central",
          nativeAvailable: true,
        }),
        cameraPayload({
          id: edgeCameraId,
          name: "Depot Yard",
          mode: "edge",
          nativeAvailable: false,
        }),
      ]),
    });
  });

  await page.route("**/api/v1/sites", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: siteId,
          tenant_id: "tenant-1",
          name: "Zurich Lab",
          description: null,
          tz: "Europe/Zurich",
          geo_point: null,
          created_at: "2026-05-09T07:00:00Z",
        },
      ]),
    });
  });

  await page.route("**/api/v1/incidents**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "99999999-9999-9999-9999-999999999999",
          camera_id: cameraId,
          camera_name: "North Gate",
          ts: "2026-05-09T08:10:00Z",
          type: "zone-entry",
          payload: { severity: "medium" },
          snapshot_url: null,
          clip_url: "https://minio.local/signed/incidents/north-gate.mjpeg",
          storage_bytes: 1048576,
          review_status: "pending",
          reviewed_at: null,
          reviewed_by_subject: null,
        },
      ]),
    });
  });

  await page.route("**/api/v1/operations/fleet", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(fleetPayload()),
    });
  });

  await page.route("**/api/v1/models", async (route) => {
    await route.fulfill({ contentType: "application/json", body: "[]" });
  });

  await page.route("**/api/v1/model-catalog", async (route) => {
    await route.fulfill({ contentType: "application/json", body: "[]" });
  });

  await page.route("**/api/v1/streams/*/hls.m3u8**", async (route) => {
    await route.fulfill({
      contentType: "application/vnd.apple.mpegurl",
      body: "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n#EXTINF:2.0,\nsegment.ts\n",
    });
  });
}

test.describe("Operational readiness UI", () => {
  test.beforeEach(async ({ page }) => {
    await installOperationalReadinessFixtures(page);
  });

  test("dashboard exposes deployment posture and the attention stack", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    await expect(page.getByTestId("deployment-posture-strip")).toBeVisible();
    await expect(page.getByTestId("attention-stack")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /attention stack/i }),
    ).toBeVisible();
  });

  test("operations exposes the scene intelligence matrix", async ({ page }) => {
    await page.goto("/settings");

    await expect(page.getByTestId("scene-intelligence-matrix")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /scene intelligence matrix/i }),
    ).toBeVisible();
  });

  test("live and scenes keep their primary workspaces", async ({ page }) => {
    await page.goto("/live");
    await expect(page.getByTestId("live-intelligence-workspace")).toBeVisible();

    await page.goto("/cameras");
    await expect(page.getByTestId("scene-setup-workspace")).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: /readiness/i }),
    ).toBeVisible();
  });
});
