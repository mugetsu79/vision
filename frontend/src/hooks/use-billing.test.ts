import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    GET: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) => new Error(fallbackMessage),
}));

import { useBillingInvoiceRuns } from "@/hooks/use-billing";
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
});
