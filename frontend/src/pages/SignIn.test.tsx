import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

import { SignInPage } from "@/pages/SignIn";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("SignInPage", () => {
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

  test("starts the OIDC login flow when the user clicks sign in", async () => {
    const user = userEvent.setup();
    const signIn = vi.fn().mockResolvedValue(undefined);

    useAuthStore.setState({ signIn });

    render(<SignInPage />);
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(signIn).toHaveBeenCalledTimes(1);
  });
});
