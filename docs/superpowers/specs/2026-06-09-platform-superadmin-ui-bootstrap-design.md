# Platform Superadmin UI Bootstrap Design

## Status

Planned follow-up from the 2026-06-09 whole-product smoke closure. The current
branch includes the Users UI/API that a platform superadmin can use after
authentication, but the installed product does not yet create or sign in the
first platform-superadmin account from Vezor UI.

## Problem

Vezor now distinguishes tenant admins from platform superadmins:

- tenant admins are issued by the tenant realm and can manage users inside one
  tenant;
- platform superadmins are only recognized when the token role is `superadmin`
  and the issuer realm is `platform-admin`.

The installed first-run path creates a tenant realm and a first tenant admin. It
does not create the `platform-admin` realm, a platform OIDC client, or the first
platform-superadmin account. The installed frontend also points to one OIDC
authority, currently the tenant realm, so a platform-superadmin user cannot sign
in from the product UI even if an operator creates the realm manually.

## Goals

- Create the first platform superadmin from Vezor UI, not from the Keycloak
  administration console.
- Keep tenant-admin user management unchanged and tenant-scoped.
- Add a platform sign-in path that can authenticate against the
  `platform-admin` realm.
- Let authenticated platform superadmins use the existing Users UI to list all
  tenants, create tenants, create tenant users, and manage tenant users.
- Avoid printing, returning, logging, or committing raw bootstrap tokens,
  passwords, Keycloak admin credentials, bearer tokens, or reflector secrets.

## Non-Goals

- Replacing Keycloak as the identity provider.
- Allowing tenant admins to grant `superadmin`.
- Allowing one user account to be assigned to multiple tenants.
- Implementing self-service public signup.

## Proposed Product Flow

1. The master installer creates a local-only platform bootstrap token after
   first-run support files are created. The token is separate from the first-run
   bootstrap token and is stored under the installer config directory with
   owner-readable permissions.
2. After first-run completes, tenant admins see a guarded Platform Bootstrap
   entry only while no platform superadmin has been provisioned.
3. The Platform Bootstrap UI asks for the local bootstrap token, first name,
   last name, email, and password.
4. The backend validates that the request is local or carries the installer
   bootstrap token, creates or repairs the `platform-admin` realm, creates
   `argus-frontend` and `argus-cli` clients, creates the `superadmin` role,
   creates the first platform user, assigns the role, and consumes the bootstrap
   session.
5. The sign-in page exposes a normal tenant sign-in and a platform sign-in. The
   platform sign-in uses `VITE_PLATFORM_OIDC_AUTHORITY`, not the tenant realm.
6. Once signed in through the platform realm, the existing Users page renders in
   platform-superadmin mode and exposes tenant creation plus cross-tenant user
   management.

## Backend Requirements

- Add persistent platform bootstrap state, including consumed timestamp and
  hashed token, similar to master first-run bootstrap sessions.
- Add a `PlatformIdentityProvisioner` path that creates or repairs the
  `platform-admin` realm, clients, and `superadmin` role.
- Add `GET /api/v1/platform/bootstrap/status`.
- Add `POST /api/v1/platform/bootstrap/complete`.
- Reject bootstrap completion when a platform superadmin already exists unless
  the request is authenticated as an existing platform superadmin.
- Keep platform-superadmin records outside tenant-scoped `users` rows unless the
  user schema is deliberately extended for nullable tenant ownership.

## Frontend Requirements

- Add runtime config key `VITE_PLATFORM_OIDC_AUTHORITY`.
- Support a platform OIDC manager alongside the tenant OIDC manager.
- Add a platform sign-in action from `/signin`.
- Add a Platform Bootstrap page or card that is reachable only after first-run
  and only while bootstrap is available.
- Do not render or store generated passwords or bootstrap tokens after submit.

## Verification Requirements

- Backend tests prove bootstrap status, token consumption, Keycloak realm/client
  provisioning calls, role assignment, and replay rejection.
- Frontend tests prove tenant sign-in still uses the tenant realm and platform
  sign-in uses the platform realm.
- Installed live smoke must create the first platform superadmin from UI, sign
  in with that platform identity, create a second tenant from Users, and create
  one tenant admin in that second tenant.
