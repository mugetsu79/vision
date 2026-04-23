import { describe, expect, test } from "vitest";

import { buildHistoryChartOption } from "@/components/history/HistoryTrendChart";

const BASE_POINT = {
  bucket: "2026-04-23T00:00:00Z",
  values: { car: 12, person: 4 },
  total_count: 16,
};

describe("buildHistoryChartOption", () => {
  test("renders a single grid when speed is off", () => {
    const option = buildHistoryChartOption({
      classNames: ["car", "person"],
      points: [BASE_POINT],
      includeSpeed: false,
    });
    expect(Array.isArray(option.grid) ? option.grid.length : 1).toBe(1);
    expect(Array.isArray(option.series)).toBe(true);
    expect((option.series as unknown as { name: string }[]).map((s) => s.name)).toEqual([
      "car",
      "person",
    ]);
  });

  test("adds a speed panel with p50 and p95 series when speed is on", () => {
    const option = buildHistoryChartOption({
      classNames: ["car"],
      points: [
        {
          ...BASE_POINT,
          speed_p50: { car: 40 },
          speed_p95: { car: 55 },
          speed_sample_count: { car: 12 },
        },
      ],
      includeSpeed: true,
      speedClassesUsed: ["car"],
    });
    const names = (option.series as unknown as { name: string }[]).map((s) => s.name);
    expect(names).toContain("car p50");
    expect(names).toContain("car p95");
    expect(Array.isArray(option.grid) ? option.grid.length : 1).toBe(2);
  });

  test("adds violation bars and a threshold markLine when a threshold is set", () => {
    const option = buildHistoryChartOption({
      classNames: ["car"],
      points: [
        {
          ...BASE_POINT,
          speed_p50: { car: 40 },
          speed_p95: { car: 55 },
          speed_sample_count: { car: 12 },
          over_threshold_count: { car: 3 },
        },
      ],
      includeSpeed: true,
      speedThreshold: 50,
      speedClassesUsed: ["car"],
    });
    const seriesList = option.series as unknown as Array<{
      name: string;
      type: string;
      markLine?: { data: Array<{ yAxis: number }> };
    }>;
    const violation = seriesList.find((s) => s.name === "car (over threshold)");
    expect(violation).toBeDefined();
    expect(violation?.type).toBe("bar");
    const p95 = seriesList.find((s) => s.name === "car p95");
    expect(p95?.markLine?.data?.[0].yAxis).toBe(50);
  });
});
