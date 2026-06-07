import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  test("renders scene readiness rows with grouped runtime and stream signals", () => {
    render(
      <MemoryRouter>
        <SceneIntelligenceMatrix rows={rows} />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: /scene readiness/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("North Gate")).toBeInTheDocument();
    expect(screen.getByText("Depot Yard")).toBeInTheDocument();
    expect(screen.getAllByText("Zurich Lab")).toHaveLength(2);
    expect(
      screen.getByText(/central processing on master supervisor/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/edge processing on orin1/i)).toBeInTheDocument();
    expect(screen.queryByText("central / central")).not.toBeInTheDocument();
    expect(screen.queryByText("edge / orin1")).not.toBeInTheDocument();
    expect(screen.getAllByText("Runtime")).toHaveLength(2);
    expect(screen.getAllByText("Stream")).toHaveLength(2);
    expect(
      screen.getAllByText(/face\/plate filtering configured/i).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("Rules")).toHaveLength(2);
    expect(screen.getByText("2 active rules")).toBeInTheDocument();
    expect(screen.getByText(/ffffffffffff/i)).toBeInTheDocument();
    expect(screen.getByText(/12 may 2026/i)).toBeInTheDocument();
    expect(screen.getByText(/no active rules/i)).toBeInTheDocument();
    expect(screen.getAllByText(/worker stale/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Transport")).toHaveLength(2);
    expect(screen.getAllByText("Live rendition")).toHaveLength(2);
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

  test("paginates long readiness sets at operator-selected page sizes", async () => {
    const user = userEvent.setup();
    const manyRows = Array.from({ length: 12 }, (_, index) => ({
      ...rows[0],
      cameraId: `camera-${index + 1}`,
      cameraName: `Batch Scene ${String(index + 1).padStart(2, "0")}`,
    }));

    render(
      <MemoryRouter>
        <SceneIntelligenceMatrix rows={manyRows} />
      </MemoryRouter>,
    );

    const matrix = screen.getByTestId("scene-intelligence-matrix");
    expect(within(matrix).getByText("Batch Scene 10")).toBeInTheDocument();
    expect(within(matrix).queryByText("Batch Scene 11")).not.toBeInTheDocument();
    expect(within(matrix).getByText("1-10 of 12 scenes")).toBeInTheDocument();

    await user.selectOptions(
      within(matrix).getByLabelText(/scene readiness per page/i),
      "25",
    );

    expect(within(matrix).getByText("Batch Scene 11")).toBeInTheDocument();
    expect(within(matrix).getByText("1-12 of 12 scenes")).toBeInTheDocument();
  });
});
