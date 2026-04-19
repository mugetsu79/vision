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

import { createQueryClient } from "@/app/query-client";
import { IncidentsPage } from "@/pages/Incidents";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("IncidentsPage", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "incident-token",
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

  test("renders snapshot previews and refetches when camera or type filters change", async () => {
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
            name: "Forklift Gate",
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

      if (url.pathname === "/api/v1/incidents") {
        return Promise.resolve(
          jsonResponse([
            {
              id: "99999999-9999-9999-9999-999999999999",
              camera_id: "11111111-1111-1111-1111-111111111111",
              ts: "2026-04-18T10:15:00Z",
              type: url.searchParams.get("type") ?? "ppe-missing",
              payload: { hard_hat: false, severity: "high" },
              snapshot_url: "https://minio.local/signed/incidents/forklift-gate.jpg",
              clip_url: "https://minio.local/signed/incidents/forklift-gate.mjpeg",
              storage_bytes: 2097152,
            },
          ]),
        );
      }

      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    render(
      <QueryClientProvider client={createQueryClient()}>
        <IncidentsPage />
      </QueryClientProvider>,
    );

    await screen.findByRole("img", { name: /incident preview for forklift gate/i });
    expect(screen.getByRole("heading", { name: /forklift gate/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open clip/i })).toHaveAttribute(
      "href",
      "https://minio.local/signed/incidents/forklift-gate.mjpeg",
    );
    expect(screen.getByText("2.0 MB secured")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/camera filter/i), [
      "11111111-1111-1111-1111-111111111111",
    ]);
    await user.selectOptions(screen.getByLabelText(/incident type/i), ["ppe-missing"]);

    await waitFor(() => {
      const incidentRequests = requests.filter(
        (request) => new URL(request.url).pathname === "/api/v1/incidents",
      );
      expect(incidentRequests.length).toBeGreaterThan(1);

      const latestUrl = new URL((incidentRequests.at(-1) as Request).url);
      expect(latestUrl.searchParams.get("camera_id")).toBe(
        "11111111-1111-1111-1111-111111111111",
      );
      expect(latestUrl.searchParams.get("type")).toBe("ppe-missing");
    });
  });
});
