import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/auth", () => ({
  mapOidcUser: vi.fn(),
  oidcManager: {
    getUser: vi.fn(),
    signinRedirect: vi.fn(),
    signinRedirectCallback: vi.fn(),
    signoutRedirect: vi.fn(),
  },
}));

import { RequireRole } from "@/components/auth/RequireRole";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("RequireRole", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  afterEach(() => {
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("renders an access denied state when the user lacks the required role", () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "token",
      user: {
        sub: "viewer-1",
        email: "viewer@argus.local",
        role: "viewer",
        realm: "argus-dev",
        isSuperadmin: false,
        tenantId: "tenant-1",
      },
    });

    render(
      <RequireRole role="admin">
        <div>Admin content</div>
      </RequireRole>,
    );

    expect(screen.getByText(/you do not have access to this page/i)).toBeInTheDocument();
    expect(screen.queryByText("Admin content")).not.toBeInTheDocument();
  });
});
