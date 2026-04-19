import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
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
    <div data-testid={`stream-${cameraName}`}>
      {cameraName} stream {defaultProfile}
    </div>
  ),
}));

vi.mock("@/components/live/TelemetryCanvas", () => ({
  TelemetryCanvas: () => null,
}));

import { createQueryClient } from "@/app/query-client";
import { DashboardPage } from "@/pages/Dashboard";
import { useAuthStore } from "@/stores/auth-store";

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

describe("DashboardPage", () => {
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
        <DashboardPage />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument(),
    );
    expect(screen.getByRole("heading", { name: "Depot Yard" })).toBeInTheDocument();
    expect(screen.getByTestId("stream-North Gate")).toBeInTheDocument();
    expect(screen.getByTestId("stream-Depot Yard")).toBeInTheDocument();

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

    await waitFor(() => expect(screen.getAllByText(/online/i).length).toBeGreaterThanOrEqual(2));
    expect(screen.getByText("car")).toBeInTheDocument();
    expect(screen.getByText("bus")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/query argus/i), "only show cars");
    await user.click(screen.getByRole("button", { name: /apply query/i }));

    await waitFor(() =>
      expect(screen.getAllByText(/query-rules-v1/i).length).toBeGreaterThanOrEqual(1),
    );
    await waitFor(() => expect(screen.queryByText("bus")).not.toBeInTheDocument());
  });
});
