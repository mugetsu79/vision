import { useMemo } from "react";

import { useLiveSparkline } from "@/hooks/use-live-sparkline";
import type { SignalCountRow } from "@/lib/live-signal-stability";

type TelemetryTerrainProps = {
  cameraId: string;
  cameraName: string;
  activeClasses: string[];
  signalRows: SignalCountRow[];
};

const EMPTY_SERIES = [0, 0, 0, 0, 0, 0];
const FALLBACK_COLOR = {
  family: "other" as const,
  stroke: "#4dd7ff",
  fill: "rgba(77, 215, 255, 0.12)",
  text: "#d9f7ff",
};

export function TelemetryTerrain({
  cameraId,
  cameraName,
  activeClasses,
  signalRows,
}: TelemetryTerrainProps) {
  const { buckets, loading, error } = useLiveSparkline(cameraId);

  const rankedRows = useMemo<SignalCountRow[]>(() => {
    if (signalRows.length > 0) {
      return signalRows.slice(0, 3);
    }

    return activeClasses.slice(0, 3).map((className) => ({
      className,
      color: FALLBACK_COLOR,
      liveCount: 0,
      heldCount: 0,
      totalCount: 0,
      state: "held",
    }));
  }, [activeClasses, signalRows]);

  const primary = rankedRows[0];
  const series = primary ? (buckets[primary.className] ?? EMPTY_SERIES) : EMPTY_SERIES;
  const terrainId = `telemetry-terrain-${sanitizeId(cameraId)}`;
  const linePath = buildLinePath(series);
  const areaPath = buildAreaPath(series);

  if (loading) {
    return <div className="h-20 animate-pulse rounded-md bg-white/[0.04]" />;
  }

  if (error) {
    return <p className="text-xs text-[#f0b7c1]">Telemetry terrain unavailable: {error.message}</p>;
  }

  return (
    <section
      aria-label={`${cameraName} telemetry terrain`}
      data-testid="telemetry-terrain"
      className="space-y-3 rounded-md border border-white/10 bg-[#08111f]/80 p-3"
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-[#d9e5f7]">
          Telemetry terrain
        </h3>
        <div className="flex flex-wrap justify-end gap-1.5">
          {rankedRows.map((row) => (
            <span
              key={row.className}
              className="inline-flex items-center gap-1 rounded border border-white/10 px-1.5 py-0.5 text-[11px] font-medium text-[#c9d7eb]"
            >
              <span
                aria-hidden="true"
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: row.color.stroke }}
              />
              {row.className} {row.state === "live" ? "active" : "held"}
            </span>
          ))}
        </div>
      </div>

      <svg
        aria-label={`${primary?.className ?? "scene"} signal terrain`}
        className="h-16 w-full overflow-visible"
        preserveAspectRatio="none"
        role="img"
        viewBox="0 0 100 48"
      >
        <defs>
          <linearGradient id={terrainId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={primary?.color.stroke ?? FALLBACK_COLOR.stroke} stopOpacity="0.34" />
            <stop offset="100%" stopColor={primary?.color.stroke ?? FALLBACK_COLOR.stroke} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill={`url(#${terrainId})`} />
        <path
          d={linePath}
          fill="none"
          stroke={primary?.color.stroke ?? FALLBACK_COLOR.stroke}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2.5"
          vectorEffect="non-scaling-stroke"
        />
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

  return `${line} L 100.00 46.00 L 0.00 46.00 Z`;
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
    y: 42 - (Math.max(0, value) / max) * 34,
  }));
}

function sanitizeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}
