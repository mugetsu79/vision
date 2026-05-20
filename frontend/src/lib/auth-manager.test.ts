import { afterEach, describe, expect, test, vi } from "vitest";

describe("oidcManager", () => {
  afterEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.doUnmock("@/lib/config");
    vi.doUnmock("oidc-client-ts");
  });

  test("passes the LAN HTTP PKCE compatibility flag to oidc-client-ts", async () => {
    const userManager = vi.fn();
    const webStorageStateStore = vi.fn();

    vi.doMock("@/lib/config", () => ({
      frontendConfig: {
        apiBaseUrl: "http://192.168.8.199:8000",
        oidcAuthority: "http://192.168.8.199:8080/realms/argus-dev",
        oidcClientId: "argus-frontend",
        oidcRedirectUri: "http://192.168.8.199:3000/auth/callback",
        oidcPostLogoutRedirectUri: "http://192.168.8.199:3000/signin",
        oidcDisablePkce: true,
      },
    }));
    vi.doMock("oidc-client-ts", () => ({
      UserManager: userManager,
      WebStorageStateStore: webStorageStateStore,
    }));

    await import("@/lib/auth");

    expect(userManager).toHaveBeenCalledWith(
      expect.objectContaining({
        disablePKCE: true,
      }),
    );
  });
});
