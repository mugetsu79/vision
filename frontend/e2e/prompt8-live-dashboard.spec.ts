import { expect, test } from "@playwright/test";

function cameraPayload(id: string, name: string, profile: string, mode: string) {
  return {
    id,
    site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    edge_node_id: null,
    name,
    rtsp_url_masked: "rtsp://***",
    processing_mode: mode,
    primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    secondary_model_id: null,
    tracker_type: "botsort",
    active_classes: ["car", "bus"],
    attribute_rules: [],
    zones: [],
    homography: {
      src: [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      dst: [
        [0, 0],
        [10, 0],
        [10, 10],
        [0, 10],
      ],
      ref_distance_m: 10,
    },
    privacy: {
      blur_faces: mode !== "hybrid",
      blur_plates: mode !== "hybrid",
      method: "gaussian",
      strength: 7,
    },
    browser_delivery: {
      default_profile: profile,
      allow_native_on_demand: true,
      profiles: [],
    },
    frame_skip: 1,
    fps_cap: 25,
    created_at: "2026-04-18T10:00:00Z",
    updated_at: "2026-04-18T10:00:00Z",
  };
}

test("dashboard shows two live tiles and removes bus overlays after a cars-only query", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const instrumentedWindow = window as unknown as Window & {
      __argusCanvasContexts: Set<CanvasRenderingContext2D>;
      __emitArgusTelemetry?: (payload: unknown) => void;
      __getArgusCanvasLabels?: () => string[];
    };
    const originalFillText = Reflect.get(
      CanvasRenderingContext2D.prototype,
      "fillText",
    );
    const originalClearRect = Reflect.get(
      CanvasRenderingContext2D.prototype,
      "clearRect",
    );

    Object.defineProperty(window, "__argusCanvasContexts", {
      value: new Set<CanvasRenderingContext2D>(),
      configurable: true,
      enumerable: false,
      writable: false,
    });

    CanvasRenderingContext2D.prototype.fillText = function (...args) {
      const text = String(args[0] ?? "");
      (this as CanvasRenderingContext2D & { __argusLabels?: string[] }).__argusLabels ??= [];
      (this as CanvasRenderingContext2D & { __argusLabels?: string[] }).__argusLabels?.push(text);
      instrumentedWindow.__argusCanvasContexts.add(this);
      return originalFillText.apply(this, args);
    };

    CanvasRenderingContext2D.prototype.clearRect = function (...args) {
      (this as CanvasRenderingContext2D & { __argusLabels?: string[] }).__argusLabels = [];
      instrumentedWindow.__argusCanvasContexts.add(this);
      return originalClearRect.apply(this, args);
    };

    instrumentedWindow.__getArgusCanvasLabels = () =>
      Array.from(instrumentedWindow.__argusCanvasContexts).flatMap(
        (context) =>
          (context as CanvasRenderingContext2D & { __argusLabels?: string[] })
            .__argusLabels ?? [],
      );

    class FakeWebSocket {
      static instances: FakeWebSocket[] = [];

      onopen: (() => void) | null = null;
      onmessage: ((event: { data: string }) => void) | null = null;
      onclose: (() => void) | null = null;
      readyState = 1;

      constructor(url: string) {
        void url;
        FakeWebSocket.instances.push(this);
        window.setTimeout(() => this.onopen?.(), 0);
      }

      close() {
        this.onclose?.();
      }

      send() {}
    }

    instrumentedWindow.__emitArgusTelemetry = (payload: unknown) => {
      for (const socket of FakeWebSocket.instances) {
        socket.onmessage?.({ data: JSON.stringify(payload) });
      }
    };

    Object.defineProperty(window, "WebSocket", {
      value: FakeWebSocket,
      configurable: true,
    });

    Object.defineProperty(window, "RTCPeerConnection", {
      value: class FailingRTCPeerConnection {
        constructor() {
          throw new Error("Prompt 8 local dev uses fallback media transport.");
        }
      },
      configurable: true,
    });

    const originalCanPlayType = Reflect.get(
      HTMLMediaElement.prototype,
      "canPlayType",
    );
    HTMLMediaElement.prototype.canPlayType = function (type: string) {
      if (type.includes("mpegurl")) {
        return "probably";
      }
      return originalCanPlayType.call(this, type);
    };
  });

  await page.route("**/api/v1/cameras", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        cameraPayload(
          "11111111-1111-1111-1111-111111111111",
          "North Gate",
          "720p10",
          "central",
        ),
        cameraPayload(
          "22222222-2222-2222-2222-222222222222",
          "Depot Yard",
          "540p5",
          "hybrid",
        ),
      ]),
    });
  });

  await page.route("**/api/v1/query", async (route) => {
    const payload = route.request().postDataJSON() as { prompt?: string };
    expect(payload.prompt).toBe("only show cars");

    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        resolved_classes: ["car"],
        provider: "deterministic",
        model: "query-rules-v1",
        latency_ms: 21,
        camera_ids: [
          "11111111-1111-1111-1111-111111111111",
          "22222222-2222-2222-2222-222222222222",
        ],
      }),
    });
  });

  await page.route("**/api/v1/streams/*/hls.m3u8**", async (route) => {
    await route.fulfill({
      contentType: "application/vnd.apple.mpegurl",
      body: "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n#EXTINF:2.0,\nsegment.ts\n",
    });
  });

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "North Gate" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Depot Yard" })).toBeVisible();

  await page.evaluate(() => {
    const emit = (
      window as Window & {
        __emitArgusTelemetry?: (payload: unknown) => void;
      }
    ).__emitArgusTelemetry;

    emit?.({
      camera_id: "11111111-1111-1111-1111-111111111111",
      ts: new Date().toISOString(),
      profile: "central-gpu",
      stream_mode: "annotated-whip",
      counts: { car: 1, bus: 1 },
      tracks: [
        {
          class_name: "car",
          confidence: 0.94,
          bbox: { x1: 80, y1: 110, x2: 240, y2: 240 },
          track_id: 3,
          speed_kph: 36,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
        {
          class_name: "bus",
          confidence: 0.88,
          bbox: { x1: 300, y1: 90, x2: 560, y2: 280 },
          track_id: 9,
          speed_kph: null,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
      ],
    });

    emit?.({
      camera_id: "22222222-2222-2222-2222-222222222222",
      ts: new Date().toISOString(),
      profile: "jetson-nano",
      stream_mode: "filtered-preview",
      counts: { car: 2, bus: 1 },
      tracks: [
        {
          class_name: "car",
          confidence: 0.91,
          bbox: { x1: 90, y1: 120, x2: 220, y2: 250 },
          track_id: 5,
          speed_kph: 18,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
        {
          class_name: "bus",
          confidence: 0.81,
          bbox: { x1: 260, y1: 100, x2: 520, y2: 300 },
          track_id: 11,
          speed_kph: null,
          direction_deg: null,
          zone_id: null,
          attributes: {},
        },
      ],
    });
  });

  await expect(page.getByText("car").first()).toBeVisible();
  await expect(page.getByText("bus")).toBeVisible();
  await expect(page.getByText(/online/i).first()).toBeVisible();

  await page.getByLabel("Query Vezor").fill("only show cars");
  await page.getByRole("button", { name: "Apply query" }).click();

  await expect(page.getByText("query-rules-v1").first()).toBeVisible();
  await expect(page.getByText("car").first()).toBeVisible();
  await expect(page.getByText("bus")).toHaveCount(0, { timeout: 2_000 });

  await expect
    .poll(
      async () =>
        page.evaluate(() =>
          (
            window as Window & {
              __getArgusCanvasLabels?: () => string[];
            }
          )
            .__getArgusCanvasLabels?.()
            .some((label) => /bus/i.test(label)) ?? false,
        ),
      { timeout: 2_000 },
    )
    .toBe(false);
});
