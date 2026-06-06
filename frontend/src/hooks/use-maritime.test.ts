import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type PropsWithChildren } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    GET: vi.fn(),
    POST: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) => new Error(fallbackMessage),
}));

import {
  useCreateMaritimeVessel,
  useDeactivateMaritimeVessel,
  useFleetOpsVesselDetail,
  useMaritimeRuntime,
  useUpdateMaritimeVessel,
} from "@/hooks/use-maritime";
import { apiClient } from "@/lib/api";
import { createTestQueryWrapper } from "@/test/query-test-utils";

describe("maritime hooks", () => {
  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.POST).mockReset();
    vi.mocked(apiClient.PATCH).mockReset();
    vi.mocked(apiClient.DELETE).mockReset();
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: { pack_id: "maritime-fleet", enabled: true },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);
    vi.mocked(apiClient.POST).mockResolvedValue({
      data: { id: "00000000-0000-4000-8000-000000000010" },
      error: undefined,
      response: new Response(null, { status: 201 }),
    } as Awaited<ReturnType<typeof apiClient.POST>>);
    vi.mocked(apiClient.PATCH).mockResolvedValue({
      data: { id: "00000000-0000-4000-8000-000000000010" },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.PATCH>>);
    vi.mocked(apiClient.DELETE).mockResolvedValue({
      data: undefined,
      error: undefined,
      response: new Response(null, { status: 204 }),
    } as Awaited<ReturnType<typeof apiClient.DELETE>>);
  });

  test("useMaritimeRuntime queries the maritime runtime endpoint", async () => {
    renderHook(() => useMaritimeRuntime(), {
      wrapper: createTestQueryWrapper(),
    });

    await waitFor(() => {
      expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/maritime/runtime");
    });
  });

  test("useFleetOpsVesselDetail composes vessel telemetry link evidence billing and support queries", async () => {
    const vesselId = "00000000-0000-4000-8000-000000000010";

    renderHook(() => useFleetOpsVesselDetail(vesselId), {
      wrapper: createTestQueryWrapper(),
    });

    await waitFor(() => {
      expect(apiClient.GET).toHaveBeenCalledWith(
        "/api/v1/maritime/vessels/{vessel_id}",
        { params: { path: { vessel_id: vesselId } } },
      );
      expect(apiClient.GET).toHaveBeenCalledWith(
        "/api/v1/maritime/vessels/{vessel_id}/telemetry",
        { params: { path: { vessel_id: vesselId } } },
      );
      expect(apiClient.GET).toHaveBeenCalledWith(
        "/api/v1/maritime/vessels/{vessel_id}/link-status",
        { params: { path: { vessel_id: vesselId } } },
      );
      expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/maritime/evidence-context");
      expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/maritime/billing/usage");
      expect(apiClient.GET).toHaveBeenCalledWith(
        "/api/v1/maritime/support/diagnostics",
      );
    });
  });

  test("useCreateMaritimeVessel posts create_site payload and refreshes vessel data", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const wrapper = ({ children }: PropsWithChildren) => (
      createElement(QueryClientProvider, { client: queryClient }, children)
    );
    const { result } = renderHook(() => useCreateMaritimeVessel(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        name: "MV Resolute",
        create_site: {
          name: "MV Resolute",
          description: "FleetOps vessel site for MV Resolute",
          tz: "UTC",
        },
        imo_number: "9876543",
        metadata: { home_port: "Rotterdam" },
      });
    });

    expect(apiClient.POST).toHaveBeenCalledWith("/api/v1/maritime/vessels", {
      body: {
        name: "MV Resolute",
        create_site: {
          name: "MV Resolute",
          description: "FleetOps vessel site for MV Resolute",
          tz: "UTC",
        },
        imo_number: "9876543",
        metadata: { home_port: "Rotterdam" },
      },
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["maritime", "vessels"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["sites"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["fleet"] });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["operations", "fleet"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["maritime", "vessels", "00000000-0000-4000-8000-000000000010"],
    });
  });

  test("useUpdateMaritimeVessel patches vessel details and refreshes detail data", async () => {
    const vesselId = "00000000-0000-4000-8000-000000000010";
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const wrapper = ({ children }: PropsWithChildren) =>
      createElement(QueryClientProvider, { client: queryClient }, children);
    const { result } = renderHook(() => useUpdateMaritimeVessel(vesselId), {
      wrapper,
    });

    await act(async () => {
      await result.current.mutateAsync({
        name: "MV Endurance",
        metadata: { home_port: "Rotterdam" },
      });
    });

    expect(apiClient.PATCH).toHaveBeenCalledWith(
      "/api/v1/maritime/vessels/{vessel_id}",
      {
        params: { path: { vessel_id: vesselId } },
        body: {
          name: "MV Endurance",
          metadata: { home_port: "Rotterdam" },
        },
      },
    );
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["maritime", "vessels"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["sites"] });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["maritime", "vessels", vesselId],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["fleet"] });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["operations", "fleet"],
    });
  });

  test("useDeactivateMaritimeVessel deletes vessel and refreshes fleet state", async () => {
    const vesselId = "00000000-0000-4000-8000-000000000010";
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const wrapper = ({ children }: PropsWithChildren) =>
      createElement(QueryClientProvider, { client: queryClient }, children);
    const { result } = renderHook(() => useDeactivateMaritimeVessel(), {
      wrapper,
    });

    await act(async () => {
      await result.current.mutateAsync(vesselId);
    });

    expect(apiClient.DELETE).toHaveBeenCalledWith(
      "/api/v1/maritime/vessels/{vessel_id}",
      { params: { path: { vessel_id: vesselId } } },
    );
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["maritime", "vessels"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["sites"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["fleet"] });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["operations", "fleet"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["maritime", "vessels", vesselId],
    });
  });
});
