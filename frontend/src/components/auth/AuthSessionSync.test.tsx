import { act, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

let userLoadedHandler: ((user: unknown) => void) | undefined;
let accessTokenExpiredHandler: (() => void) | undefined;
let silentRenewErrorHandler: (() => void) | undefined;
let userSignedOutHandler: (() => void) | undefined;

vi.mock("@/lib/auth", () => ({
  mapOidcUser: vi.fn((user: { profile?: Record<string, unknown> }) => ({
    sub: String(user.profile?.sub ?? ""),
    email: typeof user.profile?.email === "string" ? user.profile.email : null,
    role: "admin",
    realm: "argus-dev",
    tenantId: "tenant-1",
    isSuperadmin: false,
  })),
  oidcManager: {
    getUser: vi.fn(),
    signinRedirect: vi.fn(),
    signinRedirectCallback: vi.fn(),
    signoutRedirect: vi.fn(),
    events: {
      addUserLoaded: vi.fn((callback: (user: unknown) => void) => {
        userLoadedHandler = callback;
        return vi.fn();
      }),
      addAccessTokenExpired: vi.fn((callback: () => void) => {
        accessTokenExpiredHandler = callback;
        return vi.fn();
      }),
      addSilentRenewError: vi.fn((callback: () => void) => {
        silentRenewErrorHandler = callback;
        return vi.fn();
      }),
      addUserSignedOut: vi.fn((callback: () => void) => {
        userSignedOutHandler = callback;
        return vi.fn();
      }),
    },
  },
}));

import { oidcManager } from "@/lib/auth";
import { AuthSessionSync } from "@/components/auth/AuthSessionSync";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("AuthSessionSync", () => {
  beforeEach(() => {
    userLoadedHandler = undefined;
    accessTokenExpiredHandler = undefined;
    silentRenewErrorHandler = undefined;
    userSignedOutHandler = undefined;
    vi.mocked(oidcManager.getUser).mockResolvedValue(null);

    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("hydrates the auth store with renewed users loaded by oidc-client-ts", async () => {
    render(<AuthSessionSync />);

    await waitFor(() =>
      expect(vi.mocked(oidcManager.events.addUserLoaded)).toHaveBeenCalled(),
    );

    act(() => {
      userLoadedHandler?.({
        access_token: "fresh-token",
        expired: false,
        profile: {
          sub: "admin-1",
          email: "admin@argus.local",
          iss: "http://127.0.0.1:8080/realms/argus-dev",
        },
      });
    });

    expect(useAuthStore.getState().status).toBe("authenticated");
    expect(useAuthStore.getState().accessToken).toBe("fresh-token");
  });

  test("restores the current oidc session when the access token expires or renew errors", async () => {
    vi.mocked(oidcManager.getUser).mockResolvedValue({
      access_token: "refreshed-token",
      expired: false,
      profile: {
        sub: "admin-1",
        email: "admin@argus.local",
        iss: "http://127.0.0.1:8080/realms/argus-dev",
      },
    } as Awaited<ReturnType<typeof oidcManager.getUser>>);

    render(<AuthSessionSync />);

    await waitFor(() => expect(useAuthStore.getState().accessToken).toBe("refreshed-token"));

    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "stale-token",
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

    act(() => {
      accessTokenExpiredHandler?.();
      silentRenewErrorHandler?.();
    });

    await waitFor(() => expect(useAuthStore.getState().accessToken).toBe("refreshed-token"));

    act(() => {
      userSignedOutHandler?.();
    });

    expect(useAuthStore.getState().status).toBe("anonymous");
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
