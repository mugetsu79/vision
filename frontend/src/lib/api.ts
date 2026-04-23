import createClient from "openapi-fetch";

import { oidcManager } from "@/lib/auth";
import type { paths } from "@/lib/api.generated";
import { frontendConfig } from "@/lib/config";
import { useAuthStore } from "@/stores/auth-store";

async function resolveAccessToken() {
  try {
    const user = await oidcManager.getUser();

    if (user?.access_token && !user.expired) {
      return user.access_token;
    }
  } catch {
    // Fall back to the in-memory auth store when the OIDC store is unavailable.
  }

  return useAuthStore.getState().accessToken;
}

export const apiClient = createClient<paths>({
  baseUrl: frontendConfig.apiBaseUrl,
  fetch: async (request: Request) => {
    const accessToken = await resolveAccessToken();
    const headers = new Headers(request.headers);

    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }

    return fetch(new Request(request, { headers }));
  },
});

export function toApiError(error: unknown, fallbackMessage: string): Error {
  if (error instanceof Error) {
    return error;
  }

  if (typeof error === "string" && error.trim().length > 0) {
    return new Error(error);
  }

  if (typeof error === "object" && error !== null) {
    const maybeError = error as {
      message?: unknown;
      detail?: unknown;
    };

    if (typeof maybeError.detail === "string" && maybeError.detail.trim().length > 0) {
      return new Error(maybeError.detail);
    }

    if (typeof maybeError.message === "string" && maybeError.message.trim().length > 0) {
      return new Error(maybeError.message);
    }
  }

  return new Error(fallbackMessage);
}
