import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type ManagedTenant = components["schemas"]["ManagedTenantResponse"];
export type CreateManagedTenantInput =
  components["schemas"]["ManagedTenantCreate"];
export type ManagedUser = components["schemas"]["ManagedUserResponse"];
export type CreateManagedUserInput =
  components["schemas"]["ManagedUserCreate"];
export type UpdateManagedUserInput =
  components["schemas"]["ManagedUserPatch"];
export type ResetManagedUserPasswordInput =
  components["schemas"]["ManagedUserResetPassword"];

const tenantsQueryKey = ["managed-tenants"] as const;
const usersQueryKey = ["managed-users"] as const;

export function useManagedTenants(enabled: boolean) {
  return useQuery({
    queryKey: tenantsQueryKey,
    enabled,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/tenants");

      if (error) {
        throw toApiError(error, "Failed to load tenants.");
      }

      return data ?? [];
    },
  });
}

export function useManagedUsers() {
  return useQuery({
    queryKey: usersQueryKey,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/users");

      if (error) {
        throw toApiError(error, "Failed to load users.");
      }

      return data ?? [];
    },
  });
}

export function useCreateManagedTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateManagedTenantInput) => {
      const { data, error } = await apiClient.POST("/api/v1/tenants", {
        body: payload,
      });

      if (error) {
        throw toApiError(error, "Failed to create tenant.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: tenantsQueryKey });
    },
  });
}

export function useCreateManagedUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateManagedUserInput) => {
      const { data, error } = await apiClient.POST("/api/v1/users", {
        body: payload,
      });

      if (error) {
        throw toApiError(error, "Failed to create user.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: usersQueryKey });
    },
  });
}

export function useUpdateManagedUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      userId,
      payload,
    }: {
      userId: string;
      payload: UpdateManagedUserInput;
    }) => {
      const { data, error } = await apiClient.PATCH("/api/v1/users/{user_id}", {
        params: { path: { user_id: userId } },
        body: payload,
      });

      if (error) {
        throw toApiError(error, "Failed to update user.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: usersQueryKey });
    },
  });
}

export function useResetManagedUserPassword() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      userId,
      payload,
    }: {
      userId: string;
      payload: ResetManagedUserPasswordInput;
    }) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/users/{user_id}/reset-password",
        {
          params: { path: { user_id: userId } },
          body: payload,
        },
      );

      if (error) {
        throw toApiError(error, "Failed to reset password.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: usersQueryKey });
    },
  });
}
