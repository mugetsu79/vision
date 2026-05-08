import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import { DashboardPage } from "@/pages/Dashboard";

vi.mock("@/hooks/use-cameras", () => ({
  useCameras: () => ({
    data: [
      { id: "camera-1", name: "North Gate", site_id: "site-1" },
      { id: "camera-2", name: "Depot Yard", site_id: "site-1" },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-incidents", () => ({
  useIncidents: () => ({
    data: [
      { id: "incident-1", review_status: "pending", type: "ppe-missing" },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-sites", () => ({
  useSites: () => ({
    data: [{ id: "site-1", name: "HQ", tz: "Europe/Zurich" }],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: {
      summary: {
        desired_workers: 2,
        running_workers: 1,
        stale_nodes: 0,
        offline_nodes: 0,
        native_unavailable_cameras: 1,
      },
    },
    isLoading: false,
    isError: false,
  }),
}));

describe("DashboardPage", () => {
  test("renders an OmniSight overview cockpit", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "OmniSight Overview" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("omnisight-lens")).toBeInTheDocument();
    expect(screen.getByText("Live scenes")).toBeInTheDocument();
    expect(screen.getByText("Evidence queue")).toBeInTheDocument();
    expect(screen.getByText("Edge workers")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Open Live Intelligence/i }),
    ).toHaveAttribute("href", "/live");
    expect(
      screen.getByRole("link", { name: /Review Evidence/i }),
    ).toHaveAttribute("href", "/incidents");
  });
});
