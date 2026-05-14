import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type Site = components["schemas"]["SiteResponse"];
export type CreateSiteInput = components["schemas"]["SiteCreate"];

export function useSites() {
  return useQuery({
    queryKey: ["sites"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/sites");

      if (error) {
        throw toApiError(error, "Failed to load sites.");
      }

      return data ?? [];
    },
  });
}

export function useCreateSite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateSiteInput) => {
      const { data, error } = await apiClient.POST("/api/v1/sites", {
        body: payload,
      });

      if (error) {
        throw toApiError(error, "Failed to create site.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sites"] });
    },
  });
}

export function useDeleteSite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (siteId: string) => {
      const { error } = await apiClient.DELETE("/api/v1/sites/{site_id}", {
        params: { path: { site_id: siteId } },
      });

      if (error) {
        throw toApiError(error, "Failed to delete site.");
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sites"] });
    },
  });
}
