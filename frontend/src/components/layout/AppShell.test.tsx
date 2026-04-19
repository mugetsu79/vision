import { act, render, screen, within } from "@testing-library/react";
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
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("AppShell", () => {
  beforeEach(() => {
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
    const operationsNav = screen.getByRole("navigation", { name: /operations/i });
    const configurationNav = screen.getByRole("navigation", { name: /configuration/i });

    expect(operationsNav).toBeInTheDocument();
    expect(configurationNav).toBeInTheDocument();
    expect(within(operationsNav).getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(within(operationsNav).getByRole("link", { name: "Live" })).toBeInTheDocument();
    expect(within(operationsNav).getByRole("link", { name: "History" })).toBeInTheDocument();
    expect(within(operationsNav).getByRole("link", { name: "Incidents" })).toBeInTheDocument();
    expect(within(configurationNav).getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(within(configurationNav).getByRole("link", { name: "Sites" })).toBeInTheDocument();
    expect(within(configurationNav).getByRole("link", { name: "Cameras" })).toBeInTheDocument();
    expect(screen.queryByText(/management/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/configuration surfaces stay one step away/i),
    ).not.toBeInTheDocument();
  });

  test("routes authenticated users through the shell on dashboard paths", async () => {
    window.history.pushState({}, "", "/dashboard");

    const { default: App } = await import("@/App");
    render(<App />);

    const primaryWorkspaceNav = await screen.findByRole("navigation", {
      name: /primary workspace/i,
    });

    expect(primaryWorkspaceNav).toBeInTheDocument();
    expect(within(primaryWorkspaceNav).getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
  });
});
