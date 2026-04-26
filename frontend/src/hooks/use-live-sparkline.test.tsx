import { describe, expect, test } from "vitest";

import type { TelemetryFrame } from "@/lib/live";
import { mergeOccupancySnapshot } from "@/hooks/use-live-sparkline";

describe("useLiveSparkline helpers", () => {
  test("keeps a stationary object's occupancy at the bucket peak instead of accumulating", () => {
    const windowEndMs = Date.parse("2026-04-25T10:05:00.000Z");
    const bucketStartMs = windowEndMs;
    const initialBuckets = {
      person: new Array(30).fill(0),
    };
    const frame: Pick<TelemetryFrame, "counts"> = {
      counts: { person: 1 },
    } as Pick<TelemetryFrame, "counts">;

    const once = mergeOccupancySnapshot(initialBuckets, bucketStartMs, frame, windowEndMs);
    const twice = mergeOccupancySnapshot(once, bucketStartMs, frame, windowEndMs);

    expect(twice.person[29]).toBe(1);
  });

  test("stores the peak occupancy observed within the same minute bucket", () => {
    const windowEndMs = Date.parse("2026-04-25T10:05:00.000Z");
    const bucketStartMs = windowEndMs;
    const initialBuckets = {
      car: new Array(30).fill(0),
    };

    const low: Pick<TelemetryFrame, "counts"> = { counts: { car: 1 } } as Pick<
      TelemetryFrame,
      "counts"
    >;
    const high: Pick<TelemetryFrame, "counts"> = { counts: { car: 3 } } as Pick<
      TelemetryFrame,
      "counts"
    >;

    const afterLow = mergeOccupancySnapshot(initialBuckets, bucketStartMs, low, windowEndMs);
    const afterHigh = mergeOccupancySnapshot(afterLow, bucketStartMs, high, windowEndMs);

    expect(afterHigh.car[29]).toBe(3);
  });
});
