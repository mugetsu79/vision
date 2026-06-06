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
        link_state: "satellite degraded",
        evidence_queue: "4 pending exports",
      },
    },
  ],
  billingUsage: {
    items: [
      {
        meter_key: "vessel_month",
        label: "vessel month",
        quantity: "1",
      },
    ],
  },
  supportDiagnostics: {
    groups: {
      support_roles: {
        label: "Open support sessions",
        checks: ["support_readiness"],
      },
    },
  },
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
  useMaritimeBillingUsage: () => ({
    data: fleetOpsMocks.billingUsage,
    isLoading: false,
    isError: false,
  }),
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
  });

  test("FleetOps overview renders vessels, link state, evidence queue, billing, and support status", async () => {
    renderWithProviders(<FleetOps />);

    expect(
      await screen.findByRole("heading", { name: /FleetOps/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/MV Resolute/i)).toBeInTheDocument();
    expect(
      screen.getByText(/port wifi|satellite degraded|dark|recovering/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Evidence queue/i)).toBeInTheDocument();
    expect(screen.getByText(/Current billable usage/i)).toBeInTheDocument();
    expect(screen.getByText(/Open support sessions/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Onboarding/i })).toHaveAttribute(
      "href",
      "/fleetops/onboarding",
    );
  });

  test("traffic public space route is not present in workspace navigation", () => {
    const labels = workspaceNavItems.map((item) => item.label.toLowerCase());
    expect(labels.join(" ")).not.toContain("traffic");
    expect(labels.join(" ")).not.toContain("public space");
  });
});
