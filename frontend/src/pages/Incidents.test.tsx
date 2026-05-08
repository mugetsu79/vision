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

import { createQueryClient } from "@/app/query-client";
import { IncidentsPage } from "@/pages/Incidents";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
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
  };
}

function incidentPayload(overrides: Record<string, unknown> = {}) {
  return {
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
    ...overrides,
  };
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

  test("renders evidence desk queue, clip-only hero, facts, and filters", async () => {
    const user = userEvent.setup();
    const requests: Request[] = [];

    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      requests.push(request);
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(jsonResponse([cameraPayload()]));
      }

      if (url.pathname === "/api/v1/incidents") {
        return Promise.resolve(jsonResponse([incidentPayload()]));
      }

      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    render(
      <QueryClientProvider client={createQueryClient()}>
        <IncidentsPage />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: /evidence desk/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("evidence-desk-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("evidence-filter-bar")).toBeInTheDocument();
    expect(screen.getByTestId("review-queue")).toBeInTheDocument();
    expect(screen.getByTestId("evidence-media")).toBeInTheDocument();
    expect(screen.getByTestId("evidence-media")).toHaveClass(
      "bg-[color:var(--vezor-media-black)]",
    );
    expect(screen.getByTestId("facts-rail")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /review queue/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /facts/i })).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: /^facts$/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("complementary", { name: /incident facts/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/move from signal to decision/i),
    ).toBeInTheDocument();

    const hero = screen.getByRole("region", { name: /selected evidence/i });
    expect(within(hero).getByText(/clip-only evidence/i)).toBeInTheDocument();
    expect(
      within(hero).getByRole("link", { name: /open clip/i }),
    ).toHaveAttribute(
      "href",
      "https://minio.local/signed/incidents/forklift-gate.mjpeg",
    );
    expect(
      within(hero).getByRole("button", { name: /^review$/i }),
    ).toBeInTheDocument();

    expect(screen.getAllByText("2.0 MB secured").length).toBeGreaterThan(0);

    expect(screen.queryByLabelText(/camera filter/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/incident type/i)).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/scene filter/i), [
      "11111111-1111-1111-1111-111111111111",
    ]);
    await user.selectOptions(screen.getByLabelText(/event type/i), [
      "ppe-missing",
    ]);
    await user.selectOptions(screen.getByLabelText(/review status/i), [
      "reviewed",
    ]);

    await waitFor(() => {
      const incidentRequests = requests.filter(
        (request) => new URL(request.url).pathname === "/api/v1/incidents",
      );
      const latestUrl = new URL((incidentRequests.at(-1) as Request).url);

      expect(latestUrl.searchParams.get("camera_id")).toBe(
        "11111111-1111-1111-1111-111111111111",
      );
      expect(latestUrl.searchParams.get("type")).toBe("ppe-missing");
      expect(latestUrl.searchParams.get("review_status")).toBe("reviewed");
    });
  });

  test("keeps snapshot evidence inspectable", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(jsonResponse([cameraPayload()]));
      }

      if (url.pathname === "/api/v1/incidents") {
        return Promise.resolve(
          jsonResponse([
            incidentPayload({
              snapshot_url:
                "https://minio.local/signed/incidents/forklift-gate.jpg",
            }),
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

    expect(
      await screen.findByRole("img", { name: /evidence record/i }),
    ).toBeInTheDocument();
  });

  test("wraps selected evidence in an animated swap region", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(jsonResponse([cameraPayload()]));
      }

      if (url.pathname === "/api/v1/incidents") {
        return Promise.resolve(
          jsonResponse([
            incidentPayload(),
            incidentPayload({
              id: "88888888-8888-8888-8888-888888888888",
              camera_name: "Loading Dock",
              type: "zone-entry",
              ts: "2026-04-18T10:25:00Z",
            }),
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

    const swapRegion = await screen.findByTestId("evidence-media-swap");
    expect(
      within(swapRegion).getByRole("region", { name: /selected evidence/i }),
    ).toHaveTextContent("Forklift Gate");

    await user.click(screen.getByRole("button", { name: /loading dock/i }));

    await waitFor(() => {
      expect(
        screen
          .getAllByTestId("evidence-media-swap")
          .some((region) => region.textContent?.includes("Loading Dock")),
      ).toBe(true);
    });
  });

  test("persists review state from the evidence hero", async () => {
    const user = userEvent.setup();
    const requests: Request[] = [];
    const patchBodies: Array<{ review_status?: string }> = [];
    let incident = incidentPayload();

    vi.spyOn(global, "fetch").mockImplementation(async (input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      requests.push(request);
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(jsonResponse([cameraPayload()]));
      }

      if (url.pathname === "/api/v1/incidents") {
        const reviewStatus = url.searchParams.get("review_status");
        const incidentReviewStatus = String(incident.review_status);

        if (!reviewStatus || reviewStatus === incidentReviewStatus) {
          return Promise.resolve(jsonResponse([incident]));
        }

        return Promise.resolve(jsonResponse([]));
      }

      if (
        url.pathname ===
        "/api/v1/incidents/99999999-9999-9999-9999-999999999999/review"
      ) {
        const body = (await request.clone().json()) as {
          review_status?: string;
        };
        patchBodies.push(body);
        incident = incidentPayload(
          body.review_status === "reviewed"
            ? {
                review_status: "reviewed",
                reviewed_at: "2026-04-18T10:20:00Z",
                reviewed_by_subject: "analyst-1",
              }
            : { review_status: "pending" },
        );
        return Promise.resolve(jsonResponse(incident));
      }

      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    render(
      <QueryClientProvider client={createQueryClient()}>
        <IncidentsPage />
      </QueryClientProvider>,
    );

    const hero = await screen.findByRole("region", {
      name: /selected evidence/i,
    });
    await user.click(within(hero).getByRole("button", { name: /^review$/i }));

    expect(
      await screen.findByText(/no evidence records match/i),
    ).toBeInTheDocument();

    const reviewRequest = requests.find(
      (request) =>
        new URL(request.url).pathname ===
        "/api/v1/incidents/99999999-9999-9999-9999-999999999999/review",
    );
    expect(reviewRequest?.method).toBe("PATCH");
    expect(patchBodies[0]).toEqual({ review_status: "reviewed" });

    await user.selectOptions(screen.getByLabelText(/review status/i), [
      "reviewed",
    ]);

    const reviewedHero = await screen.findByRole("region", {
      name: /selected evidence/i,
    });
    expect(
      within(reviewedHero).getByRole("button", { name: /^reopen$/i }),
    ).toBeInTheDocument();

    await user.click(
      within(reviewedHero).getByRole("button", { name: /^reopen$/i }),
    );

    await waitFor(() => {
      expect(patchBodies[1]).toEqual({ review_status: "pending" });
    });
  });

  test("explains operator access requirement when review is denied", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation(async (input, init) => {
      const request =
        input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(jsonResponse([cameraPayload()]));
      }

      if (url.pathname === "/api/v1/incidents") {
        const reviewStatus = url.searchParams.get("review_status");
        return Promise.resolve(
          jsonResponse(reviewStatus === "reviewed" ? [] : [incidentPayload()]),
        );
      }

      if (
        url.pathname ===
        "/api/v1/incidents/99999999-9999-9999-9999-999999999999/review"
      ) {
        return Promise.resolve(
          jsonResponse({ detail: "Insufficient role." }, 403),
        );
      }

      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    render(
      <QueryClientProvider client={createQueryClient()}>
        <IncidentsPage />
      </QueryClientProvider>,
    );

    const hero = await screen.findByRole("region", {
      name: /selected evidence/i,
    });
    await user.click(within(hero).getByRole("button", { name: /^review$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Operator access is required to change review state.",
    );

    await user.selectOptions(screen.getByLabelText(/review status/i), [
      "reviewed",
    ]);

    await waitFor(() => {
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });
});
