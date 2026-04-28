import { lazy, Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import type { CoverageCopy } from "@/lib/history-workbench";
import type { HistoryMetric } from "@/lib/history-url-state";

const HistoryTrendChart = lazy(async () => ({
  default: (await import("@/components/history/HistoryTrendChart")).HistoryTrendChart,
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
  const reviewBucket = series.selectedBucket ?? series.points[0]?.bucket ?? null;
  const reviewBucketLabel = series.selectedBucket ? "Review selected bucket" : "Review first bucket";

  return (
    <section className="overflow-hidden rounded-[1.1rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,15,24,0.98),rgba(5,9,18,0.98))] shadow-[0_22px_56px_-46px_rgba(63,121,255,0.42)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Trend</p>
          <p className="mt-1 text-sm text-[#dce6f7]">{bucketCopy(granularity)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select
            aria-label="Review bucket"
            className="h-8 w-44 rounded-xl px-3 py-1.5 text-xs"
            value={series.selectedBucket ?? ""}
            onChange={(event) => {
              if (event.currentTarget.value) onBucketSelect(event.currentTarget.value);
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
      <Suspense fallback={<div className="px-6 py-16 text-sm text-[#93a7c5]">Loading chart...</div>}>
        <HistoryTrendChart
          className="px-2 py-4"
          metric={metric}
          series={series}
          onBucketSelect={onBucketSelect}
        />
      </Suspense>
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
  if (granularity === "1h") return "Hourly buckets - timestamps mark bucket starts";
  if (granularity === "1d") return "Daily buckets - timestamps mark bucket starts";
  if (granularity === "5m") return "5-minute buckets - timestamps mark bucket starts";
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
