import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];
type TelemetryTrack = components["schemas"]["TelemetryTrack"];

export const DEFAULT_SIGNAL_HOLD_MS = 1_200;

export type SignalState = "live" | "held";
export type SignalColorFamily = "human" | "vehicle" | "safety" | "alert" | "other";

export type SignalColor = {
  family: SignalColorFamily;
  stroke: string;
  fill: string;
  text: string;
};

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

const HUMAN_CLASSES = new Set(["person", "worker", "hi_vis_worker"]);
const VEHICLE_CLASSES = new Set(["car", "truck", "bus", "motorcycle", "bicycle"]);
const SAFETY_CLASSES = new Set(["helmet", "vest", "ppe", "hard_hat"]);
const ALERT_CLASSES = new Set(["violation", "alert", "intrusion"]);

const FALLBACK_COLORS: SignalColor[] = [
  { family: "other", stroke: "#4dd7ff", fill: "rgba(77, 215, 255, 0.12)", text: "#d9f7ff" },
  { family: "other", stroke: "#a98bff", fill: "rgba(169, 139, 255, 0.13)", text: "#eee8ff" },
  { family: "other", stroke: "#f7c56b", fill: "rgba(247, 197, 107, 0.12)", text: "#fff1ca" },
];

export function trackKey(track: Pick<TelemetryTrack, "class_name" | "track_id">): string {
  return `${track.class_name}:${track.track_id}`;
}

export function colorForClass(className: string): SignalColor {
  const normalized = className.toLowerCase();
  if (HUMAN_CLASSES.has(normalized)) {
    return { family: "human", stroke: "#61e6a6", fill: "rgba(97, 230, 166, 0.12)", text: "#e8fff4" };
  }
  if (VEHICLE_CLASSES.has(normalized)) {
    return { family: "vehicle", stroke: "#62a6ff", fill: "rgba(98, 166, 255, 0.12)", text: "#e9f3ff" };
  }
  if (SAFETY_CLASSES.has(normalized)) {
    return { family: "safety", stroke: "#f7c56b", fill: "rgba(247, 197, 107, 0.13)", text: "#fff2cf" };
  }
  if (ALERT_CLASSES.has(normalized)) {
    return { family: "alert", stroke: "#ff6f9d", fill: "rgba(255, 111, 157, 0.13)", text: "#ffe7ef" };
  }

  return FALLBACK_COLORS[hashClassName(normalized) % FALLBACK_COLORS.length];
}

export function updateSignalTracks({
  previous,
  frame,
  activeClasses,
  nowMs,
  holdMs = DEFAULT_SIGNAL_HOLD_MS,
}: {
  previous: SignalTrack[];
  frame: TelemetryFrame | null | undefined;
  activeClasses: string[] | null;
  nowMs: number;
  holdMs?: number;
}): SignalTrack[] {
  const allowed = activeClasses && activeClasses.length > 0 ? new Set(activeClasses) : null;
  const nextByKey = new Map<string, SignalTrack>();
  const previousByKey = new Map(previous.map((item) => [item.key, item]));

  for (const track of frame?.tracks ?? []) {
    if (allowed && !allowed.has(track.class_name)) {
      continue;
    }

    const key = trackKey(track);
    const existing = previousByKey.get(key);
    nextByKey.set(key, {
      key,
      track,
      color: colorForClass(track.class_name),
      state: "live",
      firstSeenMs: existing?.firstSeenMs ?? nowMs,
      lastSeenMs: nowMs,
      ageMs: 0,
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

function compareSignalTracks(left: SignalTrack, right: SignalTrack): number {
  if (left.state !== right.state) {
    return left.state === "live" ? -1 : 1;
  }

  return left.track.class_name.localeCompare(right.track.class_name) || left.track.track_id - right.track.track_id;
}

function hashClassName(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}
