import { Badge } from "@/components/ui/badge";
import { type BucketDetail } from "@/lib/history-workbench";
import { type HistoryMetric, historyMetricCopy } from "@/lib/history-url-state";

export function HistoryBucketDetail({
  detail,
  metric,
}: {
  detail: BucketDetail | null;
  metric: HistoryMetric;
}) {
  const metricCopy = historyMetricCopy(metric);

  return (
    <section className="rounded-lg border border-white/10 bg-[#07101c] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Bucket review</h2>
          <h3
            className="mt-1 text-lg font-semibold text-[#f3f7ff]"
            aria-label={detail ? undefined : "Select a bucket"}
          >
            {detail ? formatBucketHeading(detail.bucket) : "Choose a bucket"}
          </h3>
        </div>
        {detail ? <Badge>{detail.coverage.label}</Badge> : null}
      </div>

      {!detail ? (
        <p className="mt-4 text-sm text-[#93a7c5]">
          Select a bucket from the chart to inspect totals, coverage, and speed signals.
        </p>
      ) : (
        <div className="mt-4 space-y-4">
          <div>
            <p className="text-2xl font-semibold text-[#f4f8ff]">
              {detail.totalCount} {metricCopy.countLabel}
            </p>
            <p className="mt-1 text-sm text-[#93a7c5]">
              {detail.bucketSpan} UTC - {detail.coverage.message}
            </p>
          </div>

          <div className="space-y-2">
            {Object.entries(detail.values).map(([className, value]) => (
              <div
                key={className}
                className="flex items-center justify-between rounded-md bg-white/[0.04] px-3 py-2 text-sm"
              >
                <span className="text-[#dce6f7]">{className}</span>
                <span className="font-semibold text-[#f4f8ff]">{value}</span>
              </div>
            ))}
          </div>

          {Object.keys(detail.speedP50).length > 0 || Object.keys(detail.speedP95).length > 0 ? (
            <div className="space-y-2 rounded-md border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-[#dce6f7]">
              {Object.keys({ ...detail.speedP50, ...detail.speedP95 }).map((className) => (
                <p key={className}>
                  {className}: p50 {formatSpeed(detail.speedP50[className])}, p95{" "}
                  {formatSpeed(detail.speedP95[className])}
                </p>
              ))}
            </div>
          ) : null}

          {Object.keys(detail.overThresholdCount).length > 0 ? (
            <div className="rounded-md border border-[#705e29] bg-[#1d1b08]/80 px-3 py-2 text-sm text-[#ffe5a8]">
              {Object.entries(detail.overThresholdCount).map(([className, value]) => (
                <p key={className}>
                  {value} {className} over speed threshold
                </p>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

function formatBucketHeading(bucket: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(new Date(bucket));
}

function formatSpeed(value: number | undefined): string {
  return typeof value === "number" ? `${value} km/h` : "none";
}
