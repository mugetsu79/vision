import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

const apiBaseUrl = "http://127.0.0.1:8000";

async function login(page: Page) {
  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();
  await expect(page).toHaveURL(/\/live$/);
}

async function readAccessToken(page: Page) {
  const accessToken = await page.evaluate(() => {
    for (const key of Object.keys(window.localStorage)) {
      if (!key.startsWith("oidc.user:")) {
        continue;
      }
      const rawValue = window.localStorage.getItem(key);
      if (!rawValue) {
        continue;
      }
      const parsed = JSON.parse(rawValue) as { access_token?: unknown };
      if (typeof parsed.access_token === "string" && parsed.access_token.length > 0) {
        return parsed.access_token;
      }
    }
    return null;
  });

  expect(accessToken).toBeTruthy();
  return accessToken as string;
}

async function apiPost<T>(
  request: APIRequestContext,
  accessToken: string,
  path: string,
  data: unknown,
) {
  const response = await request.post(`${apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    data,
  });
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return (await response.json()) as T;
}

async function apiPut<T>(
  request: APIRequestContext,
  accessToken: string,
  path: string,
  data: unknown,
) {
  const response = await request.put(`${apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    data,
  });
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return (await response.json()) as T;
}

async function apiGet<T>(
  request: APIRequestContext,
  accessToken: string,
  path: string,
  params?: Record<string, string>,
) {
  const search = new URLSearchParams(params ?? {});
  const url = search.size > 0 ? `${apiBaseUrl}${path}?${search}` : `${apiBaseUrl}${path}`;
  const response = await request.get(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return (await response.json()) as T;
}

async function seedFleetOps(request: APIRequestContext, accessToken: string) {
  const suffix = Date.now().toString();
  const mmsi = suffix.slice(-9).padStart(9, "2");
  const vessel = await apiPost<{ id: string; name: string; site_id: string }>(
    request,
    accessToken,
    "/api/v1/maritime/vessels",
    {
      name: `MV FleetOps ${suffix}`,
      mmsi,
      call_sign: `VZ${suffix.slice(-4)}`,
      create_site: { name: `FleetOps Site ${suffix}`, tz: "UTC" },
      metadata: {
        evidence_queue: "4 pending exports",
        link_state: "satellite_degraded",
        templates: ["Gangway Access"],
      },
    },
  );
  const model = await apiPost<{ id: string }>(
    request,
    accessToken,
    "/api/v1/models",
    {
      name: `FleetOps Model ${suffix}`,
      version: `1.0.${suffix}`,
      task: "detect",
      path: `/models/fleetops-${suffix}.engine`,
      format: "engine",
      classes: ["person", "boat", "truck"],
      input_shape: { h: 640, w: 640, c: 3 },
      sha256: "b".repeat(64),
      size_bytes: 123456,
      license: "Apache-2.0",
    },
  );
  const camera = await apiPost<{ id: string }>(
    request,
    accessToken,
    "/api/v1/cameras",
    {
      site_id: vessel.site_id,
      name: `Gangway Camera ${suffix}`,
      rtsp_url: `rtsp://127.0.0.1:1/fleetops-${suffix}`,
      processing_mode: "central",
      primary_model_id: model.id,
      secondary_model_id: null,
      tracker_type: "botsort",
      active_classes: ["person", "boat"],
      attribute_rules: [],
      zones: [],
      detection_regions: [],
      privacy: {
        blur_faces: true,
        blur_plates: true,
        method: "gaussian",
        strength: 7,
      },
      frame_skip: 1,
      fps_cap: 25,
    },
  );
  const voyage = await apiPost<{ id: string }>(
    request,
    accessToken,
    `/api/v1/maritime/vessels/${vessel.id}/voyages`,
    {
      name: `FleetOps Leg ${suffix}`,
      voyage_number: `FO-${suffix.slice(-6)}`,
      origin: "Aberdeen",
      destination: "Rotterdam",
      scheduled_departure_at: "2026-06-05T06:00:00Z",
      scheduled_arrival_at: "2026-06-05T18:00:00Z",
    },
  );
  await apiPost(
    request,
    accessToken,
    `/api/v1/maritime/voyages/${voyage.id}/activate`,
    {},
  );
  await apiPost(
    request,
    accessToken,
    `/api/v1/maritime/voyages/${voyage.id}/port-calls`,
    {
      port_name: "Rotterdam",
      terminal_name: "Waalhaven",
      eta: "2026-06-05T17:45:00Z",
      etd: "2026-06-06T04:30:00Z",
      link_profile: "port_wifi",
    },
  );
  await apiPost(request, accessToken, "/api/v1/maritime/ingest/ais", {
    vessel_id: vessel.id,
    payload: {
      mmsi,
      lat: 51.9244,
      lon: 4.4777,
      sog: 7.1,
      cog: 92,
      heading: 91,
      reported_at: "2026-06-05T09:15:00Z",
    },
  });
  await apiPost(
    request,
    accessToken,
    "/api/v1/maritime/ingest/carrier-terminal",
    {
      vessel_id: vessel.id,
      payload: {
        terminal_id: `st-${suffix}`,
        provider: "managed_satellite",
        status: "degraded",
        link_state: "satellite_degraded",
        downlink_mbps: 1.8,
        uplink_mbps: 0.8,
        latency_ms: 1200,
        packet_loss_percent: 8.5,
        last_seen_at: "2026-06-05T09:15:00Z",
      },
    },
  );
  await apiPut(request, accessToken, `/api/v1/link/sites/${vessel.site_id}/budget`, {
    monthly_bytes: 5000000000,
    bulk_daily_bytes: 150000000,
  });
  await apiPost(request, accessToken, `/api/v1/link/sites/${vessel.site_id}/probes`, {
    latency_ms: 1200,
    throughput_mbps: 1.8,
    packet_loss_percent: 8.5,
    reachable: true,
    source: "carrier-terminal",
  });
  const node = await apiPost<{ id: string }>(
    request,
    accessToken,
    "/api/v1/billing/nodes",
    { label: vessel.name, kind: "vessel", pack_id: "maritime-fleet" },
  );
  const account = await apiPost<{ id: string }>(
    request,
    accessToken,
    "/api/v1/billing/accounts",
    {
      name: `FleetOps Account ${suffix}`,
      node_ids: [node.id],
      pack_id: "maritime-fleet",
    },
  );
  await apiPost(request, accessToken, "/api/v1/billing/usage", {
    meter_key: "evidence_pack_export",
    quantity: "1",
    account_id: account.id,
    node_id: node.id,
    source_object_type: "playwright_seed",
    source_object_id: "00000000-0000-4000-8000-000000000050",
    occurred_on: "2026-06-05",
    pack_id: "maritime-fleet",
    metadata: { vessel_id: vessel.id },
  });
  const evidenceContext = await apiGet<{
    vessel_name?: string;
    port_name?: string;
    telemetry_freshness?: { ais?: string; carrier?: string };
  }>(request, accessToken, "/api/v1/maritime/evidence-context", {
    camera_id: camera.id,
    incident_time: "2026-06-05T09:15:00Z",
  });
  expect(evidenceContext.vessel_name).toBe(vessel.name);
  expect(evidenceContext.port_name).toBe("Rotterdam");
  expect(evidenceContext.telemetry_freshness?.ais).toBe("fresh");
  expect(evidenceContext.telemetry_freshness?.carrier).toBe("fresh");
  await apiPost(request, accessToken, "/api/v1/support/bundles", {
    site_id: vessel.site_id,
    include_logs: false,
    pack_id: "maritime-fleet",
    diagnostics: { link_state: "degraded" },
  });
  await apiPost(request, accessToken, "/api/v1/support/onboarding-checks/run", {
    site_id: vessel.site_id,
    pack_id: "maritime-fleet",
    metadata: { vessel_id: vessel.id },
  });
  return vessel;
}

test("real FleetOps workspace covers overview, vessel detail, evidence, billing, and support", async ({
  page,
  request,
}) => {
  await login(page);
  const accessToken = await readAccessToken(page);
  const vessel = await seedFleetOps(request, accessToken);

  await page.goto("/fleetops");
  await expect(page.getByTestId("fleetops-workspace")).toBeVisible();
  await expect(page.getByRole("heading", { name: "FleetOps" })).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "Packs" })
      .getByRole("link", { name: "FleetOps" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: vessel.name })).toBeVisible();
  await expect(page.getByText("Current billable usage")).toBeVisible();

  await page.getByRole("link", { name: vessel.name }).click();
  await expect(page.getByRole("heading", { level: 1, name: vessel.name })).toBeVisible();
  await expect(page.getByText("Voyage timeline")).toBeVisible();
  await expect(page.getByText("Latest AIS")).toBeVisible();
  await expect(page.getByText("Evidence context")).toBeVisible();
  await expect(page.getByText("Link operations")).toBeVisible();
  await expect(page.getByText("Export builder")).toBeVisible();

  await page.goto("/fleetops/evidence");
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
  await expect(page.getByText("Export builder")).toBeVisible();
  await expect(page.getByRole("button", { name: "Prepare export" })).toBeVisible();

  await page.goto("/fleetops/billing");
  await expect(page.getByRole("heading", { name: "Billing" })).toBeVisible();
  await expect(page.getByText("Base commercial unit")).toBeVisible();
  await expect(page.getByText("vessel month")).toBeVisible();
  await expect(page.getByText("Value meters")).toBeVisible();
  await expect(page.getByText("Current billable usage")).toBeVisible();

  await page.goto("/fleetops/support");
  await expect(page.getByRole("heading", { name: "Support" })).toBeVisible();
  await expect(page.getByText("Support bundles")).toBeVisible();
  await expect(page.getByText("Tunnel lifecycle")).toBeVisible();
  await expect(page.getByText("Break-glass")).toBeVisible();
  await expect(page.getByText("Onboarding checks")).toBeVisible();
});
