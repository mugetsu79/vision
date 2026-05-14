import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

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

vi.mock("@/hooks/use-bootstrap", () => ({
  useBootstrapStatus: () => ({
    data: { first_run_required: false },
    isLoading: false,
  }),
}));

describe("App", () => {
  test("renders the branded sign-in entry point for anonymous users", async () => {
    vi.resetModules();
    window.history.pushState({}, "", "/");

    const { default: App } = await import("@/App");
    render(<App />);

    expect(
      await screen.findByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("group", { name: /Vezor product lockup/i })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /omnisight for every live environment/i }),
    ).toBeInTheDocument();
  });
});
