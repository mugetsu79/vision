import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { HistoryBucketDetail } from "@/components/history/HistoryBucketDetail";
import { HistoryToolbar } from "@/components/history/HistoryToolbar";
import { HistoryTrendPanel } from "@/components/history/HistoryTrendPanel";
import { OmniSightField } from "@/components/brand/OmniSightField";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { omniLabels } from "@/copy/omnisight";
import { COCO_CLASSES } from "@/lib/coco-classes";
import { buildHistorySearchResults, type HistorySearchResult } from "@/lib/history-search";
import { buildBucketDetails, buildDisplaySeries, getCoverageCopy } from "@/lib/history-workbench";
import {
  type HistoryFilterState,
  type HistoryMetric,
  type RelativeHistoryWindow,
  historyMetricCopy,
  readHistoryFiltersFromSearch,
  resolveRelativeWindow,
  writeHistoryFiltersToSearch,
} from "@/lib/history-url-state";
import { useCameras } from "@/hooks/use-cameras";
import {
  downloadHistoryExport,
  useHistoryClasses,
  useHistorySeries,
} from "@/hooks/use-history";

export function HistoryPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { data: cameras = [] } = useCameras();
  const selfWrittenSearchRef = useRef<string | null>(null);

  const [state, setState] = useState<HistoryFilterState>(() =>
    readHistoryFiltersFromSearch(new URLSearchParams(location.search)),
  );
  const [showAllClasses, setShowAllClasses] = useState(false);
  const [isDownloading, setIsDownloading] = useState<"csv" | "parquet" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [selectedBucket, setSelectedBucket] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [, setFollowNowRefreshKey] = useState(0);

  const applyState = useCallback(
    (next: HistoryFilterState | ((prev: HistoryFilterState) => HistoryFilterState)) => {
      setState((prev) => {
        const resolved = typeof next === "function" ? next(prev) : next;
        return resolved;
      });
      // navigate happens after commit, via useEffect on `state` below
    },
    [],
  );

  // When state changes, sync the URL (replace so back-button stays natural).
  useEffect(() => {
    const search = writeHistoryFiltersToSearch(state);
    const currentSearch = location.search.startsWith("?")
      ? location.search.slice(1)
      : location.search;
    if (search !== currentSearch) {
      selfWrittenSearchRef.current = search;
      navigate({ pathname: location.pathname, search: `?${search}` }, { replace: true });
    }
  }, [state, location.pathname, location.search, navigate]);

  useEffect(() => {
    const currentSearch = location.search.startsWith("?")
      ? location.search.slice(1)
      : location.search;
    if (selfWrittenSearchRef.current === currentSearch) {
      selfWrittenSearchRef.current = null;
      return;
    }
    const parsed = readHistoryFiltersFromSearch(new URLSearchParams(location.search));
    setState(parsed);
  }, [location.search]);

  useEffect(() => {
    if (state.windowMode !== "relative" || !state.followNow) return;
    const interval = window.setInterval(() => {
      setFollowNowRefreshKey((key) => key + 1);
    }, 60_000);
    return () => window.clearInterval(interval);
  }, [state.followNow, state.relativeWindow, state.windowMode]);

  const resolvedWindow =
    state.windowMode === "relative" && state.followNow
      ? resolveRelativeWindow(state.relativeWindow)
      : { from: state.from, to: state.to };

  const filters = useMemo(
    () => ({
      from: resolvedWindow.from,
      to: resolvedWindow.to,
      granularity: state.granularity,
      metric: resolveHistoryMetric(state.metric, cameras, state.cameraIds),
      cameraIds: state.cameraIds,
      classNames: state.classNames,
      includeSpeed: state.speed,
      speedThreshold: state.speedThreshold,
    }),
    [
      cameras,
      resolvedWindow.from,
      resolvedWindow.to,
      state.cameraIds,
      state.classNames,
      state.granularity,
      state.metric,
      state.speed,
      state.speedThreshold,
    ],
  );

  const metric = filters.metric;
  const metricCopy = useMemo(() => historyMetricCopy(metric), [metric]);

  const { data, isLoading, error } = useHistorySeries(filters);
  const { data: classesData } = useHistoryClasses({
    from: resolvedWindow.from,
    to: resolvedWindow.to,
    metric,
    cameraIds: state.cameraIds,
  });

  const observedClasses = useMemo(
    () => classesData?.classes ?? [],
    [classesData],
  );
  const searchResults = useMemo(
    () =>
      buildHistorySearchResults({
        query: search,
        cameras,
        classes: classesData ?? observedClasses,
        series: data,
      }),
    [cameras, classesData, data, observedClasses, search],
  );
  const unseenCocoClasses = useMemo(() => {
    const seen = new Set(observedClasses.map((c) => c.class_name));
    return COCO_CLASSES.filter((name) => !seen.has(name));
  }, [observedClasses]);

  const displaySeries = useMemo(
    () => (data ? buildDisplaySeries(data) : { classNames: [], points: [] }),
    [data],
  );
  const validSelectedBucket = useMemo(() => {
    if (!selectedBucket) return null;
    return data?.rows.some((row) => row.bucket === selectedBucket) ? selectedBucket : null;
  }, [data?.rows, selectedBucket]);
  const bucketDetail = useMemo(
    () => (data ? buildBucketDetails(data, validSelectedBucket) : null),
    [data, validSelectedBucket],
  );
  const coverageCopy = useMemo(() => getCoverageCopy(data?.coverage_status), [data?.coverage_status]);

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

  function applyPresetRange(relativeWindow: RelativeHistoryWindow) {
    applyState((prev) => {
      const { from, to } = resolveRelativeWindow(relativeWindow);
      return { ...prev, from, to, windowMode: "relative", relativeWindow, followNow: true };
    });
  }

  function resumeFollowingNow() {
    applyState((prev) => {
      const relativeWindow = prev.windowMode === "relative" ? prev.relativeWindow : "last_24h";
      const { from, to } = resolveRelativeWindow(relativeWindow);
      return { ...prev, from, to, windowMode: "relative", relativeWindow, followNow: true };
    });
  }

  function selectSearchResult(result: HistorySearchResult) {
    if (result.type === "camera") {
      applyState((previous) => ({ ...previous, cameraIds: [result.cameraId] }));
    }
    if (result.type === "class") {
      applyState((previous) => ({ ...previous, classNames: [result.className] }));
    }
    if (result.type === "boundary" && result.cameraId) {
      const cameraId = result.cameraId;
      applyState((previous) => ({ ...previous, cameraIds: [cameraId] }));
    }
    if (result.type === "bucket") {
      setSelectedBucket(result.bucket);
    }
    setSearch("");
  }

  return (
    <div className="grid gap-5 p-5 sm:p-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-4">
        <section className="relative overflow-hidden rounded-[1.1rem] border border-white/10 bg-[color:var(--vezor-surface-depth)] px-5 py-5">
          <OmniSightField variant="quiet" className="opacity-50" />
          <div className="relative z-10">
            <PageHeader
              className="border-b-0 pb-0"
              eyebrow="History"
              title={omniLabels.historyTitle}
              description="Explore how signals, events, and scene patterns change over time."
            />
          </div>
        </section>

        <HistoryToolbar
          state={state}
          metric={metric}
          search={search}
          searchResults={searchResults}
          onChange={applyState}
          onResumeFollowing={resumeFollowingNow}
          onSearchChange={setSearch}
          onSearchSelect={selectSearchResult}
        />

        <section className="rounded-lg border border-white/10 bg-[#07101c] p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="text-sm text-[#dce6f7]">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Export</p>
              <p className="mt-1">
                Export the current pattern view at {state.granularity} granularity.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                className="bg-white/[0.06] px-4 py-2 text-[#e7efff] shadow-none hover:bg-white/[0.1]"
                onClick={() => applyPresetRange("last_24h")}
              >
                Last 24h
              </Button>
              <Button
                className="bg-white/[0.06] px-4 py-2 text-[#e7efff] shadow-none hover:bg-white/[0.1]"
                onClick={() => applyPresetRange("last_7d")}
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
          {downloadError ? <p className="mt-3 text-sm text-[#f0b7c1]">{downloadError}</p> : null}
        </section>

        {isLoading ? (
          <div className="rounded-lg border border-white/10 bg-[#050912] px-6 py-16 text-sm text-[#93a7c5]">
            Loading history...
          </div>
        ) : error ? (
          <div className="rounded-lg border border-white/10 bg-[#050912] px-6 py-16 text-sm text-[#f0b7c1]">
            {error instanceof Error ? error.message : "Failed to load history."}
          </div>
        ) : chartEmpty ? (
          <div className="space-y-4 rounded-lg border border-white/10 bg-[#050912] px-6 py-16 text-sm text-[#93a7c5]">
            <p>{metricCopy.emptyState}</p>
            <Button onClick={() => applyPresetRange("last_7d")}>Try last 7 days</Button>
          </div>
        ) : data ? (
          <div className="space-y-3">
            {granularityBumped ? (
              <p className="rounded-md border border-[#705e29] bg-[#1d1b08]/80 px-4 py-3 text-sm text-[#ffe5a8]">
                Granularity adjusted to {data.granularity}.
              </p>
            ) : null}
            {speedCapped ? (
              <p className="rounded-md border border-[#705e29] bg-[#1d1b08]/80 px-4 py-3 text-sm text-[#ffe5a8]">
                Speed panel capped at 20 classes.
              </p>
            ) : null}
            {speedRequestedButEmpty ? (
              <p className="rounded-md border border-[#705e29] bg-[#1d1b08]/80 px-4 py-3 text-sm text-[#ffe5a8]">
                None of the selected classes have speed data in this window - try widening the range or check camera
                homography.
              </p>
            ) : null}
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
              <HistoryTrendPanel
                series={{
                  classNames: displaySeries.classNames,
                  points: displaySeries.points,
                  includeSpeed: state.speed,
                  speedThreshold: state.speedThreshold ?? null,
                  speedClassesUsed: data.speed_classes_used ?? null,
                  selectedBucket: validSelectedBucket,
                }}
                metric={metric}
                granularity={data.granularity}
                coverage={coverageCopy}
                onBucketSelect={setSelectedBucket}
              />
              <HistoryBucketDetail detail={bucketDetail} metric={metric} />
            </div>
          </div>
        ) : null}
      </div>

      <aside className="space-y-6">
        <section className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,15,24,0.98),rgba(4,7,12,0.96))]">
          <div className="border-b border-white/8 px-5 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">Filters</p>
            <h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">Scope the historical view</h3>
          </div>

          <div className="space-y-4 px-5 py-5">
            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Metric</span>
              <Select
                aria-label="Metric"
                value={metric}
                onChange={(e) => applyState((p) => ({ ...p, metric: e.target.value as HistoryMetric }))}
              >
                <option value="occupancy">
                  {historyMetricCopy("occupancy").label} — {historyMetricCopy("occupancy").description}
                </option>
                <option value="count_events">
                  {historyMetricCopy("count_events").label} — {historyMetricCopy("count_events").description}
                </option>
                <option value="observations">
                  {historyMetricCopy("observations").label} (debug) —{" "}
                  {historyMetricCopy("observations").description}
                </option>
              </Select>
              {state.metric === null ? (
                <p className="text-xs text-[#8ea8cf]">
                  Automatically using {metricCopy.label.toLowerCase()} for the selected cameras.
                </p>
              ) : null}
            </label>

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
                    {entry.class_name} ({entry.event_count} {metricCopy.countLabel})
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

function resolveHistoryMetric(
  explicitMetric: HistoryMetric | null,
  cameras: Array<{ id: string; zones?: Array<Record<string, unknown>> }>,
  selectedCameraIds: string[],
): HistoryMetric {
  if (explicitMetric !== null) {
    return explicitMetric;
  }

  const selectedCameras =
    selectedCameraIds.length === 0
      ? cameras
      : cameras.filter((camera) => selectedCameraIds.includes(camera.id));
  return selectedCameras.length > 0 && selectedCameras.every(cameraHasCountBoundaries)
    ? "count_events"
    : "occupancy";
}

function cameraHasCountBoundaries(camera: { zones?: Array<Record<string, unknown>> }): boolean {
  return (
    camera.zones?.some((zone) => {
      const zoneType = typeof zone?.type === "string" ? zone.type.toLowerCase() : null;
      return zoneType === "line" || zoneType === "polygon" || Array.isArray(zone?.polygon);
    }) ?? false
  );
}
