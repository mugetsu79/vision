import { useQuery } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";

export function useBillingInvoiceRuns() {
  return useQuery({
    queryKey: ["billing", "invoice-runs"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/billing/invoice-runs");
      if (error) {
        throw toApiError(error, "Failed to load invoice runs.");
      }
      return data?.items ?? [];
    },
  });
}

export function useBillingUsage() {
  return useQuery({
    queryKey: ["billing", "usage"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/billing/usage");
      if (error) {
        throw toApiError(error, "Failed to load billing usage.");
      }
      return data?.items ?? [];
    },
  });
}

export function useBillingMeters() {
  return useQuery({
    queryKey: ["billing", "meters"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/billing/meters");
      if (error) {
        throw toApiError(error, "Failed to load billing meters.");
      }
      return data?.items ?? [];
    },
  });
}
