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
  transport: { health: "unknown", label: "Inherited transport" },
  liveRendition: { health: "healthy", label: "Native clean" },
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
    expect(screen.getByText(/native clean/i)).toBeInTheDocument();
    expect(screen.getByText(/inherited transport/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/direct stream unavailable/i),
    ).not.toBeInTheDocument();
  });

  test("renders live rendition detail for unavailable native delivery", () => {
    render(
      <SceneStatusStrip
        row={{
          ...row,
          liveRendition: {
            health: "danger",
            label: "Native clean",
            detail: "privacy filtering required",
          },
        }}
      />,
    );

    expect(
      screen.getByText(/native clean: privacy filtering required/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/direct stream unavailable/i),
    ).not.toBeInTheDocument();
  });

  test("renders active worker detail quietly", () => {
    render(
      <SceneStatusStrip
        row={{
          ...row,
          worker: {
            health: "healthy",
            label: "Worker active",
            detail: "runtime report pending",
          },
        }}
      />,
    );

    expect(screen.getByText(/^worker active$/i)).toBeInTheDocument();
    expect(
      screen.getByText(/worker active: runtime report pending/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/worker awaiting report/i)).not.toBeInTheDocument();
  });
});
