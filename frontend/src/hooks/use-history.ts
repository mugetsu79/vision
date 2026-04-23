import { queryOptions, useQuery } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";
import { buildApiUrl } from "@/lib/ws";
import { useAuthStore } from "@/stores/auth-store";

export type HistorySeriesResponse = components["schemas"]["HistorySeriesResponse"];
export type HistoryClassesResponse = components["schemas"]["HistoryClassesResponse"];

export type HistoryFilters = {
  from: Date;
  to: Date;
  granularity: "1m" | "5m" | "1h" | "1d";
  cameraIds: string[];
  classNames: string[];
  includeSpeed?: boolean;
  speedThreshold?: number | null;
};

export function createDefaultHistoryFilters(now = new Date()): HistoryFilters {
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
    includeSpeed: false,
    speedThreshold: null,
  };
}

export function historySeriesQueryOptions(filters: HistoryFilters) {
  return queryOptions({
    queryKey: [
      "history-series",
      filters.from.toISOString(),
      filters.to.toISOString(),
      filters.granularity,
      filters.cameraIds,
      filters.classNames,
      filters.includeSpeed ?? false,
      filters.speedThreshold ?? null,
    ],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/history/series", {
        params: {
          query: {
            from: filters.from.toISOString(),
            to: filters.to.toISOString(),
            granularity: filters.granularity,
            camera_ids: filters.cameraIds.length > 0 ? filters.cameraIds : undefined,
            class_names: filters.classNames.length > 0 ? filters.classNames : undefined,
            include_speed: filters.includeSpeed ? true : undefined,
            speed_threshold:
              filters.includeSpeed && filters.speedThreshold !== null && filters.speedThreshold !== undefined
                ? filters.speedThreshold
                : undefined,
          },
        },
      });
      if (error || !data) {
        throw toApiError(error, "Failed to load history.");
      }
      return data;
    },
  });
}

export function useHistorySeries(filters: HistoryFilters) {
  return useQuery(historySeriesQueryOptions(filters));
}

export function historyClassesQueryOptions(params: {
  from: Date;
  to: Date;
  cameraIds: string[];
}) {
  return queryOptions({
    queryKey: [
      "history-classes",
      params.from.toISOString(),
      params.to.toISOString(),
      params.cameraIds,
    ],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/history/classes", {
        params: {
          query: {
            from: params.from.toISOString(),
            to: params.to.toISOString(),
            camera_ids: params.cameraIds.length > 0 ? params.cameraIds : undefined,
          },
        },
      });
      if (error || !data) {
        throw toApiError(error, "Failed to load class list.");
      }
      return data;
    },
  });
}

export function useHistoryClasses(params: { from: Date; to: Date; cameraIds: string[] }) {
  return useQuery(historyClassesQueryOptions(params));
}

export async function downloadHistoryExport(
  filters: HistoryFilters,
  format: "csv" | "parquet",
) {
  const { accessToken, user } = useAuthStore.getState();
  const headers = new Headers();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  if (user?.tenantId) {
    headers.set("X-Tenant-ID", user.tenantId);
  }

  const response = await fetch(
    buildApiUrl("/api/v1/export", {
      from: filters.from.toISOString(),
      to: filters.to.toISOString(),
      granularity: filters.granularity,
      format,
      camera_ids: filters.cameraIds,
      class_names: filters.classNames,
    }),
    { headers },
  );

  if (!response.ok) {
    throw new Error(`Failed to export ${format.toUpperCase()} history.`);
  }

  const blob = await response.blob();
  const filename = parseFilename(response.headers.get("Content-Disposition"), format);

  if (typeof window === "undefined" || typeof window.URL.createObjectURL !== "function") {
    return;
  }

  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}

function parseFilename(header: string | null, format: "csv" | "parquet"): string {
  const match = header?.match(/filename="(?<filename>[^"]+)"/);
  return match?.groups?.filename ?? `history.${format}`;
}
