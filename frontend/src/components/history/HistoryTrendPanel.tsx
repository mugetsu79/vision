import { motion } from "framer-motion";
import { lazy, Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import type { CoverageCopy } from "@/lib/history-workbench";
import type { HistoryMetric } from "@/lib/history-url-state";

const HistoryTrendChart = lazy(async () => ({
  default: (await import("@/components/history/HistoryTrendChart"))
    .HistoryTrendChart,
}));

type TrendSeries = {
  classNames: string[];
  points: Array<{
    bucket: string;
    values: Record<string, number>;
    total_count?: number;
    speed_p50?: Record<string, number> | null;
    speed_p95?: Record<string, number> | null;
    speed_sample_count?: Record<string, number> | null;
    over_threshold_count?: Record<string, number> | null;
  }>;
  includeSpeed?: boolean;
  speedThreshold?: number | null;
  speedClassesUsed?: string[] | null;
  selectedBucket?: string | null;
};

export function HistoryTrendPanel({
  series,
  metric,
  granularity,
  coverage,
  onBucketSelect,
}: {
  series: TrendSeries;
  metric: HistoryMetric;
  granularity: string;
  coverage: CoverageCopy;
  onBucketSelect: (bucket: string) => void;
}) {
  const reviewBucket =
    series.selectedBucket ?? series.points[0]?.bucket ?? null;
  const reviewBucketLabel = series.selectedBucket
    ? "Review selected bucket"
    : "Review first bucket";

  return (
    <section
      data-testid="pattern-trend-panel"
      className="overflow-hidden rounded-[0.9rem] border border-white/10 bg-[color:var(--vezor-surface-neutral)] shadow-[0_22px_56px_-48px_rgba(0,0,0,0.92)]"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
            Pattern trend
          </p>
          <p className="mt-1 text-sm text-[#dce6f7]">
            {bucketCopy(granularity)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select
            aria-label="Review bucket"
            className="h-8 w-44 rounded-xl px-3 py-1.5 text-xs"
            value={series.selectedBucket ?? ""}
            onChange={(event) => {
              if (event.currentTarget.value)
                onBucketSelect(event.currentTarget.value);
            }}
          >
            <option value="">Select bucket</option>
            {series.points.map((point) => (
              <option key={point.bucket} value={point.bucket}>
                {formatBucketOption(point.bucket)}
              </option>
            ))}
          </Select>
          <Button
            className="h-8 px-3 text-xs"
            disabled={!reviewBucket}
            onClick={() => {
              if (reviewBucket) onBucketSelect(reviewBucket);
            }}
          >
            {reviewBucketLabel}
          </Button>
          <Badge>{coverage.label}</Badge>
        </div>
      </div>
      <div className="relative">
        <Suspense
          fallback={
            <div className="px-6 py-16 text-sm text-[#93a7c5]">
              Loading chart...
            </div>
          }
        >
          <HistoryTrendChart
            className="px-2 py-4"
            metric={metric}
            series={series}
            onBucketSelect={onBucketSelect}
          />
        </Suspense>
        {series.selectedBucket ? (
          <motion.div
            key={series.selectedBucket}
            aria-hidden="true"
            data-testid="history-bucket-shaft"
            layoutId="history-bucket-shaft"
            className="pointer-events-none absolute top-0 bottom-0 w-[2.4%] bg-[rgba(110,189,255,0.12)]"
            style={{
              left: bucketLeftPercent(series.points, series.selectedBucket),
            }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="absolute left-1/2 top-0 bottom-0 w-px -translate-x-1/2 bg-[var(--vz-lens-cerulean)] opacity-60" />
          </motion.div>
        ) : null}
      </div>
      {coverage.status !== "populated" ? (
        <div className="border-t border-white/8 px-4 py-3 text-sm text-[#dce6f7]">
          <span className="font-semibold">{coverage.label}</span>
          <span className="ml-2 text-[#93a7c5]">{coverage.message}</span>
        </div>
      ) : null}
    </section>
  );
}

function bucketCopy(granularity: string): string {
  if (granularity === "1h")
    return "Hourly buckets - timestamps mark bucket starts";
  if (granularity === "1d")
    return "Daily buckets - timestamps mark bucket starts";
  if (granularity === "5m")
    return "5-minute buckets - timestamps mark bucket starts";
  return "1-minute buckets - timestamps mark bucket starts";
}

function formatBucketOption(bucket: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(new Date(bucket));
}

function bucketLeftPercent(
  points: ReadonlyArray<{ bucket: string }>,
  selected: string,
): string {
  const idx = points.findIndex((point) => point.bucket === selected);
  if (idx < 0 || points.length <= 1) return "0%";
  return `${(idx / (points.length - 1)) * 100}%`;
}
