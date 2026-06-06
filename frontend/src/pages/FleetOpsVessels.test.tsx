import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import type { MaritimeVesselCreateInput } from "@/hooks/use-maritime";
import type { components } from "@/lib/api.generated";
import { FleetOpsVessels } from "@/pages/FleetOpsVessels";

type SiteResponse = components["schemas"]["SiteResponse"];

const vesselPageMocks = vi.hoisted(() => ({
  vessels: [] as unknown[],
  sites: [] as SiteResponse[],
  createVessel: vi.fn<
    (payload: MaritimeVesselCreateInput) => Promise<{ id: string }>
  >(),
}));

vi.mock("@/hooks/use-maritime", () => ({
  useMaritimeVessels: () => ({
    data: vesselPageMocks.vessels,
    isLoading: false,
    isError: false,
  }),
  useCreateMaritimeVessel: () => ({
    mutateAsync: vesselPageMocks.createVessel,
    isPending: false,
  }),
}));

vi.mock("@/hooks/use-sites", () => ({
  useSites: () => ({
    data: vesselPageMocks.sites,
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

describe("FleetOpsVessels", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vesselPageMocks.vessels = [];
    vesselPageMocks.sites = [];
    vesselPageMocks.createVessel.mockResolvedValue({
      id: "00000000-0000-4000-8000-000000000010",
    });
  });

  test("empty vessels state opens a labelled add vessel dialog", async () => {
    const user = userEvent.setup();
    renderWithProviders(<FleetOpsVessels />);

    await user.click(screen.getAllByRole("button", { name: /add vessel/i })[0]);

    expect(screen.getByRole("dialog", { name: /add vessel/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/vessel name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/imo number/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create vessel/i }),
    ).toBeInTheDocument();
  });

  test("add vessel submits a create_site payload by default", async () => {
    const user = userEvent.setup();
    renderWithProviders(<FleetOpsVessels />);

    await user.click(screen.getAllByRole("button", { name: /add vessel/i })[0]);
    await user.type(screen.getByLabelText(/vessel name/i), "MV Resolute");
    await user.type(screen.getByLabelText(/imo number/i), "9876543");
    await user.type(screen.getByLabelText(/home port/i), "Rotterdam");
    await user.click(screen.getByRole("button", { name: /create vessel/i }));

    expect(vesselPageMocks.createVessel).toHaveBeenCalledWith({
      name: "MV Resolute",
      create_site: {
        name: "MV Resolute",
        description: "FleetOps vessel site for MV Resolute",
        tz: "UTC",
      },
      imo_number: "9876543",
      metadata: { home_port: "Rotterdam" },
    });
  });

  test("add vessel can bind an existing site without empty optional fields", async () => {
    vesselPageMocks.sites = [
      {
        id: "00000000-0000-4000-8000-000000000020",
        name: "Prepared berth site",
        tenant_id: "00000000-0000-4000-8000-000000000001",
        description: null,
        tz: "UTC",
        geo_point: null,
        created_at: "2026-06-06T00:00:00Z",
      },
    ];
    const user = userEvent.setup();
    renderWithProviders(<FleetOpsVessels />);

    await user.click(screen.getAllByRole("button", { name: /add vessel/i })[0]);
    await user.type(screen.getByLabelText(/vessel name/i), "MV Existing");
    await user.click(screen.getByLabelText(/bind existing site/i));
    await user.selectOptions(
      screen.getByRole("combobox", { name: /existing site/i }),
      "00000000-0000-4000-8000-000000000020",
    );
    await user.click(screen.getByRole("button", { name: /create vessel/i }));

    const payload = vesselPageMocks.createVessel.mock.calls[0]?.[0];
    expect(payload).toMatchObject({
      name: "MV Existing",
      site_id: "00000000-0000-4000-8000-000000000020",
    });
    expect(payload?.create_site).toBeUndefined();
    expect(payload?.imo_number).toBeUndefined();
    expect(payload?.metadata).toBeUndefined();
  });
});
