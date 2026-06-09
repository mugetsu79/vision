# Tenant User and Admin Management Design

## Status

Implemented in `codex/sceneops-pack-registry` for backend/API/UI automated
coverage and tenant-admin installed-stack live smoke. Platform-superadmin
first-account bootstrap from UI is tracked separately in
`docs/superpowers/specs/2026-06-09-platform-superadmin-ui-bootstrap-design.md`.

## Problem

First-run creates the first tenant and first admin account, but the installed
product does not yet expose a normal Vezor user-management surface for adding
additional tenant admins, operators, or viewers. Additional accounts can be
created through Keycloak today, but that is an installer/admin workaround rather
than a product workflow.

## Current Behavior

- `/first-run` completes `POST /api/v1/deployment/bootstrap/complete`.
- `DeploymentNodeService.complete_master_bootstrap` creates the Vezor `Tenant`
  and first local `User` row.
- `KeycloakBootstrapProvisioner.provision_tenant_admin` creates or repairs the
  Keycloak realm, clients, `tenant` and `tenant_id` protocol mappers, and the
  first Keycloak user.
- Tokens are accepted when they contain a recognized realm role: `viewer`,
  `operator`, `admin`, or `superadmin`.
- `admin` is tenant-scoped through the `tenant_id` or `tenant` token claim.
- `superadmin` is only superadmin when the token role is `superadmin` and the
  realm is the configured platform realm.

## Goals

- Platform superadmins can list tenants, create tenants, see users across every
  tenant, and create tenant users from Vezor.
- Tenant admins can create, list, disable, update, and reset additional users
  for their tenant from Vezor.
- New users are provisioned in Keycloak and mirrored in the local `users` table.
- Roles remain tenant-scoped: `viewer`, `operator`, and `admin`.
- The first-run user and later tenant admins have equivalent tenant-admin rights.
- Account creation never exposes Keycloak admin credentials, raw reset tokens,
  bearer tokens, or passwords in logs or API responses.

## Non-Goals

- Replacing Keycloak as the identity provider.
- Bootstrapping the first platform-realm superadmin account; see the dedicated
  platform-superadmin UI bootstrap spec.
- Assigning a single user account to multiple tenants.
- Implementing self-service sign-up.

## Product Model

Vezor remains the system of record for tenant-scoped authorization metadata used
by the API, while Keycloak remains the system of record for authentication,
passwords, OIDC clients, and token issuance.

Each managed user has:

- one local `users` row with `tenant_id`, `email`, `oidc_sub`, and `role`
- one Keycloak user in the configured bootstrap realm
- Keycloak attributes `tenant=[tenant_slug]` and `tenant_id=[tenant_uuid]`
- one realm role from `viewer`, `operator`, or `admin`

## API Requirements

- `GET /api/v1/tenants` returns all tenants for platform superadmins.
- `POST /api/v1/tenants` creates a tenant for platform superadmins.
- `GET /api/v1/users` returns users for the current tenant; platform
  superadmins can list across tenants.
- `POST /api/v1/users` creates a Keycloak user and local user row. Tenant
  admins create users in their current tenant; platform superadmins must choose
  the target tenant.
- `PATCH /api/v1/users/{user_id}` updates name, enabled state, and role.
- `POST /api/v1/users/{user_id}/reset-password` sets a temporary password or
  creates a one-time reset action without returning sensitive material.
- Tenant admins can manage only users in their own tenant.
- Tenant admins cannot assign `superadmin`.
- Users cannot remove the last enabled tenant admin.

## UI Requirements

- Add an Account or Users view reachable by tenant admins.
- Platform superadmins see tenant creation, tenant selection, and cross-tenant
  user rows.
- Tenant admins see tenant-scoped user creation and rows only.
- Show email, name, role, enabled state, and last known local metadata.
- Provide create user, change role, disable user, and reset password actions.
- Never show bootstrap tokens, bearer tokens, node credentials, or Keycloak
  admin credentials.

## Security Requirements

- All account-management routes require `admin`.
- Cross-tenant user IDs return `404` rather than leaking existence.
- Passwords and reset material are write-only request fields.
- Audit log every create, role change, disable, and reset action with actor
  subject, target user id, tenant id, and timestamp.

## Open Operational Workaround

Until this is implemented, adding another tenant admin with equivalent rights to
the first-run admin requires Keycloak administration:

1. Create a user in the configured tenant realm.
2. Set attributes `tenant` to the tenant slug and `tenant_id` to the tenant UUID.
3. Assign the realm role `admin`.
4. Set a password or required password-reset action.
5. Ensure the `argus-frontend` and `argus-cli` clients still have protocol
   mappers for `tenant` and `tenant_id`.
