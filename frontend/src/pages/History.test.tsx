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

vi.mock("@/components/history/HistoryTrendChart", () => ({
  HistoryTrendChart: ({
    series,
  }: {
    series: { classNames: string[]; points: Array<{ bucket: string }> };
  }) => (
    <div data-testid="history-trend-chart">
      {series.classNames.join(",")}::{series.points.length}
    </div>
  ),
}));

import { createQueryClient } from "@/app/query-client";
import { HistoryPage } from "@/pages/History";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("HistoryPage", () => {
  beforeEach(() => {
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
  });

  afterEach(() => {
    vi.restoreAllMocks();
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("loads chart-ready history, supports multi-filters, and downloads CSV exports", async () => {
    const user = userEvent.setup();
    const requests: Request[] = [];

    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      requests.push(request);
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(
          jsonResponse([
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
          },
          ]),
        );
      }

      if (url.pathname === "/api/v1/history/series") {
        return Promise.resolve(
          jsonResponse({
          granularity: url.searchParams.get("granularity") ?? "1h",
          class_names: ["car", "bus"],
          rows: [
            {
              bucket: "2026-04-12T00:00:00Z",
              values: { car: 22, bus: 6 },
              total_count: 28,
            },
            {
              bucket: "2026-04-12T01:00:00Z",
              values: { car: 18, bus: 4 },
              total_count: 22,
            },
          ],
          }),
        );
      }

      if (url.pathname === "/api/v1/export") {
        return Promise.resolve(
          new Response("bucket,class_name,event_count\n2026-04-12T00:00:00Z,car,22\n", {
            status: 200,
            headers: {
              "Content-Type": "text/csv; charset=utf-8",
              "Content-Disposition": 'attachment; filename="history.csv"',
            },
          }),
        );
      }

      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    render(
      <QueryClientProvider client={createQueryClient()}>
        <HistoryPage />
      </QueryClientProvider>,
    );

    await screen.findByRole("button", { name: /download csv/i });
    await waitFor(() =>
      expect(screen.getByTestId("history-trend-chart")).toHaveTextContent("car,bus::2"),
    );

    await user.selectOptions(screen.getByLabelText(/camera filters/i), [
      "11111111-1111-1111-1111-111111111111",
    ]);
    await user.selectOptions(screen.getByLabelText(/class filters/i), ["bus"]);
    await user.selectOptions(screen.getByLabelText(/granularity/i), "5m");

    await waitFor(() => {
      const seriesRequests = requests.filter(
        (request) => new URL(request.url).pathname === "/api/v1/history/series",
      );
      expect(seriesRequests.length).toBeGreaterThan(1);

      const latestRequest = seriesRequests.at(-1);
      expect(latestRequest).toBeDefined();

      const latestUrl = new URL((latestRequest as Request).url);
      expect(latestUrl.searchParams.get("granularity")).toBe("5m");
      expect(latestUrl.searchParams.getAll("camera_ids")).toEqual([
        "11111111-1111-1111-1111-111111111111",
      ]);
      expect(latestUrl.searchParams.getAll("class_names")).toEqual(["bus"]);
    });

    await user.click(screen.getByRole("button", { name: /download csv/i }));

    await waitFor(() => {
      const exportRequest = requests.find(
        (request) => new URL(request.url).pathname === "/api/v1/export",
      );
      expect(exportRequest).toBeDefined();

      const exportUrl = new URL((exportRequest as Request).url);
      expect(exportUrl.searchParams.get("format")).toBe("csv");
      expect(exportUrl.searchParams.get("granularity")).toBe("5m");
      expect(exportUrl.searchParams.getAll("class_names")).toEqual(["bus"]);
    });
  });
});
