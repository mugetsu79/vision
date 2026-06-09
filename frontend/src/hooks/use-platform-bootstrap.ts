import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { toApiError } from "@/lib/api";
import { frontendConfig } from "@/lib/config";

export interface PlatformBootstrapStatus {
  available: boolean;
  consumed_at: string | null;
}

export interface PlatformBootstrapComplete {
  bootstrap_token: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
}

export interface PlatformBootstrapCompleteResponse {
  email: string;
  realm: string;
  role: string;
  completed_at: string;
}

const platformBootstrapStatusKey = ["platform", "bootstrap", "status"] as const;

function platformBootstrapUrl(path: string) {
  return `${frontendConfig.apiBaseUrl.replace(/\/+$/u, "")}${path}`;
}

async function readJson<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw toApiError(body, fallbackMessage);
  }

  return body as T;
}

export function usePlatformBootstrapStatus() {
  return useQuery({
    queryKey: platformBootstrapStatusKey,
    queryFn: async () => {
      const response = await fetch(
        platformBootstrapUrl("/api/v1/platform/bootstrap/status"),
      );
      return readJson<PlatformBootstrapStatus>(
        response,
        "Failed to load platform bootstrap status.",
      );
    },
    staleTime: 10_000,
    retry: false,
  });
}

export function useCompletePlatformBootstrap() {
  const queryClient = useQueryClient();

  return useMutation<
    PlatformBootstrapCompleteResponse,
    Error,
    PlatformBootstrapComplete
  >({
    mutationFn: async (payload) => {
      const response = await fetch(
        platformBootstrapUrl("/api/v1/platform/bootstrap/complete"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      return readJson<PlatformBootstrapCompleteResponse>(
        response,
        "Failed to create the platform admin.",
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: platformBootstrapStatusKey,
      });
    },
  });
}
