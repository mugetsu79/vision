import { lazy, startTransition, Suspense, useDeferredValue, useMemo, useState } from "react";
import type { DateRange } from "react-day-picker";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Select } from "@/components/ui/select";
import { productBrand } from "@/brand/product";
import { useCameras } from "@/hooks/use-cameras";
import { downloadHistoryExport, useHistorySeries } from "@/hooks/use-history";

type Granularity = "1m" | "5m" | "1h" | "1d";

const HistoryTrendChart = lazy(async () => ({
  default: (await import("@/components/history/HistoryTrendChart")).HistoryTrendChart,
}));

export function HistoryPage() {
  const brandName = productBrand.name;
  const { data: cameras = [] } = useCameras();
  const [granularity, setGranularity] = useState<Granularity>("1h");
  const [selectedCameraIds, setSelectedCameraIds] = useState<string[]>([]);
  const [selectedClassNames, setSelectedClassNames] = useState<string[]>([]);
  const [range, setRange] = useState<DateRange | undefined>(() => createDefaultRange());
  const [isDownloading, setIsDownloading] = useState<"csv" | "parquet" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const filters = useMemo(
    () => ({
      from: range?.from ?? createDefaultRange().from!,
      to: range?.to ?? new Date(),
      granularity,
      cameraIds: selectedCameraIds,
      classNames: selectedClassNames,
    }),
    [granularity, range, selectedCameraIds, selectedClassNames],
  );

  const { data, isLoading, error } = useHistorySeries(filters);
  const deferredData = useDeferredValue(data);

  const chartSeries = useMemo(
    () => ({
      classNames: deferredData?.class_names ?? [],
      points: deferredData?.rows ?? [],
    }),
    [deferredData],
  );

  const availableClassNames = useMemo(() => {
    if (selectedClassNames.length === 0) {
      return data?.class_names ?? [];
    }

    return Array.from(
      new Set([...(data?.class_names ?? []), ...selectedClassNames]),
    );
  }, [data?.class_names, selectedClassNames]);

  const totalCount = useMemo(
    () => (deferredData?.rows ?? []).reduce((sum, row) => sum + row.total_count, 0),
    [deferredData],
  );

  const chartEmpty = !isLoading && (deferredData?.rows.length ?? 0) === 0;

  async function handleDownload(format: "csv" | "parquet") {
    setIsDownloading(format);
    setDownloadError(null);
    try {
      await downloadHistoryExport(filters, format);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : `Failed to export ${format}.`);
    } finally {
      setIsDownloading(null);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(62,115,255,0.16),transparent_34%),linear-gradient(180deg,rgba(13,18,29,0.98),rgba(5,8,14,0.96))] shadow-[0_36px_100px_-62px_rgba(53,107,255,0.45)]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
                History
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
                Fleet history without reshaping penalties in the browser.
              </h2>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                {brandName} delivers chart-ready time buckets directly from the backend so long
                forensic ranges stay fast even when operators pivot across classes and
                cameras.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                {granularity}
              </Badge>
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                {totalCount} detections
              </Badge>
            </div>
          </div>
        </div>

        <div className="space-y-6 px-6 py-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea8cf]">
                Time window
              </p>
              <p className="mt-2 text-sm text-[#dce6f7]">{formatRangeLabel(filters.from, filters.to)}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                className="bg-white/[0.06] px-4 py-2 text-[#e7efff] shadow-none hover:bg-white/[0.1]"
                onClick={() => {
                  startTransition(() => setRange(createPresetRange(1)));
                }}
              >
                Last 24h
              </Button>
              <Button
                className="bg-white/[0.06] px-4 py-2 text-[#e7efff] shadow-none hover:bg-white/[0.1]"
                onClick={() => {
                  startTransition(() => setRange(createPresetRange(7)));
                }}
              >
                Last 7d
              </Button>
              <Button disabled={isDownloading !== null} onClick={() => void handleDownload("csv")}>
                {isDownloading === "csv" ? "Downloading..." : "Download CSV"}
              </Button>
              <Button
                disabled={isDownloading !== null}
                className="bg-white/[0.06] text-[#edf3ff] shadow-none hover:bg-white/[0.1]"
                onClick={() => void handleDownload("parquet")}
              >
                {isDownloading === "parquet" ? "Downloading..." : "Download Parquet"}
              </Button>
            </div>
          </div>

          <div className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(8,13,22,0.98),rgba(4,7,12,0.96))]">
            {isLoading ? (
              <div className="px-6 py-16 text-sm text-[#93a7c5]">Loading history…</div>
            ) : error ? (
              <div className="px-6 py-16 text-sm text-[#f0b7c1]">
                {error instanceof Error ? error.message : "Failed to load history."}
              </div>
            ) : chartEmpty ? (
              <div className="px-6 py-16 text-sm text-[#93a7c5]">
                No history rows matched the current filters.
              </div>
            ) : (
              <Suspense fallback={<div className="px-6 py-16 text-sm text-[#93a7c5]">Loading chart…</div>}>
                <HistoryTrendChart className="px-2 py-4" series={chartSeries} />
              </Suspense>
            )}
          </div>

          {downloadError ? <p className="text-sm text-[#f0b7c1]">{downloadError}</p> : null}
        </div>
      </section>

      <aside className="space-y-6">
        <section className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,15,24,0.98),rgba(4,7,12,0.96))]">
          <div className="border-b border-white/8 px-5 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">
              Date range
            </p>
            <h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">
              Calendar-driven forensic window
            </h3>
          </div>
          <div className="px-4 py-4">
            <Calendar
              aria-label="History date range"
              mode="range"
              numberOfMonths={2}
              selected={range}
              defaultMonth={range?.from}
              onSelect={(nextRange) => {
                startTransition(() => {
                  setRange(normalizeRange(nextRange));
                });
              }}
            />
          </div>
        </section>

        <section className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,15,24,0.98),rgba(4,7,12,0.96))]">
          <div className="border-b border-white/8 px-5 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">
              Filters
            </p>
            <h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">
              Scope the historical view
            </h3>
          </div>

          <div className="space-y-4 px-5 py-5">
            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
                Granularity
              </span>
              <Select
                aria-label="Granularity"
                value={granularity}
                onChange={(event) => {
                  setGranularity(event.target.value as Granularity);
                }}
              >
                <option value="1m">1 minute</option>
                <option value="5m">5 minutes</option>
                <option value="1h">1 hour</option>
                <option value="1d">1 day</option>
              </Select>
            </label>

            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
                Camera filters
              </span>
              <Select
                aria-label="Camera filters"
                multiple
                className="min-h-36 rounded-[1.5rem] py-3"
                value={selectedCameraIds}
                onChange={(event) => {
                  setSelectedCameraIds(readSelectedValues(event.currentTarget));
                }}
              >
                {cameras.map((camera) => (
                  <option key={camera.id} value={camera.id}>
                    {camera.name}
                  </option>
                ))}
              </Select>
            </label>

            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
                Class filters
              </span>
              <Select
                aria-label="Class filters"
                multiple
                className="min-h-36 rounded-[1.5rem] py-3"
                value={selectedClassNames}
                onChange={(event) => {
                  setSelectedClassNames(readSelectedValues(event.currentTarget));
                }}
              >
                {availableClassNames.map((className) => (
                  <option key={className} value={className}>
                    {className}
                  </option>
                ))}
              </Select>
            </label>
          </div>
        </section>
      </aside>
    </div>
  );
}

function createDefaultRange(): DateRange {
  return createPresetRange(7);
}

function createPresetRange(days: number): DateRange {
  const to = new Date();
  to.setSeconds(0, 0);
  const from = new Date(to);
  from.setDate(from.getDate() - days);
  return { from, to };
}

function normalizeRange(range: DateRange | undefined): DateRange | undefined {
  if (!range?.from) {
    return range;
  }
  if (!range.to) {
    return { from: range.from, to: new Date() };
  }
  return range;
}

function readSelectedValues(element: HTMLSelectElement): string[] {
  return Array.from(element.selectedOptions, (option) => option.value);
}

function formatRangeLabel(from: Date, to: Date): string {
  return `${from.toLocaleDateString("en-GB", { month: "short", day: "numeric", year: "numeric" })} to ${to.toLocaleDateString("en-GB", { month: "short", day: "numeric", year: "numeric" })}`;
}
