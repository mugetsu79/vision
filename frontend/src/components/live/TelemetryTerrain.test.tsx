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
  test("renders accessible live signal terrain for the primary class", () => {
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
    expect(within(terrain).getByText(/telemetry terrain/i)).toBeInTheDocument();
    expect(within(terrain).getByText(/person active/i)).toBeInTheDocument();
    expect(within(terrain).getByText(/car held/i)).toBeInTheDocument();
    expect(within(terrain).getByLabelText(/person signal terrain/i)).toBeInTheDocument();
  });
});
