import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { FleetOpsBilling } from "@/pages/FleetOpsBilling";

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
  ],
  usage: {
    items: [
      {
        meter_key: "evidence_pack_export",
        label: "evidence pack export",
        quantity: "3",
      },
    ],
  },
}));

vi.mock("@/hooks/use-billing", () => ({
  useBillingMeters: () => ({
    data: billingMocks.meters,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/hooks/use-maritime", () => ({
  useMaritimeBillingUsage: () => ({
    data: billingMocks.usage,
    isLoading: false,
    isError: false,
  }),
}));

function renderWithProviders(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
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
    expect(screen.queryByText(/invoice|payment|accounting/i)).not.toBeInTheDocument();
  });
});
