import { act, render, screen, waitFor } from "@testing-library/react";
import React from "react";
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

import { AuthCallbackPage } from "@/pages/AuthCallback";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();
const routerFuture = {
  v7_relativeSplatPath: true,
  v7_startTransition: true,
} as const;

describe("AuthCallbackPage", () => {
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

  test("returns to sign-in when callback completion fails and only runs once in strict mode", async () => {
    const completeSignIn = vi.fn().mockRejectedValue(new Error("bad callback"));

    act(() => {
      useAuthStore.setState({
        ...initialAuthState,
        completeSignIn,
      });
    });

    render(
      <React.StrictMode>
        <MemoryRouter future={routerFuture} initialEntries={["/auth/callback"]}>
          <Routes>
            <Route path="/signin" element={<div>Sign in page</div>} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
          </Routes>
        </MemoryRouter>
      </React.StrictMode>,
    );

    expect(await screen.findByText("Sign in page")).toBeInTheDocument();
    await waitFor(() => expect(completeSignIn).toHaveBeenCalledTimes(1));
  });
});
