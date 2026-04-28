import { describe, expect, test, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiClient: {
    GET: vi.fn(async () => ({
      data: {
        mode: "manual_dev",
        generated_at: "2026-04-28T07:00:00Z",
        summary: {
          desired_workers: 1,
          running_workers: 0,
          stale_nodes: 0,
          offline_nodes: 0,
          native_unavailable_cameras: 0,
        },
        nodes: [],
        camera_workers: [],
        delivery_diagnostics: [],
      },
      error: undefined,
    })),
    POST: vi.fn(async () => ({
      data: {
        edge_node_id: "00000000-0000-0000-0000-000000000123",
        api_key: "edge_secret_once",
        nats_nkey_seed: "nats_secret_once",
        subjects: [],
        mediamtx_url: "http://mediamtx:9997",
        overlay_network_hints: {},
        dev_compose_command: "docker compose -f infra/docker-compose.edge.yml up inference-worker",
        supervisor_environment: {},
      },
      error: undefined,
    })),
  },
  toApiError: (error: unknown, fallback: string) => new Error(fallback),
}));

import { apiClient } from "@/lib/api";
import {
  createBootstrapMutationOptions,
  fleetOverviewQueryOptions,
} from "@/hooks/use-operations";

describe("use-operations query helpers", () => {
  test("builds the fleet overview query", async () => {
    const options = fleetOverviewQueryOptions();
    const queryFn = options.queryFn;
    if (typeof queryFn !== "function") {
      throw new Error("Expected fleet overview queryFn.");
    }
    const data = await queryFn({} as never);

    expect(options.queryKey).toEqual(["operations", "fleet"]);
    expect(data.mode).toBe("manual_dev");
    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/operations/fleet");
  });

  test("builds the bootstrap mutation", async () => {
    const options = createBootstrapMutationOptions();
    const data = await options.mutationFn({
      site_id: "00000000-0000-0000-0000-000000000001",
      hostname: "edge-kit-01",
      version: "0.1.0",
    });

    expect(data.api_key).toBe("edge_secret_once");
    expect(apiClient.POST).toHaveBeenCalledWith("/api/v1/operations/bootstrap", {
      body: {
        site_id: "00000000-0000-0000-0000-000000000001",
        hostname: "edge-kit-01",
        version: "0.1.0",
      },
    });
  });
});
