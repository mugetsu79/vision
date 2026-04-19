import { useEffect, useMemo, useRef } from "react";
import type { EChartsOption } from "echarts";
import { BrushComponent, GridComponent, LegendComponent, ToolboxComponent, TooltipComponent } from "echarts/components";
import { LineChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { init, type EChartsType, use as registerECharts } from "echarts/core";

import { cn } from "@/lib/utils";

type HistoryTrendSeries = {
  classNames: string[];
  points: Array<{
    bucket: string;
    values: Record<string, number>;
    total_count?: number;
  }>;
};

registerECharts([
  LineChart,
  BrushComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  TooltipComponent,
  CanvasRenderer,
]);

export function HistoryTrendChart({
  series,
  className,
}: {
  series: HistoryTrendSeries;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsType | null>(null);

  const option = useMemo<EChartsOption>(() => {
    const buckets = series.points.map((point) => formatBucket(point.bucket));
    return {
      animation: false,
      color: ["#4f8cff", "#8b6dff", "#26d0ff", "#6de4a7", "#ffaf52", "#ff6b91"],
      legend: {
        top: 0,
        textStyle: { color: "#dbe7ff" },
        itemGap: 18,
      },
      grid: {
        top: 56,
        left: 20,
        right: 16,
        bottom: 56,
        containLabel: true,
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(6, 11, 18, 0.96)",
        borderColor: "rgba(90, 149, 255, 0.28)",
        textStyle: { color: "#eef4ff" },
      },
      toolbox: {
        right: 0,
        iconStyle: {
          borderColor: "#8ea8cf",
        },
        feature: {
          dataZoom: { yAxisIndex: "none" },
          restore: {},
        },
      },
      brush: {
        toolbox: ["rect", "clear"],
        xAxisIndex: "all",
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: buckets,
        axisLine: { lineStyle: { color: "rgba(117, 146, 187, 0.32)" } },
        axisLabel: { color: "#8ea8cf", hideOverlap: true },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        splitLine: { lineStyle: { color: "rgba(117, 146, 187, 0.14)" } },
        axisLine: { show: false },
        axisLabel: { color: "#8ea8cf" },
      },
      series: series.classNames.map((className) => ({
        name: className,
        type: "line",
        smooth: true,
        showSymbol: false,
        emphasis: { focus: "series" },
        lineStyle: { width: 2.5 },
        areaStyle: { opacity: 0.1 },
        data: series.points.map((point) => point.values[className] ?? 0),
      })),
    };
  }, [series]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const chart = chartRef.current ?? init(container, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(option, true);

    function handleResize() {
      chart.resize();
    }

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [option]);

  useEffect(() => {
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={cn("h-[360px] w-full", className)}
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
