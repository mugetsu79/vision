import { afterEach, describe, expect, test, vi } from "vitest";

import { formatHeartbeat, type TelemetryFrame } from "@/lib/live";

function frameAt(ts: string): TelemetryFrame {
  return {
    camera_id: "11111111-1111-1111-1111-111111111111",
    ts,
    profile: "central-gpu",
    stream_mode: "passthrough",
    stream_profile_id: "native",
    counts: {},
    tracks: [],
  };
}

describe("formatHeartbeat", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  test("keeps recently arriving passthrough telemetry labeled live", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-04T08:00:02.000Z"));

    expect(formatHeartbeat(frameAt("2026-06-04T08:00:00.000Z"))).toBe(
      "Heartbeat live",
    );
  });

  test("shows elapsed age once telemetry falls outside the live display window", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-04T08:00:06.000Z"));

    expect(formatHeartbeat(frameAt("2026-06-04T08:00:00.000Z"))).toBe(
      "Heartbeat 6s ago",
    );
  });
});
