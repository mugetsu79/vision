import type { HistorySeriesResponse } from "@/hooks/use-history";

type CoverageStatus = NonNullable<HistorySeriesResponse["coverage_status"]>;
type HistoryRow = HistorySeriesResponse["rows"][number];

export type CoverageCopy = {
  status: CoverageStatus;
  label: string;
  message: string;
};

export type BucketDetail = {
  bucket: string;
  bucketSpan: string;
  values: Record<string, number>;
  totalCount: number;
  coverage: CoverageCopy;
  speedP50: Record<string, number>;
  speedP95: Record<string, number>;
  overThresholdCount: Record<string, number>;
};

const COVERAGE_COPY: Record<CoverageStatus, Omit<CoverageCopy, "status">> = {
  populated: {
    label: "Populated",
    message: "Detections are available for this bucket.",
  },
  zero: {
    label: "No detections",
    message: "Telemetry was valid and no detections matched this scope.",
  },
  no_telemetry: {
    label: "No telemetry",
    message: "No usable telemetry was available for this bucket.",
  },
  camera_offline: {
    label: "Camera offline",
    message: "The selected camera was offline for this bucket.",
  },
  worker_offline: {
    label: "Worker offline",
    message: "Processing was unavailable for this bucket.",
  },
  source_unavailable: {
    label: "Source unavailable",
    message: "The stream source was unavailable for this bucket.",
  },
  no_scope: {
    label: "No scope selected",
    message: "The current filters exclude usable cameras, classes, or boundaries.",
  },
  access_limited: {
    label: "Access limited",
    message: "Some matching data may be hidden by your tenant or permission scope.",
  },
};

const BUCKET_DURATION_MS: Partial<Record<string, number>> = {
  "1m": 60 * 1000,
  "5m": 5 * 60 * 1000,
  "1h": 60 * 60 * 1000,
  "1d": 24 * 60 * 60 * 1000,
};

export function getCoverageCopy(status: CoverageStatus | undefined | null): CoverageCopy {
  const resolved: CoverageStatus = status ?? "populated";
  return { status: resolved, ...COVERAGE_COPY[resolved] };
}

export function buildDisplaySeries(series: HistorySeriesResponse): {
  classNames: string[];
  points: HistoryRow[];
} {
  if (series.class_names.length > 0) {
    return {
      classNames: series.class_names,
      points: series.rows,
    };
  }

  return {
    classNames: ["Total"],
    points: series.rows.map((row) => ({
      ...row,
      values: { Total: row.total_count },
    })),
  };
}

export function buildBucketDetails(
  series: HistorySeriesResponse,
  selectedBucket: string | null,
): BucketDetail | null {
  if (!selectedBucket) return null;
  const row = series.rows.find((entry) => entry.bucket === selectedBucket);
  if (!row) return null;
  const coverageEntry = series.coverage_by_bucket?.find((entry) => entry.bucket === selectedBucket);
  return {
    bucket: row.bucket,
    bucketSpan: formatBucketSpan(row.bucket, series.granularity),
    values: row.values,
    totalCount: row.total_count,
    coverage: getCoverageCopy(coverageEntry?.status ?? series.coverage_status),
    speedP50: compactRecord(row.speed_p50),
    speedP95: compactRecord(row.speed_p95),
    overThresholdCount: compactRecord(row.over_threshold_count),
  };
}

export function formatBucketSpan(bucket: string, granularity: string): string {
  const start = new Date(bucket);
  const durationMs = BUCKET_DURATION_MS[granularity] ?? 1;
  const end = new Date(start.getTime() + durationMs - 1);
  const format = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
  return `${format.format(start)}-${format.format(end)}`;
}

function compactRecord(value: Record<string, number> | null | undefined): Record<string, number> {
  return value ?? {};
}
