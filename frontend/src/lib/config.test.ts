import { describe, expect, test } from "vitest";

import { mergeFrontendRuntimeEnv, resolveFrontendConfig } from "@/lib/config";

describe("resolveFrontendConfig", () => {
  test("derives local development defaults when Vite env vars are absent", () => {
    expect(
      resolveFrontendConfig(
        {
          VITE_API_BASE_URL: undefined,
          VITE_OIDC_AUTHORITY: undefined,
          VITE_PLATFORM_OIDC_AUTHORITY: undefined,
          VITE_OIDC_CLIENT_ID: undefined,
          VITE_OIDC_REDIRECT_URI: undefined,
          VITE_OIDC_POST_LOGOUT_REDIRECT_URI: undefined,
          VITE_OIDC_DISABLE_PKCE: undefined,
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
      platformOidcAuthority: "http://127.0.0.1:8080/realms/platform-admin",
      oidcClientId: "argus-frontend",
      oidcRedirectUri: "http://127.0.0.1:3000/auth/callback",
      oidcPostLogoutRedirectUri: "http://127.0.0.1:3000/signin",
      oidcDisablePkce: false,
    });
  });

  test("throws when production config is missing a required env var", () => {
    expect(() =>
      resolveFrontendConfig(
        {
          VITE_API_BASE_URL: undefined,
          VITE_OIDC_AUTHORITY: "http://127.0.0.1:8080/realms/argus-dev",
          VITE_PLATFORM_OIDC_AUTHORITY: "http://127.0.0.1:8080/realms/platform-admin",
          VITE_OIDC_CLIENT_ID: "argus-frontend",
          VITE_OIDC_REDIRECT_URI: "http://127.0.0.1:3000/auth/callback",
          VITE_OIDC_POST_LOGOUT_REDIRECT_URI: "http://127.0.0.1:3000/signin",
          VITE_OIDC_DISABLE_PKCE: undefined,
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

  test("prefers injected appliance runtime config over build-time env vars", () => {
    expect(
      mergeFrontendRuntimeEnv(
        {
          VITE_API_BASE_URL: "http://build-time:8000",
          VITE_OIDC_AUTHORITY: undefined,
          VITE_PLATFORM_OIDC_AUTHORITY: undefined,
          VITE_OIDC_CLIENT_ID: undefined,
          VITE_OIDC_REDIRECT_URI: undefined,
          VITE_OIDC_POST_LOGOUT_REDIRECT_URI: undefined,
          VITE_OIDC_DISABLE_PKCE: undefined,
        },
        {
          VITE_API_BASE_URL: "http://runtime:8000",
          VITE_OIDC_AUTHORITY: "http://runtime:8080/realms/argus-dev",
          VITE_PLATFORM_OIDC_AUTHORITY: "http://runtime:8080/realms/platform-admin",
          VITE_OIDC_CLIENT_ID: "argus-frontend",
          VITE_OIDC_REDIRECT_URI: "http://runtime:3000/auth/callback",
          VITE_OIDC_POST_LOGOUT_REDIRECT_URI: "http://runtime:3000/signin",
          VITE_OIDC_DISABLE_PKCE: "true",
        },
      ),
    ).toEqual({
      VITE_API_BASE_URL: "http://runtime:8000",
      VITE_OIDC_AUTHORITY: "http://runtime:8080/realms/argus-dev",
      VITE_PLATFORM_OIDC_AUTHORITY: "http://runtime:8080/realms/platform-admin",
      VITE_OIDC_CLIENT_ID: "argus-frontend",
      VITE_OIDC_REDIRECT_URI: "http://runtime:3000/auth/callback",
      VITE_OIDC_POST_LOGOUT_REDIRECT_URI: "http://runtime:3000/signin",
      VITE_OIDC_DISABLE_PKCE: "true",
    });
  });

  test("parses the portable LAN HTTP PKCE compatibility flag", () => {
    expect(
      resolveFrontendConfig(
        {
          VITE_API_BASE_URL: "http://192.168.8.199:8000",
          VITE_OIDC_AUTHORITY: "http://192.168.8.199:8080/realms/argus-dev",
          VITE_PLATFORM_OIDC_AUTHORITY:
            "http://192.168.8.199:8080/realms/platform-admin",
          VITE_OIDC_CLIENT_ID: "argus-frontend",
          VITE_OIDC_REDIRECT_URI: "http://192.168.8.199:3000/auth/callback",
          VITE_OIDC_POST_LOGOUT_REDIRECT_URI: "http://192.168.8.199:3000/signin",
          VITE_OIDC_DISABLE_PKCE: "true",
        },
        {
          origin: "http://192.168.8.199:3000",
          protocol: "http:",
          hostname: "192.168.8.199",
        },
        false,
      ),
    ).toEqual({
      apiBaseUrl: "http://192.168.8.199:8000",
      oidcAuthority: "http://192.168.8.199:8080/realms/argus-dev",
      platformOidcAuthority: "http://192.168.8.199:8080/realms/platform-admin",
      oidcClientId: "argus-frontend",
      oidcRedirectUri: "http://192.168.8.199:3000/auth/callback",
      oidcPostLogoutRedirectUri: "http://192.168.8.199:3000/signin",
      oidcDisablePkce: true,
    });
  });
});
