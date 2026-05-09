import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { useStableSignalFrame } from "@/hooks/use-stable-signal-frame";
import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];

function frame(tracks: TelemetryFrame["tracks"]): TelemetryFrame {
  return {
    camera_id: "11111111-1111-1111-1111-111111111111",
    ts: new Date().toISOString(),
    profile: "central-gpu",
    stream_mode: "annotated-whip",
    counts: {},
    tracks,
  };
}

const person = {
  class_name: "person",
  confidence: 0.91,
  bbox: { x1: 10, y1: 20, x2: 100, y2: 180 },
  track_id: 12,
  speed_kph: null,
  direction_deg: null,
  zone_id: null,
  attributes: {},
};

describe("useStableSignalFrame", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("returns live tracks from the latest frame", () => {
    const view = renderHook(({ latest }) => useStableSignalFrame(latest, null), {
      initialProps: { latest: frame([person]) },
    });

    expect(view.result.current.counts.liveTotal).toBe(1);
    expect(view.result.current.tracks[0].state).toBe("live");
  });

  test("keeps missing tracks held until the hold window expires", () => {
    const view = renderHook(({ latest }) => useStableSignalFrame(latest, null), {
      initialProps: { latest: frame([person]) },
    });

    act(() => {
      vi.setSystemTime(1_500);
      view.rerender({ latest: frame([]) });
    });

    expect(view.result.current.counts.liveTotal).toBe(0);
    expect(view.result.current.counts.heldTotal).toBe(1);
    expect(view.result.current.tracks[0].state).toBe("held");

    act(() => {
      vi.setSystemTime(2_400);
      vi.advanceTimersByTime(900);
    });

    expect(view.result.current.counts.total).toBe(0);
  });

  test("expires live tracks when telemetry stops without a replacement frame", () => {
    const view = renderHook(({ latest }) => useStableSignalFrame(latest, null), {
      initialProps: { latest: frame([person]) },
    });

    expect(view.result.current.counts.liveTotal).toBe(1);

    act(() => {
      vi.setSystemTime(2_300);
      vi.advanceTimersByTime(1_300);
    });

    expect(view.result.current.counts.total).toBe(0);
  });
});
