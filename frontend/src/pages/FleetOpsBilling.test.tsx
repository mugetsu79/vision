import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { FleetOpsBilling } from "@/pages/FleetOpsBilling";
import { TestMemoryRouter } from "@/test/router";

const billingMocks = vi.hoisted(() => ({
  meters: [
    {
      meter_key: "vessel_month",
      label: "vessel month",
      category: "base",
      unit_label: "month",
    },
    {
      meter_key: "camera_capacity_tier",
      label: "camera capacity tier",
      category: "capacity",
      unit_label: "tier",
    },
    {
      meter_key: "evidence_pack_export",
      label: "evidence pack export",
      category: "value",
      unit_label: "export",
    },
    {
      meter_key: "managed_link_gb",
      label: "managed link GB",
      category: "capacity",
      unit_label: "GB",
      pack_id: "maritime-fleet",
    },
  ],
  usage: {
    items: [
      {
        meter_key: "vessel_month",
        label: "vessel month",
        quantity: "1",
        pack_id: "maritime-fleet",
      },
      {
        meter_key: "evidence_pack_export",
        label: "evidence pack export",
        quantity: "3",
        pack_id: "maritime-fleet",
      },
    ],
  },
  invoiceRuns: [
    {
      id: "invoice-run-1",
      status: "draft",
      period_start: "2026-06-01",
      period_end: "2026-06-30",
    },
  ],
}));

vi.mock("@/hooks/use-billing", () => ({
  useBillingInvoiceRuns: () => ({
    data: billingMocks.invoiceRuns,
    isLoading: false,
    isError: false,
  }),
  useBillingMeters: () => ({
    data: billingMocks.meters,
    isLoading: false,
    isError: false,
  }),
  useBillingUsage: () => ({
    data: billingMocks.usage,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/hooks/use-maritime", () => ({
  useMaritimeBillingUsage: () => ({
    data: { items: [] },
    isLoading: false,
    isError: false,
  }),
}));

function renderWithProviders(ui: ReactElement) {
  return render(<TestMemoryRouter>{ui}</TestMemoryRouter>);
}

describe("FleetOpsBilling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("Billing page separates capacity guardrails, vessel month, and value meters", async () => {
    renderWithProviders(<FleetOpsBilling />);

    expect(await screen.findByText(/Value meters/i)).toBeInTheDocument();
    expect(screen.getByText(/vessel month/i)).toBeInTheDocument();
    expect(screen.getByText(/camera capacity tier/i)).toBeInTheDocument();
    expect(screen.getByText(/evidence pack export/i)).toBeInTheDocument();
    expect(screen.queryByText(/payment|accounting/i)).not.toBeInTheDocument();
  });

  test("FleetOps billing combines maritime rollups with core meters", async () => {
    renderWithProviders(<FleetOpsBilling />);

    expect(await screen.findByText(/vessel month/i)).toBeInTheDocument();
    expect(screen.getAllByText(/managed link GB/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/2 active usage records/i)).toBeInTheDocument();
    expect(screen.getByText(/invoice runs/i)).toBeInTheDocument();
  });
});
