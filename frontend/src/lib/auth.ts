import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";

import { frontendConfig } from "@/lib/config";

export type ArgusRole = "viewer" | "operator" | "admin" | "superadmin";

export interface SessionUser {
  sub: string;
  email: string | null;
  role: ArgusRole;
  realm: string;
  tenantId: string | null;
  isSuperadmin: boolean;
}

const rolePriority: ArgusRole[] = ["superadmin", "admin", "operator", "viewer"];

export const oidcManager = new UserManager({
  authority: frontendConfig.oidcAuthority,
  client_id: frontendConfig.oidcClientId,
  redirect_uri: frontendConfig.oidcRedirectUri,
  post_logout_redirect_uri: frontendConfig.oidcPostLogoutRedirectUri,
  response_type: "code",
  scope: "openid profile email",
  userStore: new WebStorageStateStore({ store: window.localStorage }),
});

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const [, payload] = token.split(".");

  if (!payload) {
    return null;
  }

  try {
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
    return JSON.parse(globalThis.atob(padded)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function getRealmRoles(user: User): string[] {
  const realmAccess = user.profile.realm_access as { roles?: unknown } | undefined;

  if (Array.isArray(realmAccess?.roles)) {
    return realmAccess.roles.filter((role): role is string => typeof role === "string");
  }

  if (!user.access_token) {
    return [];
  }

  const tokenClaims = decodeJwtPayload(user.access_token);
  const accessTokenRealmAccess = tokenClaims?.realm_access as { roles?: unknown } | undefined;

  return Array.isArray(accessTokenRealmAccess?.roles)
    ? accessTokenRealmAccess.roles.filter((role): role is string => typeof role === "string")
    : [];
}

export function mapOidcUser(user: User): SessionUser {
  const roles = getRealmRoles(user);
  const role = rolePriority.find((candidate) => roles.includes(candidate));
  const issuer = typeof user.profile.iss === "string" ? user.profile.iss : "";
  const realm = issuer.split("/").filter(Boolean).at(-1) ?? "argus-dev";

  if (!role) {
    throw new Error("OIDC user is missing a recognized Argus role.");
  }

  return {
    sub: String(user.profile.sub ?? ""),
    email: typeof user.profile.email === "string" ? user.profile.email : null,
    role,
    realm,
    tenantId:
      typeof user.profile.tenant_id === "string"
        ? user.profile.tenant_id
        : typeof user.profile.tenant === "string"
          ? user.profile.tenant
          : null,
    isSuperadmin: realm === "platform-admin" && role === "superadmin",
  };
}
