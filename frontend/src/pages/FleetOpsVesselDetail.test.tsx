import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
        site_id: "00000000-0000-4000-8000-000000000020",
        metadata: {
          templates: ["Gangway access", "Cargo hatch watch"],
        } as Record<string, unknown>,
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
        budget: {
          monthly_bytes: 1000000000,
          bulk_daily_bytes: 250000000,
        },
        latest_probe: {
          latency_ms: 42,
          throughput_mbps: 120,
          packet_loss_percent: 0.1,
          source: "fiber",
        },
      },
      isLoading: false,
      isError: false,
    },
    coreLinkStatus: {
      data: {
        active_connection: {
          id: "connection-1",
          label: "Fiber berth",
          transport_kind: "fiber",
          status: "online",
          availability_scope: "local",
          metered: false,
        },
      },
      isLoading: false,
      isError: false,
    },
    linkConnections: [
      {
        id: "connection-1",
        label: "Fiber berth",
        transport_kind: "fiber",
        status: "online",
        availability_scope: "local",
        metered: false,
      },
    ],
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
  updateVessel: vi.fn(),
  deactivateVessel: vi.fn(),
}));

vi.mock("@/hooks/use-maritime", () => ({
  useFleetOpsVesselDetail: () => vesselDetailMocks.detail,
  useUpdateMaritimeVessel: () => ({
    mutateAsync: vesselDetailMocks.updateVessel,
    isPending: false,
  }),
  useDeactivateMaritimeVessel: () => ({
    mutateAsync: vesselDetailMocks.deactivateVessel,
    isPending: false,
  }),
}));

vi.mock("@/hooks/use-link", () => ({
  useLinkSiteStatus: () => vesselDetailMocks.detail.coreLinkStatus,
  useLinkConnections: () => ({
    data: vesselDetailMocks.detail.linkConnections,
    isLoading: false,
    isError: false,
  }),
}));

function renderWithProviders(ui: ReactElement) {
  return render(
    <MemoryRouter
      future={{
        v7_relativeSplatPath: true,
        v7_startTransition: true,
      }}
    >
      {ui}
    </MemoryRouter>,
  );
}

describe("FleetOpsVesselDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vesselDetailMocks.detail.vessel.data = {
      id: "00000000-0000-4000-8000-000000000010",
      name: "MV Resolute",
      site_id: "00000000-0000-4000-8000-000000000020",
      metadata: {
        templates: ["Gangway access", "Cargo hatch watch"],
      },
    };
    vesselDetailMocks.updateVessel.mockResolvedValue({
      id: "00000000-0000-4000-8000-000000000010",
      name: "MV Endurance",
    });
    vesselDetailMocks.deactivateVessel.mockResolvedValue(
      "00000000-0000-4000-8000-000000000010",
    );
  });

  test("Vessel detail renders voyage timeline, templates, telemetry, and evidence context", async () => {
    renderWithProviders(<FleetOpsVesselDetail />);

    expect(await screen.findByText(/Voyage timeline/i)).toBeInTheDocument();
    expect(screen.getByText(/Gangway access/i)).toBeInTheDocument();
    expect(screen.getByText(/Latest AIS/i)).toBeInTheDocument();
    expect(screen.getByText(/Evidence context/i)).toBeInTheDocument();
  });

  test("Vessel detail links to core link performance for its site", async () => {
    renderWithProviders(<FleetOpsVesselDetail />);

    expect(
      await screen.findByRole("link", { name: /open link performance/i }),
    ).toHaveAttribute(
      "href",
      "/links?site=00000000-0000-4000-8000-000000000020",
    );
  });

  test("Vessel detail renders link connections, budget, probes, and queue depth", async () => {
    renderWithProviders(<FleetOpsVesselDetail />);

    expect(await screen.findByText(/Active connection/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Fiber berth/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Satellite/i)).toBeInTheDocument();
    expect(screen.getByText(/LTE/i)).toBeInTheDocument();
    expect(screen.getByText(/5G/i)).toBeInTheDocument();
    expect(screen.getByText(/Wi-Fi/i)).toBeInTheDocument();
    expect(screen.getByText(/Ethernet/i)).toBeInTheDocument();
    expect(screen.getByText(/Budget/i)).toBeInTheDocument();
    expect(screen.getByText(/Latest probe/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Evidence queue/i).length).toBeGreaterThan(0);
  });

  test("edit vessel action submits an update payload", async () => {
    const user = userEvent.setup();
    renderWithProviders(<FleetOpsVesselDetail />);

    await user.click(screen.getByRole("button", { name: /edit vessel/i }));
    await user.clear(screen.getByLabelText(/vessel name/i));
    await user.type(screen.getByLabelText(/vessel name/i), "MV Endurance");
    await user.type(screen.getByLabelText(/home port/i), "Rotterdam");
    await user.click(screen.getByRole("button", { name: /save vessel/i }));

    expect(vesselDetailMocks.updateVessel).toHaveBeenCalledWith({
      name: "MV Endurance",
      metadata: {
        templates: ["Gangway access", "Cargo hatch watch"],
        home_port: "Rotterdam",
      },
    });
  });

  test("deactivate vessel action calls the deactivate mutation", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithProviders(<FleetOpsVesselDetail />);

    await user.click(screen.getByRole("button", { name: /deactivate vessel/i }));

    expect(confirmSpy).toHaveBeenCalledWith("Deactivate MV Resolute?");
    expect(vesselDetailMocks.deactivateVessel).toHaveBeenCalledWith(
      "00000000-0000-4000-8000-000000000010",
    );
  });

  test("edit vessel action can clear the final metadata field", async () => {
    vesselDetailMocks.detail.vessel.data.metadata = {
      home_port: "Rotterdam",
    };
    const user = userEvent.setup();
    renderWithProviders(<FleetOpsVesselDetail />);

    await user.click(screen.getByRole("button", { name: /edit vessel/i }));
    await user.clear(screen.getByLabelText(/home port/i));
    await user.click(screen.getByRole("button", { name: /save vessel/i }));

    expect(vesselDetailMocks.updateVessel).toHaveBeenCalledWith(
      expect.objectContaining({
        metadata: {},
      }),
    );
  });

  test("deactivate vessel action reports mutation failures", async () => {
    vesselDetailMocks.deactivateVessel.mockRejectedValueOnce(
      new Error("Cannot deactivate active vessel."),
    );
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithProviders(<FleetOpsVesselDetail />);

    await user.click(screen.getByRole("button", { name: /deactivate vessel/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cannot deactivate active vessel.",
    );
  });
});
