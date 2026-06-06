import { useQuery } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";

export const FLEETOPS_PACK_ID = "maritime-fleet";

type BillingInvoiceRunItem = {
  line_items?: Array<{ pack_id?: unknown }>;
};

export function useBillingInvoiceRuns(packId: string | null = FLEETOPS_PACK_ID) {
  return useQuery({
    queryKey: ["billing", "invoice-runs", packId ?? "all"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/billing/invoice-runs");
      if (error) {
        throw toApiError(error, "Failed to load invoice runs.");
      }
      return filterInvoiceRuns(arrayItems<BillingInvoiceRunItem>(data), packId);
    },
  });
}

export function useBillingUsage(packId: string | null = FLEETOPS_PACK_ID) {
  return useQuery({
    queryKey: ["billing", "usage", packId ?? "all"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/billing/usage", {
        params: { query: packId ? { pack_id: packId } : {} },
      });
      if (error) {
        throw toApiError(error, "Failed to load billing usage.");
      }
      return {
        ...objectValue(data),
        items: filterPackItems(arrayItems(data), packId),
      };
    },
  });
}

export function useBillingMeters(packId: string | null = FLEETOPS_PACK_ID) {
  return useQuery({
    queryKey: ["billing", "meters", packId ?? "all"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/billing/meters", {
        params: { query: packId ? { pack_id: packId } : {} },
      });
      if (error) {
        throw toApiError(error, "Failed to load billing meters.");
      }
      return filterPackItems(arrayItems(data), packId);
    },
  });
}

export function useBillingExport(exportId?: string | null) {
  return useQuery({
    queryKey: ["billing", "exports", exportId ?? "none"],
    enabled: Boolean(exportId),
    queryFn: async () => {
      if (!exportId) {
        return null;
      }
      const { data, error } = await apiClient.GET(
        "/api/v1/billing/exports/{export_id}",
        { params: { path: { export_id: exportId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to load billing export.");
      }
      return data ?? null;
    },
  });
}

function filterPackItems<T extends { pack_id?: unknown }>(
  items: T[],
  packId: string | null,
) {
  if (!packId) {
    return items;
  }
  return items.filter((item) => item.pack_id === packId);
}

function arrayItems<T = { pack_id?: unknown }>(value: unknown): T[] {
  if (
    typeof value === "object" &&
    value !== null &&
    "items" in value &&
    Array.isArray(value.items)
  ) {
    return value.items as T[];
  }
  return [];
}

function objectValue(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function filterInvoiceRuns<
  T extends { line_items?: Array<{ pack_id?: unknown }> },
>(items: T[], packId: string | null) {
  if (!packId) {
    return items;
  }
  return items.filter((item) =>
    item.line_items?.some((lineItem) => lineItem.pack_id === packId),
  );
}
