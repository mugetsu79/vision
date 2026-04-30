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
import { SitesPage } from "@/pages/Sites";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("SitesPage", () => {
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

  test("loads sites and creates a new site through the dialog", async () => {
    const user = userEvent.setup();
    const createdSite = {
      id: "11111111-1111-1111-1111-111111111111",
      tenant_id: "22222222-2222-2222-2222-222222222222",
      name: "HQ",
      description: "Main site",
      tz: "Europe/Zurich",
      geo_point: null,
      created_at: "2026-04-18T10:00:00Z",
    };
    let sites: unknown[] = [];
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input) => {
      const request = input as Request;
      const url = new URL(request.url);

      if (url.pathname === "/api/v1/cameras") {
        return Promise.resolve(new Response(
          JSON.stringify([
            {
              id: "camera-1",
              name: "Dock Scene",
              site_id: "11111111-1111-1111-1111-111111111111",
            },
          ]),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ));
      }

      if (url.pathname === "/api/v1/sites" && request.method === "POST") {
        sites = [createdSite];
        return Promise.resolve(new Response(JSON.stringify(createdSite), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }));
      }

      if (url.pathname === "/api/v1/sites") {
        return Promise.resolve(new Response(JSON.stringify(sites), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }));
      }

      return Promise.resolve(new Response("Not found", { status: 404 }));
    });

    render(
      <QueryClientProvider client={createQueryClient()}>
        <SitesPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByTestId("sites-workspace")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Deployment Sites" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("site-context-grid")).toBeInTheDocument();
    expect(
      screen.getByText(/sites anchor deployment locations/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/camera placement/i)).not.toBeInTheDocument();

    await user.click(await screen.findByRole("button", { name: /add site/i }));
    await user.type(screen.getByLabelText(/site name/i), "HQ");
    await user.type(screen.getByLabelText(/description/i), "Main site");
    await user.clear(screen.getByLabelText(/time zone/i));
    await user.type(screen.getByLabelText(/time zone/i), "Europe/Zurich");
    await user.click(screen.getByRole("button", { name: /save site/i }));

    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByRole("cell", { name: "HQ" })).toBeInTheDocument(),
    );
    expect(
      screen.getAllByText(/deployment location/i).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("1 scene")).toBeInTheDocument();

    const siteCreateRequest = fetchMock.mock.calls
      .map((call) => call[0])
      .find(
        (request) => request instanceof Request && request.method === "POST",
      );
    expect(siteCreateRequest).toBeInstanceOf(Request);

    const siteCreatePayload: unknown = await (siteCreateRequest as Request)
      .clone()
      .json();
    expect(siteCreatePayload).toMatchObject({
      name: "HQ",
      description: "Main site",
      tz: "Europe/Zurich",
      geo_point: null,
    });

    expect(fetchMock).toHaveBeenCalled();
  });
});
