import { describe, expect, test } from "vitest";

import {
  DEFAULT_SIGNAL_HOLD_MS,
  colorForClass,
  deriveSignalCounts,
  trackKey,
  updateSignalTracks,
} from "@/lib/live-signal-stability";
import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];
type TelemetryTrack = components["schemas"]["TelemetryTrack"];

function track(
  className: string,
  trackId: number,
  bbox: TelemetryTrack["bbox"] = { x1: 10, y1: 20, x2: 100, y2: 180 },
): TelemetryTrack {
  return {
    class_name: className,
    confidence: 0.91,
    bbox,
    track_id: trackId,
    speed_kph: null,
    direction_deg: null,
    zone_id: null,
    attributes: {},
  };
}

function frame(tracks: TelemetryTrack[]): TelemetryFrame {
  return {
    camera_id: "11111111-1111-1111-1111-111111111111",
    ts: "2026-05-09T08:00:00Z",
    profile: "central-gpu",
    stream_mode: "annotated-whip",
    counts: tracks.reduce<Record<string, number>>((counts, item) => {
      counts[item.class_name] = (counts[item.class_name] ?? 0) + 1;
      return counts;
    }, {}),
    tracks,
  };
}

describe("live signal stability", () => {
  test("creates stable track keys from class and track id", () => {
    expect(trackKey(track("person", 12))).toBe("person:12");
  });

  test("maps common classes to semantic colors", () => {
    expect(colorForClass("person").family).toBe("human");
    expect(colorForClass("car").family).toBe("vehicle");
    expect(colorForClass("hard_hat").family).toBe("safety");
    expect(colorForClass("forklift").family).toBe("other");
  });

  test("keeps a missing track as held within the hold window", () => {
    const first = updateSignalTracks({
      previous: [],
      frame: frame([track("person", 12)]),
      activeClasses: null,
      nowMs: 1_000,
    });

    const second = updateSignalTracks({
      previous: first,
      frame: frame([]),
      activeClasses: null,
      nowMs: 1_000 + DEFAULT_SIGNAL_HOLD_MS - 1,
    });

    expect(second).toHaveLength(1);
    expect(second[0]).toMatchObject({
      key: "person:12",
      state: "held",
      ageMs: DEFAULT_SIGNAL_HOLD_MS - 1,
    });
  });

  test("expires held tracks after the hold window", () => {
    const first = updateSignalTracks({
      previous: [],
      frame: frame([track("person", 12)]),
      activeClasses: null,
      nowMs: 1_000,
    });

    const expired = updateSignalTracks({
      previous: first,
      frame: frame([]),
      activeClasses: null,
      nowMs: 1_000 + DEFAULT_SIGNAL_HOLD_MS + 1,
    });

    expect(expired).toEqual([]);
  });

  test("filters live and held tracks by active classes", () => {
    const first = updateSignalTracks({
      previous: [],
      frame: frame([track("person", 12), track("car", 7)]),
      activeClasses: ["person"],
      nowMs: 1_000,
    });

    expect(first.map((item) => item.track.class_name)).toEqual(["person"]);
  });

  test("derives live held and total counts by class", () => {
    const first = updateSignalTracks({
      previous: [],
      frame: frame([track("person", 12), track("car", 7)]),
      activeClasses: null,
      nowMs: 1_000,
    });
    const second = updateSignalTracks({
      previous: first,
      frame: frame([track("car", 7)]),
      activeClasses: null,
      nowMs: 1_500,
    });

    const counts = deriveSignalCounts(second);

    expect(counts.liveTotal).toBe(1);
    expect(counts.heldTotal).toBe(1);
    expect(counts.rows.map((row) => [row.className, row.liveCount, row.heldCount])).toEqual([
      ["car", 1, 0],
      ["person", 0, 1],
    ]);
  });
});
