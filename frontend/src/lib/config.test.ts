import { describe, expect, test } from "vitest";

import { resolveFrontendConfig } from "@/lib/config";

describe("resolveFrontendConfig", () => {
  test("derives local development defaults when Vite env vars are absent", () => {
    expect(
      resolveFrontendConfig(
        {
          VITE_API_BASE_URL: undefined,
          VITE_OIDC_AUTHORITY: undefined,
          VITE_OIDC_CLIENT_ID: undefined,
          VITE_OIDC_REDIRECT_URI: undefined,
          VITE_OIDC_POST_LOGOUT_REDIRECT_URI: undefined,
        },
        {
          origin: "http://127.0.0.1:3000",
          protocol: "http:",
          hostname: "127.0.0.1",
        },
        true,
      ),
    ).toEqual({
      apiBaseUrl: "http://127.0.0.1:8000",
      oidcAuthority: "http://127.0.0.1:8080/realms/argus-dev",
      oidcClientId: "argus-frontend",
      oidcRedirectUri: "http://127.0.0.1:3000/auth/callback",
      oidcPostLogoutRedirectUri: "http://127.0.0.1:3000/signin",
    });
  });

  test("throws when production config is missing a required env var", () => {
    expect(() =>
      resolveFrontendConfig(
        {
          VITE_API_BASE_URL: undefined,
          VITE_OIDC_AUTHORITY: "http://127.0.0.1:8080/realms/argus-dev",
          VITE_OIDC_CLIENT_ID: "argus-frontend",
          VITE_OIDC_REDIRECT_URI: "http://127.0.0.1:3000/auth/callback",
          VITE_OIDC_POST_LOGOUT_REDIRECT_URI: "http://127.0.0.1:3000/signin",
        },
        {
          origin: "https://argus.example",
          protocol: "https:",
          hostname: "argus.example",
        },
        false,
      ),
    ).toThrow(/VITE_API_BASE_URL/);
  });
});
