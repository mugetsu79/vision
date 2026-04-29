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
    onBucketSelect,
  }: {
    series: {
      classNames: string[];
      points: Array<{ bucket: string }>;
      includeSpeed?: boolean;
      speedThreshold?: number | null;
      selectedBucket?: string | null;
    };
    metric?: string;
    onBucketSelect?: (bucket: string) => void;
  }) => (
    <button
      type="button"
      data-testid="history-trend-chart"
      onClick={() => onBucketSelect?.(series.points[0]?.bucket ?? "")}
    >
      {series.classNames.join(",")}::{series.points.length}::speed=
      {String(!!series.includeSpeed)}::threshold=
      {String(series.speedThreshold ?? "none")}::metric={metric ?? "none"}
      ::selected={series.selectedBucket ?? "none"}
    </button>
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
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function historySeriesResponse(overrides: Record<string, unknown> = {}) {
  return {
    granularity: "1h",
    class_names: ["car", "bus"],
    rows: [
      {
        bucket: "2026-04-12T00:00:00Z",
        values: { car: 22, bus: 6 },
        total_count: 28,
      },
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
    (request) =>
      request.pathname === pathname &&
      request.searchParams.get("metric") === metric,
  );
}

function historyRequests(pathname: string, metric: string) {
  return recordedRequests.filter(
    (request) =>
      request.pathname === pathname &&
      request.searchParams.get("metric") === metric,
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
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras")
        return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
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
                    over_threshold_count: url.searchParams.get(
                      "speed_threshold",
                    )
                      ? { car: 5 }
                      : null,
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
    vi.useRealTimers();
    vi.restoreAllMocks();
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("hydrates filter state from URL and calls endpoint with include_speed", async () => {
    renderPage(
      "/history?metric=observations&speed=1&speedThreshold=50&granularity=5m",
    );
    expect(
      await screen.findByRole("heading", { name: /history & patterns/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("patterns-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("patterns-instrument-rail")).toBeInTheDocument();
    expect(screen.getByTestId("pattern-export-surface")).toBeInTheDocument();
    expect(screen.getByTestId("pattern-filter-rail")).toBeInTheDocument();
    expect(screen.getByLabelText(/search patterns/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/scene filters/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/camera filters/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/as .* buckets/i)).not.toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("history-trend-chart")).toHaveTextContent(
        "speed=true::threshold=50::metric=observations",
      ),
    );
    expect(
      findHistoryRequest("/api/v1/history/series", "observations"),
    ).toBeDefined();
    expect(
      findHistoryRequest("/api/v1/history/classes", "observations"),
    ).toBeDefined();
  });

  test("defaults to count_events when selected cameras have count boundaries", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(
          jsonResponse([cameraResponse({ zones: [{ type: "line" }] })]),
        );
      }
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series")
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history?cameras=cam-1");

    await waitFor(() => {
      expect(
        findHistoryRequest("/api/v1/history/series", "count_events"),
      ).toBeDefined();
      expect(
        findHistoryRequest("/api/v1/history/classes", "count_events"),
      ).toBeDefined();
    });
    expect(screen.getByLabelText("Metric")).toHaveValue("count_events");
    expect(screen.getByTestId("history-trend-chart")).toHaveTextContent(
      "metric=count_events",
    );
  });

  test("defaults to count_events when selected cameras only have polygon zones", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(
          jsonResponse([
            cameraResponse({
              zones: [
                {
                  id: "workspace",
                  polygon: [
                    [0, 0],
                    [10, 0],
                    [10, 10],
                    [0, 10],
                  ],
                },
              ],
            }),
          ]),
        );
      }
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series")
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history?cameras=cam-1");

    await waitFor(() => {
      expect(
        findHistoryRequest("/api/v1/history/series", "count_events"),
      ).toBeDefined();
      expect(
        findHistoryRequest("/api/v1/history/classes", "count_events"),
      ).toBeDefined();
    });
    expect(screen.getByLabelText("Metric")).toHaveValue("count_events");
  });

  test("defaults to count_events with no explicit camera filter when the camera inventory has count boundaries", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(
          jsonResponse([cameraResponse({ zones: [{ type: "line" }] })]),
        );
      }
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series")
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history");

    await waitFor(() => {
      expect(
        findHistoryRequest("/api/v1/history/series", "count_events"),
      ).toBeDefined();
      expect(
        findHistoryRequest("/api/v1/history/classes", "count_events"),
      ).toBeDefined();
    });
    expect(screen.getByLabelText("Metric")).toHaveValue("count_events");
  });

  test("stays on occupancy when only some selected cameras have count boundaries", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
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
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series")
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history?cameras=cam-1,cam-2");

    await waitFor(() => {
      expect(
        findHistoryRequest("/api/v1/history/series", "occupancy"),
      ).toBeDefined();
      expect(
        findHistoryRequest("/api/v1/history/classes", "occupancy"),
      ).toBeDefined();
    });
    expect(screen.getByLabelText("Metric")).toHaveValue("occupancy");
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
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      if (url.pathname === "/api/v1/cameras")
        return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") {
        return Promise.resolve(
          jsonResponse(historySeriesResponse({ rows: [] })),
        );
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /try last 7 days/i }),
      ).toBeInTheDocument(),
    );
  });

  test("renders zero coverage as no detections instead of generic emptiness", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      if (url.pathname === "/api/v1/cameras")
        return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") {
        return Promise.resolve(
          jsonResponse(
            historySeriesResponse({
              class_names: ["car"],
              rows: [
                {
                  bucket: "2026-04-12T00:00:00Z",
                  values: { car: 0 },
                  total_count: 0,
                },
              ],
              coverage_status: "zero",
              coverage_by_bucket: [
                {
                  bucket: "2026-04-12T00:00:00Z",
                  status: "zero",
                  reason: null,
                },
              ],
            }),
          ),
        );
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage();

    await screen.findByText(/telemetry was valid and no detections/i);
    expect(screen.getAllByText(/no detections/i).length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getByTestId("history-trend-chart")).toBeInTheDocument();
  });

  test("renders no telemetry coverage distinctly", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      if (url.pathname === "/api/v1/cameras")
        return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") {
        return Promise.resolve(
          jsonResponse(
            historySeriesResponse({
              class_names: ["car"],
              rows: [
                {
                  bucket: "2026-04-12T00:00:00Z",
                  values: { car: 0 },
                  total_count: 0,
                },
              ],
              coverage_status: "no_telemetry",
              coverage_by_bucket: [
                {
                  bucket: "2026-04-12T00:00:00Z",
                  status: "no_telemetry",
                  reason: null,
                },
              ],
            }),
          ),
        );
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage();

    await screen.findByText(/no usable telemetry/i);
    expect(screen.getAllByText(/no telemetry/i).length).toBeGreaterThanOrEqual(
      1,
    );
  });

  test("keeps last 7 days preset as the active relative window", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-04-27T12:34:56.000Z"));
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("button", { name: /download csv/i });
    recordedRequests = [];

    await user.click(screen.getByRole("button", { name: /last 7d/i }));
    await user.click(screen.getByLabelText(/show speed/i));

    await waitFor(() => {
      const requests = historyRequests(
        "/api/v1/history/series",
        "occupancy",
      ).filter(
        (request) => request.searchParams.get("include_speed") === "true",
      );
      expect(requests.length).toBeGreaterThanOrEqual(1);
      const latest = requests.at(-1);
      expect(latest?.searchParams.get("from")).toBe("2026-04-20T12:34:00.000Z");
      expect(latest?.searchParams.get("to")).toBe("2026-04-27T12:34:00.000Z");
    });
  });

  test("refreshes following-now bounds when filters change after time advances", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-04-27T12:34:56.000Z"));
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("history-trend-chart");
    expect(screen.getByText(/following now/i)).toBeInTheDocument();

    recordedRequests = [];
    vi.setSystemTime(new Date("2026-04-27T13:34:56.000Z"));
    await user.click(screen.getByLabelText(/show speed/i));

    await waitFor(() => {
      const requests = historyRequests(
        "/api/v1/history/series",
        "occupancy",
      ).filter(
        (request) => request.searchParams.get("include_speed") === "true",
      );
      expect(requests.length).toBeGreaterThanOrEqual(1);
      const latest = requests.at(-1);
      expect(latest?.searchParams.get("from")).toBe("2026-04-26T13:34:00.000Z");
      expect(latest?.searchParams.get("to")).toBe("2026-04-27T13:34:00.000Z");
    });
  });

  test("refreshes following-now bounds without filter interaction", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    vi.setSystemTime(new Date("2026-04-27T12:34:56.000Z"));
    renderPage("/history?window=last_1h&follow=1");

    await screen.findByTestId("history-trend-chart");
    recordedRequests = [];

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    await waitFor(() => {
      const latest = historyRequests("/api/v1/history/series", "occupancy").at(
        -1,
      );
      expect(latest?.searchParams.get("from")).toBe("2026-04-27T11:35:00.000Z");
      expect(latest?.searchParams.get("to")).toBe("2026-04-27T12:35:00.000Z");
    });
  });

  test("class filter is populated by /history/classes", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByRole("option", { name: /car \(40 visible samples\)/i }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("option", {
        name: /person \(5 visible samples\) — no speed data in this window/i,
      }),
    ).toBeInTheDocument();
  });

  test("observations metric is clearly labeled as a debug/raw view", async () => {
    renderPage("/history?metric=observations");

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: /raw tracking samples/i }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("option", {
        name: /raw tracking samples \(debug\) — per-frame tracking density for debugging/i,
      }),
    ).toBeInTheDocument();
  });

  test("Show all 80 COCO classes expander reveals unseen classes", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("option", { name: /car \(40 visible samples\)/i });
    await user.click(
      screen.getByRole("button", { name: /show all 80 coco classes/i }),
    );
    expect(
      screen.getByRole("option", { name: /giraffe \(0\)/i }),
    ).toBeInTheDocument();
  });

  test("downloads exports with the selected metric", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn(() => "blob:history");
    const revokeObjectURL = vi.fn();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
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
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras")
        return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series")
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      if (url.pathname === "/api/v1/export") {
        return Promise.resolve(
          new Response("bucket,class_name,event_count\n", {
            status: 200,
            headers: {
              "Content-Disposition": 'attachment; filename="history.csv"',
            },
          }),
        );
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage("/history?metric=count_events");
    await screen.findByTestId("history-trend-chart");

    await user.click(screen.getByRole("button", { name: /download csv/i }));

    await waitFor(() => {
      expect(
        findHistoryRequest("/api/v1/export", "count_events"),
      ).toBeDefined();
    });
    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalled();
    clickSpy.mockRestore();
  });

  test("exports the visible resolved follow-now window", async () => {
    const user = userEvent.setup();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-04-27T12:34:56Z"));

    const createObjectURL = vi.fn(() => "blob:history");
    const revokeObjectURL = vi.fn();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
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

    renderPage("/history?window=last_1h&follow=1&metric=count_events");
    await screen.findByTestId("history-trend-chart");
    await user.click(screen.getByRole("button", { name: /download csv/i }));

    await waitFor(() => {
      const request = findHistoryRequest("/api/v1/export", "count_events");
      expect(request?.searchParams.get("from")).toBe(
        "2026-04-27T11:34:00.000Z",
      );
      expect(request?.searchParams.get("to")).toBe("2026-04-27T12:34:00.000Z");
    });

    clickSpy.mockRestore();
    vi.useRealTimers();
  });

  test("renders split review and selects a bucket from the chart", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("history-trend-chart");
    expect(
      screen.getByRole("heading", { name: /bucket review/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/select a bucket/i)).toBeInTheDocument();

    await user.click(screen.getByTestId("history-trend-chart"));

    const selectedHeading = screen.getByRole("heading", { name: /12 apr/i });
    expect(selectedHeading).toBeInTheDocument();
    expect(selectedHeading).not.toHaveTextContent(/\(Apr 12\)/i);
    expect(screen.getByText(/28 visible samples/i)).toBeInTheDocument();
  });

  test("selects any bucket from the accessible bucket picker", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras")
        return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") {
        return Promise.resolve(
          jsonResponse(
            historySeriesResponse({
              rows: [
                {
                  bucket: "2026-04-12T00:00:00Z",
                  values: { car: 22, bus: 6 },
                  total_count: 28,
                },
                {
                  bucket: "2026-04-12T01:00:00Z",
                  values: { car: 5, bus: 2 },
                  total_count: 7,
                },
              ],
            }),
          ),
        );
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage();
    await screen.findByTestId("history-trend-chart");

    await user.selectOptions(
      screen.getByLabelText("Review bucket"),
      "2026-04-12T01:00:00Z",
    );

    expect(
      screen.getByRole("heading", { name: /12 Apr, 01:00/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/7 visible samples/i)).toBeInTheDocument();
  });

  test("shows following-now controls by default and resumes from absolute windows", async () => {
    const user = userEvent.setup();
    renderPage(
      "/history?from=2026-04-01T00%3A00%3A00.000Z&to=2026-04-02T00%3A00%3A00.000Z",
    );

    await screen.findByTestId("history-trend-chart");
    expect(screen.getByText(/absolute window/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /resume following now/i }),
    );

    expect(screen.getByText(/following now/i)).toBeInTheDocument();
  });

  test("resuming a paused relative window preserves the selected relative window", async () => {
    const user = userEvent.setup();
    renderPage("/history?window=last_7d&follow=0");

    await screen.findByTestId("history-trend-chart");
    expect(screen.getByText(/paused window/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /resume following now/i }),
    );

    expect(screen.getByLabelText("Time window")).toHaveValue("last_7d");
    expect(screen.getByText(/following now/i)).toBeInTheDocument();
  });

  test("paused relative windows keep their stored bounds until resumed", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-04-27T12:34:56.000Z"));
    const user = userEvent.setup();
    renderPage("/history?window=last_24h&follow=0");

    await screen.findByTestId("history-trend-chart");
    expect(screen.getByText(/paused window/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /resume following now/i }),
    ).toBeInTheDocument();

    recordedRequests = [];
    vi.setSystemTime(new Date("2026-04-27T13:34:56.000Z"));
    await user.click(screen.getByLabelText(/show speed/i));

    await waitFor(() => {
      const requests = historyRequests(
        "/api/v1/history/series",
        "occupancy",
      ).filter(
        (request) => request.searchParams.get("include_speed") === "true",
      );
      expect(requests.length).toBeGreaterThanOrEqual(1);
      const latest = requests.at(-1);
      expect(latest?.searchParams.get("from")).toBe("2026-04-26T12:34:00.000Z");
      expect(latest?.searchParams.get("to")).toBe("2026-04-27T12:34:00.000Z");
    });
  });

  test("clears chart selection when the selected bucket leaves the current series", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras")
        return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes")
        return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") {
        if (url.searchParams.get("metric") === "count_events") {
          return Promise.resolve(
            jsonResponse(
              historySeriesResponse({
                metric: "count_events",
                rows: [
                  {
                    bucket: "2026-04-13T00:00:00Z",
                    values: { car: 7, bus: 3 },
                    total_count: 10,
                  },
                ],
              }),
            ),
          );
        }
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage();
    await screen.findByTestId("history-trend-chart");

    await user.click(screen.getByTestId("history-trend-chart"));
    expect(screen.getByTestId("history-trend-chart")).toHaveTextContent(
      "selected=2026-04-12T00:00:00Z",
    );

    await user.selectOptions(
      screen.getByLabelText("Toolbar metric"),
      "count_events",
    );

    await waitFor(() =>
      expect(screen.getByTestId("history-trend-chart")).toHaveTextContent(
        "metric=count_events::selected=none",
      ),
    );
  });

  test("unified search selects cameras classes and buckets", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId("history-trend-chart");
    await user.type(screen.getByLabelText(/search patterns/i), "car");
    await user.click(screen.getByRole("option", { name: "car" }));

    await waitFor(() => {
      const request = recordedRequests.find(
        (url) =>
          url.pathname === "/api/v1/history/series" &&
          url.searchParams.get("class_names") === "car",
      );
      expect(request).toBeDefined();
    });

    await user.clear(screen.getByLabelText(/search patterns/i));
    await user.type(screen.getByLabelText(/search patterns/i), "spike");
    await user.click(screen.getByRole("option", { name: /28 events/i }));

    expect(screen.getByText(/28 visible samples/i)).toBeInTheDocument();
  });

  test("unified search selects boundary summaries by matching camera zones", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      recordedRequests.push(url);
      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(
          jsonResponse([cameraResponse({ zones: [{ name: "Entry Line" }] })]),
        );
      }
      if (url.pathname === "/api/v1/history/classes") {
        return Promise.resolve(
          jsonResponse({
            ...classesResponse(),
            boundaries: [
              { boundary_id: "entry-line", event_types: ["line_cross"] },
            ],
          }),
        );
      }
      if (url.pathname === "/api/v1/history/series")
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    renderPage();
    await screen.findByTestId("history-trend-chart");
    recordedRequests = [];

    await user.type(screen.getByLabelText(/search patterns/i), "entry-line");
    await user.click(screen.getByRole("option", { name: "entry-line" }));

    await waitFor(() => {
      const request = recordedRequests.find(
        (url) =>
          url.pathname === "/api/v1/history/series" &&
          url.searchParams.get("camera_ids") === "cam-1",
      );
      expect(request).toBeDefined();
    });
  });
});
