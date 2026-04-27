import { lazy, Suspense } from "react";

import { Badge } from "@/components/ui/badge";
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
  return (
    <section className="overflow-hidden rounded-lg border border-white/10 bg-[#050912]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Trend</p>
          <p className="mt-1 text-sm text-[#dce6f7]">{bucketCopy(granularity)}</p>
        </div>
        <Badge>{coverage.label}</Badge>
      </div>
      <Suspense fallback={<div className="px-6 py-16 text-sm text-[#93a7c5]">Loading chart...</div>}>
        <HistoryTrendChart
          className="px-2 py-4"
          metric={metric}
          series={series}
          onBucketSelect={onBucketSelect}
        />
      </Suspense>
    </section>
  );
}

function bucketCopy(granularity: string): string {
  if (granularity === "1h") return "Hourly buckets - timestamps mark bucket starts";
  if (granularity === "1d") return "Daily buckets - timestamps mark bucket starts";
  if (granularity === "5m") return "5-minute buckets - timestamps mark bucket starts";
  return "1-minute buckets - timestamps mark bucket starts";
}
