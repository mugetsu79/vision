import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

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
  }: {
    cameraName: string;
    defaultProfile: string;
  }) => (
    <div aria-label={`${cameraName} video stream`} data-testid={`stream-${cameraName}`}>
      {cameraName} stream {defaultProfile}
    </div>
  ),
}));

vi.mock("@/components/live/TelemetryCanvas", () => ({
  TelemetryCanvas: () => <canvas aria-label="Telemetry overlay" />,
}));

vi.mock("@/components/live/LiveSparkline", () => ({
  LiveSparkline: () => <div data-testid="live-sparkline-mock" />,
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

    render(
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
    expect(screen.getAllByTestId("scene-portal")).toHaveLength(2);
    expect(screen.getByText(/active scenes/i)).toBeInTheDocument();
    expect(screen.getByTestId("stream-North Gate")).toBeInTheDocument();
    expect(screen.getByTestId("stream-Depot Yard")).toBeInTheDocument();
    expect(screen.getAllByLabelText(/video stream/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByLabelText(/telemetry overlay/i).length).toBeGreaterThanOrEqual(2);

    expect(FakeWebSocket.instances[0]?.url).toContain("/ws/telemetry");
    expect(FakeWebSocket.instances[0]?.url).toContain("access_token=dashboard-token");

    act(() => {
      FakeWebSocket.instances[0]?.emit({
        camera_id: "11111111-1111-1111-1111-111111111111",
        ts: new Date().toISOString(),
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
    expect(within(dynamicStats as HTMLElement).getByText("3")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: /ask vezor/i }), "only show cars");
    await user.click(screen.getByRole("button", { name: /^apply$/i }));

    await waitFor(() =>
      expect(screen.getAllByText(/query-rules-v1/i).length).toBeGreaterThanOrEqual(1),
    );
    await waitFor(() => expect(screen.queryByText("bus")).not.toBeInTheDocument());
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
        stream_mode: "passthrough",
        counts: {},
        tracks: [],
      });
    });

    expect(await screen.findByText(/telemetry stale/i)).toBeInTheDocument();
    expect(screen.queryByText(/^offline$/i)).not.toBeInTheDocument();
  });
});
