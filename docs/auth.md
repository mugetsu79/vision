# Vezor Auth Primer

Status: Reference primer for ADR-0001.
Last updated: 2026-05-19

This primer records the identity-provider model chosen in
[ADR-0001](ADR/ADR-0001-identity-provider.md). It is not a production security
hardening guide; use it to keep the vocabulary consistent while the installer
and first-run flows mature.

## Current Shape

- Local development uses the seeded Keycloak realm from
  `infra/docker-compose.dev.yml`.
- Installed pilots use first-run bootstrap, node pairing, and node-bound
  credentials before a production OIDC/TLS package is finalized.
- The long-term identity provider remains Keycloak unless a future ADR
  supersedes ADR-0001.

## Terms

- `realm`: an isolated Keycloak tenant boundary.
- `client`: an application registered with the realm, such as the frontend SPA
  or backend API.
- `role`: an authorization label assigned to a user or service identity.
- `edge credential`: a node-bound credential used by installed central or edge
  supervisors after pairing.

## Roles

The product role model remains:

- `viewer`: read-only live/history access.
- `operator`: normal monitoring and response workflows.
- `admin`: site and camera configuration.
- `superadmin`: tenant and platform administration.

## Related Docs

- [ADR-0001: Identity Provider](ADR/ADR-0001-identity-provider.md)
- [Product installer and first-run guide](product-installer-and-first-run-guide.md)
- [Runbook](runbook.md)
