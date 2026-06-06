import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    GET: vi.fn(),
  },
  toApiError: (_error: unknown, fallbackMessage: string) => new Error(fallbackMessage),
}));

import {
  useFleetOpsVesselDetail,
  useMaritimeRuntime,
} from "@/hooks/use-maritime";
import { apiClient } from "@/lib/api";
import { createTestQueryWrapper } from "@/test/query-test-utils";

describe("maritime hooks", () => {
  beforeEach(() => {
    vi.mocked(apiClient.GET).mockReset();
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: { pack_id: "maritime-fleet", enabled: true },
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);
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
});
