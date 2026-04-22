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

vi.mock("@/lib/auth", () => ({
  mapOidcUser: vi.fn(),
  oidcManager: {
    getUser: vi.fn(),
    signinRedirect: vi.fn(),
    signinRedirectCallback: vi.fn(),
    signoutRedirect: vi.fn(),
  },
}));

import { createQueryClient } from "@/app/query-client";
import { CamerasPage } from "@/pages/Cameras";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

function renderPage() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <CamerasPage />
    </QueryClientProvider>,
  );
}

describe("CamerasPage", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "token",
        user: {
          sub: "admin-1",
          email: "admin@argus.local",
          role: "admin",
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

  test("refetches models when the create wizard opens so newly registered models appear", async () => {
    const user = userEvent.setup();
    let modelRequests = 0;

    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        modelRequests += 1;
        return new Response(
          JSON.stringify(
            modelRequests === 1
              ? []
              : [
                  {
                    id: "model-1",
                    name: "Vezor Radar",
                    version: "1.0.0",
                    task: "detect",
                    path: "/models/radar.onnx",
                    format: "onnx",
                    classes: ["person", "car"],
                    input_shape: { width: 640, height: 640 },
                    sha256: "a".repeat(64),
                    size_bytes: 1024,
                    license: "Apache-2.0",
                  },
                ],
          ),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    await user.click(await screen.findByRole("button", { name: /add camera/i }));
    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() => expect(screen.getByLabelText(/primary model/i)).toHaveValue(""));
    expect(
      within(screen.getByLabelText(/primary model/i)).getByRole("option", {
        name: /vezor radar 1\.0\.0/i,
      }),
    ).toBeInTheDocument();
    expect(modelRequests).toBeGreaterThanOrEqual(2);
  });

  test("shows a models loading failure inside the wizard instead of an empty silent select", async () => {
    const user = userEvent.setup();

    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        return new Response(
          JSON.stringify({ detail: "Failed to load models." }),
          {
            status: 500,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    await user.click(await screen.findByRole("button", { name: /add camera/i }));
    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(
      await screen.findByText(/failed to load models\./i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /retry model lookup/i }),
    ).toBeInTheDocument();
  });

  test("creates a camera with active classes after refetching class-bearing models", async () => {
    const user = userEvent.setup();
    let modelRequests = 0;

    vi.spyOn(global, "fetch").mockImplementation(async (input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras" && request.method === "GET") {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/cameras" && request.method === "POST") {
        const body = (await request.json()) as { active_classes?: string[] };

        expect(body.active_classes).toEqual(["person"]);

        return new Response(JSON.stringify({ id: "camera-1" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.pathname === "/api/v1/sites") {
        return new Response(
          JSON.stringify([
            {
              id: "site-1",
              tenant_id: "tenant-1",
              name: "HQ",
              description: null,
              tz: "Europe/Zurich",
              geo_point: null,
              created_at: "2026-04-20T10:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (url.pathname === "/api/v1/models") {
        modelRequests += 1;
        return new Response(
          JSON.stringify(
            modelRequests === 1
              ? []
              : [
                  {
                    id: "model-1",
                    name: "Vezor Radar",
                    version: "1.0.0",
                    task: "detect",
                    path: "/models/radar.onnx",
                    format: "onnx",
                    classes: ["person", "car"],
                    input_shape: { width: 640, height: 640 },
                    sha256: "a".repeat(64),
                    size_bytes: 1024,
                    license: "Apache-2.0",
                  },
                ],
          ),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      throw new Error(`Unexpected request to ${url.pathname}`);
    });

    renderPage();

    await user.click(await screen.findByRole("button", { name: /add camera/i }));
    await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
    await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
    await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
    await user.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() => expect(screen.getByLabelText(/primary model/i)).toHaveValue(""));
    await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
    await user.click(screen.getByLabelText("person"));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /next/i }));

    for (let count = 0; count < 4; count += 1) {
      await user.click(screen.getByRole("button", { name: /add source point/i }));
      await user.click(
        screen.getByRole("button", { name: /add destination point/i }),
      );
    }

    await user.clear(screen.getByLabelText(/reference distance \(m\)/i));
    await user.type(screen.getByLabelText(/reference distance \(m\)/i), "12.5");
    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /create camera/i }));

    expect(modelRequests).toBeGreaterThanOrEqual(2);
  });
});
