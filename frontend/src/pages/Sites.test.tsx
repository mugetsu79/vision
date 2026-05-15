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
import { SitesPage } from "@/pages/Sites";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

const hqSite = {
  id: "11111111-1111-1111-1111-111111111111",
  tenant_id: "22222222-2222-2222-2222-222222222222",
  name: "HQ",
  description: "Main site",
  tz: "Europe/Zurich",
  geo_point: null,
  created_at: "2026-04-18T10:00:00Z",
};

const depotSite = {
  id: "33333333-3333-3333-3333-333333333333",
  tenant_id: "22222222-2222-2222-2222-222222222222",
  name: "Depot",
  description: null,
  tz: "America/New_York",
  geo_point: null,
  created_at: "2026-04-18T10:00:00Z",
};

const dockScene = {
  id: "camera-1",
  name: "Dock Scene",
  site_id: hqSite.id,
};

const yardScene = {
  id: "camera-2",
  name: "Yard Scene",
  site_id: depotSite.id,
};

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function mockSitesApi({
  sites = [],
  cameras = [],
  deleteStatus = 204,
  deleteBody,
}: {
  sites?: unknown[];
  cameras?: unknown[];
  deleteStatus?: number;
  deleteBody?: unknown;
} = {}) {
  let currentSites = sites;

  return vi.spyOn(global, "fetch").mockImplementation(async (input) => {
    const request = input as Request;
    const url = new URL(request.url);

    if (url.pathname === "/api/v1/cameras") {
      return jsonResponse(cameras);
    }

    if (url.pathname === "/api/v1/sites" && request.method === "POST") {
      const payload = (await request.clone().json()) as Record<string, unknown>;
      const createdSite = { ...hqSite, ...payload };
      currentSites = [createdSite];
      return jsonResponse(createdSite, 201);
    }

    if (url.pathname.startsWith("/api/v1/sites/") && request.method === "DELETE") {
      if (deleteStatus >= 400) {
        return jsonResponse(deleteBody ?? { detail: "Site is still in use." }, deleteStatus);
      }
      const siteId = url.pathname.split("/").pop();
      currentSites = currentSites.filter((site) => {
        if (
          typeof site === "object" &&
          site !== null &&
          "id" in site &&
          typeof site.id === "string"
        ) {
          return site.id !== siteId;
        }
        return true;
      });
      return Promise.resolve(new Response(null, { status: 204 }));
    }

    if (url.pathname === "/api/v1/sites") {
      return jsonResponse(currentSites);
    }

    return Promise.resolve(new Response("Not found", { status: 404 }));
  });
}

function renderSitesPage() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <SitesPage />
    </QueryClientProvider>,
  );
}

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

  test("renders one card per site without a duplicate table", async () => {
    mockSitesApi({
      sites: [hqSite, depotSite],
      cameras: [dockScene, yardScene],
    });

    renderSitesPage();

    expect(await screen.findByTestId("sites-workspace")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();

    const grid = await screen.findByTestId("site-context-grid");
    expect(within(grid).getAllByText(/deployment location/i)).toHaveLength(2);
    expect(
      within(grid).getByRole("heading", { name: "HQ" }),
    ).toBeInTheDocument();
    expect(
      within(grid).getByRole("heading", { name: "Depot" }),
    ).toBeInTheDocument();
    expect(within(grid).getAllByText("1 scene")).toHaveLength(2);
  });

  test("shows empty state when there are no sites", async () => {
    mockSitesApi();

    renderSitesPage();

    expect(
      await screen.findByText(/no deployment sites yet/i),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /add site/i }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByTestId("site-context-grid")).toBeNull();
  });

  test("loads sites and creates a new site through the dialog", async () => {
    const user = userEvent.setup();
    const fetchMock = mockSitesApi({
      cameras: [dockScene],
    });

    renderSitesPage();

    expect(await screen.findByTestId("sites-workspace")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Deployment Sites" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/no deployment sites yet/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/sites anchor deployment locations/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/camera placement/i)).not.toBeInTheDocument();

    const [addSiteButton] = await screen.findAllByRole("button", {
      name: /add site/i,
    });
    await user.click(addSiteButton);
    await user.type(screen.getByLabelText(/site name/i), "HQ");
    await user.type(screen.getByLabelText(/description/i), "Main site");
    await user.clear(screen.getByLabelText(/time zone/i));
    await user.type(screen.getByLabelText(/time zone/i), "Europe/Zurich");
    await user.click(screen.getByRole("button", { name: /save site/i }));

    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "HQ" })).toBeInTheDocument(),
    );
    expect(screen.queryByRole("table")).toBeNull();
    const grid = screen.getByTestId("site-context-grid");
    expect(
      within(grid).getAllByText(/deployment location/i).length,
    ).toBe(1);
    expect(within(grid).getByText("1 scene")).toBeInTheDocument();

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

  test("deletes a site from its location card after confirmation", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchMock = mockSitesApi({
      sites: [hqSite, depotSite],
      cameras: [dockScene, yardScene],
    });

    renderSitesPage();

    const grid = await screen.findByTestId("site-context-grid");
    const hqCard = within(grid)
      .getByRole("heading", { name: "HQ" })
      .closest("section");

    expect(hqCard).not.toBeNull();
    await user.click(
      within(hqCard as HTMLElement).getByRole("button", { name: /delete site/i }),
    );

    await waitFor(() =>
      expect(within(grid).queryByRole("heading", { name: "HQ" })).not.toBeInTheDocument(),
    );
    expect(confirmSpy).toHaveBeenCalledWith("Delete HQ? This cannot be undone.");

    const siteDeleteRequest = fetchMock.mock.calls
      .map((call) => call[0])
      .find(
        (request) =>
          request instanceof Request &&
          request.method === "DELETE" &&
          new URL(request.url).pathname === `/api/v1/sites/${hqSite.id}`,
      );

    expect(siteDeleteRequest).toBeInstanceOf(Request);
    expect(
      within(grid).getByRole("heading", { name: "Depot" }),
    ).toBeInTheDocument();
  });

  test("shows backend delete errors when a site is still referenced", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockSitesApi({
      sites: [hqSite],
      cameras: [dockScene],
      deleteStatus: 409,
      deleteBody: { detail: "Delete cameras and edge nodes before deleting this site." },
    });

    renderSitesPage();

    const grid = await screen.findByTestId("site-context-grid");
    await user.click(within(grid).getByRole("button", { name: /delete site/i }));

    expect(
      await screen.findByText(/delete cameras and edge nodes before deleting this site/i),
    ).toBeInTheDocument();
    expect(within(grid).getByRole("heading", { name: "HQ" })).toBeInTheDocument();
  });
});
