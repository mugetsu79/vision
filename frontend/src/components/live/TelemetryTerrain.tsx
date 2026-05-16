import { useMemo } from "react";

import { useLiveSparkline } from "@/hooks/use-live-sparkline";
import {
  colorForClass,
  type SignalCountRow,
} from "@/lib/live-signal-stability";

type TelemetryTerrainProps = {
  cameraId: string;
  cameraName: string;
  activeClasses: string[];
  signalRows: SignalCountRow[];
};

const EMPTY_SERIES = [0, 0, 0, 0, 0, 0];

export function TelemetryTerrain({
  cameraId,
  cameraName,
  activeClasses,
  signalRows,
}: TelemetryTerrainProps) {
  const { buckets, latestValues, loading, error } = useLiveSparkline(cameraId);

  const rankedRows = useMemo<SignalCountRow[]>(() => {
    if (signalRows.length > 0) {
      return signalRows.slice(0, 3);
    }

    return activeClasses.slice(0, 3).map((className) => ({
      className,
      color: colorForClass(className),
      liveCount: 0,
      heldCount: 0,
      totalCount: 0,
      state: "held",
    }));
  }, [activeClasses, signalRows]);

  const trendRows = rankedRows.slice(0, 3).map((row) => ({
    row,
    series: buckets[row.className] ?? EMPTY_SERIES,
    latestValue: latestValues[row.className] ?? 0,
  }));
  const primaryTrend = trendRows[0];
  const terrainId = `telemetry-terrain-${sanitizeId(cameraId)}`;

  if (loading) {
    return (
      <div className="h-32 animate-pulse rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.04] lg:h-36" />
    );
  }

  if (error) {
    return (
      <section
        aria-label={`${cameraName} telemetry terrain`}
        data-testid="telemetry-terrain"
        className="min-h-32 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[linear-gradient(180deg,rgba(8,17,31,0.9),rgba(4,9,17,0.88))] p-4"
      >
        <p className="text-xs text-[#f0b7c1]">
          Signal trend unavailable: {error.message}
        </p>
      </section>
    );
  }

  return (
    <section
      aria-label={`${cameraName} telemetry terrain`}
      data-testid="telemetry-terrain"
      className="space-y-3 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[linear-gradient(180deg,rgba(8,17,31,0.9),rgba(4,9,17,0.88))] p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-[#d9e5f7]">
          Signal trend
        </h3>
        <div className="flex flex-wrap justify-end gap-1.5">
          {trendRows.map(({ row, latestValue }) => (
            <span
              key={row.className}
              className="inline-flex items-center gap-1 rounded border border-white/10 px-1.5 py-0.5 text-[11px] font-medium"
              style={{ color: row.color.text }}
            >
              <span
                aria-hidden="true"
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: row.color.stroke }}
              />
              {row.className} {row.state === "live" ? "active" : "held"}{" "}
              {currentCountForRow(row, latestValue)}
            </span>
          ))}
        </div>
      </div>

      <svg
        aria-label={`${primaryTrend?.row.className ?? "scene"} signal trend`}
        className="h-32 w-full overflow-visible lg:h-36"
        preserveAspectRatio="none"
        role="img"
        viewBox="0 0 100 72"
      >
        <defs>
          <linearGradient id={terrainId} x1="0" x2="0" y1="0" y2="1">
            <stop
              offset="0%"
              stopColor={primaryTrend?.row.color.stroke ?? "#4dd7ff"}
              stopOpacity="0.34"
            />
            <stop
              offset="100%"
              stopColor={primaryTrend?.row.color.stroke ?? "#4dd7ff"}
              stopOpacity="0.02"
            />
          </linearGradient>
        </defs>
        {primaryTrend ? (
          <path d={buildAreaPath(primaryTrend.series)} fill={`url(#${terrainId})`} />
        ) : null}
        {trendRows.map(({ row, series }, index) => (
          <path
            key={row.className}
            d={buildLinePath(series)}
            fill="none"
            stroke={row.color.stroke}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={index === 0 ? "3" : "2"}
            opacity={index === 0 ? 1 : 0.72}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
    </section>
  );
}

function buildLinePath(series: number[]): string {
  const points = normalizeSeries(series);
  return buildStepPath(points);
}

function buildAreaPath(series: number[]): string {
  const points = normalizeSeries(series);
  const line = buildStepPath(points);

  return `${line} L 100.00 68.00 L 0.00 68.00 Z`;
}

function buildStepPath(points: Array<{ x: number; y: number }>): string {
  const [first, ...rest] = points;
  if (!first) {
    return "";
  }

  const segments = [`M ${first.x.toFixed(2)} ${first.y.toFixed(2)}`];
  for (const point of rest) {
    segments.push(`H ${point.x.toFixed(2)}`, `V ${point.y.toFixed(2)}`);
  }

  return segments.join(" ");
}

function normalizeSeries(series: number[]): Array<{ x: number; y: number }> {
  const values = series.length > 0 ? series : EMPTY_SERIES;
  const max = Math.max(1, ...values);
  const divisor = Math.max(1, values.length - 1);

  return values.map((value, index) => ({
    x: (index / divisor) * 100,
    y: 62 - (Math.max(0, value) / max) * 50,
  }));
}

function currentCountForRow(row: SignalCountRow, latestValue: number): number {
  const liveOrHeldCount = row.state === "live" ? row.liveCount : row.heldCount;
  return liveOrHeldCount > 0 ? liveOrHeldCount : latestValue;
}

function sanitizeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}
