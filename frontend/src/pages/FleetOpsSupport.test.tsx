import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { FleetOpsSupport } from "@/pages/FleetOpsSupport";

const supportMocks = vi.hoisted(() => ({
  onboardingCheckSiteIds: [] as Array<string | null | undefined>,
  bundles: [
    {
      id: "00000000-0000-4000-8000-000000000030",
      site_id: "00000000-0000-4000-8000-000000000020",
      include_logs: true,
      created_at: "2026-06-06T08:00:00Z",
    },
  ],
  diagnostics: {
    groups: {
      satellite_link: {
        label: "Satellite link",
        checks: ["link_state"],
      },
    },
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
  ],
}));

vi.mock("@/hooks/use-support", () => ({
  useSupportBundles: () => ({
    data: supportMocks.bundles,
    isLoading: false,
    isError: false,
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
  });

  test("Support page renders bundles, tunnel lifecycle, break-glass, and onboarding checks", async () => {
    renderWithProviders(<FleetOpsSupport />);

    expect(await screen.findByText(/Support bundles/i)).toBeInTheDocument();
    expect(screen.getByText(/Tunnel lifecycle/i)).toBeInTheDocument();
    expect(screen.getByText(/Break-glass/i)).toBeInTheDocument();
    expect(screen.getByText(/Onboarding checks/i)).toBeInTheDocument();
    expect(supportMocks.onboardingCheckSiteIds).toContain(
      "00000000-0000-4000-8000-000000000020",
    );
  });
});
