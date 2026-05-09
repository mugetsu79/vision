import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { DeploymentPostureStrip } from "@/components/operations/DeploymentPostureStrip";
import type { DeploymentPosture } from "@/lib/operational-health";

const posture: DeploymentPosture = {
  siteCount: 2,
  sceneCount: 5,
  centralScenes: 2,
  edgeScenes: 2,
  hybridScenes: 1,
  assignedEdgeNodes: 1,
  pendingEvidence: 3,
  privacyConfiguredScenes: 4,
  fleetHealth: {
    health: "attention",
    label: "Attention needed",
    reasons: ["1 worker missing"],
  },
};

describe("DeploymentPostureStrip", () => {
  test("renders sites scenes modes privacy evidence and fleet posture", () => {
    render(<DeploymentPostureStrip posture={posture} />);

    expect(screen.getByTestId("deployment-posture-strip")).toBeInTheDocument();
    expect(screen.getByText("Sites")).toBeInTheDocument();
    expect(screen.getByText("2 / 2 / 1")).toBeInTheDocument();
    expect(screen.getByText("Privacy configured")).toBeInTheDocument();
    expect(screen.getByText("Evidence awaiting review")).toBeInTheDocument();
    expect(screen.getByText("Attention needed")).toBeInTheDocument();
  });
});
