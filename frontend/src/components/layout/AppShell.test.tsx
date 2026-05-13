import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
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

vi.mock("@/lib/auth", () => ({
  mapOidcUser: vi.fn(),
  oidcManager: {
    getUser: vi.fn(),
    signinRedirect: vi.fn(),
    signinRedirectCallback: vi.fn(),
    signoutRedirect: vi.fn(),
  },
}));

import { AppShell } from "@/components/layout/AppShell";
import { createQueryClient } from "@/app/query-client";
import { oidcManager } from "@/lib/auth";
import {
  type WorkspaceNavItem,
  workspaceNavGroups,
} from "@/components/layout/workspace-nav";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("AppShell", () => {
  beforeEach(() => {
    window.localStorage.clear();
    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "test-token",
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
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("renders the unified left rail workspace shell", () => {
    render(
      <QueryClientProvider client={createQueryClient()}>
        <MemoryRouter
          future={{
            v7_relativeSplatPath: true,
            v7_startTransition: true,
          }}
        >
          <AppShell>
            <div>Page body</div>
          </AppShell>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("navigation", { name: /primary workspace/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("spatial-cockpit-shell")).toBeInTheDocument();
    expect(screen.getByTestId("spatial-workspace-stage")).toBeInTheDocument();
    expect(screen.getByTestId("omnisight-field")).toHaveClass(
      "omnisight-field--shell",
    );
    expect(screen.getByTestId("workspace-transition")).toBeInTheDocument();
    const intelligenceNav = screen.getByRole("navigation", {
      name: /intelligence/i,
    });
    const controlNav = screen.getByRole("navigation", { name: /control/i });

    expect(intelligenceNav).toBeInTheDocument();
    expect(controlNav).toBeInTheDocument();
    expect(
      within(intelligenceNav).getByRole("link", { name: "Dashboard" }),
    ).toBeInTheDocument();
    expect(
      within(intelligenceNav).getByRole("link", { name: "Live" }),
    ).toBeInTheDocument();
    expect(
      within(intelligenceNav).getByRole("link", { name: "Patterns" }),
    ).toBeInTheDocument();
    expect(
      within(intelligenceNav).getByRole("link", { name: "Evidence" }),
    ).toBeInTheDocument();
    expect(
      within(controlNav).getByRole("link", { name: "Operations" }),
    ).toBeInTheDocument();
    expect(
      within(controlNav).getByRole("link", { name: "Deployment" }),
    ).toBeInTheDocument();
    expect(
      within(controlNav).getByRole("link", { name: "Sites" }),
    ).toBeInTheDocument();
    expect(
      within(controlNav).getByRole("link", { name: "Scenes" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/workspace/i)).toBeInTheDocument();
    expect(screen.getByText(/omnisight control layer/i)).toBeInTheDocument();
    expect(screen.queryByText(/management/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/configuration surfaces stay one step away/i),
    ).not.toBeInTheDocument();
  });

  test("labels the settings route as operations", () => {
    const allItems: WorkspaceNavItem[] = workspaceNavGroups.flatMap((group) => [
      ...group.items,
    ]);

    expect(allItems).toContainEqual(
      expect.objectContaining({
        label: "Operations",
        to: "/settings",
      }),
    );
    expect(allItems).toContainEqual(
      expect.objectContaining({
        label: "Deployment",
        to: "/deployment",
      }),
    );
  });

  test("lets operators collapse the grouped section rail without losing the icon rail", async () => {
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={createQueryClient()}>
        <MemoryRouter
          future={{
            v7_relativeSplatPath: true,
            v7_startTransition: true,
          }}
        >
          <AppShell>
            <div>Page body</div>
          </AppShell>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("navigation", { name: /primary workspace/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: /intelligence/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: /control/i }),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /hide section rail/i }),
    );

    expect(
      screen.getByRole("navigation", { name: /primary workspace/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: /intelligence/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: /control/i }),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /show section rail/i }),
    );

    expect(
      screen.getByRole("navigation", { name: /intelligence/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: /control/i }),
    ).toBeInTheDocument();
  });

  test("routes authenticated users into the refreshed omnisight workspace", async () => {
    window.history.pushState({}, "", "/live");
    vi.mocked(oidcManager).getUser.mockResolvedValue({
      access_token: "test-token",
      expired: false,
      profile: {
        sub: "admin-1",
        email: "admin@argus.local",
        iss: "http://127.0.0.1:8080/realms/argus-dev",
        realm_access: { roles: ["admin"] },
      },
    } as unknown as Awaited<ReturnType<typeof oidcManager.getUser>>);

    const { default: App } = await import("@/App");
    render(<App />);

    const primaryWorkspaceNav = await screen.findByRole("navigation", {
      name: /primary workspace/i,
    });
    expect(
      await screen.findByRole("heading", { name: /live intelligence/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        /operator-grade visibility without native-bandwidth waste/i,
      ),
    ).not.toBeInTheDocument();
    expect(
      within(primaryWorkspaceNav).getByRole("link", { name: "Dashboard" }),
    ).toBeInTheDocument();
    expect(
      within(primaryWorkspaceNav).getByRole("link", { name: "Live" }),
    ).toBeInTheDocument();
    expect(
      within(primaryWorkspaceNav).getByRole("link", { name: "Patterns" }),
    ).toBeInTheDocument();
    expect(
      within(primaryWorkspaceNav).getByRole("link", { name: "Deployment" }),
    ).toBeInTheDocument();
    expect(
      within(primaryWorkspaceNav).queryByRole("link", { name: "Cameras" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("navigation", {
        name: /intelligence/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", {
        name: /control/i,
      }),
    ).toBeInTheDocument();
  });
});
