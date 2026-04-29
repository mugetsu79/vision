import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { productBrand } from "@/brand/product";

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

  test("renders the shared product lockup and a single primary sign-in action", () => {
    render(<SignInPage />);

    expect(
      screen.getByRole("group", { name: new RegExp(`${productBrand.name} product lockup`, "i") }),
    ).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /vezor 2d logo/i })).toHaveAttribute(
      "src",
      "/brand/2d_logo_no_ring.png",
    );
    expect(
      screen.getByRole("heading", { name: /omnisight for every live environment/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/connects scenes, models, events, evidence, and edge operations/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("signin-spatial-stage")).toBeInTheDocument();
    expect(screen.getByTestId("signin-orbit-auth")).toBeInTheDocument();
    expect(screen.queryByTestId("omnisight-empty-surface")).not.toBeInTheDocument();
    expect(screen.getByTestId("omnisight-field")).toHaveClass("omnisight-field--entry");
    expect(
      screen.getByText(
        new RegExp(`use your ${productBrand.name} identity provider account to continue\\.`, "i"),
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
  });
});
