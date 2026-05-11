import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type OperatorConfigKind = components["schemas"]["OperatorConfigProfileKind"];
export type OperatorConfigScope = components["schemas"]["OperatorConfigScope"];
export type OperatorConfigProfile = components["schemas"]["OperatorConfigProfileResponse"];
export type OperatorConfigProfileCreate =
  components["schemas"]["OperatorConfigProfileCreate"];
export type OperatorConfigProfileUpdate =
  components["schemas"]["OperatorConfigProfileUpdate"];
export type OperatorConfigBindingRequest =
  components["schemas"]["OperatorConfigBindingRequest"];
export type OperatorConfigBindingResponse =
  components["schemas"]["OperatorConfigBindingResponse"];
export type OperatorConfigTestResponse =
  components["schemas"]["OperatorConfigTestResponse"];
export type ResolvedOperatorConfig =
  components["schemas"]["ResolvedOperatorConfigResponse"];

export type ConfigurationCatalog = {
  kinds?: Array<{
    kind: OperatorConfigKind;
    label: string;
    secret_keys?: string[];
  }>;
};

export function useConfigurationCatalog() {
  return useQuery({
    queryKey: ["configuration", "catalog"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/configuration/catalog");
      if (error || !data) {
        throw toApiError(error, "Failed to load configuration catalog.");
      }
      return data as ConfigurationCatalog;
    },
  });
}

export function useConfigurationProfiles(kind?: OperatorConfigKind) {
  return useQuery({
    queryKey: ["configuration", "profiles", kind ?? "all"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/configuration/profiles", {
        params: { query: kind ? { kind } : {} },
      });
      if (error) {
        throw toApiError(error, "Failed to load configuration profiles.");
      }
      return data ?? [];
    },
  });
}

export function useCreateConfigurationProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: OperatorConfigProfileCreate) => {
      const { data, error } = await apiClient.POST("/api/v1/configuration/profiles", {
        body: payload,
      });
      if (error || !data) {
        throw toApiError(error, "Failed to create configuration profile.");
      }
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["configuration"] });
    },
  });
}

export function useUpdateConfigurationProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      profileId,
      payload,
    }: {
      profileId: string;
      payload: OperatorConfigProfileUpdate;
    }) => {
      const { data, error } = await apiClient.PATCH(
        "/api/v1/configuration/profiles/{profile_id}",
        {
          params: { path: { profile_id: profileId } },
          body: payload,
        },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to update configuration profile.");
      }
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["configuration"] });
    },
  });
}

export function useDeleteConfigurationProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (profileId: string) => {
      const { error } = await apiClient.DELETE(
        "/api/v1/configuration/profiles/{profile_id}",
        { params: { path: { profile_id: profileId } } },
      );
      if (error) {
        throw toApiError(error, "Failed to delete configuration profile.");
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["configuration"] });
    },
  });
}

export function useTestConfigurationProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (profileId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/configuration/profiles/{profile_id}/test",
        { params: { path: { profile_id: profileId } } },
      );
      if (error || !data) {
        throw toApiError(error, "Failed to test configuration profile.");
      }
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["configuration"] });
    },
  });
}

export function useUpsertConfigurationBinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: OperatorConfigBindingRequest) => {
      const { data, error } = await apiClient.POST("/api/v1/configuration/bindings", {
        body: payload,
      });
      if (error || !data) {
        throw toApiError(error, "Failed to bind configuration profile.");
      }
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["configuration"] });
    },
  });
}

export function useResolvedConfiguration(cameraId?: string) {
  return useQuery({
    queryKey: ["configuration", "resolved", cameraId ?? "tenant"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/configuration/resolved", {
        params: { query: cameraId ? { camera_id: cameraId } : {} },
      });
      if (error || !data) {
        throw toApiError(error, "Failed to resolve configuration.");
      }
      return data;
    },
  });
}
