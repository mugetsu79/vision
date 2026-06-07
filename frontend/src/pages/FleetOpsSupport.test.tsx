import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { FleetOpsSupport } from "@/pages/FleetOpsSupport";

const supportMocks = vi.hoisted(() => ({
  onboardingCheckSiteIds: [] as Array<string | null | undefined>,
  createBundle: vi.fn(),
  createSession: vi.fn(),
  requestTunnel: vi.fn(),
  openBreakGlass: vi.fn(),
  bundles: [
    {
      id: "00000000-0000-4000-8000-000000000030",
      site_id: "00000000-0000-4000-8000-000000000020",
      include_logs: true,
      created_at: "2026-06-06T08:00:00Z",
    },
  ],
  diagnostics: {
    label: "Support readiness",
    groups: [
      {
        id: "connectivity",
        label: "Connectivity readiness",
        status: "attention",
        checks: [
          {
            key: "link_state",
            label: "Link state",
            status: "attention",
            source: "core link",
          },
        ],
        next_action: "Review active connection and queued evidence work.",
      },
    ],
  },
  onboardingChecks: {
    checks: [
      {
        key: "credential_rotation",
        label: "Credential rotation",
        status: "ready",
      },
    ],
  },
  vessels: [
    {
      id: "00000000-0000-4000-8000-000000000010",
      name: "MV Resolute",
      site_id: "00000000-0000-4000-8000-000000000020",
    },
    {
      id: "00000000-0000-4000-8000-000000000011",
      name: "MV Horizon",
      site_id: "00000000-0000-4000-8000-000000000021",
    },
  ],
}));

vi.mock("@/hooks/use-support", () => ({
  useSupportBundles: () => ({
    data: supportMocks.bundles,
    isLoading: false,
    isError: false,
  }),
  useCreateSupportBundle: () => ({
    mutateAsync: supportMocks.createBundle,
    isPending: false,
  }),
  useCreateSupportSession: () => ({
    mutateAsync: supportMocks.createSession,
    isPending: false,
  }),
  useRequestSupportTunnel: () => ({
    mutateAsync: supportMocks.requestTunnel,
    isPending: false,
  }),
  useOpenBreakGlass: () => ({
    mutateAsync: supportMocks.openBreakGlass,
    isPending: false,
  }),
  useMaritimeSupportDiagnostics: () => ({
    data: supportMocks.diagnostics,
    isLoading: false,
    isError: false,
  }),
  useSupportOnboardingChecks: (siteId?: string | null) => {
    supportMocks.onboardingCheckSiteIds.push(siteId);
    return {
      data: supportMocks.onboardingChecks,
      isLoading: false,
      isError: false,
    };
  },
}));

vi.mock("@/hooks/use-maritime", () => ({
  useMaritimeVessels: () => ({
    data: supportMocks.vessels,
    isLoading: false,
    isError: false,
  }),
}));

function renderWithProviders(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("FleetOpsSupport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    supportMocks.onboardingCheckSiteIds = [];
    supportMocks.createBundle.mockResolvedValue({
      id: "bundle-1",
    });
  });

  test("FleetOps support requires explicit vessel scope before actions run", async () => {
    const user = userEvent.setup();
    renderWithProviders(<FleetOpsSupport />);

    expect(
      await screen.findByRole("heading", { name: /^Support$/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/search fleetops vessel scope/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/choose a vessel or site to review support/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Support readiness/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /generate bundle/i }),
    ).not.toBeInTheDocument();

    await user.type(
      screen.getByLabelText(/search fleetops vessel scope/i),
      "horizon",
    );
    await user.click(screen.getByRole("button", { name: /mv horizon/i }));

    expect(screen.getByText(/Support readiness/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /generate bundle/i }));
    expect(supportMocks.createBundle).toHaveBeenCalledWith(
      expect.objectContaining({
        include_logs: true,
        pack_id: "maritime-fleet",
        site_id: "00000000-0000-4000-8000-000000000021",
      }),
    );
    expect(screen.getByText(/Tunnel lifecycle/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Break-glass/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/setup checks/i)).not.toBeInTheDocument();
    expect(supportMocks.onboardingCheckSiteIds).toEqual([]);
  });
});
