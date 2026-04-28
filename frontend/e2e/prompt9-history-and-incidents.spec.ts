import fs from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

function operationsLink(page: Page, name: string) {
  return page
    .getByRole("navigation", { name: "Operations" })
    .getByRole("link", { name });
}

function cameraPayload() {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    edge_node_id: null,
    name: "Forklift Gate",
    rtsp_url_masked: "rtsp://***",
    processing_mode: "central",
    primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    secondary_model_id: null,
    tracker_type: "botsort",
    active_classes: ["car", "bus"],
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
    },
    frame_skip: 1,
    fps_cap: 25,
    created_at: "2026-04-18T10:00:00Z",
    updated_at: "2026-04-18T10:00:00Z",
  };
}

function historySeriesPayload() {
  const rows = [];
  const start = Date.parse("2026-04-12T00:00:00Z");
  for (let index = 0; index < 168; index += 1) {
    const bucket = new Date(start + index * 60 * 60 * 1000).toISOString();
    const car = 12 + (index % 8);
    const bus = 3 + (index % 3);
    rows.push({
      bucket,
      values: { car, bus },
      total_count: car + bus,
    });
  }
  return {
    granularity: "1h",
    class_names: ["car", "bus"],
    rows,
    coverage_status: "populated",
    coverage_by_bucket: rows.map((row) => ({
      bucket: row.bucket,
      status: row.total_count > 0 ? "populated" : "zero",
      reason: null,
    })),
    effective_from: "2026-04-12T00:00:00Z",
    effective_to: "2026-04-19T00:00:00Z",
    bucket_count: rows.length,
    bucket_span: "1h",
  };
}

test("history renders quickly, CSV export works, and incidents cover review flow", async ({
  page,
}) => {
  await page.route("**/api/v1/cameras", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([cameraPayload()]),
    });
  });

  await page.route("**/api/v1/history/series**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(historySeriesPayload()),
    });
  });

  await page.route("**/api/v1/export**", async (route) => {
    const url = new URL(route.request().url());
    expect(url.searchParams.get("format")).toBe("csv");

    const from = new Date(url.searchParams.get("from") ?? "");
    const to = new Date(url.searchParams.get("to") ?? "");
    const hours = Math.round((to.getTime() - from.getTime()) / (60 * 60 * 1000));
    expect(hours).toBeLessThanOrEqual(25);

    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="history.csv"',
      },
      body: "bucket,class_name,event_count\n2026-04-18T00:00:00Z,car,16\n",
    });
  });

  let incident: {
    id: string;
    camera_id: string;
    camera_name: string;
    ts: string;
    type: string;
    payload: { hard_hat: boolean; severity: string };
    snapshot_url: string | null;
    clip_url: string;
    storage_bytes: number;
    review_status: "pending" | "reviewed";
    reviewed_at: string | null;
    reviewed_by_subject: string | null;
  } = {
    id: "99999999-9999-9999-9999-999999999999",
    camera_id: "11111111-1111-1111-1111-111111111111",
    camera_name: "Forklift Gate",
    ts: "2026-04-18T10:15:00Z",
    type: "ppe-missing",
    payload: { hard_hat: false, severity: "high" },
    snapshot_url: null,
    clip_url: "https://minio.local/signed/incidents/forklift-gate.mjpeg",
    storage_bytes: 2097152,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
  };

  await page.route("**/api/v1/incidents**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (
      request.method() === "PATCH" &&
      url.pathname === `/api/v1/incidents/${incident.id}/review`
    ) {
      const body = request.postDataJSON() as { review_status?: string };
      incident =
        body.review_status === "reviewed"
          ? {
              ...incident,
              review_status: "reviewed",
              reviewed_at: "2026-04-18T10:20:00Z",
              reviewed_by_subject: "admin-dev",
            }
          : {
              ...incident,
              review_status: "pending",
              reviewed_at: null,
              reviewed_by_subject: null,
            };

      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(incident),
      });
      return;
    }

    if (request.method() === "GET" && url.pathname === "/api/v1/incidents") {
      const reviewStatus = url.searchParams.get("review_status");
      const incidents =
        !reviewStatus || reviewStatus === "all" || reviewStatus === incident.review_status
          ? [incident]
          : [];

      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(incidents),
      });
      return;
    }

    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not found" }),
    });
  });

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/\/live$/);

  // Warm the dev server route chunk before measuring the history render budget.
  await operationsLink(page, "History").click();
  await expect(page).toHaveURL(/\/history(?:\?|$)/);
  await expect(page.getByRole("img", { name: "History trend chart" })).toBeVisible();
  await operationsLink(page, "Live").click();
  await expect(page).toHaveURL(/\/live$/);

  await page.evaluate(() => {
    (window as Window & { __argusHistoryStart?: number }).__argusHistoryStart = performance.now();
  });
  await operationsLink(page, "History").click();
  await expect(page).toHaveURL(/\/history(?:\?|$)/);
  await expect(page.getByRole("img", { name: "History trend chart" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /bucket review/i })).toBeVisible();
  const historyRenderMs = await page.evaluate(() => {
    const startedAt = (window as Window & { __argusHistoryStart?: number }).__argusHistoryStart;
    if (typeof startedAt !== "number") {
      throw new Error("Missing history render start mark.");
    }
    return performance.now() - startedAt;
  });
  expect(historyRenderMs).toBeLessThan(500);
  const reviewBucket = page.getByRole("button", { name: /review first bucket/i });
  await reviewBucket.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText(/visible samples/i)).toBeVisible();

  await page.getByRole("button", { name: "Last 24h" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download CSV" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("history.csv");
  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  if (!downloadPath) {
    throw new Error("Expected a CSV download path.");
  }
  const csv = await fs.readFile(downloadPath, "utf-8");
  expect(csv).toContain("bucket,class_name,event_count");

  await operationsLink(page, "Incidents").click();
  await expect(page).toHaveURL(/\/incidents$/);
  await expect(page.getByRole("heading", { name: "Queue" })).toBeVisible();
  await expect(
    page.getByRole("complementary", { name: "Incident facts" }),
  ).toBeVisible();
  const evidence = page.getByRole("region", { name: /selected evidence/i });
  await expect(evidence.getByText("Clip-only evidence")).toBeVisible();
  await expect(evidence.getByRole("link", { name: "Open clip" })).toBeVisible();

  await evidence.getByRole("button", { name: "Review" }).click();
  await expect(page.getByText(/no incident records match/i)).toBeVisible();

  await page.getByLabel("Review status").selectOption("reviewed");
  const reviewedEvidence = page.getByRole("region", { name: /selected evidence/i });
  await expect(reviewedEvidence.getByRole("heading", { name: "Forklift Gate" })).toBeVisible();
  await expect(reviewedEvidence.getByRole("button", { name: "Reopen" })).toBeVisible();
});

test("history filter state survives navigation via URL", async ({ page }) => {
  await page.route("**/api/v1/cameras", async (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([cameraPayload()]),
    }),
  );
  await page.route("**/api/v1/history/classes**", async (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        from: "2026-04-23T00:00:00Z",
        to: "2026-04-23T23:00:00Z",
        classes: [
          { class_name: "car", event_count: 40, has_speed_data: true },
        ],
      }),
    }),
  );
  await page.route("**/api/v1/history/series**", async (route) => {
    const url = new URL(route.request().url());
    const includeSpeed = url.searchParams.get("include_speed") === "true";
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        granularity: "1h",
        class_names: ["car"],
        rows: [
          {
            bucket: "2026-04-23T00:00:00Z",
            values: { car: 10 },
            total_count: 10,
            speed_p50: includeSpeed ? { car: 42 } : null,
            speed_p95: includeSpeed ? { car: 55 } : null,
            speed_sample_count: includeSpeed ? { car: 10 } : null,
            over_threshold_count:
              includeSpeed && url.searchParams.get("speed_threshold")
                ? { car: 3 }
                : null,
          },
        ],
        granularity_adjusted: false,
        speed_classes_capped: false,
        speed_classes_used: includeSpeed ? ["car"] : null,
      }),
    });
  });

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/\/live$/);
  await operationsLink(page, "History").click();
  await expect(page).toHaveURL(/\/history/);

  await page.getByLabel("Show speed").check();
  await page.getByLabel("Speed threshold").fill("60");

  await expect(page).toHaveURL(/speed=1/);
  await expect(page).toHaveURL(/speedThreshold=60/);

  await operationsLink(page, "Live").click();
  await expect(page).toHaveURL(/\/live$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/history.*speed=1.*speedThreshold=60/);
  await expect(page.getByLabel("Show speed")).toBeChecked();
  await expect(page.getByLabel("Speed threshold")).toHaveValue("60");
});

test("deep link with speed params applies state on load", async ({ page }) => {
  const historySeriesRequests: URL[] = [];

  await page.route("**/api/v1/cameras", async (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([cameraPayload()]),
    }),
  );
  await page.route("**/api/v1/history/classes**", async (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        from: "2026-04-23T00:00:00Z",
        to: "2026-04-23T23:00:00Z",
        classes: [{ class_name: "car", event_count: 40, has_speed_data: true }],
      }),
    }),
  );
  await page.route("**/api/v1/history/series**", async (route) => {
    const url = new URL(route.request().url());
    historySeriesRequests.push(url);
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        granularity: url.searchParams.get("granularity") ?? "1h",
        class_names: ["car"],
        rows: [],
        granularity_adjusted: false,
        speed_classes_capped: false,
        speed_classes_used: ["car"],
      }),
    });
  });

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/\/live$/);
  await page.goto("/history?speed=1&speedThreshold=60&granularity=5m");
  await expect(page.getByLabel("Show speed")).toBeChecked();
  await expect(page.getByLabel("Speed threshold")).toHaveValue("60");
  await expect
    .poll(() =>
      historySeriesRequests.some(
        (request) =>
          request.searchParams.get("include_speed") === "true" &&
          request.searchParams.get("speed_threshold") === "60" &&
          request.searchParams.get("granularity") === "5m",
      ),
    )
    .toBe(true);
});
