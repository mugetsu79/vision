import type { components } from "@/lib/api.generated";

export type TelemetryFrame = components["schemas"]["TelemetryFrame"];
export type TelemetryTrack = components["schemas"]["TelemetryTrack"];
export type HeartbeatStatus = "unknown" | "fresh" | "stale";

export function parseTelemetryPayload(payload: unknown): TelemetryFrame[] {
  if (isTelemetryFrame(payload)) {
    return [payload];
  }

  if (
    typeof payload === "object" &&
    payload !== null &&
    Array.isArray((payload as { events?: unknown }).events)
  ) {
    return (payload as { events: unknown[] }).events.filter(isTelemetryFrame);
  }

  return [];
}

export function filterTracks(
  frame: TelemetryFrame | null | undefined,
  activeClasses: string[] | null,
): TelemetryTrack[] {
  if (!frame) {
    return [];
  }

  if (!activeClasses || activeClasses.length === 0) {
    return frame.tracks;
  }

  const allowed = new Set(activeClasses);
  return frame.tracks.filter((track) => allowed.has(track.class_name));
}

export function countTracksByClass(
  frame: TelemetryFrame | null | undefined,
  activeClasses: string[] | null,
): Record<string, number> {
  const counts: Record<string, number> = {};

  for (const track of filterTracks(frame, activeClasses)) {
    counts[track.class_name] = (counts[track.class_name] ?? 0) + 1;
  }

  return counts;
}

export function getHeartbeatStatus(
  frame: TelemetryFrame | null | undefined,
  maxAgeMs = 15_000,
): HeartbeatStatus {
  if (!frame) {
    return "unknown";
  }

  const ts = Date.parse(frame.ts);
  if (Number.isNaN(ts)) {
    return "unknown";
  }

  return Date.now() - ts <= maxAgeMs ? "fresh" : "stale";
}

export function isHeartbeatFresh(
  frame: TelemetryFrame | null | undefined,
  maxAgeMs = 15_000,
): boolean {
  return getHeartbeatStatus(frame, maxAgeMs) === "fresh";
}

export function formatHeartbeat(frame: TelemetryFrame | null | undefined): string {
  if (!frame) {
    return "Awaiting heartbeat";
  }

  const ts = Date.parse(frame.ts);
  if (Number.isNaN(ts)) {
    return "Awaiting heartbeat";
  }

  const deltaSeconds = Math.max(0, Math.round((Date.now() - ts) / 1000));
  if (deltaSeconds < 2) {
    return "Heartbeat live";
  }
  if (deltaSeconds < 60) {
    return `Heartbeat ${deltaSeconds}s ago`;
  }

  const deltaMinutes = Math.round(deltaSeconds / 60);
  return `Heartbeat ${deltaMinutes}m ago`;
}

function isTelemetryFrame(value: unknown): value is TelemetryFrame {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as { camera_id?: unknown; tracks?: unknown; ts?: unknown };
  return (
    typeof candidate.camera_id === "string" &&
    typeof candidate.ts === "string" &&
    Array.isArray(candidate.tracks)
  );
}
