import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const { telemetryCanvasMock } = vi.hoisted(() => ({
  telemetryCanvasMock: vi.fn(),
}));

vi.mock("@/lib/config", () => ({
  frontendConfig: {
    apiBaseUrl: "http://127.0.0.1:8000",
    oidcAuthority: "http://127.0.0.1:8080/realms/argus-dev",
    oidcClientId: "argus-frontend",
    oidcRedirectUri: "http://127.0.0.1:3000/auth/callback",
    oidcPostLogoutRedirectUri: "http://127.0.0.1:3000/signin",
  },
}));

vi.mock("@/components/live/VideoStream", () => ({
  VideoStream: ({
    cameraName,
    defaultProfile,
    deliveryMode,
  }: {
    cameraName: string;
    defaultProfile: string;
    deliveryMode?: string | null;
  }) => (
    <div aria-label={`${cameraName} video stream`} data-testid={`stream-${cameraName}`}>
      {cameraName} stream {defaultProfile} {deliveryMode ?? "default-delivery"}
    </div>
  ),
}));

vi.mock("@/components/live/TelemetryCanvas", () => ({
  TelemetryCanvas: (props: unknown) => {
    telemetryCanvasMock(props);
    return <canvas aria-label="Telemetry overlay" />;
  },
}));

vi.mock("@/components/live/TelemetryTerrain", () => ({
  TelemetryTerrain: ({ cameraName }: { cameraName: string }) => (
    <div data-testid={`terrain-${cameraName}`}>
      Telemetry terrain for {cameraName}
    </div>
  ),
}));

vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: {
      mode: "manual_dev",
      generated_at: "2026-05-09T08:00:00Z",
      summary: {
        desired_workers: 2,
        running_workers: 2,
        stale_nodes: 0,
        offline_nodes: 0,
        native_unavailable_cameras: 0,
      },
      nodes: [],
      camera_workers: [
        {
          camera_id: "11111111-1111-1111-1111-111111111111",
          camera_name: "North Gate",
          site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
          node_id: null,
          node_hostname: null,
          processing_mode: "central",
          desired_state: "manual",
          runtime_status: "running",
          lifecycle_owner: "manual_dev",
          dev_run_command: null,
          detail: null,
        },
      ],
      delivery_diagnostics: [
        {
          camera_id: "11111111-1111-1111-1111-111111111111",
          camera_name: "North Gate",
          processing_mode: "central",
          assigned_node_id: null,
          source_capability: { width: 1920, height: 1080, fps: 15 },
          default_profile: "native",
          available_profiles: [],
          native_status: { available: true, reason: null },
          selected_stream_mode: "passthrough",
        },
      ],
    },
  }),
}));

import { createQueryClient } from "@/app/query-client";
import { LivePage } from "@/pages/Live";
import { useAuthStore } from "@/stores/auth-store";
import { useTelemetryStore } from "@/stores/telemetry-store";

const initialAuthState = useAuthStore.getState();

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  readyState = 1;

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this);
    queueMicrotask(() => this.onopen?.());
  }

  send() {}

  close() {
    this.onclose?.();
  }

  emit(payload: unknown) {
    this.onmessage?.(
      new MessageEvent("message", {
        data: JSON.stringify(payload),
      }),
    );
  }
}

describe("LivePage", () => {
  beforeEach(() => {
    telemetryCanvasMock.mockClear();
    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "dashboard-token",
        user: {
          sub: "operator-1",
          email: "operator@argus.local",
          role: "operator",
          realm: "argus-dev",
          tenantId: "tenant-1",
          isSuperadmin: false,
        },
      });
    });

    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    act(() => {
      useAuthStore.setState(initialAuthState, true);
      useTelemetryStore.setState({
        instance: null,
        accessToken: null,
        tenantId: null,
      });
    });
  });

  test("renders the multi-camera live wall, presence badges, and query-driven stats", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: "11111111-1111-1111-1111-111111111111",
              site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              edge_node_id: null,
              name: "North Gate",
              rtsp_url_masked: "rtsp://***",
              processing_mode: "central",
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
            },
            {
              id: "22222222-2222-2222-2222-222222222222",
              site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              edge_node_id: null,
              name: "Depot Yard",
              rtsp_url_masked: "rtsp://***",
              processing_mode: "hybrid",
              primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
              secondary_model_id: null,
              tracker_type: "bytetrack",
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
                blur_faces: false,
                blur_plates: false,
                method: "gaussian",
                strength: 7,
              },
              browser_delivery: {
                default_profile: "540p5",
                allow_native_on_demand: true,
                profiles: [],
              },
              frame_skip: 1,
              fps_cap: 15,
              created_at: "2026-04-18T10:00:00Z",
              updated_at: "2026-04-18T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            resolved_classes: ["car"],
            provider: "deterministic",
            model: "query-rules-v1",
            latency_ms: 14,
            camera_ids: [
              "11111111-1111-1111-1111-111111111111",
              "22222222-2222-2222-2222-222222222222",
            ],
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

    const { container } = render(
      <QueryClientProvider client={createQueryClient()}>
        <LivePage />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument(),
    );
    expect(await screen.findByRole("heading", { name: /live intelligence/i })).toBeInTheDocument();
    expect(screen.getByTestId("live-intelligence-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("ask-vezor-dock")).toBeInTheDocument();
    expect(screen.getByTestId("scene-portal-grid")).toBeInTheDocument();
    expect(screen.getByTestId("spatial-instrument-rail")).toBeInTheDocument();
    expect(screen.getByText(/^signals in view$/i)).toBeInTheDocument();
    expect(screen.getByText(/^resolved intent$/i)).toBeInTheDocument();
    expect(screen.queryByText(/live command surface/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\d+ cameras/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/dynamic stats/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/current command resolution/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/\d+ connected scenes/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("heading", { name: "Depot Yard" })).toBeInTheDocument();
    const scenePortals = screen.getAllByTestId("scene-portal");
    expect(scenePortals).toHaveLength(2);
    expect(scenePortals[0]).toHaveAttribute("data-scene-portal-tile");
    expect(scenePortals[0]).toHaveAttribute("tabindex", "0");
    expect(scenePortals[0]).toHaveClass("hover:-translate-y-0.5");
    expect(scenePortals[0]).toHaveClass("hover:shadow-[var(--vz-elev-glow-cerulean)]");
    const mediaPlates = container.querySelectorAll("[data-scene-portal-media]");
    expect(mediaPlates).toHaveLength(2);
    expect(mediaPlates[0]?.querySelector("[data-bracket]")).toBeInTheDocument();
    expect(screen.getByText(/active scenes/i)).toBeInTheDocument();
    expect(screen.getByTestId("stream-North Gate")).toBeInTheDocument();
    expect(screen.getByTestId("terrain-North Gate")).toBeInTheDocument();
    expect(screen.getByTestId("stream-Depot Yard")).toBeInTheDocument();
    expect(screen.getAllByLabelText(/video stream/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByLabelText(/telemetry overlay/i).length).toBeGreaterThanOrEqual(2);
    const northGateStatus = within(scenePortals[0]).getByRole("group", {
      name: /north gate operational status/i,
    });
    const depotYardStatus = within(scenePortals[1]).getByRole("group", {
      name: /depot yard operational status/i,
    });
    expect(within(northGateStatus).getByText(/^central scene$/i)).toBeInTheDocument();
    expect(within(northGateStatus).getByText(/worker running/i)).toBeInTheDocument();
    expect(within(northGateStatus).getAllByText(/native clean/i).length).toBeGreaterThan(0);
    expect(within(northGateStatus).getByText(/inherited transport/i)).toBeInTheDocument();
    expect(within(depotYardStatus).getByText(/^hybrid scene$/i)).toBeInTheDocument();
    expect(
      within(depotYardStatus).getByText(/worker awaiting report/i),
    ).toBeInTheDocument();
    expect(
      within(depotYardStatus).getByText(/540p \/ 5 fps/i),
    ).toBeInTheDocument();

    expect(FakeWebSocket.instances[0]?.url).toContain("/ws/telemetry");
    expect(FakeWebSocket.instances[0]?.url).toContain("access_token=dashboard-token");

    act(() => {
      FakeWebSocket.instances[0]?.emit({
        camera_id: "11111111-1111-1111-1111-111111111111",
        ts: "2026-05-09T08:00:00.000Z",
        profile: "central-gpu",
        stream_mode: "annotated-whip",
        counts: { bus: 1, car: 2 },
        tracks: [
          {
            class_name: "car",
            confidence: 0.92,
            bbox: { x1: 100, y1: 120, x2: 260, y2: 260 },
            track_id: 4,
            speed_kph: 35,
            direction_deg: null,
            zone_id: null,
            attributes: {},
          },
          {
            class_name: "bus",
            confidence: 0.87,
            bbox: { x1: 300, y1: 130, x2: 520, y2: 300 },
            track_id: 9,
            speed_kph: null,
            direction_deg: null,
            zone_id: null,
            attributes: {},
          },
        ],
      });
      FakeWebSocket.instances[0]?.emit({
        camera_id: "22222222-2222-2222-2222-222222222222",
        ts: new Date().toISOString(),
        profile: "jetson-nano",
        stream_mode: "filtered-preview",
        counts: { car: 1 },
        tracks: [
          {
            class_name: "car",
            confidence: 0.9,
            bbox: { x1: 80, y1: 100, x2: 220, y2: 250 },
            track_id: 3,
            speed_kph: 18,
            direction_deg: null,
            zone_id: null,
            attributes: {},
          },
        ],
      });
    });

    await waitFor(
      () => expect(screen.getAllByText(/telemetry live/i).length).toBeGreaterThanOrEqual(2),
    );
    expect(screen.getByText("car")).toBeInTheDocument();
    expect(screen.getByText("bus")).toBeInTheDocument();
    expect(screen.getAllByText(/visible now/i).length).toBeGreaterThanOrEqual(2);
    const dynamicStats = screen.getByRole("heading", { name: /live signals in view/i }).closest("section");
    expect(dynamicStats).not.toBeNull();
    expect(within(dynamicStats as HTMLElement).getByText("2")).toBeInTheDocument();
    expect(within(dynamicStats as HTMLElement).getByText("1")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: /ask vezor/i }), "only show cars");
    await user.click(screen.getByRole("button", { name: /^apply$/i }));

    await waitFor(() =>
      expect(screen.getAllByText(/query-rules-v1/i).length).toBeGreaterThanOrEqual(1),
    );
    await waitFor(() => expect(screen.queryByText("bus")).not.toBeInTheDocument());
  });

  test("does not count held tracks as visible now when a frame arrives without tracks", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          {
            id: "11111111-1111-1111-1111-111111111111",
            site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            edge_node_id: null,
            name: "North Gate",
            rtsp_url_masked: "rtsp://***",
            processing_mode: "central",
            primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            secondary_model_id: null,
            tracker_type: "botsort",
            active_classes: ["person", "car"],
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
          },
        ]),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(
      <QueryClientProvider client={createQueryClient()}>
        <LivePage />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument(),
    );

    act(() => {
      FakeWebSocket.instances[0]?.emit({
        camera_id: "11111111-1111-1111-1111-111111111111",
        ts: "2026-05-09T08:00:00.000Z",
        profile: "central-gpu",
        stream_mode: "annotated-whip",
        counts: { person: 1 },
        tracks: [
          {
            class_name: "person",
            confidence: 0.92,
            bbox: { x1: 100, y1: 120, x2: 260, y2: 260 },
            track_id: 12,
            speed_kph: null,
            direction_deg: null,
            zone_id: null,
            attributes: {},
          },
        ],
      });
    });

    await waitFor(() =>
      expect(screen.getByText("1 visible now")).toBeInTheDocument(),
    );

    act(() => {
      FakeWebSocket.instances[0]?.emit({
        camera_id: "11111111-1111-1111-1111-111111111111",
        ts: "2026-05-09T08:00:01.000Z",
        profile: "central-gpu",
        stream_mode: "annotated-whip",
        counts: {},
        tracks: [],
      });
    });

    await waitFor(() => {
      const lastCanvasProps = telemetryCanvasMock.mock.calls.at(-1)?.[0] as
        | { frame?: { ts?: string }; tracks?: unknown[] }
        | undefined;
      expect(lastCanvasProps?.frame?.ts).toBe("2026-05-09T08:00:01.000Z");
      expect(lastCanvasProps?.tracks).toEqual([]);
    });
    expect(screen.getByText("0 visible now")).toBeInTheDocument();
  });

  test("shows why native is unavailable for a camera", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          {
            id: "11111111-1111-1111-1111-111111111111",
            site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            edge_node_id: null,
            name: "North Gate",
            rtsp_url_masked: "rtsp://***",
            processing_mode: "central",
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
              blur_faces: true,
              blur_plates: true,
              method: "gaussian",
              strength: 7,
            },
            browser_delivery: {
              default_profile: "720p10",
              allow_native_on_demand: true,
              profiles: [
                { id: "native", kind: "passthrough" },
                { id: "720p10", kind: "transcode", w: 1280, h: 720, fps: 10 },
              ],
              native_status: {
                available: false,
                reason: "privacy_filtering_required",
              },
            },
            source_capability: {
              width: 1280,
              height: 720,
              fps: 20,
              codec: "h264",
              aspect_ratio: "16:9",
            },
            frame_skip: 1,
            fps_cap: 25,
            created_at: "2026-04-18T10:00:00Z",
            updated_at: "2026-04-18T10:00:00Z",
          },
        ]),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(
      <QueryClientProvider client={createQueryClient()}>
        <LivePage />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/direct stream unavailable: privacy filtering required/i),
    ).toBeInTheDocument();
  });

  test("shows the resolved delivery profile label and actual passthrough stream mode", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          {
            id: "11111111-1111-1111-1111-111111111111",
            site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            edge_node_id: null,
            name: "North Gate",
            rtsp_url_masked: "rtsp://***",
            processing_mode: "central",
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
              blur_faces: false,
              blur_plates: false,
              method: "gaussian",
              strength: 7,
            },
            browser_delivery: {
              default_profile: "native",
              allow_native_on_demand: true,
              delivery_profile_id: "44444444-4444-4444-4444-444444444444",
              delivery_profile_name: "Edge HLS delivery",
              delivery_mode: "hls",
              profiles: [
                {
                  id: "native",
                  kind: "passthrough",
                  label: "Native camera",
                },
              ],
            },
            frame_skip: 1,
            fps_cap: 25,
            created_at: "2026-04-18T10:00:00Z",
            updated_at: "2026-04-18T10:00:00Z",
          },
        ]),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(
      <QueryClientProvider client={createQueryClient()}>
        <LivePage />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument(),
    );
    expect(screen.getByText(/central processing · Native camera/i)).toBeInTheDocument();
    expect(screen.getByTestId("stream-North Gate")).toHaveTextContent("hls");

    act(() => {
      FakeWebSocket.instances[0]?.emit({
        camera_id: "11111111-1111-1111-1111-111111111111",
        ts: new Date().toISOString(),
        profile: "central-gpu",
        stream_mode: "passthrough",
        counts: {},
        tracks: [],
      });
    });

    await waitFor(() =>
      expect(screen.getAllByText(/telemetry live/i).length).toBeGreaterThanOrEqual(2),
    );
    expect(screen.getByText(/^passthrough$/i)).toBeInTheDocument();
    expect(screen.queryByText(/native clean/i)).not.toBeInTheDocument();
  });

  test("stages and applies a camera live rendition without changing transport fields", async () => {
    const user = userEvent.setup();
    const patchBodies: unknown[] = [];
    const camera = {
      id: "11111111-1111-1111-1111-111111111111",
      site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      edge_node_id: null,
      name: "North Gate",
      rtsp_url_masked: "rtsp://***",
      processing_mode: "central",
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
        blur_faces: true,
        blur_plates: true,
        method: "gaussian",
        strength: 7,
      },
      browser_delivery: {
        default_profile: "720p10",
        allow_native_on_demand: true,
        delivery_profile_id: "44444444-4444-4444-4444-444444444444",
        delivery_profile_name: "Edge HLS delivery",
        delivery_profile_hash: "transport-hash",
        delivery_mode: "hls",
        public_base_url: "https://video.example.test",
        edge_override_url: "https://edge.example.test",
        profiles: [
          { id: "native", kind: "passthrough", label: "Native camera" },
          { id: "720p10", kind: "transcode", w: 1280, h: 720, fps: 10, label: "720p / 10 fps" },
          { id: "540p5", kind: "transcode", w: 960, h: 540, fps: 5, label: "540p / 5 fps" },
        ],
        unsupported_profiles: [{ id: "1080p15", reason: "source_resolution_too_low" }],
        native_status: {
          available: false,
          reason: "privacy_filtering_required",
        },
      },
      source_capability: {
        width: 1280,
        height: 720,
        fps: 20,
        codec: "h264",
        aspect_ratio: "16:9",
      },
      frame_skip: 1,
      fps_cap: 25,
      created_at: "2026-04-18T10:00:00Z",
      updated_at: "2026-04-18T10:00:00Z",
    };

    vi.spyOn(global, "fetch").mockImplementation(async (input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras" && request.method === "GET") {
        return new Response(JSON.stringify([camera]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (
        url.pathname ===
          "/api/v1/cameras/11111111-1111-1111-1111-111111111111" &&
        request.method === "PATCH"
      ) {
        const body = (await request.clone().json()) as unknown;
        patchBodies.push(body);
        return new Response(
          JSON.stringify({
            ...camera,
            browser_delivery: {
              ...camera.browser_delivery,
              default_profile: "540p5",
            },
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      return new Response("Not found", { status: 404 });
    });

    render(
      <QueryClientProvider client={createQueryClient()}>
        <LivePage />
      </QueryClientProvider>,
    );

    await screen.findByRole("heading", { name: "North Gate" });
    const renditionSelect = screen.getByLabelText(/north gate live rendition/i);
    expect(within(renditionSelect).queryByRole("option", { name: /native camera/i })).toBeNull();

    await user.selectOptions(renditionSelect, "540p5");
    expect(screen.getByText(/will reconfigure the worker to publish 540p \/ 5 fps/i)).toBeInTheDocument();
    expect(patchBodies).toHaveLength(0);

    await user.click(screen.getByRole("button", { name: /apply to scene/i }));

    await waitFor(() => expect(patchBodies).toHaveLength(1));
    expect(patchBodies[0]).toEqual({
      browser_delivery: {
        ...camera.browser_delivery,
        default_profile: "540p5",
      },
    });
  });

  test("lets operators disable browser-only overlays per live tile", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          {
            id: "11111111-1111-1111-1111-111111111111",
            site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            edge_node_id: null,
            name: "North Gate",
            rtsp_url_masked: "rtsp://***",
            processing_mode: "central",
            primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            secondary_model_id: null,
            tracker_type: "botsort",
            active_classes: ["person"],
            attribute_rules: [],
            zones: [],
            homography: null,
            privacy: {
              blur_faces: false,
              blur_plates: false,
              method: "gaussian",
              strength: 7,
            },
            browser_delivery: {
              default_profile: "native",
              allow_native_on_demand: true,
              profiles: [{ id: "native", kind: "passthrough", label: "Native camera" }],
            },
            frame_skip: 1,
            fps_cap: 25,
            created_at: "2026-04-18T10:00:00Z",
            updated_at: "2026-04-18T10:00:00Z",
          },
        ]),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(
      <QueryClientProvider client={createQueryClient()}>
        <LivePage />
      </QueryClientProvider>,
    );

    await screen.findByRole("heading", { name: "North Gate" });
    expect(telemetryCanvasMock.mock.calls.at(-1)?.[0]).toMatchObject({
      disabled: false,
    });

    await user.click(screen.getByRole("checkbox", { name: /browser overlay/i }));

    await waitFor(() =>
      expect(telemetryCanvasMock.mock.calls.at(-1)?.[0]).toMatchObject({
        disabled: true,
      }),
    );
  });

  test("shows telemetry stale instead of offline when the last worker frame is old", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          {
            id: "11111111-1111-1111-1111-111111111111",
            site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            edge_node_id: null,
            name: "North Gate",
            rtsp_url_masked: "rtsp://***",
            processing_mode: "central",
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
              blur_faces: false,
              blur_plates: false,
              method: "gaussian",
              strength: 7,
            },
            browser_delivery: {
              default_profile: "native",
              allow_native_on_demand: true,
              profiles: [],
            },
            frame_skip: 1,
            fps_cap: 25,
            created_at: "2026-04-18T10:00:00Z",
            updated_at: "2026-04-18T10:00:00Z",
          },
        ]),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(
      <QueryClientProvider client={createQueryClient()}>
        <LivePage />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument(),
    );

    act(() => {
      FakeWebSocket.instances[0]?.emit({
        camera_id: "11111111-1111-1111-1111-111111111111",
        ts: new Date(Date.now() - 28_000).toISOString(),
        profile: "central-gpu",
        stream_mode: "annotated-whip",
        counts: {},
        tracks: [],
      });
    });

    expect(
      (await screen.findAllByText(/telemetry stale/i)).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/annotated-whip/i)).toBeInTheDocument();
    expect(screen.queryByText(/^offline$/i)).not.toBeInTheDocument();
  });
});
