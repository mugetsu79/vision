import { useEffect, useMemo, useRef } from "react";
import type { EChartsOption } from "echarts";
import { BarChart, LineChart } from "echarts/charts";
import {
  BrushComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  ToolboxComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { init, type EChartsType, use as registerECharts } from "echarts/core";

import { cn } from "@/lib/utils";

type HistoryTrendPoint = {
  bucket: string;
  values: Record<string, number>;
  total_count?: number;
  speed_p50?: Record<string, number> | null;
  speed_p95?: Record<string, number> | null;
  speed_sample_count?: Record<string, number> | null;
  over_threshold_count?: Record<string, number> | null;
};

type HistoryTrendSeries = {
  classNames: string[];
  points: HistoryTrendPoint[];
  speedClassesUsed?: string[] | null;
  includeSpeed?: boolean;
  speedThreshold?: number | null;
};

registerECharts([
  LineChart,
  BarChart,
  BrushComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  ToolboxComponent,
  TooltipComponent,
  CanvasRenderer,
]);

const PALETTE = ["#4f8cff", "#8b6dff", "#26d0ff", "#6de4a7", "#ffaf52", "#ff6b91", "#c28bff", "#f5d570"];

export function buildHistoryChartOption(series: HistoryTrendSeries): EChartsOption {
  const buckets = series.points.map((p) => formatBucket(p.bucket));
  const speedOn = !!series.includeSpeed;
  const thresholdSet = speedOn && series.speedThreshold !== null && series.speedThreshold !== undefined;
  const speedClasses = series.speedClassesUsed ?? [];

  const grids: NonNullable<EChartsOption["grid"]> = [
    { top: 56, left: 20, right: 16, bottom: thresholdSet ? 260 : speedOn ? 216 : 56, containLabel: true },
  ];
  const xAxes: NonNullable<EChartsOption["xAxis"]> = [
    {
      type: "category",
      gridIndex: 0,
      boundaryGap: false,
      data: buckets,
      axisLine: { lineStyle: { color: "rgba(117, 146, 187, 0.32)" } },
      axisLabel: { color: "#8ea8cf", hideOverlap: true },
    },
  ];
  const yAxes: NonNullable<EChartsOption["yAxis"]> = [
    {
      type: "value",
      gridIndex: 0,
      minInterval: 1,
      splitLine: { lineStyle: { color: "rgba(117, 146, 187, 0.14)" } },
      axisLine: { show: false },
      axisLabel: { color: "#8ea8cf" },
    },
  ];

  const seriesList: NonNullable<EChartsOption["series"]> = series.classNames.map((cls, i) => ({
    name: cls,
    type: "line",
    smooth: true,
    showSymbol: false,
    color: PALETTE[i % PALETTE.length],
    lineStyle: { width: 2.5 },
    areaStyle: { opacity: 0.1 },
    xAxisIndex: 0,
    yAxisIndex: 0,
    data: series.points.map((p) => p.values[cls] ?? 0),
  }));

  if (thresholdSet) {
    grids.push({ top: 320, left: 20, right: 16, height: 56, containLabel: true });
    xAxes.push({
      type: "category",
      gridIndex: 1,
      boundaryGap: true,
      data: buckets,
      show: false,
    });
    yAxes.push({
      type: "value",
      gridIndex: 1,
      minInterval: 1,
      splitLine: { show: false },
      axisLine: { show: false },
      axisLabel: { color: "#8ea8cf" },
    });
    speedClasses.forEach((cls, i) => {
      seriesList.push({
        name: `${cls} (over threshold)`,
        type: "bar",
        stack: "violations",
        xAxisIndex: 1,
        yAxisIndex: 1,
        color: PALETTE[i % PALETTE.length],
        data: series.points.map((p) => p.over_threshold_count?.[cls] ?? 0),
      });
    });
  }

  if (speedOn) {
    const speedGridTop = thresholdSet ? 400 : 320;
    grids.push({ top: speedGridTop, left: 20, right: 16, bottom: 40, containLabel: true });
    xAxes.push({
      type: "category",
      gridIndex: grids.length - 1,
      boundaryGap: false,
      data: buckets,
      axisLine: { lineStyle: { color: "rgba(117, 146, 187, 0.32)" } },
      axisLabel: { color: "#8ea8cf", hideOverlap: true },
    });
    yAxes.push({
      type: "value",
      gridIndex: grids.length - 1,
      name: "km/h",
      nameTextStyle: { color: "#8ea8cf" },
      splitLine: { lineStyle: { color: "rgba(117, 146, 187, 0.14)" } },
      axisLine: { show: false },
      axisLabel: { color: "#8ea8cf" },
    });

    speedClasses.forEach((cls, i) => {
      const color = PALETTE[i % PALETTE.length];
      const xIndex = xAxes.length - 1;
      const yIndex = yAxes.length - 1;
      seriesList.push({
        name: `${cls} p50`,
        type: "line",
        smooth: true,
        showSymbol: false,
        xAxisIndex: xIndex,
        yAxisIndex: yIndex,
        color,
        lineStyle: { width: 2, type: "solid" },
        data: series.points.map((p) => p.speed_p50?.[cls] ?? null),
      });
      seriesList.push({
        name: `${cls} p95`,
        type: "line",
        smooth: true,
        showSymbol: false,
        xAxisIndex: xIndex,
        yAxisIndex: yIndex,
        color,
        lineStyle: { width: 1.5, type: "dashed" },
        areaStyle: { opacity: 0.08 },
        data: series.points.map((p) => p.speed_p95?.[cls] ?? null),
        markLine: thresholdSet && i === 0
          ? {
              symbol: "none",
              lineStyle: { color: "#ff6b91", type: "dashed" },
              data: [{ yAxis: series.speedThreshold ?? 0, name: "threshold" }],
            }
          : undefined,
      });
    });
  }

  return {
    animation: false,
    color: PALETTE,
    legend: { top: 0, textStyle: { color: "#dbe7ff" }, itemGap: 18 },
    grid: grids,
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", link: [{ xAxisIndex: "all" }] },
      backgroundColor: "rgba(6, 11, 18, 0.96)",
      borderColor: "rgba(90, 149, 255, 0.28)",
      textStyle: { color: "#eef4ff" },
    },
    toolbox: {
      right: 0,
      iconStyle: { borderColor: "#8ea8cf" },
      feature: {
        dataZoom: { yAxisIndex: "none" },
        restore: {},
      },
    },
    brush: { toolbox: ["rect", "clear"], xAxisIndex: "all" },
    xAxis: xAxes,
    yAxis: yAxes,
    series: seriesList,
  };
}

export function HistoryTrendChart({
  series,
  className,
}: {
  series: HistoryTrendSeries;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsType | null>(null);
  const option = useMemo(() => buildHistoryChartOption(series), [series]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart = chartRef.current ?? init(container, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(option, true);
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [option]);

  useEffect(() => {
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  const height = series.includeSpeed
    ? series.speedThreshold !== null && series.speedThreshold !== undefined
      ? "680px"
      : "560px"
    : "360px";

  return (
    <div
      ref={containerRef}
      className={cn("w-full", className)}
      style={{ height }}
      role="img"
      aria-label="History trend chart"
    />
  );
}

function formatBucket(value: string): string {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(date);
}
