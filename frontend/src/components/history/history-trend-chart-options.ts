import type { EChartsOption } from "echarts";

import { colorForClass } from "@/lib/signal-colors";

export type HistoryTrendPoint = {
  bucket: string;
  values: Record<string, number>;
  total_count?: number;
  speed_p50?: Record<string, number> | null;
  speed_p95?: Record<string, number> | null;
  speed_sample_count?: Record<string, number> | null;
  over_threshold_count?: Record<string, number> | null;
};

export type HistoryTrendSeries = {
  classNames: string[];
  points: HistoryTrendPoint[];
  speedClassesUsed?: string[] | null;
  includeSpeed?: boolean;
  speedThreshold?: number | null;
  selectedBucket?: string | null;
};

export type HistoryTrendChartClickParams = {
  componentType?: string;
  dataType?: string;
  dataIndex?: number;
};

export function bucketFromChartClick(
  params: HistoryTrendChartClickParams,
  points: HistoryTrendPoint[],
): string | null {
  if (params.componentType !== "series") return null;
  if (params.dataType === "markLine") return null;
  if (typeof params.dataIndex !== "number") return null;
  return points[params.dataIndex]?.bucket ?? null;
}

export function buildHistoryChartOption(
  series: HistoryTrendSeries,
): EChartsOption {
  const buckets = series.points.map((p) => formatBucket(p.bucket));
  const selectedBucketLabel = series.selectedBucket
    ? formatBucket(series.selectedBucket)
    : null;
  const speedOn = !!series.includeSpeed;
  const thresholdSet =
    speedOn &&
    series.speedThreshold !== null &&
    series.speedThreshold !== undefined;
  const speedClasses = series.speedClassesUsed ?? [];

  const paletteOf = (cls: string) => colorForClass(cls).stroke;
  const palette = Array.from(
    new Set([...series.classNames, ...speedClasses].map(paletteOf)),
  );

  const grids: NonNullable<EChartsOption["grid"]> = [
    {
      top: 56,
      left: 20,
      right: 16,
      bottom: thresholdSet ? 260 : speedOn ? 216 : 56,
      containLabel: true,
    },
  ];
  const xAxes: NonNullable<EChartsOption["xAxis"]> = [
    {
      type: "category",
      gridIndex: 0,
      boundaryGap: false,
      data: buckets,
      axisLine: { lineStyle: { color: "rgba(206, 224, 255, 0.16)" } },
      axisLabel: { color: "#8497b3", hideOverlap: true },
    },
  ];
  const yAxes: NonNullable<EChartsOption["yAxis"]> = [
    {
      type: "value",
      gridIndex: 0,
      minInterval: 1,
      splitLine: { lineStyle: { color: "rgba(206, 224, 255, 0.08)" } },
      axisLine: { lineStyle: { color: "rgba(206, 224, 255, 0.16)" } },
      axisLabel: { color: "#8497b3" },
    },
  ];

  const seriesList: NonNullable<EChartsOption["series"]> =
    series.classNames.map((cls) => ({
      name: cls,
      type: "line",
      smooth: true,
      showSymbol: false,
      color: paletteOf(cls),
      lineStyle: { width: 3 },
      areaStyle: { opacity: 0.12 },
      emphasis: { focus: "series" },
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: series.points.map((p) => p.values[cls] ?? 0),
      markLine: selectedBucketLabel
        ? {
          symbol: "none",
            lineStyle: {
              color: "rgba(110, 189, 255, 0.42)",
              type: "dashed",
              width: 1.5,
            },
            data: [{ xAxis: selectedBucketLabel, name: "selected bucket" }],
          }
        : undefined,
    }));

  if (thresholdSet) {
    grids.push({
      top: 320,
      left: 20,
      right: 16,
      height: 56,
      containLabel: true,
    });
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
      axisLine: { lineStyle: { color: "rgba(206, 224, 255, 0.16)" } },
      axisLabel: { color: "#8497b3" },
    });
    speedClasses.forEach((cls) => {
      seriesList.push({
        name: `${cls} (over threshold)`,
        type: "bar",
        stack: "violations",
        xAxisIndex: 1,
        yAxisIndex: 1,
        color: paletteOf(cls),
        data: series.points.map((p) => p.over_threshold_count?.[cls] ?? 0),
      });
    });
  }

  if (speedOn) {
    const speedGridTop = thresholdSet ? 400 : 320;
    grids.push({
      top: speedGridTop,
      left: 20,
      right: 16,
      bottom: 40,
      containLabel: true,
    });
    xAxes.push({
      type: "category",
      gridIndex: grids.length - 1,
      boundaryGap: false,
      data: buckets,
      axisLine: { lineStyle: { color: "rgba(206, 224, 255, 0.16)" } },
      axisLabel: { color: "#8497b3", hideOverlap: true },
    });
    yAxes.push({
      type: "value",
      gridIndex: grids.length - 1,
      name: "km/h",
      nameTextStyle: { color: "#8497b3" },
      splitLine: { lineStyle: { color: "rgba(206, 224, 255, 0.08)" } },
      axisLine: { lineStyle: { color: "rgba(206, 224, 255, 0.16)" } },
      axisLabel: { color: "#8497b3" },
    });

    speedClasses.forEach((cls, i) => {
      const color = paletteOf(cls);
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
        lineStyle: { width: 2.4, type: "solid" },
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
        lineStyle: { width: 1.8, type: "dashed" },
        areaStyle: { opacity: 0.06 },
        data: series.points.map((p) => p.speed_p95?.[cls] ?? null),
        markLine:
          thresholdSet && i === 0
            ? {
                symbol: "none",
                lineStyle: { color: "#ff6f9d", type: "dashed", width: 1.5 },
                data: [
                  { yAxis: series.speedThreshold ?? 0, name: "threshold" },
                ],
              }
            : undefined,
      });
    });
  }

  return {
    animation: false,
    color: palette,
    legend: { top: 0, textStyle: { color: "#dbe7ff" }, itemGap: 18 },
    grid: grids,
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", link: [{ xAxisIndex: "all" }] },
      backgroundColor: "rgba(3, 5, 10, 0.96)",
      borderColor: "rgba(110, 189, 255, 0.28)",
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
