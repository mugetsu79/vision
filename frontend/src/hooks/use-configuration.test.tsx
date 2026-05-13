import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  useUpdateConfigurationProfile,
  useUpsertConfigurationBinding,
} from "@/hooks/use-configuration";
import { apiClient } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  apiClient: {
    PATCH: vi.fn(),
    POST: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) => new Error(fallbackMessage),
}));

describe("configuration mutations", () => {
  beforeEach(() => {
    vi.mocked(apiClient.PATCH).mockReset();
    vi.mocked(apiClient.POST).mockReset();
  });

  test("profile updates invalidate configuration and operations fleet queries", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
    });
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    vi.mocked(apiClient.PATCH).mockResolvedValue({
      data: { id: "profile-1" },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.PATCH>>);

    const { result } = renderHook(() => useUpdateConfigurationProfile(), {
      wrapper: wrapperFor(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({
        profileId: "profile-1",
        payload: { name: "Default operations mode" },
      });
    });

    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["configuration"] });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["operations", "fleet"],
    });
  });

  test("profile bindings invalidate configuration and operations fleet queries", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
    });
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    vi.mocked(apiClient.POST).mockResolvedValue({
      data: { id: "binding-1" },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.POST>>);

    const { result } = renderHook(() => useUpsertConfigurationBinding(), {
      wrapper: wrapperFor(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({
        kind: "operations_mode",
        scope: "camera",
        scope_key: "camera-1",
        profile_id: "profile-1",
      });
    });

    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["configuration"] });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["operations", "fleet"],
    });
  });
});

function wrapperFor(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}
