import { useEffect, useMemo, useRef, useState } from "react";

import { apiClient, toApiError } from "@/lib/api";
import type { TelemetryFrame } from "@/lib/live";
import { ensureTelemetryStore } from "@/stores/telemetry-store";
import { useAuthStore } from "@/stores/auth-store";

const BUCKET_COUNT = 30;
const BUCKET_MS = 60_000;

export type SparklineBuckets = Record<string, number[]>;
export type SparklineLatestValues = Record<string, number>;

export type UseLiveSparklineResult = {
  buckets: SparklineBuckets;
  latestValues: SparklineLatestValues;
  loading: boolean;
  error: Error | null;
};

function floorMinute(value: number): number {
  return value - (value % BUCKET_MS);
}

// windowEndMs is the START of the most recent bucket (i.e. floorMinute(now)).
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

function setBucketPeaks(
  buckets: SparklineBuckets,
  classesCount: Record<string, number>,
  index: number,
): SparklineBuckets {
  const next: SparklineBuckets = { ...buckets };
  for (const [cls, count] of Object.entries(classesCount)) {
    const series = next[cls] ?? new Array(BUCKET_COUNT).fill(0);
    const copy = series.slice();
    copy[index] = Math.max(copy[index] ?? 0, count);
    next[cls] = copy;
  }
  return next;
}

export function mergeOccupancySnapshot(
  buckets: SparklineBuckets,
  bucketStartMs: number,
  frame: Pick<TelemetryFrame, "counts">,
  windowEndMs: number,
): SparklineBuckets {
  const index = bucketIndex(bucketStartMs, windowEndMs);
  if (index < 0 || index >= BUCKET_COUNT) {
    return buckets;
  }
  return setBucketPeaks(buckets, frame.counts ?? {}, index);
}

function shiftBuckets(buckets: SparklineBuckets, steps: number): SparklineBuckets {
  if (steps <= 0) return buckets;
  const capped = Math.min(steps, BUCKET_COUNT);
  const next: SparklineBuckets = {};
  for (const [cls, series] of Object.entries(buckets)) {
    next[cls] = [...series.slice(capped), ...new Array(capped).fill(0)];
  }
  return next;
}

function latestBucketValues(buckets: SparklineBuckets): SparklineLatestValues {
  const latest: SparklineLatestValues = {};
  for (const [cls, series] of Object.entries(buckets)) {
    latest[cls] = series[BUCKET_COUNT - 1] ?? 0;
  }
  return latest;
}

export function useLiveSparkline(cameraId: string): UseLiveSparklineResult {
  const accessToken = useAuthStore((state) => state.accessToken);
  const tenantId = useAuthStore((state) => state.user?.tenantId ?? null);
  const windowEndRef = useRef<number>(floorMinute(Date.now()));
  const [buckets, setBuckets] = useState<SparklineBuckets>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [seedReady, setSeedReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const nowMs = Date.now();
    const currentBucketStartMs = floorMinute(nowMs);
    const fromDate = new Date(currentBucketStartMs - (BUCKET_COUNT - 1) * BUCKET_MS);
    windowEndRef.current = currentBucketStartMs;
    setSeedReady(false);

    (async () => {
      try {
        const { data, error: apiError } = await apiClient.GET("/api/v1/history/series", {
          params: {
            query: {
              granularity: "1m",
              metric: "occupancy",
              from: fromDate.toISOString(),
              to: new Date(currentBucketStartMs - 1).toISOString(),
              camera_ids: [cameraId],
            },
          },
        });
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
            const copy = series.slice();
            copy[idx] = Math.max(copy[idx] ?? 0, count);
            seed[cls] = copy;
          }
        }
        setBuckets(seed);
      } catch (err) {
        if (!cancelled) setError(err as Error);
      } finally {
        if (!cancelled) {
          setSeedReady(true);
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [cameraId]);

  useEffect(() => {
    if (!seedReady) return;

    const store = ensureTelemetryStore(accessToken, tenantId);
    if (!store) return;
    store.subscribe(cameraId);
    let lastFrame: TelemetryFrame | null = null;

    const applyFrame = (frame: TelemetryFrame) => {
      const alignedTsMs = floorMinute(Date.parse(frame.ts));
      const steps = Math.floor((alignedTsMs - windowEndRef.current) / BUCKET_MS);
      if (steps > 0) {
        windowEndRef.current += steps * BUCKET_MS;
        setBuckets((current) => shiftBuckets(current, steps));
      }

      const end = windowEndRef.current;
      const oldestBucketMs = end - (BUCKET_COUNT - 1) * BUCKET_MS;
      if (alignedTsMs < oldestBucketMs) return;

      const idx = bucketIndex(alignedTsMs, end);
      if (idx < 0 || idx >= BUCKET_COUNT) return;

      setBuckets((current) => setBucketPeaks(current, frame.counts ?? {}, idx));
    };

    const bufferedFrames = store
      .getBuffer(cameraId)
      .filter((frame) => floorMinute(Date.parse(frame.ts)) === windowEndRef.current);
    for (const frame of bufferedFrames) {
      applyFrame(frame);
      lastFrame = frame;
    }

    const unsubscribe = store.onChange(() => {
      const frame = store.getLatest(cameraId);
      if (!frame || frame === lastFrame) return;
      lastFrame = frame;
      applyFrame(frame);
    });

    return () => {
      unsubscribe();
      store.unsubscribe(cameraId);
    };
  }, [cameraId, accessToken, tenantId, seedReady]);

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

  const latestValues = useMemo(() => latestBucketValues(buckets), [buckets]);

  return { buckets, latestValues, loading, error };
}
