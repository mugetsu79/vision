import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { FleetOpsOnboarding } from "@/pages/FleetOpsOnboarding";
import { TestMemoryRouter } from "@/test/router";

const onboardingMocks = vi.hoisted(() => ({
  onboardingCheckSiteIds: [] as Array<string | null | undefined>,
  runChecks: vi.fn(),
  diagnostics: {
    label: "Support readiness",
    groups: [
      {
        id: "access_and_roles",
        label: "Access and roles readiness",
        status: "ready",
        checks: [
          {
            key: "handoff_ready",
            label: "Handoff ready",
            status: "ready",
          },
        ],
        next_action: "Confirm support contacts before first voyage.",
      },
    ],
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
    {
      id: "00000000-0000-4000-8000-000000000011",
      name: "MV Horizon",
      site_id: "00000000-0000-4000-8000-000000000021",
    },
  ],
}));

vi.mock("@/hooks/use-support", () => ({
  useMaritimeSupportDiagnostics: () => ({
    data: onboardingMocks.diagnostics,
    isLoading: false,
    isError: false,
  }),
  useRunSupportOnboardingChecks: () => ({
    mutateAsync: onboardingMocks.runChecks,
    isPending: false,
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
  return render(<TestMemoryRouter>{ui}</TestMemoryRouter>);
}

describe("FleetOpsOnboarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    onboardingMocks.onboardingCheckSiteIds = [];
    onboardingMocks.runChecks.mockResolvedValue({
      run_id: "run-1",
    });
  });

  test("FleetOps onboarding requires explicit vessel scope before running checks", async () => {
    const user = userEvent.setup();
    renderWithProviders(<FleetOpsOnboarding />);

    expect(
      await screen.findByRole("heading", { name: /Onboarding/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/search fleetops vessel scope/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/choose a vessel to review onboarding/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /run checks/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /open link performance/i }),
    ).not.toBeInTheDocument();
    expect(onboardingMocks.onboardingCheckSiteIds.at(-1)).toBeNull();

    await user.type(
      screen.getByLabelText(/search fleetops vessel scope/i),
      "horizon",
    );
    await user.click(screen.getByRole("button", { name: /mv horizon/i }));

    expect(
      screen.getByRole("link", { name: /open link performance/i }),
    ).toHaveAttribute(
      "href",
      "/links?site=00000000-0000-4000-8000-000000000021",
    );
    expect(screen.getAllByText(/setup checks/i).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: /run checks/i }));
    expect(onboardingMocks.runChecks).toHaveBeenCalledWith(
      expect.objectContaining({
        pack_id: "maritime-fleet",
        site_id: "00000000-0000-4000-8000-000000000021",
      }),
    );
    expect(screen.queryByText(/Generate bundle/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Satellite fallback/i).length).toBeGreaterThan(
      0,
    );
    expect(onboardingMocks.onboardingCheckSiteIds).toContain(
      "00000000-0000-4000-8000-000000000021",
    );
  });
});
