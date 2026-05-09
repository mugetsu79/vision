import { describe, expect, test } from "vitest";

import {
  DEFAULT_SIGNAL_HOLD_MS,
  colorForClass,
  deriveSignalCounts,
  selectDrawableSignalTracks,
  trackKey,
  updateSignalTracks,
  type SignalTrack,
} from "@/lib/live-signal-stability";
import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];
type TelemetryTrack = components["schemas"]["TelemetryTrack"];

function track(
  className: string,
  trackId: number,
  bbox: TelemetryTrack["bbox"] = { x1: 10, y1: 20, x2: 100, y2: 180 },
  lifecycle: Partial<
    Pick<
      TelemetryTrack,
      "stable_track_id" | "track_state" | "last_seen_age_ms" | "source_track_id"
    >
  > = {},
): TelemetryTrack {
  return {
    class_name: className,
    confidence: 0.91,
    bbox,
    track_id: trackId,
    ...lifecycle,
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

  test("maps backend coasting lifecycle tracks to held display state", () => {
    const snapshot = updateSignalTracks({
      previous: [],
      frame: frame([
        track("person", 12, undefined, {
          stable_track_id: 12,
          source_track_id: 4,
          track_state: "coasting",
          last_seen_age_ms: 900,
        }),
      ]),
      activeClasses: null,
      nowMs: 2_000,
    });

    expect(snapshot).toHaveLength(1);
    expect(snapshot[0]).toMatchObject({
      key: "person:12",
      state: "held",
      ageMs: 900,
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

  test("draws no frontend overlays on server annotated streams", () => {
    const live = signalTrack("person", 12, "live");
    const held = signalTrack("person", 13, "held");

    expect(selectDrawableSignalTracks([live, held], "annotated-whip")).toEqual([]);
  });

  test("draws all frontend overlays on unannotated streams", () => {
    const live = signalTrack("person", 12, "live");
    const held = signalTrack("person", 13, "held");

    expect(selectDrawableSignalTracks([live, held], "filtered-preview")).toEqual([live, held]);
  });
});

function signalTrack(
  className: string,
  trackId: number,
  state: SignalTrack["state"],
): SignalTrack {
  const item = track(className, trackId);
  return {
    key: `${className}:${trackId}`,
    track: item,
    color: colorForClass(className),
    state,
    firstSeenMs: 1_000,
    lastSeenMs: 1_000,
    ageMs: state === "held" ? 500 : 0,
  };
}
