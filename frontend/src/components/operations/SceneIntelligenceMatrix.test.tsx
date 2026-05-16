import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { SceneIntelligenceMatrix } from "@/components/operations/SceneIntelligenceMatrix";
import type { SceneHealthRow } from "@/lib/operational-health";

const rows: SceneHealthRow[] = [
  {
    cameraId: "camera-1",
    cameraName: "North Gate",
    siteName: "Zurich Lab",
    nodeLabel: "central",
    processingMode: "central",
    readiness: { health: "healthy", label: "Ready" },
    overall: { health: "healthy", label: "Worker running" },
    privacy: { health: "healthy", label: "Face/plate filtering configured" },
    worker: { health: "healthy", label: "Worker running" },
    rules: {
      health: "healthy",
      label: "2 active rules",
      detail: "loaded - ffffffffffff - 12 May 2026, 09:30",
    },
    delivery: { health: "healthy", label: "Native stream available" },
    transport: { health: "healthy", label: "WebRTC relay ready" },
    liveRendition: { health: "healthy", label: "Native clean" },
    telemetry: { health: "healthy", label: "Telemetry live" },
    actionHref: "/live",
    actionLabel: "Open live",
  },
  {
    cameraId: "camera-2",
    cameraName: "Depot Yard",
    siteName: "Zurich Lab",
    nodeLabel: "orin1",
    processingMode: "edge",
    readiness: { health: "attention", label: "Needs setup" },
    overall: { health: "danger", label: "Direct stream unavailable" },
    privacy: { health: "healthy", label: "Face/plate filtering configured" },
    worker: {
      health: "attention",
      label: "Worker stale",
      detail: "Edge heartbeat is stale.",
    },
    rules: {
      health: "unknown",
      label: "No active rules",
      detail: "not configured",
    },
    delivery: {
      health: "danger",
      label: "Direct stream unavailable",
      detail: "source unavailable",
    },
    transport: { health: "unknown", label: "Inherited transport" },
    liveRendition: {
      health: "danger",
      label: "Native clean",
      detail: "source unavailable",
    },
    telemetry: { health: "unknown", label: "Awaiting telemetry" },
    actionHref: "/settings",
    actionLabel: "Inspect delivery",
  },
];

describe("SceneIntelligenceMatrix", () => {
  test("renders scene rows with site mode privacy worker delivery telemetry and actions", () => {
    render(
      <MemoryRouter>
        <SceneIntelligenceMatrix rows={rows} />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: /scene intelligence matrix/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("North Gate")).toBeInTheDocument();
    expect(screen.getByText("Depot Yard")).toBeInTheDocument();
    expect(screen.getAllByText("Zurich Lab")).toHaveLength(2);
    expect(screen.getByText("central / central")).toBeInTheDocument();
    expect(screen.getByText("edge / orin1")).toBeInTheDocument();
    expect(
      screen.getAllByText(/face\/plate filtering configured/i).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Rules")).toBeInTheDocument();
    expect(screen.getByText("2 active rules")).toBeInTheDocument();
    expect(screen.getByText(/ffffffffffff/i)).toBeInTheDocument();
    expect(screen.getByText(/12 may 2026/i)).toBeInTheDocument();
    expect(screen.getByText(/no active rules/i)).toBeInTheDocument();
    expect(screen.getAllByText(/worker stale/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Transport")).toBeInTheDocument();
    expect(screen.getByText("Live rendition")).toBeInTheDocument();
    expect(screen.getByText(/webrtc relay ready/i)).toBeInTheDocument();
    expect(screen.getAllByText(/native clean/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/inherited transport/i)).toBeInTheDocument();
    expect(screen.getByText(/source unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/awaiting telemetry/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /inspect delivery for depot yard/i }),
    ).toHaveAttribute("href", "/settings");
  });

  test("renders an empty state when no scenes exist", () => {
    render(
      <MemoryRouter>
        <SceneIntelligenceMatrix rows={[]} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/no scenes configured/i)).toBeInTheDocument();
  });
});
