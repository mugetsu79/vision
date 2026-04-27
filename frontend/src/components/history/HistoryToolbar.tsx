import { Button } from "@/components/ui/button";
import { HistorySearchBox } from "@/components/history/HistorySearchBox";
import { Select } from "@/components/ui/select";
import {
  type HistoryFilterState,
  type HistoryMetric,
  historyMetricCopy,
} from "@/lib/history-url-state";
import type { HistorySearchResult } from "@/lib/history-search";

export function HistoryToolbar({
  state,
  metric,
  search,
  searchResults,
  onChange,
  onResumeFollowing,
  onSearchChange,
  onSearchSelect,
}: {
  state: HistoryFilterState;
  metric: HistoryMetric;
  search: string;
  searchResults: HistorySearchResult[];
  onChange: (next: HistoryFilterState | ((previous: HistoryFilterState) => HistoryFilterState)) => void;
  onResumeFollowing: () => void;
  onSearchChange: (value: string) => void;
  onSearchSelect: (result: HistorySearchResult) => void;
}) {
  const isFollowingNow = state.windowMode === "relative" && state.followNow;

  return (
    <section className="rounded-lg border border-white/10 bg-[#07101c] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">History</p>
          <h1 className="mt-1 text-2xl font-semibold text-[#f4f8ff]">{historyMetricCopy(metric).label}</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md border border-white/10 px-3 py-2 text-sm text-[#dce6f7]">
            {isFollowingNow ? "Following now" : state.windowMode === "relative" ? "Paused window" : "Absolute window"}
          </span>
          {!isFollowingNow ? (
            <Button type="button" onClick={onResumeFollowing}>
              Resume following now
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-4">
        <HistorySearchBox
          value={search}
          results={searchResults}
          onChange={onSearchChange}
          onSelect={onSearchSelect}
        />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Select
          aria-label="Toolbar metric"
          value={metric}
          onChange={(event) =>
            onChange((previous) => ({ ...previous, metric: event.target.value as HistoryMetric }))
          }
        >
          <option value="occupancy">{historyMetricCopy("occupancy").label}</option>
          <option value="count_events">{historyMetricCopy("count_events").label}</option>
          <option value="observations">{historyMetricCopy("observations").label} (debug)</option>
        </Select>
        <Select
          aria-label="Time window"
          value={state.windowMode === "relative" ? state.relativeWindow : "absolute"}
          onChange={(event) => {
            const value = event.target.value;
            if (value === "absolute") return;
            onChange((previous) => ({
              ...previous,
              windowMode: "relative",
              relativeWindow: value as HistoryFilterState["relativeWindow"],
              followNow: true,
            }));
          }}
        >
          <option value="last_15m">Last 15m</option>
          <option value="last_1h">Last 1h</option>
          <option value="last_24h">Last 24h</option>
          <option value="last_7d">Last 7d</option>
          {state.windowMode === "absolute" ? <option value="absolute">Custom absolute range</option> : null}
        </Select>
        <Select
          aria-label="Toolbar granularity"
          value={state.granularity}
          onChange={(event) =>
            onChange((previous) => ({
              ...previous,
              granularity: event.target.value as HistoryFilterState["granularity"],
            }))
          }
        >
          <option value="1m">1 minute</option>
          <option value="5m">5 minutes</option>
          <option value="1h">1 hour</option>
          <option value="1d">1 day</option>
        </Select>
      </div>
    </section>
  );
}
