import { useMemo, useState } from "react";

import { useLiveSparkline } from "@/hooks/use-live-sparkline";

const PALETTE = ["#4f8cff", "#8b6dff", "#26d0ff", "#6de4a7", "#ffaf52", "#ff6b91", "#c28bff", "#f5d570"];
const TOP_N = 3;

type LiveSparklineProps = {
  cameraId: string;
  activeClasses: string[];
};

type RowProps = {
  className: string;
  color: string;
  series: number[];
  total: number;
};

function SparklineRow({ className, color, series, total }: RowProps) {
  const max = Math.max(1, ...series);
  const points = useMemo(
    () =>
      series
        .map((value, index) => {
          const x = (index / (series.length - 1)) * 100;
          const y = 100 - (value / max) * 100;
          return `${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(" "),
    [series, max],
  );
  return (
    <div className="flex items-center gap-2 text-xs text-[#d9e5f7]">
      <span className="w-16 truncate font-medium">{className}</span>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="h-5 flex-1"
        aria-label={`${className} sparkline`}
      >
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="3"
          vectorEffect="non-scaling-stroke"
          points={points}
        />
      </svg>
      <span className="w-10 text-right tabular-nums text-[#8ea8cf]">{total}</span>
    </div>
  );
}

export function LiveSparkline({ cameraId, activeClasses }: LiveSparklineProps) {
  const { buckets, totals, loading, error } = useLiveSparkline(cameraId);
  const [showAll, setShowAll] = useState(false);

  const ranked = useMemo(
    () =>
      activeClasses
        .map((cls) => [cls, totals[cls] ?? 0] as const)
        .sort(([, a], [, b]) => b - a)
        .map(([cls]) => cls),
    [activeClasses, totals],
  );
  const top = ranked.slice(0, TOP_N);
  const rest = ranked.slice(TOP_N);

  if (loading) {
    return <div className="h-16 animate-pulse rounded-md bg-white/[0.04]" />;
  }
  if (error) {
    return <p className="text-xs text-[#f0b7c1]">Sparkline unavailable: {error.message}</p>;
  }

  const renderRow = (cls: string, index: number) => (
    <SparklineRow
      key={cls}
      className={cls}
      color={PALETTE[index % PALETTE.length]}
      series={buckets[cls] ?? []}
      total={totals[cls] ?? 0}
    />
  );

  return (
    <div className="space-y-1.5">
      {top.map((cls, index) => renderRow(cls, index))}
      {rest.length > 0 && !showAll && (
        <button
          type="button"
          onClick={() => setShowAll(true)}
          className="text-xs text-[#8ea8cf] underline"
        >
          +{rest.length} more
        </button>
      )}
      {showAll && rest.map((cls, index) => renderRow(cls, TOP_N + index))}
    </div>
  );
}
