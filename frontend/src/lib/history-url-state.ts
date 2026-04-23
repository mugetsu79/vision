export type HistoryGranularity = "1m" | "5m" | "1h" | "1d";

export interface HistoryFilterState {
  from: Date;
  to: Date;
  granularity: HistoryGranularity;
  cameraIds: string[];
  classNames: string[];
  speed: boolean;
  speedThreshold: number | null;
}

const GRANULARITIES = new Set<HistoryGranularity>(["1m", "5m", "1h", "1d"]);

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

export function defaultHistoryFilters(now = new Date()): HistoryFilterState {
  const to = new Date(now);
  to.setSeconds(0, 0);
  const from = new Date(to);
  from.setDate(from.getDate() - 1);
  return {
    from,
    to,
    granularity: "1h",
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
  return {
    from: toDate(params.get("from"), defaults.from),
    to: toDate(params.get("to"), defaults.to),
    granularity: toGranularity(params.get("granularity")),
    cameraIds: toList(params.get("cameras")),
    classNames: toList(params.get("classes")),
    speed: params.get("speed") === "1",
    speedThreshold: toPositiveNumber(params.get("speedThreshold")),
  };
}

export function writeHistoryFiltersToSearch(state: HistoryFilterState): string {
  const params = new URLSearchParams();
  params.set("from", state.from.toISOString());
  params.set("to", state.to.toISOString());
  params.set("granularity", state.granularity);
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
