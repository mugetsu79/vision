import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { FleetOpsVesselDetail } from "@/pages/FleetOpsVesselDetail";

const vesselDetailMocks = vi.hoisted(() => ({
  detail: {
    vessel: {
      data: {
        id: "00000000-0000-4000-8000-000000000010",
        name: "MV Resolute",
        metadata: {
          templates: ["Gangway access", "Cargo hatch watch"],
        },
      },
      isLoading: false,
      isError: false,
    },
    telemetry: {
      data: {
        latest_ais_position: {
          latitude: 46.12,
          longitude: 8.94,
          speed_over_ground: 11.4,
          navigational_status: "under way",
        },
      },
      isLoading: false,
      isError: false,
    },
    linkStatus: {
      data: {
        link_state: "recovering",
        queue_depth: { evidence: 2 },
      },
      isLoading: false,
      isError: false,
    },
    evidenceContext: {
      data: {
        vessel_name: "MV Resolute",
        port_name: "Rotterdam",
        resolution_source: "voyage_window",
      },
      isLoading: false,
      isError: false,
    },
    billingUsage: {
      data: { items: [] },
      isLoading: false,
      isError: false,
    },
    supportDiagnostics: {
      data: { groups: {} },
      isLoading: false,
      isError: false,
    },
  },
}));

vi.mock("@/hooks/use-maritime", () => ({
  useFleetOpsVesselDetail: () => vesselDetailMocks.detail,
}));

function renderWithProviders(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("FleetOpsVesselDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("Vessel detail renders voyage timeline, templates, telemetry, and evidence context", async () => {
    renderWithProviders(<FleetOpsVesselDetail />);

    expect(await screen.findByText(/Voyage timeline/i)).toBeInTheDocument();
    expect(screen.getByText(/Gangway access/i)).toBeInTheDocument();
    expect(screen.getByText(/Latest AIS/i)).toBeInTheDocument();
    expect(screen.getByText(/Evidence context/i)).toBeInTheDocument();
  });
});
