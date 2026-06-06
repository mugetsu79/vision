import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    GET: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) => new Error(fallbackMessage),
}));

import {
  useBillingInvoiceRuns,
  useBillingMeters,
  useBillingUsage,
} from "@/hooks/use-billing";
import { apiClient } from "@/lib/api";
import { createTestQueryWrapper } from "@/test/query-test-utils";

describe("billing hooks", () => {
  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: { items: [] },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);
  });

  test("useBillingInvoiceRuns keeps core billing routes generic", async () => {
    renderHook(() => useBillingInvoiceRuns(), {
      wrapper: createTestQueryWrapper(),
    });

    await waitFor(() => {
      expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/billing/invoice-runs");
    });
  });

  test("useBillingUsage filters FleetOps items from the core billing route", async () => {
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: {
        items: [
          { meter_key: "vessel_month", pack_id: "maritime-fleet" },
          { meter_key: "storage_gb", pack_id: "other-pack" },
        ],
      },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);

    const { result } = renderHook(() => useBillingUsage(), {
      wrapper: createTestQueryWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual({
        items: [{ meter_key: "vessel_month", pack_id: "maritime-fleet" }],
      });
    });
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/billing/usage", {
      params: { query: { pack_id: "maritime-fleet" } },
    });
  });

  test("useBillingMeters filters FleetOps meters from the core billing route", async () => {
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: {
        items: [
          { meter_key: "managed_link_gb", pack_id: "maritime-fleet" },
          { meter_key: "generic_runtime_hour", pack_id: "other-pack" },
        ],
      },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);

    const { result } = renderHook(() => useBillingMeters(), {
      wrapper: createTestQueryWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual([
        { meter_key: "managed_link_gb", pack_id: "maritime-fleet" },
      ]);
    });
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/billing/meters", {
      params: { query: { pack_id: "maritime-fleet" } },
    });
  });
});
