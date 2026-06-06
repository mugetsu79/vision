import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { workspaceNavItems } from "@/components/layout/workspace-nav";
import { FleetOps } from "@/pages/FleetOps";

const fleetOpsMocks = vi.hoisted(() => ({
  vessels: [
    {
      id: "00000000-0000-4000-8000-000000000010",
      name: "MV Resolute",
      site_id: "00000000-0000-4000-8000-000000000020",
      active: true,
      metadata: {
        link_state: "active connection degraded",
        evidence_queue: "4 pending exports",
      },
    },
  ],
  billingUsage: {
    items: [
      {
        meter_key: "evidence_pack_export",
        quantity: "1",
      },
    ],
  },
  supportDiagnostics: {
    label: "Support readiness",
    groups: [
      {
        id: "connectivity",
        label: "Connection readiness",
        status: "ready",
        checks: [{ key: "support_readiness", label: "Support path", status: "ready" }],
      },
    ],
  },
  useBillingUsage: vi.fn(),
  useMaritimeBillingUsage: vi.fn(),
}));

vi.mock("@/hooks/use-maritime", () => ({
  useMaritimeRuntime: () => ({
    data: { pack_id: "maritime-fleet", enabled: true },
    isLoading: false,
    isError: false,
  }),
  useMaritimeVessels: () => ({
    data: fleetOpsMocks.vessels,
    isLoading: false,
    isError: false,
  }),
  useMaritimeBillingUsage: fleetOpsMocks.useMaritimeBillingUsage,
}));

vi.mock("@/hooks/use-billing", () => ({
  useBillingUsage: fleetOpsMocks.useBillingUsage,
}));

vi.mock("@/hooks/use-fleet", () => ({
  useFleetExceptions: () => ({
    data: { items: [] },
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/hooks/use-support", () => ({
  useMaritimeSupportDiagnostics: () => ({
    data: fleetOpsMocks.supportDiagnostics,
    isLoading: false,
    isError: false,
  }),
}));

function renderWithProviders(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("FleetOps", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fleetOpsMocks.useBillingUsage.mockReturnValue({
      data: fleetOpsMocks.billingUsage,
      isLoading: false,
      isError: false,
    });
    fleetOpsMocks.useMaritimeBillingUsage.mockReturnValue({
      data: fleetOpsMocks.billingUsage,
      isLoading: false,
      isError: false,
    });
  });

  test("FleetOps overview renders vessels, link state, evidence queue, billing, and support status", async () => {
    renderWithProviders(<FleetOps />);

    expect(
      await screen.findByRole("heading", { name: /FleetOps/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/MV Resolute/i)).toBeInTheDocument();
    expect(
      screen.getByText(/active connection degraded|dark|recovering/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Evidence queue/i)).toBeInTheDocument();
    expect(
      screen.getByText(/moves over the selected connection/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/moves over satellite/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Current billable usage/i)).toBeInTheDocument();
    expect(fleetOpsMocks.useBillingUsage).toHaveBeenCalled();
    expect(fleetOpsMocks.useMaritimeBillingUsage).not.toHaveBeenCalled();
    expect(screen.getByText(/evidence pack export/i)).toBeInTheDocument();
    expect(screen.queryByText(/^vessel month$/i)).not.toBeInTheDocument();
    expect(screen.getByText("Support readiness")).toBeInTheDocument();
    expect(screen.getByText(/1 readiness group/i)).toBeInTheDocument();
  });

  test("FleetOps overview exposes operator workflow links", async () => {
    renderWithProviders(<FleetOps />);

    await screen.findByRole("heading", { name: /FleetOps/i });

    expectLink(/Add Vessel/i, "/fleetops/vessels");
    expectLink(/Review Evidence/i, "/fleetops/evidence");
    expectLink(/Open Billing/i, "/fleetops/billing");
    expectLink(/Open Support/i, "/fleetops/support");
    expectLink(/Open Onboarding/i, "/fleetops/onboarding");
  });

  test("traffic public space route is not present in workspace navigation", () => {
    const labels = workspaceNavItems.map((item) => item.label.toLowerCase());
    expect(labels.join(" ")).not.toContain("traffic");
    expect(labels.join(" ")).not.toContain("public space");
  });
});

function expectLink(name: RegExp, href: string) {
  expect(
    screen
      .getAllByRole("link", { name })
      .some((link) => link.getAttribute("href") === href),
  ).toBe(true);
}
