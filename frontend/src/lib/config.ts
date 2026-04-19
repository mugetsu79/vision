type FrontendEnvKey =
  | "VITE_API_BASE_URL"
  | "VITE_OIDC_AUTHORITY"
  | "VITE_OIDC_CLIENT_ID"
  | "VITE_OIDC_REDIRECT_URI"
  | "VITE_OIDC_POST_LOGOUT_REDIRECT_URI";

const runtimeEnv: Record<FrontendEnvKey, string | undefined> = {
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_OIDC_AUTHORITY: import.meta.env.VITE_OIDC_AUTHORITY,
  VITE_OIDC_CLIENT_ID: import.meta.env.VITE_OIDC_CLIENT_ID,
  VITE_OIDC_REDIRECT_URI: import.meta.env.VITE_OIDC_REDIRECT_URI,
  VITE_OIDC_POST_LOGOUT_REDIRECT_URI: import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI,
};

function requireEnv(key: FrontendEnvKey): string {
  const value = runtimeEnv[key];

  if (!value) {
    throw new Error(`Missing required frontend env var: ${key}`);
  }

  return value;
}

export const frontendConfig = {
  apiBaseUrl: requireEnv("VITE_API_BASE_URL"),
  oidcAuthority: requireEnv("VITE_OIDC_AUTHORITY"),
  oidcClientId: requireEnv("VITE_OIDC_CLIENT_ID"),
  oidcRedirectUri: requireEnv("VITE_OIDC_REDIRECT_URI"),
  oidcPostLogoutRedirectUri: requireEnv("VITE_OIDC_POST_LOGOUT_REDIRECT_URI"),
} as const;
