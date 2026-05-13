import { useEffect, useMemo, useRef } from "react";
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

import { type HistoryMetric, historyMetricCopy } from "@/lib/history-url-state";
import { cn } from "@/lib/utils";
import {
  bucketFromChartClick,
  buildHistoryChartOption,
  type HistoryTrendChartClickParams,
  type HistoryTrendSeries,
} from "./history-trend-chart-options";

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

export function HistoryTrendChart({
  series,
  className,
  metric = "occupancy",
  onBucketSelect,
}: {
  series: HistoryTrendSeries;
  className?: string;
  metric?: HistoryMetric;
  onBucketSelect?: (bucket: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsType | null>(null);
  const option = useMemo(() => buildHistoryChartOption(series), [series]);
  const metricCopy = historyMetricCopy(metric);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart =
      chartRef.current ?? init(container, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(option, true);
    const onClick = (params: HistoryTrendChartClickParams) => {
      const bucket = bucketFromChartClick(params, series.points);
      if (bucket) {
        onBucketSelect?.(bucket);
      }
    };
    chart.off("click");
    chart.on("click", onClick);
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      chart.off("click", onClick);
      window.removeEventListener("resize", onResize);
    };
  }, [onBucketSelect, option, series.points]);

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
      aria-label={`History trend chart for ${metricCopy.label.toLowerCase()}`}
    />
  );
}
