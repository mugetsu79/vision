import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { SceneStatusStrip } from "@/components/operations/SceneStatusStrip";
import type { SceneHealthRow } from "@/lib/operational-health";

const row: SceneHealthRow = {
  cameraId: "camera-1",
  cameraName: "North Gate",
  siteName: "Zurich Lab",
  nodeLabel: "central",
  processingMode: "central",
  readiness: { health: "attention", label: "Needs attention" },
  overall: { health: "attention", label: "Telemetry stale" },
  privacy: { health: "healthy", label: "Face/plate filtering configured" },
  worker: { health: "healthy", label: "Worker running" },
  delivery: { health: "healthy", label: "Native stream available" },
  telemetry: { health: "attention", label: "Telemetry stale" },
  actionHref: "/settings",
  actionLabel: "Inspect operations",
};

describe("SceneStatusStrip", () => {
  test("renders worker stream and telemetry signals", () => {
    render(<SceneStatusStrip row={row} />);

    expect(
      screen.getByRole("group", { name: /north gate operational status/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/central/i)).toBeInTheDocument();
    expect(
      screen.getByText(/face\/plate filtering configured/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/worker running/i)).toBeInTheDocument();
    expect(screen.getByText(/native stream available/i)).toBeInTheDocument();
    expect(screen.getByText(/telemetry stale/i)).toBeInTheDocument();
  });
});
