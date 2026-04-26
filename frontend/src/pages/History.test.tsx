import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
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

vi.mock("@/components/history/HistoryTrendChart", () => ({
  HistoryTrendChart: ({
    series,
    metric,
  }: {
    series: { classNames: string[]; points: unknown[]; includeSpeed?: boolean; speedThreshold?: number | null };
    metric?: string;
  }) => (
    <div data-testid="history-trend-chart">
      {series.classNames.join(",")}::{series.points.length}::speed={String(!!series.includeSpeed)}::threshold={String(series.speedThreshold ?? "none")}::metric={metric ?? "none"}
    </div>
  ),
}));

import { createQueryClient } from "@/app/query-client";
import { HistoryPage } from "@/pages/History";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();
const routerFuture = {
  v7_relativeSplatPath: true,
  v7_startTransition: true,
} as const;
let recordedRequests: URL[] = [];

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

function historySeriesResponse(overrides: Record<string, unknown> = {}) {
  return {
    granularity: "1h",
    class_names: ["car", "bus"],
    rows: [
      { bucket: "2026-04-12T00:00:00Z", values: { car: 22, bus: 6 }, total_count: 28 },
    ],
    granularity_adjusted: false,
    speed_classes_capped: false,
    speed_classes_used: null,
    ...overrides,
  };
}

function classesResponse() {
  return {
    from: "2026-04-12T00:00:00Z",
    to: "2026-04-19T00:00:00Z",
    classes: [
      { class_name: "car", event_count: 40, has_speed_data: true },
      { class_name: "bus", event_count: 10, has_speed_data: true },
      { class_name: "person", event_count: 5, has_speed_data: false },
    ],
  };
}

function cameraResponse(overrides: Record<string, unknown> = {}) {
  return {
    id: "cam-1",
    name: "Gate camera",
    zones: [],
    ...overrides,
  };
}

function renderPage(initialEntry = "/history") {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter future={routerFuture} initialEntries={[initialEntry]}>
        <HistoryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function findHistoryRequest(pathname: string, metric: string) {
  return recordedRequests.find(
    (request) => request.pathname === pathname && request.searchParams.get("metric") === metric,
  );
}

describe("HistoryPage", () => {
  beforeEach(() => {
    recordedRequests = [];
    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "history-token",
        user: {
          sub: "analyst-1",
          email: "analyst@argus.local",
          role: "viewer",
          realm: "argus-dev",
          tenantId: "tenant-1",
          isSuperadmin: false,
        },
      });
    });

    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") {
        if (url.searchParams.get("include_speed") === "true") {
          return Promise.resolve(
            jsonResponse(
              historySeriesResponse({
                rows: [
                  {
                    bucket: "2026-04-12T00:00:00Z",
                    values: { car: 22, bus: 6 },
                    total_count: 28,
                    speed_p50: { car: 42 },
                    speed_p95: { car: 55 },
                    speed_sample_count: { car: 22 },
                    over_threshold_count: url.searchParams.get("speed_threshold") ? { car: 5 } : null,
                  },
                ],
                speed_classes_used: ["car"],
              }),
            ),
          );
        }
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("hydrates filter state from URL and calls endpoint with include_speed", async () => {
    renderPage("/history?metric=observations&speed=1&speedThreshold=50&granularity=5m");
    await waitFor(() =>
      expect(screen.getByTestId("history-trend-chart")).toHaveTextContent(
        "speed=true::threshold=50::metric=observations",
      ),
    );
    expect(findHistoryRequest("/api/v1/history/series", "observations")).toBeDefined();
    expect(findHistoryRequest("/api/v1/history/classes", "observations")).toBeDefined();
  });

  test("defaults to count_events when selected cameras have count boundaries", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(jsonResponse([cameraResponse({ zones: [{ type: "line" }] })]));
      }
      if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") return Promise.resolve(jsonResponse(historySeriesResponse()));
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history?cameras=cam-1");

    await waitFor(() => {
      expect(findHistoryRequest("/api/v1/history/series", "count_events")).toBeDefined();
      expect(findHistoryRequest("/api/v1/history/classes", "count_events")).toBeDefined();
    });
    expect(screen.getByLabelText(/metric/i)).toHaveValue("count_events");
    expect(screen.getByTestId("history-trend-chart")).toHaveTextContent("metric=count_events");
  });

  test("defaults to count_events with no explicit camera filter when the camera inventory has count boundaries", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(jsonResponse([cameraResponse({ zones: [{ type: "line" }] })]));
      }
      if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") return Promise.resolve(jsonResponse(historySeriesResponse()));
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history");

    await waitFor(() => {
      expect(findHistoryRequest("/api/v1/history/series", "count_events")).toBeDefined();
      expect(findHistoryRequest("/api/v1/history/classes", "count_events")).toBeDefined();
    });
    expect(screen.getByLabelText(/metric/i)).toHaveValue("count_events");
  });

  test("stays on occupancy when only some selected cameras have count boundaries", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(
          jsonResponse([
            cameraResponse({ id: "cam-1", zones: [{ type: "line" }] }),
            cameraResponse({ id: "cam-2", name: "Lobby camera", zones: [] }),
          ]),
        );
      }
      if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") return Promise.resolve(jsonResponse(historySeriesResponse()));
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history?cameras=cam-1,cam-2");

    await waitFor(() => {
      expect(findHistoryRequest("/api/v1/history/series", "occupancy")).toBeDefined();
      expect(findHistoryRequest("/api/v1/history/classes", "occupancy")).toBeDefined();
    });
    expect(screen.getByLabelText(/metric/i)).toHaveValue("occupancy");
  });

  test("toggling Show speed and entering a threshold updates the chart props", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("button", { name: /download csv/i });

    await user.click(screen.getByLabelText(/show speed/i));
    await user.type(screen.getByLabelText(/speed threshold/i), "60");

    await waitFor(() =>
      expect(screen.getByTestId("history-trend-chart")).toHaveTextContent(
        "speed=true::threshold=60",
      ),
    );
  });

  test("empty result shows the Try last 7 days button", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      if (url.pathname === "/api/v1/cameras") return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") {
        return Promise.resolve(jsonResponse(historySeriesResponse({ rows: [] })));
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });
    renderPage();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /try last 7 days/i })).toBeInTheDocument(),
    );
  });

  test("class filter is populated by /history/classes", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /car \(40 visible samples\)/i })).toBeInTheDocument();
    });
    expect(
      screen.getByRole("option", { name: /person \(5 visible samples\) — no speed data in this window/i }),
    ).toBeInTheDocument();
  });

  test("Show all 80 COCO classes expander reveals unseen classes", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("option", { name: /car \(40 visible samples\)/i });
    await user.click(screen.getByRole("button", { name: /show all 80 coco classes/i }));
    expect(screen.getByRole("option", { name: /giraffe \(0\)/i })).toBeInTheDocument();
  });

  test("downloads exports with the selected metric", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn(() => "blob:history");
    const revokeObjectURL = vi.fn();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: createObjectURL,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: revokeObjectURL,
    });

    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") return Promise.resolve(jsonResponse(historySeriesResponse()));
      if (url.pathname === "/api/v1/export") {
        return Promise.resolve(
          new Response("bucket,class_name,event_count\n", {
            status: 200,
            headers: { "Content-Disposition": 'attachment; filename="history.csv"' },
          }),
        );
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history?metric=count_events");
    await screen.findByTestId("history-trend-chart");

    await user.click(screen.getByRole("button", { name: /download csv/i }));

    await waitFor(() => {
      expect(findHistoryRequest("/api/v1/export", "count_events")).toBeDefined();
    });
    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
});
