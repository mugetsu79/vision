import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { LinkProbePanel } from "@/components/link/LinkProbePanel";

const linkProbeMocks = vi.hoisted(() => ({
  createProbe: vi.fn(),
  deleteProbe: vi.fn(),
  measureEdgeThroughput: vi.fn(),
  measureThroughput: vi.fn(),
  runProbeTarget: vi.fn(),
}));

vi.mock("@/hooks/use-link", () => ({
  useCreateLinkProbe: () => ({
    isPending: false,
    mutateAsync: linkProbeMocks.createProbe,
  }),
  useDeleteLinkProbe: () => ({
    isPending: false,
    mutateAsync: linkProbeMocks.deleteProbe,
  }),
  useMeasureLinkProbeTargetThroughput: ({
    origin,
  }: {
    origin?: "backend_synthetic" | "edge_agent";
  } = {}) => ({
    isPending: false,
    mutateAsync:
      origin === "edge_agent"
        ? linkProbeMocks.measureEdgeThroughput
        : linkProbeMocks.measureThroughput,
  }),
  useRunLinkProbeTarget: () => ({
    isPending: false,
    mutateAsync: linkProbeMocks.runProbeTarget,
  }),
}));

describe("LinkProbePanel", () => {
  beforeEach(() => {
    linkProbeMocks.createProbe.mockReset();
    linkProbeMocks.deleteProbe.mockReset();
    linkProbeMocks.measureEdgeThroughput.mockReset();
    linkProbeMocks.measureEdgeThroughput.mockResolvedValue({});
    linkProbeMocks.measureThroughput.mockReset();
    linkProbeMocks.runProbeTarget.mockReset();
  });

  test("queues edge-origin throughput measurement for edge-agent targets", async () => {
    const user = userEvent.setup();

    render(
      <LinkProbePanel
        siteId="site-1"
        connections={[
          {
            id: "connection-1",
            label: "Control path",
            metadata: {
              monitoring_targets: [
                {
                  address: "master.vezor.local",
                  id: "vezor-master-udp-reflector",
                  label: "Vezor Master reflector",
                  monitoring: {
                    enabled: true,
                    source_type: "edge_agent",
                  },
                  probe_type: "udp",
                  purpose: "vezor_control",
                },
              ],
            },
          },
        ]}
        probes={[]}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: /measure edge throughput vezor master reflector/i,
      }),
    );

    expect(linkProbeMocks.measureEdgeThroughput).toHaveBeenCalledWith(
      "vezor-master-udp-reflector",
    );
    expect(linkProbeMocks.measureThroughput).not.toHaveBeenCalled();
  });
});
