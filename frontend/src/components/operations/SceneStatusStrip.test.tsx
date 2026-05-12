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
  rules: { health: "healthy", label: "1 active rule", detail: "loaded" },
  delivery: { health: "healthy", label: "Native stream available" },
  telemetry: { health: "attention", label: "Telemetry stale" },
  actionHref: "/settings",
  actionLabel: "Inspect operations",
};

describe("SceneStatusStrip", () => {
  test("renders calmer worker stream and telemetry groups", () => {
    render(<SceneStatusStrip row={row} />);

    expect(
      screen.getByRole("group", { name: /north gate operational status/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/telemetry stale/i)).toBeInTheDocument();
    expect(screen.getByText(/central scene/i)).toBeInTheDocument();
    expect(screen.getByText(/worker running/i)).toBeInTheDocument();
    expect(screen.getByText(/processed stream live/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/direct stream unavailable/i),
    ).not.toBeInTheDocument();
  });

  test("renders gated copy for unavailable direct delivery", () => {
    render(
      <SceneStatusStrip
        row={{
          ...row,
          delivery: {
            health: "attention",
            label: "Direct stream unavailable",
            detail: "privacy filtering required",
          },
        }}
      />,
    );

    expect(
      screen.getAllByText(/native passthrough gated/i).length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByText(/direct stream unavailable/i),
    ).not.toBeInTheDocument();
  });
});
