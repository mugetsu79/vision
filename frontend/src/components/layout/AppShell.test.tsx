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
    expect(screen.getByRole("navigation", { name: /operations/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /configuration/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /hide section rail/i }));

    expect(screen.getByRole("navigation", { name: /primary workspace/i })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: /operations/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: /configuration/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /show section rail/i }));

    expect(screen.getByRole("navigation", { name: /operations/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /configuration/i })).toBeInTheDocument();
  });

  test("routes authenticated users into the refreshed operations workspace", async () => {
    window.history.pushState({}, "", "/dashboard");

    const { default: App } = await import("@/App");
    render(<App />);

    const primaryWorkspaceNav = await screen.findByRole("navigation", {
      name: /primary workspace/i,
    });
    expect(await screen.findByRole("heading", { name: /live command surface/i })).toBeInTheDocument();
    expect(
      screen.queryByText(/operator-grade visibility without native-bandwidth waste/i),
    ).not.toBeInTheDocument();
    expect(within(primaryWorkspaceNav).getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", {
        name: /operations/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", {
        name: /configuration/i,
      }),
    ).toBeInTheDocument();
  });
});
