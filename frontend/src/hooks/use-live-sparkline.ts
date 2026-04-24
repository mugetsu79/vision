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

// windowEndMs is the START of the most recent bucket (i.e. floorMinute(now)).
// tsMs MUST be aligned to its own bucket via floorMinute() before calling —
// otherwise frames in the current minute (tsMs > windowEndMs) produce a
// negative diff and spill past the last bucket.
function bucketIndex(alignedTsMs: number, windowEndMs: number): number {
  const diff = Math.floor((windowEndMs - alignedTsMs) / BUCKET_MS);
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

// Shift every class's series left by `steps` buckets and pad with zeros on the right.
function shiftBuckets(buckets: SparklineBuckets, steps: number): SparklineBuckets {
  if (steps <= 0) return buckets;
  const capped = Math.min(steps, BUCKET_COUNT);
  const next: SparklineBuckets = {};
  for (const [cls, series] of Object.entries(buckets)) {
    next[cls] = [
      ...series.slice(capped),
      ...new Array(capped).fill(0),
    ];
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
      const alignedTsMs = floorMinute(Date.parse(frame.ts));

      // Event-driven window rollover: if this frame's bucket is ahead of the
      // current window end, advance the window and shift existing buckets.
      const steps = Math.floor((alignedTsMs - windowEndRef.current) / BUCKET_MS);
      if (steps > 0) {
        windowEndRef.current += steps * BUCKET_MS;
        setBuckets((current) => shiftBuckets(current, steps));
      }

      const end = windowEndRef.current;
      if (alignedTsMs < end - (BUCKET_COUNT - 1) * BUCKET_MS) return;
      const idx = bucketIndex(alignedTsMs, end);
      if (idx < 0 || idx >= BUCKET_COUNT) return;
      setBuckets((current) => addCounts(current, frame.counts ?? {}, idx));
    });
    return () => {
      unsubscribe();
      store.unsubscribe(cameraId);
    };
  }, [cameraId, accessToken, tenantId]);

  // Clock-aligned rollover (safety net for idle cameras). Fires at every minute
  // boundary; the live handler above handles rollover event-driven when frames
  // arrive. Aligning to the wall clock means the bucket shifts on :00 seconds
  // regardless of when the component mounted.
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | null = null;
    let interval: ReturnType<typeof setInterval> | null = null;

    const rollWindowForward = () => {
      const nowBucket = floorMinute(Date.now());
      const steps = Math.floor((nowBucket - windowEndRef.current) / BUCKET_MS);
      if (steps <= 0) return;
      windowEndRef.current += steps * BUCKET_MS;
      setBuckets((current) => shiftBuckets(current, steps));
    };

    const msToNextMinute = BUCKET_MS - (Date.now() % BUCKET_MS);
    timeout = setTimeout(() => {
      rollWindowForward();
      interval = setInterval(rollWindowForward, BUCKET_MS);
    }, msToNextMinute);

    return () => {
      if (timeout !== null) clearTimeout(timeout);
      if (interval !== null) clearInterval(interval);
    };
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
