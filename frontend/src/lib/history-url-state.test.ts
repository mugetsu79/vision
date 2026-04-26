import { describe, expect, test } from "vitest";

import {
  type HistoryFilterState,
  readHistoryFiltersFromSearch,
  writeHistoryFiltersToSearch,
} from "@/lib/history-url-state";

function roundTrip(state: HistoryFilterState): HistoryFilterState {
  const params = writeHistoryFiltersToSearch(state);
  return readHistoryFiltersFromSearch(new URLSearchParams(params));
}

describe("history-url-state", () => {
  test("round trips full state", () => {
    const state: HistoryFilterState = {
      from: new Date("2026-04-01T00:00:00Z"),
      to: new Date("2026-04-02T00:00:00Z"),
      granularity: "5m",
      metric: "count_events",
      cameraIds: ["11111111-1111-1111-1111-111111111111"],
      classNames: ["person", "car"],
      speed: true,
      speedThreshold: 60,
    };
    expect(roundTrip(state)).toEqual(state);
  });

  test("treats absent speed as false", () => {
    const parsed = readHistoryFiltersFromSearch(new URLSearchParams());
    expect(parsed.speed).toBe(false);
  });

  test("omits speedThreshold and speed when speed disabled", () => {
    const params = writeHistoryFiltersToSearch({
      from: new Date("2026-04-01T00:00:00Z"),
      to: new Date("2026-04-02T00:00:00Z"),
      granularity: "1h",
      metric: null,
      cameraIds: [],
      classNames: [],
      speed: false,
      speedThreshold: null,
    });
    const parsed = new URLSearchParams(params);
    expect(parsed.has("speed")).toBe(false);
    expect(parsed.has("speedThreshold")).toBe(false);
  });

  test("invalid granularity falls back to default", () => {
    const parsed = readHistoryFiltersFromSearch(new URLSearchParams("granularity=2d"));
    expect(parsed.granularity).toBe("1h");
  });

  test("comma-separated cameras serialise without trailing comma", () => {
    const params = writeHistoryFiltersToSearch({
      from: new Date("2026-04-01T00:00:00Z"),
      to: new Date("2026-04-02T00:00:00Z"),
      granularity: "1h",
      metric: null,
      cameraIds: ["a", "b"],
      classNames: [],
      speed: false,
      speedThreshold: null,
    });
    expect(new URLSearchParams(params).get("cameras")).toBe("a,b");
  });
});
