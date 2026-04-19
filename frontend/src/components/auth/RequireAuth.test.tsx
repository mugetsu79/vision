import { act, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuthStore } from "@/stores/auth-store";

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
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route path="/signin" element={<div>Sign in page</div>} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <div>Private dashboard</div>
              </RequireAuth>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Sign in page")).toBeInTheDocument();
  });
});
