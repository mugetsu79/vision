import { lazy, startTransition, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { productBrand } from "@/brand/product";
import { COCO_CLASSES } from "@/lib/coco-classes";
import {
  type HistoryFilterState,
  readHistoryFiltersFromSearch,
  writeHistoryFiltersToSearch,
} from "@/lib/history-url-state";
import { useCameras } from "@/hooks/use-cameras";
import {
  downloadHistoryExport,
  useHistoryClasses,
  useHistorySeries,
} from "@/hooks/use-history";

const HistoryTrendChart = lazy(async () => ({
  default: (await import("@/components/history/HistoryTrendChart")).HistoryTrendChart,
}));

export function HistoryPage() {
  const brandName = productBrand.name;
  const location = useLocation();
  const navigate = useNavigate();
  const { data: cameras = [] } = useCameras();

  const [state, setState] = useState<HistoryFilterState>(() =>
    readHistoryFiltersFromSearch(new URLSearchParams(location.search)),
  );
  const [showAllClasses, setShowAllClasses] = useState(false);
  const [isDownloading, setIsDownloading] = useState<"csv" | "parquet" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const applyState = useCallback(
    (next: HistoryFilterState | ((prev: HistoryFilterState) => HistoryFilterState)) => {
      setState((prev) => {
        const resolved = typeof next === "function" ? next(prev) : next;
        const search = writeHistoryFiltersToSearch(resolved);
        navigate({ pathname: location.pathname, search: `?${search}` }, { replace: true });
        return resolved;
      });
    },
    [location.pathname, navigate],
  );

  useEffect(() => {
    const parsed = readHistoryFiltersFromSearch(new URLSearchParams(location.search));
    setState(parsed);
  }, [location.search]);

  const filters = useMemo(
    () => ({
      from: state.from,
      to: state.to,
      granularity: state.granularity,
      cameraIds: state.cameraIds,
      classNames: state.classNames,
      includeSpeed: state.speed,
      speedThreshold: state.speedThreshold,
    }),
    [state],
  );

  const { data, isLoading, error } = useHistorySeries(filters);
  const { data: classesData } = useHistoryClasses({
    from: state.from,
    to: state.to,
    cameraIds: state.cameraIds,
  });

  const observedClasses = useMemo(
    () => classesData?.classes ?? [],
    [classesData],
  );
  const unseenCocoClasses = useMemo(() => {
    const seen = new Set(observedClasses.map((c) => c.class_name));
    return COCO_CLASSES.filter((name) => !seen.has(name));
  }, [observedClasses]);

  const chartSeries = useMemo(
    () => ({
      classNames: data?.class_names ?? [],
      points: data?.rows ?? [],
      includeSpeed: state.speed,
      speedThreshold: state.speedThreshold ?? null,
      speedClassesUsed: data?.speed_classes_used ?? null,
    }),
    [data, state.speed, state.speedThreshold],
  );

  const totalCount = useMemo(
    () => (data?.rows ?? []).reduce((sum, row) => sum + row.total_count, 0),
    [data],
  );

  const chartEmpty = !isLoading && (data?.rows.length ?? 0) === 0;
  const granularityBumped = data?.granularity_adjusted === true;
  const speedCapped = data?.speed_classes_capped === true;
  const speedRequestedButEmpty =
    state.speed && !isLoading && (data?.speed_classes_used?.length ?? 0) === 0;

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

  function applyPresetRange(days: number) {
    applyState((prev) => {
      const to = new Date();
      to.setSeconds(0, 0);
      const from = new Date(to);
      from.setDate(from.getDate() - days);
      return { ...prev, from, to };
    });
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.98),rgba(5,8,14,0.96))]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">History</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
                Fleet history and speed telemetry.
              </h2>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                {brandName} aggregates detections and speeds in buckets so operators can pivot across classes and
                cameras without reshaping data in the browser.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">{state.granularity}</Badge>
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">{totalCount} detections</Badge>
              {granularityBumped ? (
                <Badge className="border-[#705e29] bg-[#1d1b08]/80 text-[#ffe5a8]">
                  granularity adjusted to {data?.granularity}
                </Badge>
              ) : null}
              {speedCapped ? (
                <Badge className="border-[#705e29] bg-[#1d1b08]/80 text-[#ffe5a8]">
                  speed panel capped at 20 classes
                </Badge>
              ) : null}
            </div>
          </div>
        </div>

        <div className="space-y-6 px-6 py-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea8cf]">Time window</p>
              <p className="mt-2 text-sm text-[#dce6f7]">{formatRangeLabel(state.from, state.to)}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                className="bg-white/[0.06] px-4 py-2 text-[#e7efff] shadow-none hover:bg-white/[0.1]"
                onClick={() => applyPresetRange(1)}
              >
                Last 24h
              </Button>
              <Button
                className="bg-white/[0.06] px-4 py-2 text-[#e7efff] shadow-none hover:bg-white/[0.1]"
                onClick={() => applyPresetRange(7)}
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
              <div className="space-y-4 px-6 py-16 text-sm text-[#93a7c5]">
                <p>No detections in this window for the selected cameras and classes.</p>
                <Button onClick={() => applyPresetRange(7)}>Try last 7 days</Button>
              </div>
            ) : (
              <div className="space-y-3">
                {speedRequestedButEmpty ? (
                  <p className="px-6 pt-4 text-sm text-[#ffd28a]">
                    None of the selected classes have speed data in this window — try widening the range or check camera homography.
                  </p>
                ) : null}
                <Suspense fallback={<div className="px-6 py-16 text-sm text-[#93a7c5]">Loading chart…</div>}>
                  <HistoryTrendChart className="px-2 py-4" series={chartSeries} />
                </Suspense>
              </div>
            )}
          </div>

          {downloadError ? <p className="text-sm text-[#f0b7c1]">{downloadError}</p> : null}
        </div>
      </section>

      <aside className="space-y-6">
        <section className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,15,24,0.98),rgba(4,7,12,0.96))]">
          <div className="border-b border-white/8 px-5 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">Filters</p>
            <h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">Scope the historical view</h3>
          </div>

          <div className="space-y-4 px-5 py-5">
            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Granularity</span>
              <Select
                aria-label="Granularity"
                value={state.granularity}
                onChange={(e) =>
                  applyState((p) => ({ ...p, granularity: e.target.value as HistoryFilterState["granularity"] }))
                }
              >
                <option value="1m">1 minute</option>
                <option value="5m">5 minutes</option>
                <option value="1h">1 hour</option>
                <option value="1d">1 day</option>
              </Select>
            </label>

            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Camera filters</span>
              <Select
                aria-label="Camera filters"
                multiple
                className="min-h-36 rounded-[1.5rem] py-3"
                value={state.cameraIds}
                onChange={(e) =>
                  applyState((p) => ({ ...p, cameraIds: Array.from(e.currentTarget.selectedOptions, (o) => o.value) }))
                }
              >
                {cameras.map((camera) => (
                  <option key={camera.id} value={camera.id}>
                    {camera.name}
                  </option>
                ))}
              </Select>
            </label>

            <div className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Class filters</span>
              <Select
                aria-label="Class filters"
                multiple
                className="min-h-36 rounded-[1.5rem] py-3"
                value={state.classNames}
                onChange={(e) =>
                  applyState((p) => ({ ...p, classNames: Array.from(e.currentTarget.selectedOptions, (o) => o.value) }))
                }
              >
                {observedClasses.map((entry) => (
                  <option key={entry.class_name} value={entry.class_name}>
                    {entry.class_name} ({entry.event_count})
                    {entry.has_speed_data ? "" : " — no speed data in this window"}
                  </option>
                ))}
                {showAllClasses
                  ? unseenCocoClasses.map((name) => (
                      <option key={name} value={name}>
                        {name} (0)
                      </option>
                    ))
                  : null}
              </Select>
              <button
                type="button"
                className="text-xs text-[#8ea8cf] underline"
                onClick={() => setShowAllClasses((v) => !v)}
              >
                {showAllClasses ? "Hide unseen classes" : "Show all 80 COCO classes"}
              </button>
            </div>

            <label className="flex items-center gap-2 text-sm text-[#d9e5f7]">
              <input
                type="checkbox"
                aria-label="Show speed"
                checked={state.speed}
                onChange={(e) => applyState((p) => ({ ...p, speed: e.target.checked }))}
              />
              <span>Show speed</span>
            </label>

            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
                Speed threshold (km/h)
              </span>
              <Input
                aria-label="Speed threshold"
                type="number"
                min={0}
                step={1}
                disabled={!state.speed}
                value={state.speedThreshold ?? ""}
                onChange={(e) => {
                  const raw = e.target.value.trim();
                  applyState((p) => ({
                    ...p,
                    speedThreshold: raw === "" ? null : Number(raw),
                  }));
                }}
              />
            </label>
          </div>
        </section>
      </aside>
    </div>
  );
}

function formatRangeLabel(from: Date, to: Date): string {
  const fmt = (d: Date) =>
    d.toLocaleDateString("en-GB", { month: "short", day: "numeric", year: "numeric" });
  return `${fmt(from)} to ${fmt(to)}`;
}
