import { defineConfig } from "@playwright/test";

const baseURL = "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  workers: 1,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  webServer: {
    command: "corepack pnpm dev --host 127.0.0.1 --port 3000",
    url: `${baseURL}/signin`,
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    env: {
      VITE_API_BASE_URL: "http://127.0.0.1:8000",
      VITE_OIDC_AUTHORITY: "http://127.0.0.1:8080/realms/argus-dev",
      VITE_OIDC_CLIENT_ID: "argus-frontend",
      VITE_OIDC_REDIRECT_URI: `${baseURL}/auth/callback`,
      VITE_OIDC_POST_LOGOUT_REDIRECT_URI: `${baseURL}/signin`,
    },
  },
});
