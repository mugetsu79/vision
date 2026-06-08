import { act, render, screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
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

vi.mock("@/hooks/use-bootstrap", () => ({
  useBootstrapStatus: () => ({
    data: { first_run_required: false },
    isLoading: false,
  }),
}));

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuthStore } from "@/stores/auth-store";
import { TestMemoryRouter } from "@/test/router";

const initialAuthState = useAuthStore.getState();

describe("RequireAuth", () => {
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

  test("redirects anonymous users to the sign-in page", async () => {
    render(
      <TestMemoryRouter initialEntries={["/live"]}>
        <Routes>
          <Route path="/signin" element={<div>Sign in page</div>} />
          <Route
            path="/live"
            element={
              <RequireAuth>
                <div>Private dashboard</div>
              </RequireAuth>
            }
          />
        </Routes>
      </TestMemoryRouter>,
    );

    expect(await screen.findByText("Sign in page")).toBeInTheDocument();
  });
});
