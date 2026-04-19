import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type Camera = components["schemas"]["CameraResponse"];
export type CreateCameraInput = components["schemas"]["CameraCreate"];
export type UpdateCameraInput = components["schemas"]["CameraUpdate"];

export function useCameras(siteId?: string) {
  return useQuery({
    queryKey: ["cameras", siteId ?? "all"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/cameras", {
        params: { query: siteId ? { site_id: siteId } : {} },
      });

      if (error) {
        throw toApiError(error, "Failed to load cameras.");
      }

      return data ?? [];
    },
  });
}

export function useCreateCamera() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateCameraInput) => {
      const { data, error } = await apiClient.POST("/api/v1/cameras", {
        body: payload,
      });

      if (error) {
        throw toApiError(error, "Failed to create camera.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
    },
  });
}

export function useUpdateCamera() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      cameraId,
      payload,
    }: {
      cameraId: string;
      payload: UpdateCameraInput;
    }) => {
      const { data, error } = await apiClient.PATCH("/api/v1/cameras/{camera_id}", {
        params: { path: { camera_id: cameraId } },
        body: payload,
      });

      if (error) {
        throw toApiError(error, "Failed to update camera.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
    },
  });
}

export function useDeleteCamera() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (cameraId: string) => {
      const { error } = await apiClient.DELETE("/api/v1/cameras/{camera_id}", {
        params: { path: { camera_id: cameraId } },
      });

      if (error) {
        throw toApiError(error, "Failed to delete camera.");
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["cameras"] });
    },
  });
}
