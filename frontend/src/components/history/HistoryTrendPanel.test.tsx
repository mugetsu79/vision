import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { HistoryTrendPanel } from "@/components/history/HistoryTrendPanel";

vi.mock("@/components/history/HistoryTrendChart", () => ({
  HistoryTrendChart: ({ className }: { className?: string }) => (
    <div
      className={className}
      data-testid="mock-history-trend-chart"
      role="img"
      aria-label="History trend chart"
    />
  ),
}));

const BASE_SERIES = {
  classNames: ["person"],
  points: [
    { bucket: "2026-04-30T00:00:00Z", values: { person: 1 } },
    { bucket: "2026-04-30T01:00:00Z", values: { person: 2 } },
    { bucket: "2026-04-30T02:00:00Z", values: { person: 3 } },
  ],
  includeSpeed: false,
  speedThreshold: null,
  speedClassesUsed: null,
};

describe("HistoryTrendPanel", () => {
  test("renders an animated cerulean shaft over the selected bucket", async () => {
    render(
      <HistoryTrendPanel
        series={{
          ...BASE_SERIES,
          selectedBucket: "2026-04-30T01:00:00Z",
        }}
        metric="occupancy"
        granularity="1h"
        coverage={{
          status: "populated",
          label: "Populated",
          message: "Detections are available for this bucket.",
        }}
        onBucketSelect={() => {}}
      />,
    );

    await screen.findByTestId("mock-history-trend-chart");

    const shaft = screen.getByTestId("history-bucket-shaft");

    expect(shaft).toHaveAttribute("aria-hidden", "true");
    expect(shaft).toHaveStyle({ left: "50%" });
    expect(shaft).toHaveClass("bg-[rgba(110,189,255,0.18)]");
    expect(shaft.querySelector("span")).toHaveClass(
      "bg-[var(--vz-lens-cerulean)]",
    );
  });
});
