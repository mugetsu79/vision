import { describe, expect, test } from "vitest";

import {
  buildBucketDetails,
  buildDisplaySeries,
  formatBucketSpan,
  getCoverageCopy,
} from "@/lib/history-workbench";
import type { HistorySeriesResponse } from "@/hooks/use-history";

const response: HistorySeriesResponse = {
  granularity: "1h",
  metric: "occupancy",
  class_names: ["car"],
  rows: [
    { bucket: "2026-04-27T10:00:00Z", values: { car: 0 }, total_count: 0 },
    { bucket: "2026-04-27T11:00:00Z", values: { car: 4 }, total_count: 4 },
  ],
  coverage_status: "populated",
  coverage_by_bucket: [
    { bucket: "2026-04-27T10:00:00Z", status: "zero", reason: null },
    { bucket: "2026-04-27T11:00:00Z", status: "populated", reason: null },
  ],
  granularity_adjusted: false,
  speed_classes_capped: false,
  bucket_count: 2,
};

describe("history-workbench", () => {
  test("builds selected bucket details with coverage copy", () => {
    const detail = buildBucketDetails(response, "2026-04-27T10:00:00Z");

    expect(detail?.bucket).toBe("2026-04-27T10:00:00Z");
    expect(detail?.totalCount).toBe(0);
    expect(detail?.coverage.status).toBe("zero");
    expect(detail?.coverage.label).toBe("No detections");
  });

  test("falls back to total series when no class names exist", () => {
    const display = buildDisplaySeries({
      ...response,
      class_names: [],
      rows: [{ bucket: "2026-04-27T10:00:00Z", values: {}, total_count: 0 }],
    });

    expect(display.classNames).toEqual(["Total"]);
    expect(display.points[0].values).toEqual({ Total: 0 });
  });

  test("formats hourly bucket spans", () => {
    expect(formatBucketSpan("2026-04-27T10:00:00Z", "1h")).toBe("10:00-10:59");
  });

  test("returns operational copy for worker offline", () => {
    expect(getCoverageCopy("worker_offline").message).toBe("Processing was unavailable for this bucket.");
  });
});
