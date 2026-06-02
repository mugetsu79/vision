import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  useConfigurationBindings,
  useConfigurationProfileImpact,
  useDeleteConfigurationBinding,
  useDeleteConfigurationProfile,
  useUpdateConfigurationProfile,
  useUpsertConfigurationBinding,
} from "@/hooks/use-configuration";
import { apiClient } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  apiClient: {
    DELETE: vi.fn(),
    GET: vi.fn(),
    PATCH: vi.fn(),
    POST: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) => new Error(fallbackMessage),
}));

describe("configuration mutations", () => {
  beforeEach(() => {
    vi.mocked(apiClient.DELETE).mockReset();
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.PATCH).mockReset();
    vi.mocked(apiClient.POST).mockReset();
  });

  test("loads configuration bindings by kind", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
    });
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: {
        bindings: [
          {
            id: "binding-1",
            kind: "operations_mode",
            scope: "camera",
            scope_key: "camera-1",
            profile_id: "profile-1",
            created_at: "2026-06-01T10:00:00Z",
            updated_at: "2026-06-01T10:00:00Z",
          },
        ],
      },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);

    const { result } = renderHook(
      () => useConfigurationBindings("operations_mode"),
      { wrapper: wrapperFor(queryClient) },
    );

    await waitFor(() => expect(result.current.data).toHaveLength(1));

    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/configuration/bindings", {
      params: { query: { kind: "operations_mode" } },
    });
  });

  test("loads profile impact for delete confirmation", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
    });
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: {
        profile_id: "profile-1",
        kind: "operations_mode",
        is_default: true,
        direct_bindings: [],
        affected_targets_count: 4,
        requires_replacement_default: true,
        secret_state: {},
      },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);

    const { result } = renderHook(
      () => useConfigurationProfileImpact("profile-1"),
      { wrapper: wrapperFor(queryClient) },
    );

    await waitFor(() => expect(result.current.data?.affected_targets_count).toBe(4));

    expect(apiClient.GET).toHaveBeenCalledWith(
      "/api/v1/configuration/profiles/{profile_id}/impact",
      { params: { path: { profile_id: "profile-1" } } },
    );
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

  test("binding deletes invalidate configuration and operations fleet queries", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
    });
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    vi.mocked(apiClient.DELETE).mockResolvedValue({
      data: undefined,
      error: undefined,
      response: new Response(null, { status: 204 }),
    } as Awaited<ReturnType<typeof apiClient.DELETE>>);

    const { result } = renderHook(() => useDeleteConfigurationBinding(), {
      wrapper: wrapperFor(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync("binding-1");
    });

    expect(apiClient.DELETE).toHaveBeenCalledWith(
      "/api/v1/configuration/bindings/{binding_id}",
      { params: { path: { binding_id: "binding-1" } } },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["configuration"] });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["operations", "fleet"],
    });
  });

  test("profile deletes can send a replacement default", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
    });
    vi.mocked(apiClient.DELETE).mockResolvedValue({
      data: undefined,
      error: undefined,
      response: new Response(null, { status: 204 }),
    } as Awaited<ReturnType<typeof apiClient.DELETE>>);

    const { result } = renderHook(() => useDeleteConfigurationProfile(), {
      wrapper: wrapperFor(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({
        profileId: "profile-1",
        replacementDefaultProfileId: "profile-2",
      });
    });

    expect(apiClient.DELETE).toHaveBeenCalledWith(
      "/api/v1/configuration/profiles/{profile_id}",
      {
        params: { path: { profile_id: "profile-1" } },
        body: { replacement_default_profile_id: "profile-2" },
      },
    );
  });
});

function wrapperFor(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}
