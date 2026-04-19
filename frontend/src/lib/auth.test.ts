import { describe, expect, test, vi } from "vitest";
import type { User } from "oidc-client-ts";

vi.mock("@/lib/config", () => ({
  frontendConfig: {
    apiBaseUrl: "http://127.0.0.1:8000",
    oidcAuthority: "http://127.0.0.1:8080/realms/argus-dev",
    oidcClientId: "argus-frontend",
    oidcRedirectUri: "http://127.0.0.1:3000/auth/callback",
    oidcPostLogoutRedirectUri: "http://127.0.0.1:3000/signin",
  },
}));

import { mapOidcUser } from "@/lib/auth";

function createUser(profile: Record<string, unknown>): User {
  return { profile } as unknown as User;
}

describe("mapOidcUser", () => {
  test("throws when the token is missing any recognized Argus role", () => {
    const user = createUser({
      sub: "user-1",
      iss: "http://127.0.0.1:8080/realms/argus-dev",
      realm_access: {
        roles: ["mystery-role"],
      },
    });

    expect(() => mapOidcUser(user)).toThrow(/missing a recognized argus role/i);
  });

  test("maps a recognized realm role into the session user", () => {
    const user = createUser({
      sub: "admin-1",
      email: "admin@argus.local",
      iss: "http://127.0.0.1:8080/realms/argus-dev",
      realm_access: {
        roles: ["admin"],
      },
    });

    expect(mapOidcUser(user)).toMatchObject({
      sub: "admin-1",
      email: "admin@argus.local",
      role: "admin",
      realm: "argus-dev",
      isSuperadmin: false,
    });
  });
});
