import type { components } from "@/lib/api.generated";
import { colorForClass, type SignalColor } from "@/lib/signal-colors";

export { colorForClass };
export type { SignalColor, SignalColorFamily } from "@/lib/signal-colors";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];
type TelemetryTrack = components["schemas"]["TelemetryTrack"];

export const DEFAULT_SIGNAL_HOLD_MS = 1_200;
const DEFAULT_SIGNAL_LIVE_GRACE_MS = 500;

export type SignalState = "live" | "held";

export type SignalTrack = {
  key: string;
  track: TelemetryTrack;
  color: SignalColor;
  state: SignalState;
  firstSeenMs: number;
  lastSeenMs: number;
  ageMs: number;
};

export type SignalCountRow = {
  className: string;
  color: SignalColor;
  liveCount: number;
  heldCount: number;
  totalCount: number;
  state: SignalState;
};

export type SignalCounts = {
  liveTotal: number;
  heldTotal: number;
  total: number;
  rows: SignalCountRow[];
};

export function trackKey(
  track: Pick<TelemetryTrack, "class_name" | "track_id" | "stable_track_id">,
): string {
  return `${track.class_name}:${track.stable_track_id ?? track.track_id}`;
}

export function updateSignalTracks({
  previous,
  frame,
  activeClasses,
  nowMs,
  holdMs = DEFAULT_SIGNAL_HOLD_MS,
  liveGraceMs = DEFAULT_SIGNAL_LIVE_GRACE_MS,
}: {
  previous: SignalTrack[];
  frame: TelemetryFrame | null | undefined;
  activeClasses: string[] | null;
  nowMs: number;
  holdMs?: number;
  liveGraceMs?: number;
}): SignalTrack[] {
  const allowed = activeClasses && activeClasses.length > 0 ? new Set(activeClasses) : null;
  const hasFrame = frame !== null && frame !== undefined;
  const nextByKey = new Map<string, SignalTrack>();
  const previousByKey = new Map(previous.map((item) => [item.key, item]));

  for (const track of frame?.tracks ?? []) {
    if (allowed && !allowed.has(track.class_name)) {
      continue;
    }

    const key = trackKey(track);
    const existing = previousByKey.get(key);
    const state = signalStateForTelemetryTrack(track);
    const ageMs = signalAgeMsForTelemetryTrack(track);
    nextByKey.set(key, {
      key,
      track,
      color: colorForClass(track.class_name),
      state,
      firstSeenMs: existing?.firstSeenMs ?? nowMs,
      lastSeenMs: nowMs,
      ageMs,
    });
  }

  for (const item of previous) {
    if (nextByKey.has(item.key)) {
      continue;
    }
    if (allowed && !allowed.has(item.track.class_name)) {
      continue;
    }

    const ageMs = nowMs - item.lastSeenMs;
    if (!hasFrame && item.state === "live" && ageMs <= liveGraceMs) {
      nextByKey.set(item.key, {
        ...item,
        state: "live",
        ageMs,
      });
      continue;
    }

    if (ageMs <= holdMs) {
      nextByKey.set(item.key, {
        ...item,
        state: "held",
        ageMs,
      });
    }
  }

  return Array.from(nextByKey.values()).sort(compareSignalTracks);
}

export function deriveSignalCounts(tracks: SignalTrack[]): SignalCounts {
  const rowsByClass = new Map<string, SignalCountRow>();

  for (const signal of tracks) {
    const className = signal.track.class_name;
    const row =
      rowsByClass.get(className) ??
      {
        className,
        color: signal.color,
        liveCount: 0,
        heldCount: 0,
        totalCount: 0,
        state: "held" as SignalState,
      };

    if (signal.state === "live") {
      row.liveCount += 1;
    } else {
      row.heldCount += 1;
    }

    row.totalCount += 1;
    row.state = row.liveCount > 0 ? "live" : "held";
    rowsByClass.set(className, row);
  }

  const rows = Array.from(rowsByClass.values()).sort(
    (left, right) =>
      right.liveCount - left.liveCount ||
      right.totalCount - left.totalCount ||
      left.className.localeCompare(right.className),
  );

  return {
    liveTotal: rows.reduce((total, row) => total + row.liveCount, 0),
    heldTotal: rows.reduce((total, row) => total + row.heldCount, 0),
    total: rows.reduce((total, row) => total + row.totalCount, 0),
    rows,
  };
}

export function selectDrawableSignalTracks(
  tracks: SignalTrack[],
  streamMode: TelemetryFrame["stream_mode"] | null | undefined,
): SignalTrack[] {
  if (!shouldDrawBrowserTelemetryOverlay(streamMode)) {
    return [];
  }

  return tracks;
}

export function shouldDrawBrowserTelemetryOverlay(
  streamMode: TelemetryFrame["stream_mode"] | null | undefined,
): boolean {
  return streamMode !== "annotated-whip";
}

export function signalStateForTelemetryTrack(track: TelemetryTrack): SignalState {
  return track.track_state === "coasting" ? "held" : "live";
}

export function signalAgeMsForTelemetryTrack(track: TelemetryTrack): number {
  if (track.track_state !== "coasting") {
    return 0;
  }

  return Math.max(0, track.last_seen_age_ms ?? 0);
}

function compareSignalTracks(left: SignalTrack, right: SignalTrack): number {
  if (left.state !== right.state) {
    return left.state === "live" ? -1 : 1;
  }

  return left.track.class_name.localeCompare(right.track.class_name) || left.track.track_id - right.track.track_id;
}
