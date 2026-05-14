type FrontendEnvKey =
  | "VITE_API_BASE_URL"
  | "VITE_OIDC_AUTHORITY"
  | "VITE_OIDC_CLIENT_ID"
  | "VITE_OIDC_REDIRECT_URI"
  | "VITE_OIDC_POST_LOGOUT_REDIRECT_URI";

type FrontendRuntimeEnv = Readonly<Partial<Record<FrontendEnvKey, string | undefined>>>;

declare global {
  interface Window {
    __VEZOR_CONFIG__?: FrontendRuntimeEnv;
  }
}

interface FrontendLocationLike {
  origin: string;
  protocol: string;
  hostname: string;
}

const buildTimeEnv: FrontendRuntimeEnv = {
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_OIDC_AUTHORITY: import.meta.env.VITE_OIDC_AUTHORITY,
  VITE_OIDC_CLIENT_ID: import.meta.env.VITE_OIDC_CLIENT_ID,
  VITE_OIDC_REDIRECT_URI: import.meta.env.VITE_OIDC_REDIRECT_URI,
  VITE_OIDC_POST_LOGOUT_REDIRECT_URI: import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI,
};

const injectedRuntimeEnv =
  typeof window === "undefined" ? undefined : window.__VEZOR_CONFIG__;

export function mergeFrontendRuntimeEnv(
  buildEnv: FrontendRuntimeEnv,
  injectedEnv: FrontendRuntimeEnv | undefined,
): FrontendRuntimeEnv {
  return {
    VITE_API_BASE_URL: injectedEnv?.VITE_API_BASE_URL || buildEnv.VITE_API_BASE_URL,
    VITE_OIDC_AUTHORITY: injectedEnv?.VITE_OIDC_AUTHORITY || buildEnv.VITE_OIDC_AUTHORITY,
    VITE_OIDC_CLIENT_ID: injectedEnv?.VITE_OIDC_CLIENT_ID || buildEnv.VITE_OIDC_CLIENT_ID,
    VITE_OIDC_REDIRECT_URI:
      injectedEnv?.VITE_OIDC_REDIRECT_URI || buildEnv.VITE_OIDC_REDIRECT_URI,
    VITE_OIDC_POST_LOGOUT_REDIRECT_URI:
      injectedEnv?.VITE_OIDC_POST_LOGOUT_REDIRECT_URI ||
      buildEnv.VITE_OIDC_POST_LOGOUT_REDIRECT_URI,
  };
}

const runtimeEnv = mergeFrontendRuntimeEnv(buildTimeEnv, injectedRuntimeEnv);

const runtimeLocation =
  typeof window === "undefined"
    ? undefined
    : ({
        origin: window.location.origin,
        protocol: window.location.protocol,
        hostname: window.location.hostname,
      } satisfies FrontendLocationLike);

function deriveDevDefault(
  key: FrontendEnvKey,
  location: FrontendLocationLike | undefined,
): string | undefined {
  if (!location) {
    return undefined;
  }

  switch (key) {
    case "VITE_API_BASE_URL":
      return `${location.protocol}//${location.hostname}:8000`;
    case "VITE_OIDC_AUTHORITY":
      return `${location.protocol}//${location.hostname}:8080/realms/argus-dev`;
    case "VITE_OIDC_CLIENT_ID":
      return "argus-frontend";
    case "VITE_OIDC_REDIRECT_URI":
      return `${location.origin}/auth/callback`;
    case "VITE_OIDC_POST_LOGOUT_REDIRECT_URI":
      return `${location.origin}/signin`;
  }
}

function requireEnv(
  key: FrontendEnvKey,
  env: FrontendRuntimeEnv,
  location: FrontendLocationLike | undefined,
  isDev: boolean,
): string {
  const value = env[key] ?? (isDev ? deriveDevDefault(key, location) : undefined);

  if (!value) {
    throw new Error(`Missing required frontend env var: ${key}`);
  }

  return value;
}

export function resolveFrontendConfig(
  env: FrontendRuntimeEnv,
  location: FrontendLocationLike | undefined = runtimeLocation,
  isDev = import.meta.env.DEV,
) {
  return {
    apiBaseUrl: requireEnv("VITE_API_BASE_URL", env, location, isDev),
    oidcAuthority: requireEnv("VITE_OIDC_AUTHORITY", env, location, isDev),
    oidcClientId: requireEnv("VITE_OIDC_CLIENT_ID", env, location, isDev),
    oidcRedirectUri: requireEnv("VITE_OIDC_REDIRECT_URI", env, location, isDev),
    oidcPostLogoutRedirectUri: requireEnv(
      "VITE_OIDC_POST_LOGOUT_REDIRECT_URI",
      env,
      location,
      isDev,
    ),
  } as const;
}

export const frontendConfig = resolveFrontendConfig(runtimeEnv);
