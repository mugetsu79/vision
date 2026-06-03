import { render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

vi.mock("@/hooks/use-live-sparkline", () => ({
  useLiveSparkline: () => ({
    buckets: { person: [0, 1, 2, 4, 3, 1], car: [0, 0, 1, 1, 0, 0] },
    latestValues: { person: 1, car: 0 },
    loading: false,
    error: null,
  }),
}));

import { TelemetryTerrain } from "@/components/live/TelemetryTerrain";
import { colorForClass, type SignalCountRow } from "@/lib/live-signal-stability";

describe("TelemetryTerrain", () => {
  test("renders accessible live signal trend for primary and secondary classes", () => {
    const rows: SignalCountRow[] = [
      {
        className: "person",
        color: colorForClass("person"),
        liveCount: 1,
        heldCount: 0,
        totalCount: 1,
        state: "live",
      },
      {
        className: "car",
        color: colorForClass("car"),
        liveCount: 0,
        heldCount: 1,
        totalCount: 1,
        state: "held",
      },
    ];

    render(
      <TelemetryTerrain
        cameraId="camera-1"
        cameraName="North Gate"
        activeClasses={["person", "car"]}
        signalRows={rows}
      />,
    );

    const terrain = screen.getByTestId("telemetry-terrain");
    expect(terrain).toHaveAccessibleName(/north gate telemetry terrain/i);
    expect(within(terrain).getByText(/signal trend/i)).toBeInTheDocument();
    expect(within(terrain).getByText(/person active/i)).toBeInTheDocument();
    expect(within(terrain).getByText(/car held/i)).toBeInTheDocument();
    const paths = within(terrain)
      .getByLabelText(/person signal trend/i)
      .querySelectorAll("path");
    expect(paths.length).toBeGreaterThanOrEqual(3);
    expect(terrain.querySelector('path[stroke="#61e6a6"]')).toBeInTheDocument();
    expect(terrain.querySelector('path[stroke="#62a6ff"]')).toBeInTheDocument();
  });

  test("renders occupancy buckets as a stepped terrain instead of diagonal spikes", () => {
    const rows: SignalCountRow[] = [
      {
        className: "person",
        color: colorForClass("person"),
        liveCount: 3,
        heldCount: 0,
        totalCount: 3,
        state: "live",
      },
    ];

    render(
      <TelemetryTerrain
        cameraId="camera-1"
        cameraName="North Gate"
        activeClasses={["person"]}
        signalRows={rows}
      />,
    );

    const svg = screen.getByLabelText(/person signal trend/i);
    const line = svg.querySelector('path[fill="none"]');

    expect(line?.getAttribute("d")).toContain(" H ");
    expect(line?.getAttribute("d")).toContain(" V ");
    expect(line?.getAttribute("d")).not.toMatch(/\sL\s\d/);
  });

  test("adds instrument grid and class lanes without changing the primary trend", () => {
    const rows: SignalCountRow[] = [
      {
        className: "person",
        color: colorForClass("person"),
        liveCount: 2,
        heldCount: 0,
        totalCount: 2,
        state: "live",
      },
      {
        className: "car",
        color: colorForClass("car"),
        liveCount: 0,
        heldCount: 1,
        totalCount: 1,
        state: "held",
      },
    ];

    render(
      <TelemetryTerrain
        cameraId="camera-1"
        cameraName="North Gate"
        activeClasses={["person", "car"]}
        signalRows={rows}
      />,
    );

    const terrain = screen.getByTestId("telemetry-terrain");
    expect(within(terrain).getByTestId("telemetry-terrain-grid")).toBeInTheDocument();
    expect(within(terrain).getByTestId("signal-lane-person")).toHaveTextContent("2");
    expect(within(terrain).getByTestId("signal-lane-car")).toHaveTextContent("1");
  });

  test("renders live-now activity when history buckets are empty for an active class", () => {
    const rows: SignalCountRow[] = [
      {
        className: "truck",
        color: colorForClass("truck"),
        liveCount: 2,
        heldCount: 0,
        totalCount: 2,
        state: "live",
      },
    ];

    render(
      <TelemetryTerrain
        cameraId="camera-1"
        cameraName="North Gate"
        activeClasses={["truck"]}
        signalRows={rows}
      />,
    );

    const terrain = screen.getByTestId("telemetry-terrain");
    const line = within(terrain)
      .getByLabelText(/truck signal trend/i)
      .querySelector('path[fill="none"]');
    expect(line?.getAttribute("d")).toContain("V 37.00");
    expect(line?.getAttribute("d")).toContain("V 12.00");
  });
});
