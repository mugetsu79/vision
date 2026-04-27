import type { Camera } from "@/hooks/use-cameras";
import type { HistoryClassesResponse, HistorySeriesResponse } from "@/hooks/use-history";

export type HistorySearchResult =
  | { id: string; type: "camera"; group: "Cameras"; label: string; cameraId: string }
  | { id: string; type: "class"; group: "Classes"; label: string; className: string }
  | { id: string; type: "boundary"; group: "Boundaries"; label: string; boundaryId: string; cameraId?: string }
  | { id: string; type: "bucket"; group: "Buckets" | "Gaps" | "Speed breaches"; label: string; bucket: string };

export function buildHistorySearchResults({
  query,
  cameras,
  classes,
  series,
}: {
  query: string;
  cameras: Camera[];
  classes: HistoryClassesResponse | HistoryClassesResponse["classes"];
  series: HistorySeriesResponse | null | undefined;
}): HistorySearchResult[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return [];

  const results: HistorySearchResult[] = [];
  const classEntries = Array.isArray(classes) ? classes : classes.classes;
  const boundaryEntries = Array.isArray(classes) ? [] : (classes.boundaries ?? []);

  for (const camera of cameras) {
    if (matches(camera.name, normalized)) {
      results.push({
        id: `camera:${camera.id}`,
        type: "camera",
        group: "Cameras",
        label: camera.name,
        cameraId: camera.id,
      });
    }

    for (const zone of camera.zones ?? []) {
      const boundary = readBoundary(zone);
      if (!boundary || (!matches(boundary.id, normalized) && !matches(boundary.name, normalized))) {
        continue;
      }
      results.push({
        id: `boundary:${camera.id}:${boundary.id}`,
        type: "boundary",
        group: "Boundaries",
        label: boundary.name ?? boundary.id,
        boundaryId: boundary.id,
        cameraId: camera.id,
      });
    }
  }

  for (const entry of classEntries) {
    if (matches(entry.class_name, normalized)) {
      results.push({
        id: `class:${entry.class_name}`,
        type: "class",
        group: "Classes",
        label: entry.class_name,
        className: entry.class_name,
      });
    }
  }

  for (const boundary of boundaryEntries) {
    if (matches(boundary.boundary_id, normalized)) {
      results.push({
        id: `boundary:${boundary.boundary_id}`,
        type: "boundary",
        group: "Boundaries",
        label: boundary.boundary_id,
        boundaryId: boundary.boundary_id,
      });
    }
  }

  if (series) {
    const coverageByBucket = new Map(
      (series.coverage_by_bucket ?? []).map((entry) => [entry.bucket, entry.status]),
    );
    for (const row of series.rows) {
      const coverage = coverageByBucket.get(row.bucket);
      const overThreshold = Object.values(row.over_threshold_count ?? {}).reduce(
        (sum, value) => sum + value,
        0,
      );

      if (hasToken(normalized, "zero") && coverage === "zero") {
        results.push({
          id: `bucket:zero:${row.bucket}`,
          type: "bucket",
          group: "Buckets",
          label: `Zero detections · ${formatBucket(row.bucket)}`,
          bucket: row.bucket,
        });
      }

      if ((hasToken(normalized, "gap") || hasToken(normalized, "telemetry")) && coverage === "no_telemetry") {
        results.push({
          id: `bucket:gap:${row.bucket}`,
          type: "bucket",
          group: "Gaps",
          label: `No telemetry · ${formatBucket(row.bucket)}`,
          bucket: row.bucket,
        });
      }

      if ((hasToken(normalized, "speed") || hasToken(normalized, "breach")) && overThreshold > 0) {
        results.push({
          id: `bucket:speed:${row.bucket}`,
          type: "bucket",
          group: "Speed breaches",
          label: `${overThreshold} speed breaches · ${formatBucket(row.bucket)}`,
          bucket: row.bucket,
        });
      }

      if ((hasToken(normalized, "spike") || hasToken(normalized, "heavy")) && row.total_count >= 10) {
        results.push({
          id: `bucket:spike:${row.bucket}`,
          type: "bucket",
          group: "Buckets",
          label: `${row.total_count} events · ${formatBucket(row.bucket)}`,
          bucket: row.bucket,
        });
      }
    }
  }

  return results.slice(0, 20);
}

function matches(value: string | null | undefined, query: string): boolean {
  return value?.toLowerCase().includes(query) ?? false;
}

function hasToken(query: string, token: string): boolean {
  return query.includes(token);
}

function readBoundary(zone: unknown): { id: string; name?: string } | null {
  if (!zone || typeof zone !== "object") return null;
  const record = zone as Record<string, unknown>;
  const id = typeof record.id === "string" ? record.id.trim() : "";
  const name = typeof record.name === "string" ? record.name.trim() : "";
  const boundaryId = id || name;
  if (!boundaryId) return null;
  return { id: boundaryId, name: name || undefined };
}

function formatBucket(bucket: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(new Date(bucket));
}
