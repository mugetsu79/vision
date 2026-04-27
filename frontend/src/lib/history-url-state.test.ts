import { describe, expect, test } from "vitest";

import {
  type HistoryFilterState,
  readHistoryFiltersFromSearch,
  resolveRelativeWindow,
  writeHistoryFiltersToSearch,
} from "@/lib/history-url-state";

function roundTrip(state: HistoryFilterState): HistoryFilterState {
  const params = writeHistoryFiltersToSearch(state);
  return readHistoryFiltersFromSearch(new URLSearchParams(params));
}

describe("history-url-state", () => {
  test("defaults an empty URL to a following last 24 hour relative window", () => {
    const now = new Date("2026-04-27T12:34:56.789Z");
    const parsed = readHistoryFiltersFromSearch(new URLSearchParams(), now);

    expect(parsed.windowMode).toBe("relative");
    expect(parsed.relativeWindow).toBe("last_24h");
    expect(parsed.followNow).toBe(true);
    expect(parsed.to).toEqual(new Date("2026-04-27T12:34:00.000Z"));
    expect(parsed.from).toEqual(new Date("2026-04-26T12:34:00.000Z"));
  });

  test("serializes relative windows without absolute bounds", () => {
    const { from, to } = resolveRelativeWindow("last_1h", new Date("2026-04-27T12:34:56.789Z"));
    const params = writeHistoryFiltersToSearch({
      from,
      to,
      windowMode: "relative",
      relativeWindow: "last_1h",
      followNow: true,
      granularity: "1h",
      metric: null,
      cameraIds: [],
      classNames: [],
      speed: false,
      speedThreshold: null,
    });

    expect(params).toBe("window=last_1h&follow=1");
    const parsed = new URLSearchParams(params);
    expect(parsed.has("from")).toBe(false);
    expect(parsed.has("to")).toBe(false);
  });

  test("explicit absolute bounds disable follow-now", () => {
    const parsed = readHistoryFiltersFromSearch(
      new URLSearchParams("from=2026-04-01T00%3A00%3A00.000Z&to=2026-04-02T00%3A00%3A00.000Z"),
    );

    expect(parsed.windowMode).toBe("absolute");
    expect(parsed.followNow).toBe(false);
    expect(parsed.from).toEqual(new Date("2026-04-01T00:00:00.000Z"));
    expect(parsed.to).toEqual(new Date("2026-04-02T00:00:00.000Z"));
  });

  test("serializes mismatched relative state as a relative window", () => {
    const params = writeHistoryFiltersToSearch({
      from: new Date("2026-04-20T12:34:00.000Z"),
      to: new Date("2026-04-27T12:34:00.000Z"),
      windowMode: "relative",
      relativeWindow: "last_24h",
      followNow: true,
      granularity: "1h",
      metric: null,
      cameraIds: [],
      classNames: [],
      speed: false,
      speedThreshold: null,
    });
    const parsed = new URLSearchParams(params);

    expect(parsed.get("window")).toBe("last_24h");
    expect(parsed.get("follow")).toBe("1");
    expect(parsed.has("from")).toBe(false);
    expect(parsed.has("to")).toBe(false);
  });

  test("round trips full state", () => {
    const state: HistoryFilterState = {
      from: new Date("2026-04-01T00:00:00Z"),
      to: new Date("2026-04-02T00:00:00Z"),
      windowMode: "absolute",
      relativeWindow: "last_24h",
      followNow: false,
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
      windowMode: "absolute",
      relativeWindow: "last_24h",
      followNow: false,
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
      windowMode: "absolute",
      relativeWindow: "last_24h",
      followNow: false,
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
