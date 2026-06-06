import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { FleetOpsOnboarding } from "@/pages/FleetOpsOnboarding";

const onboardingMocks = vi.hoisted(() => ({
  onboardingCheckSiteIds: [] as Array<string | null | undefined>,
  diagnostics: {
    groups: {
      support_roles: {
        label: "Shipboard support roles",
        checks: ["handoff_ready"],
      },
    },
  },
  onboardingChecks: {
    checks: [
      {
        key: "satellite_fallback",
        label: "Satellite fallback",
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
  useMaritimeSupportDiagnostics: () => ({
    data: onboardingMocks.diagnostics,
    isLoading: false,
    isError: false,
  }),
  useSupportOnboardingChecks: (siteId?: string | null) => {
    onboardingMocks.onboardingCheckSiteIds.push(siteId);
    return {
      data: onboardingMocks.onboardingChecks,
      isLoading: false,
      isError: false,
    };
  },
}));

vi.mock("@/hooks/use-maritime", () => ({
  useMaritimeVessels: () => ({
    data: onboardingMocks.vessels,
    isLoading: false,
    isError: false,
  }),
}));

function renderWithProviders(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("FleetOpsOnboarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    onboardingMocks.onboardingCheckSiteIds = [];
  });

  test("requests onboarding checks for the vessel site", async () => {
    renderWithProviders(<FleetOpsOnboarding />);

    expect(await screen.findByText(/Onboarding checks/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Satellite fallback/i).length).toBeGreaterThan(0);
    expect(onboardingMocks.onboardingCheckSiteIds).toContain(
      "00000000-0000-4000-8000-000000000020",
    );
  });
});
