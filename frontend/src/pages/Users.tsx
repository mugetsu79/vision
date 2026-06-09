import { FormEvent, ReactNode, useMemo, useState } from "react";
import { KeyRound, Save, UserPlus } from "lucide-react";

import { RequireRole } from "@/components/auth/RequireRole";
import {
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useCreateManagedTenant,
  useCreateManagedUser,
  useManagedTenants,
  useManagedUsers,
  useResetManagedUserPassword,
  useUpdateManagedUser,
  type ManagedTenant,
  type ManagedUser,
} from "@/hooks/use-users";
import type { ArgusRole } from "@/lib/auth";
import { useAuthStore } from "@/stores/auth-store";

const tenantAssignableRoles = ["viewer", "operator", "admin"] as const;
type TenantAssignableRole = (typeof tenantAssignableRoles)[number];

type TenantFormState = {
  name: string;
  slug: string;
};

type UserFormState = {
  tenant_id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: TenantAssignableRole;
  temporary_password: string;
};

const emptyTenantForm: TenantFormState = {
  name: "",
  slug: "",
};

const emptyUserForm: UserFormState = {
  tenant_id: "",
  email: "",
  first_name: "",
  last_name: "",
  role: "operator",
  temporary_password: "",
};

const emptyTenants: ManagedTenant[] = [];
const emptyUsers: ManagedUser[] = [];

export function UsersPage() {
  return (
    <RequireRole role="admin">
      <UsersContent />
    </RequireRole>
  );
}

function UsersContent() {
  const currentUser = useAuthStore((state) => state.user);
  const isSuperadmin = currentUser?.isSuperadmin === true;
  const tenantsQuery = useManagedTenants(isSuperadmin);
  const usersQuery = useManagedUsers();
  const createTenant = useCreateManagedTenant();
  const createUser = useCreateManagedUser();
  const updateUser = useUpdateManagedUser();
  const resetPassword = useResetManagedUserPassword();
  const [tenantForm, setTenantForm] = useState<TenantFormState>(emptyTenantForm);
  const [userForm, setUserForm] = useState<UserFormState>(emptyUserForm);
  const [createTenantError, setCreateTenantError] = useState<string | null>(null);
  const [createUserError, setCreateUserError] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<ManagedUser | null>(null);
  const [resetSecret, setResetSecret] = useState("");
  const [resetError, setResetError] = useState<string | null>(null);
  const tenants = tenantsQuery.data ?? emptyTenants;
  const users = usersQuery.data ?? emptyUsers;
  const tenantById = useMemo(
    () => new Map(tenants.map((tenant) => [tenant.id, tenant])),
    [tenants],
  );

  async function handleCreateTenant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateTenantError(null);
    try {
      await createTenant.mutateAsync({
        name: tenantForm.name,
        slug: tenantForm.slug.trim() ? tenantForm.slug : null,
      });
      setTenantForm(emptyTenantForm);
    } catch (error) {
      setCreateTenantError(error instanceof Error ? error.message : "Unable to create tenant.");
    }
  }

  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateUserError(null);
    try {
      await createUser.mutateAsync({
        tenant_id: isSuperadmin ? userForm.tenant_id : null,
        email: userForm.email,
        first_name: userForm.first_name,
        last_name: userForm.last_name,
        role: userForm.role,
        temporary_password: userForm.temporary_password,
      });
      setUserForm(emptyUserForm);
    } catch (error) {
      setCreateUserError(error instanceof Error ? error.message : "Unable to create user.");
    }
  }

  async function handleResetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resetTarget) {
      return;
    }
    setResetError(null);
    try {
      await resetPassword.mutateAsync({
        userId: resetTarget.id,
        payload: { temporary_password: resetSecret },
      });
      setResetSecret("");
      setResetTarget(null);
    } catch (error) {
      setResetError(error instanceof Error ? error.message : "Unable to reset password.");
    }
  }

  return (
    <div data-testid="users-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Access"
        title="Users"
        description={
          isSuperadmin
            ? "Platform superadmins manage tenants and tenant accounts from this workspace."
            : "Tenant admins manage accounts inside the current tenant."
        }
      />

      {isSuperadmin ? (
        <WorkspaceSurface className="p-4">
          <form
            data-testid="create-tenant-form"
            className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(12rem,18rem)_auto] md:items-end"
            onSubmit={(event) => void handleCreateTenant(event)}
          >
            <FormField label="Tenant name">
              <Input
                aria-label="Tenant name"
                value={tenantForm.name}
                onChange={(event) =>
                  setTenantForm((current) => ({ ...current, name: event.target.value }))
                }
                required
              />
            </FormField>
            <FormField label="Tenant slug">
              <Input
                aria-label="Tenant slug"
                value={tenantForm.slug}
                onChange={(event) =>
                  setTenantForm((current) => ({ ...current, slug: event.target.value }))
                }
              />
            </FormField>
            <Button
              className="gap-2"
              disabled={createTenant.isPending}
              type="submit"
              variant="primary"
            >
              <UserPlus className="size-4" aria-hidden="true" />
              Create tenant
            </Button>
          </form>
          {createTenantError ? <ErrorLine>{createTenantError}</ErrorLine> : null}
          {tenants.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2 text-sm text-[var(--vz-text-secondary)]">
              {tenants.map((tenant) => (
                <span
                  key={tenant.id}
                  className="rounded-full border border-[color:var(--vz-hair)] px-3 py-1"
                >
                  {tenant.name}
                </span>
              ))}
            </div>
          ) : null}
        </WorkspaceSurface>
      ) : null}

      <WorkspaceSurface className="p-4">
        <form
          data-testid="create-user-form"
          className="grid gap-3 lg:grid-cols-[minmax(10rem,14rem)_repeat(5,minmax(0,1fr))_auto] lg:items-end"
          onSubmit={(event) => void handleCreateUser(event)}
        >
          {isSuperadmin ? (
            <FormField label="Tenant">
              <select
                aria-label="Tenant"
                className={selectClasses}
                value={userForm.tenant_id}
                onChange={(event) =>
                  setUserForm((current) => ({ ...current, tenant_id: event.target.value }))
                }
                required
              >
                <option value="">Select tenant</option>
                {tenants.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name}
                  </option>
                ))}
              </select>
            </FormField>
          ) : null}
          <FormField label="Email">
            <Input
              aria-label="Email"
              type="email"
              value={userForm.email}
              onChange={(event) =>
                setUserForm((current) => ({ ...current, email: event.target.value }))
              }
              required
            />
          </FormField>
          <FormField label="First name">
            <Input
              aria-label="First name"
              value={userForm.first_name}
              onChange={(event) =>
                setUserForm((current) => ({ ...current, first_name: event.target.value }))
              }
              required
            />
          </FormField>
          <FormField label="Last name">
            <Input
              aria-label="Last name"
              value={userForm.last_name}
              onChange={(event) =>
                setUserForm((current) => ({ ...current, last_name: event.target.value }))
              }
              required
            />
          </FormField>
          <FormField label="Role">
            <RoleSelect
              label="Role"
              value={userForm.role}
              onChange={(role) =>
                setUserForm((current) => ({ ...current, role }))
              }
            />
          </FormField>
          <FormField label="Temporary password">
            <Input
              aria-label="Temporary password"
              type="password"
              value={userForm.temporary_password}
              onChange={(event) =>
                setUserForm((current) => ({
                  ...current,
                  temporary_password: event.target.value,
                }))
              }
              required
            />
          </FormField>
          <Button
            className="gap-2"
            disabled={createUser.isPending}
            type="submit"
            variant="primary"
          >
            <UserPlus className="size-4" aria-hidden="true" />
            Create user
          </Button>
        </form>
        {createUserError ? <ErrorLine>{createUserError}</ErrorLine> : null}
      </WorkspaceSurface>

      <WorkspaceSurface className="overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="border-b border-[color:var(--vz-hair)] text-left text-[11px] uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
            <tr>
              <th className="px-4 py-3 font-semibold">User</th>
              {isSuperadmin ? <th className="px-4 py-3 font-semibold">Tenant</th> : null}
              <th className="px-4 py-3 font-semibold">Role</th>
              <th className="px-4 py-3 font-semibold">Enabled</th>
              <th className="px-4 py-3 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[color:var(--vz-hair)]">
            {usersQuery.isLoading ? (
              <tr>
                <td
                  className="px-4 py-6 text-[var(--vz-text-secondary)]"
                  colSpan={isSuperadmin ? 5 : 4}
                >
                  Loading users...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td
                  className="px-4 py-6 text-[var(--vz-text-secondary)]"
                  colSpan={isSuperadmin ? 5 : 4}
                >
                  No users found.
                </td>
              </tr>
            ) : (
              users.map((managedUser) => (
                <ManagedUserRow
                  key={managedUser.id}
                  isSuperadmin={isSuperadmin}
                  managedUser={managedUser}
                  onReset={() => setResetTarget(managedUser)}
                  tenant={tenantById.get(managedUser.tenant_id)}
                  updateUser={updateUser.mutateAsync}
                />
              ))
            )}
          </tbody>
        </table>
      </WorkspaceSurface>

      {resetTarget ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(2,5,10,0.78)] p-4 backdrop-blur-md">
          <WorkspaceSurface className="w-full max-w-lg p-5" role="dialog" aria-modal="true">
            <form className="space-y-4" onSubmit={(event) => void handleResetPassword(event)}>
              <div>
                <h2 className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
                  Reset password
                </h2>
                <p className="mt-1 text-sm text-[var(--vz-text-secondary)]">
                  {resetTarget.email}
                </p>
              </div>
              <FormField label="New temporary password">
                <Input
                  aria-label="New temporary password"
                  type="password"
                  value={resetSecret}
                  onChange={(event) => setResetSecret(event.target.value)}
                  required
                />
              </FormField>
              {resetError ? <ErrorLine>{resetError}</ErrorLine> : null}
              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setResetTarget(null);
                    setResetSecret("");
                    setResetError(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  className="gap-2"
                  disabled={resetPassword.isPending}
                  type="submit"
                  variant="primary"
                >
                  <KeyRound className="size-4" aria-hidden="true" />
                  Reset password
                </Button>
              </div>
            </form>
          </WorkspaceSurface>
        </div>
      ) : null}
    </div>
  );
}

function ManagedUserRow({
  isSuperadmin,
  managedUser,
  onReset,
  tenant,
  updateUser,
}: {
  isSuperadmin: boolean;
  managedUser: ManagedUser;
  onReset: () => void;
  tenant: ManagedTenant | undefined;
  updateUser: (variables: {
    userId: string;
    payload: {
      first_name?: string | null;
      last_name?: string | null;
      role?: ArgusRole | null;
      enabled?: boolean | null;
    };
  }) => Promise<unknown>;
}) {
  const [firstName, setFirstName] = useState(managedUser.first_name ?? "");
  const [lastName, setLastName] = useState(managedUser.last_name ?? "");
  const [role, setRole] = useState<TenantAssignableRole>(
    toTenantAssignableRole(managedUser.role),
  );
  const [enabled, setEnabled] = useState(managedUser.enabled);
  const [error, setError] = useState<string | null>(null);
  const fullName = [managedUser.first_name, managedUser.last_name]
    .filter(Boolean)
    .join(" ");

  async function handleSave() {
    setError(null);
    try {
      await updateUser({
        userId: managedUser.id,
        payload: {
          first_name: firstName,
          last_name: lastName,
          role,
          enabled,
        },
      });
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to update user.");
    }
  }

  return (
    <tr className="align-top transition hover:bg-white/[0.03]">
      <th scope="row" className="px-4 py-4 text-left">
        <div className="font-medium text-[var(--vz-text-primary)]">{managedUser.email}</div>
        <div className="mt-1 text-xs text-[var(--vz-text-muted)]">
          {fullName || "No name"}
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          <Input
            aria-label={`First name for ${managedUser.email}`}
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
          />
          <Input
            aria-label={`Last name for ${managedUser.email}`}
            value={lastName}
            onChange={(event) => setLastName(event.target.value)}
          />
        </div>
        {error ? <ErrorLine>{error}</ErrorLine> : null}
      </th>
      {isSuperadmin ? (
        <td className="px-4 py-4 text-[var(--vz-text-secondary)]">
          {tenant?.name ?? managedUser.tenant_id}
        </td>
      ) : null}
      <td className="px-4 py-4">
        <RoleSelect label="Role" value={role} onChange={setRole} />
      </td>
      <td className="px-4 py-4">
        <label className="inline-flex items-center gap-2 text-sm text-[var(--vz-text-secondary)]">
          <input
            aria-label="Enabled"
            checked={enabled}
            className="size-4 rounded border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-obsidian)]"
            type="checkbox"
            onChange={(event) => setEnabled(event.target.checked)}
          />
          Enabled
        </label>
      </td>
      <td className="px-4 py-4 text-right">
        <div className="flex justify-end gap-2">
          <Button
            className="gap-2 px-3 py-2"
            disabled={false}
            onClick={() => void handleSave()}
          >
            <Save className="size-4" aria-hidden="true" />
            Save
          </Button>
          <Button className="gap-2 px-3 py-2" onClick={onReset} variant="ghost">
            <KeyRound className="size-4" aria-hidden="true" />
            Reset
          </Button>
        </div>
      </td>
    </tr>
  );
}

function FormField({
  children,
  label,
}: {
  children: ReactNode;
  label: string;
}) {
  return (
    <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
      <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
        {label}
      </span>
      {children}
    </label>
  );
}

function RoleSelect({
  label,
  onChange,
  value,
}: {
  label: string;
  onChange: (role: TenantAssignableRole) => void;
  value: TenantAssignableRole;
}) {
  return (
    <select
      aria-label={label}
      className={selectClasses}
      value={value}
      onChange={(event) => onChange(event.target.value as TenantAssignableRole)}
    >
      {tenantAssignableRoles.map((role) => (
        <option key={role} value={role}>
          {role}
        </option>
      ))}
    </select>
  );
}

function ErrorLine({ children }: { children: ReactNode }) {
  return (
    <p className="mt-3 text-sm font-medium text-[#ffc2cd]" role="alert">
      {children}
    </p>
  );
}

function toTenantAssignableRole(role: ArgusRole): TenantAssignableRole {
  return tenantAssignableRoles.includes(role as TenantAssignableRole)
    ? (role as TenantAssignableRole)
    : "viewer";
}

const selectClasses =
  "w-full rounded-[0.75rem] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-obsidian)] px-3 py-2.5 text-sm text-[var(--vz-text-primary)] outline-none transition focus:border-[color:var(--vz-hair-focus)] focus:ring-2 focus:ring-[color:var(--vz-hair-focus)]/25";
