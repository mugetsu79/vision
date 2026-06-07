import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) =>
    new Error(fallbackMessage),
}));

import { useLinkSiteSummaries } from "@/hooks/use-link";
import { apiClient } from "@/lib/api";
import { createTestQueryWrapper } from "@/test/query-test-utils";

describe("link hooks", () => {
  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: [],
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);
  });

  test("useLinkSiteSummaries reads the core link summary route", async () => {
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: [
        {
          site_id: "site-1",
          site_name: "North Gate",
          site_tz: "UTC",
          link_state: "healthy",
          active_connection: null,
          connection_count: 0,
          metered_connection_count: 0,
          latest_probe: null,
          queue_depth: {},
          queued_bytes: 0,
          budget: null,
          last_sync_at: null,
          passport_hash: "hash-1",
        },
      ],
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);

    const { result } = renderHook(() => useLinkSiteSummaries(), {
      wrapper: createTestQueryWrapper(),
    });

    await waitFor(() => expect(result.current.data).toHaveLength(1));
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/link/sites/summary");
  });
});
