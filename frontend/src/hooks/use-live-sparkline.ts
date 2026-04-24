import { useEffect, useMemo, useRef, useState } from "react";

import { apiClient, toApiError } from "@/lib/api";
import type { TelemetryFrame } from "@/lib/live";
import { ensureTelemetryStore } from "@/stores/telemetry-store";
import { useAuthStore } from "@/stores/auth-store";

const BUCKET_COUNT = 30;
const BUCKET_MS = 60_000;

export type SparklineBuckets = Record<string, number[]>;
export type SparklineTotals = Record<string, number>;

export type UseLiveSparklineResult = {
  buckets: SparklineBuckets;
  totals: SparklineTotals;
  loading: boolean;
  error: Error | null;
};

function floorMinute(value: number): number {
  return value - (value % BUCKET_MS);
}

function bucketIndex(tsMs: number, windowEndMs: number): number {
  const diff = Math.floor((windowEndMs - tsMs) / BUCKET_MS);
  return BUCKET_COUNT - 1 - diff;
}

function emptyBuckets(classes: string[]): SparklineBuckets {
  const out: SparklineBuckets = {};
  for (const cls of classes) {
    out[cls] = new Array(BUCKET_COUNT).fill(0);
  }
  return out;
}

function addCounts(
  buckets: SparklineBuckets,
  classesCount: Record<string, number>,
  index: number,
): SparklineBuckets {
  const next: SparklineBuckets = { ...buckets };
  for (const [cls, count] of Object.entries(classesCount)) {
    const series = next[cls] ?? new Array(BUCKET_COUNT).fill(0);
    const copy = series.slice();
    copy[index] = (copy[index] ?? 0) + count;
    next[cls] = copy;
  }
  return next;
}

export function useLiveSparkline(cameraId: string): UseLiveSparklineResult {
  const accessToken = useAuthStore((state) => state.accessToken);
  const tenantId = useAuthStore((state) => state.user?.tenantId ?? null);
  const windowEndRef = useRef<number>(floorMinute(Date.now()));
  const [buckets, setBuckets] = useState<SparklineBuckets>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Seed from history
  useEffect(() => {
    let cancelled = false;
    const now = new Date();
    const fromDate = new Date(now.getTime() - BUCKET_COUNT * BUCKET_MS);
    windowEndRef.current = floorMinute(now.getTime());
    (async () => {
      try {
        const { data, error: apiError } = await apiClient.GET(
          "/api/v1/history/series",
          {
            params: {
              query: {
                granularity: "1m",
                from: fromDate.toISOString(),
                to: now.toISOString(),
                camera_ids: [cameraId],
              },
            },
          },
        );
        if (cancelled) return;
        if (apiError || !data) {
          throw toApiError(apiError, "Failed to seed sparkline.");
        }
        const classNames = data.class_names ?? [];
        const seed = emptyBuckets(classNames);
        for (const row of data.rows ?? []) {
          const tsMs = Date.parse(row.bucket);
          const idx = bucketIndex(tsMs, windowEndRef.current);
          if (idx < 0 || idx >= BUCKET_COUNT) continue;
          for (const [cls, count] of Object.entries(row.values ?? {})) {
            const series = seed[cls] ?? new Array(BUCKET_COUNT).fill(0);
            series[idx] = (series[idx] ?? 0) + count;
            seed[cls] = series;
          }
        }
        setBuckets(seed);
      } catch (err) {
        if (!cancelled) setError(err as Error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cameraId]);

  // Live updates from telemetry store
  useEffect(() => {
    const store = ensureTelemetryStore(accessToken, tenantId);
    if (!store) return;
    store.subscribe(cameraId);
    let lastFrame: TelemetryFrame | null = null;
    const unsubscribe = store.onChange(() => {
      const frame = store.getLatest(cameraId);
      if (!frame || frame === lastFrame) return;
      lastFrame = frame;
      const tsMs = Date.parse(frame.ts);
      const end = windowEndRef.current;
      if (tsMs < end - BUCKET_COUNT * BUCKET_MS) return;
      const idx = bucketIndex(tsMs, end);
      if (idx < 0 || idx >= BUCKET_COUNT) return;
      setBuckets((current) => addCounts(current, frame.counts ?? {}, idx));
    });
    return () => {
      unsubscribe();
      store.unsubscribe(cameraId);
    };
  }, [cameraId, accessToken, tenantId]);

  // Minute rollover
  useEffect(() => {
    const id = setInterval(() => {
      windowEndRef.current = floorMinute(Date.now());
      setBuckets((current) => {
        const next: SparklineBuckets = {};
        for (const [cls, series] of Object.entries(current)) {
          next[cls] = [...series.slice(1), 0];
        }
        return next;
      });
    }, BUCKET_MS);
    return () => clearInterval(id);
  }, []);

  const totals = useMemo(() => {
    const out: SparklineTotals = {};
    for (const [cls, series] of Object.entries(buckets)) {
      out[cls] = series.reduce((a, b) => a + b, 0);
    }
    return out;
  }, [buckets]);

  return { buckets, totals, loading, error };
}
