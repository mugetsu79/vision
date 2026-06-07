import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { FleetOpsEvidence } from "@/pages/FleetOpsEvidence";

const evidenceMocks = vi.hoisted(() => ({
  queueSiteIds: [] as Array<string | null | undefined>,
  statusSiteIds: [] as Array<string | null | undefined>,
  retryContexts: [] as Array<{
    siteId?: string | null;
    vesselId?: string | null;
  }>,
  vessels: [
    {
      id: "00000000-0000-4000-8000-000000000010",
      name: "MV Resolute",
      site_id: "00000000-0000-4000-8000-000000000020",
    },
  ],
  evidenceContext: {
    vessel_name: "MV Resolute",
    port_name: "Rotterdam",
    resolution_source: "voyage_window",
  },
  linkStatus: {
    link_state: "degraded",
    passport_hash: "abc12345",
    queue_depth: { evidence: 2, bulk: 1 },
  },
  queue: [
    {
      id: "queue-1",
      priority_lane: "evidence",
      status: "paused",
      byte_size: 125000000,
      source_object_type: "evidence_artifact",
    },
  ],
  retryQueueItem: vi.fn(),
}));

vi.mock("@/hooks/use-maritime", () => ({
  useMaritimeEvidenceContext: () => ({
    data: evidenceMocks.evidenceContext,
    isLoading: false,
    isError: false,
  }),
  useMaritimeVessels: () => ({
    data: evidenceMocks.vessels,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/hooks/use-link", () => ({
  useLinkSiteQueue: (siteId?: string | null) => {
    evidenceMocks.queueSiteIds.push(siteId);
    return {
      data: siteId ? evidenceMocks.queue : [],
      isLoading: false,
      isError: false,
    };
  },
  useLinkSiteStatus: (siteId?: string | null) => {
    evidenceMocks.statusSiteIds.push(siteId);
    return {
      data: siteId ? evidenceMocks.linkStatus : null,
      isLoading: false,
      isError: false,
    };
  },
  useRetryLinkQueueItem: (context: {
    siteId?: string | null;
    vesselId?: string | null;
  }) => {
    evidenceMocks.retryContexts.push(context);
    return {
      mutateAsync: evidenceMocks.retryQueueItem,
      isPending: false,
    };
  },
}));

function renderWithProviders(ui: ReactElement) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

describe("FleetOpsEvidence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    evidenceMocks.queueSiteIds = [];
    evidenceMocks.statusSiteIds = [];
    evidenceMocks.retryContexts = [];
  });

  test("FleetOps evidence waits for explicit vessel scope before showing queue work", async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<FleetOpsEvidence />));

    expect(
      await screen.findByRole("heading", { name: /Evidence/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/search fleetops vessel scope/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/choose a vessel or site to review evidence/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/pending/i)).not.toBeInTheDocument();
    expect(evidenceMocks.queueSiteIds.at(-1)).toBeNull();
    expect(evidenceMocks.statusSiteIds.at(-1)).toBeNull();
    expect(evidenceMocks.retryContexts.at(-1)).toMatchObject({
      siteId: null,
      vesselId: null,
    });

    await user.click(screen.getByRole("button", { name: /mv resolute/i }));

    expect(screen.getByText(/pending/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(evidenceMocks.retryQueueItem).toHaveBeenCalledWith("queue-1");
    expect(screen.getByText(/link posture/i)).toBeInTheDocument();
  });
});
