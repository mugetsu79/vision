export type HistoryGranularity = "1m" | "5m" | "1h" | "1d";
export type HistoryMetric = "occupancy" | "count_events" | "observations";
export type HistoryWindowMode = "relative" | "absolute";
export type RelativeHistoryWindow = "last_15m" | "last_1h" | "last_24h" | "last_7d";

export interface HistoryFilterState {
  from: Date;
  to: Date;
  windowMode: HistoryWindowMode;
  relativeWindow: RelativeHistoryWindow;
  followNow: boolean;
  granularity: HistoryGranularity;
  metric: HistoryMetric | null;
  cameraIds: string[];
  classNames: string[];
  speed: boolean;
  speedThreshold: number | null;
}

const GRANULARITIES = new Set<HistoryGranularity>(["1m", "5m", "1h", "1d"]);
const HISTORY_METRICS = new Set<HistoryMetric>(["occupancy", "count_events", "observations"]);
const RELATIVE_HISTORY_WINDOWS = new Set<RelativeHistoryWindow>([
  "last_15m",
  "last_1h",
  "last_24h",
  "last_7d",
]);

const RELATIVE_WINDOW_DURATIONS: Record<RelativeHistoryWindow, number> = {
  last_15m: 15 * 60 * 1000,
  last_1h: 60 * 60 * 1000,
  last_24h: 24 * 60 * 60 * 1000,
  last_7d: 7 * 24 * 60 * 60 * 1000,
};

const HISTORY_METRIC_COPY: Record<
  HistoryMetric,
  {
    label: string;
    description: string;
    countLabel: string;
    emptyState: string;
  }
> = {
  occupancy: {
    label: "Occupancy",
    description: "peak visible occupancy snapshots",
    countLabel: "visible samples",
    emptyState: "No occupancy snapshots in this window for the selected cameras and classes.",
  },
  count_events: {
    label: "Count events",
    description: "crossings, entries, and exits",
    countLabel: "events",
    emptyState: "No crossings, entries, or exits in this window for the selected cameras and classes.",
  },
  observations: {
    label: "Raw tracking samples",
    description: "per-frame tracking density for debugging",
    countLabel: "tracking samples",
    emptyState: "No raw tracking samples in this window for the selected cameras and classes.",
  },
};

function toDate(value: string | null, fallback: Date): Date {
  if (!value) {
    return fallback;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? fallback : parsed;
}

function toGranularity(value: string | null): HistoryGranularity {
  if (value && GRANULARITIES.has(value as HistoryGranularity)) {
    return value as HistoryGranularity;
  }
  return "1h";
}

function toMetric(value: string | null): HistoryMetric | null {
  if (value && HISTORY_METRICS.has(value as HistoryMetric)) {
    return value as HistoryMetric;
  }
  return null;
}

function toRelativeWindow(value: string | null): RelativeHistoryWindow {
  if (value && RELATIVE_HISTORY_WINDOWS.has(value as RelativeHistoryWindow)) {
    return value as RelativeHistoryWindow;
  }
  return "last_24h";
}

function toList(value: string | null): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function toPositiveNumber(value: string | null): number | null {
  if (value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

export function resolveRelativeWindow(
  window: RelativeHistoryWindow,
  now = new Date(),
): { from: Date; to: Date } {
  const to = new Date(now);
  to.setSeconds(0, 0);
  const from = new Date(to.getTime() - RELATIVE_WINDOW_DURATIONS[window]);
  return { from, to };
}

export function defaultHistoryFilters(now = new Date()): HistoryFilterState {
  const relativeWindow: RelativeHistoryWindow = "last_24h";
  const { from, to } = resolveRelativeWindow(relativeWindow, now);
  return {
    from,
    to,
    windowMode: "relative",
    relativeWindow,
    followNow: true,
    granularity: "1h",
    metric: null,
    cameraIds: [],
    classNames: [],
    speed: false,
    speedThreshold: null,
  };
}

export function readHistoryFiltersFromSearch(
  params: URLSearchParams,
  now = new Date(),
): HistoryFilterState {
  const defaults = defaultHistoryFilters(now);
  const relativeWindow = toRelativeWindow(params.get("window"));
  const hasAbsoluteBound = params.has("from") || params.has("to");
  const relativeBounds = resolveRelativeWindow(relativeWindow, now);
  const windowMode: HistoryWindowMode = hasAbsoluteBound ? "absolute" : "relative";
  const followNow = hasAbsoluteBound ? false : params.get("follow") !== "0";

  return {
    from: hasAbsoluteBound ? toDate(params.get("from"), defaults.from) : relativeBounds.from,
    to: hasAbsoluteBound ? toDate(params.get("to"), defaults.to) : relativeBounds.to,
    windowMode,
    relativeWindow,
    followNow,
    granularity: toGranularity(params.get("granularity")),
    metric: toMetric(params.get("metric")),
    cameraIds: toList(params.get("cameras")),
    classNames: toList(params.get("classes")),
    speed: params.get("speed") === "1",
    speedThreshold: toPositiveNumber(params.get("speedThreshold")),
  };
}

export function writeHistoryFiltersToSearch(state: HistoryFilterState): string {
  const params = new URLSearchParams();
  const relativeBounds = resolveRelativeWindow(state.relativeWindow, state.to);
  const matchesRelativeWindow =
    state.from.getTime() === relativeBounds.from.getTime() &&
    state.to.getTime() === relativeBounds.to.getTime();

  if (state.windowMode === "relative" && matchesRelativeWindow) {
    params.set("window", state.relativeWindow);
    params.set("follow", state.followNow ? "1" : "0");
  } else {
    params.set("from", state.from.toISOString());
    params.set("to", state.to.toISOString());
  }
  if (state.granularity !== "1h") {
    params.set("granularity", state.granularity);
  }
  if (state.metric !== null) {
    params.set("metric", state.metric);
  }
  if (state.cameraIds.length > 0) {
    params.set("cameras", state.cameraIds.join(","));
  }
  if (state.classNames.length > 0) {
    params.set("classes", state.classNames.join(","));
  }
  if (state.speed) {
    params.set("speed", "1");
    if (state.speedThreshold !== null) {
      params.set("speedThreshold", String(state.speedThreshold));
    }
  }
  return params.toString();
}

export function historyMetricCopy(metric: HistoryMetric) {
  return HISTORY_METRIC_COPY[metric];
}
