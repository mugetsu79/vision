# ADR-0001: Identity Provider — Keycloak vs Authentik

**Status:** Accepted
**Date:** 2026-04-18
**Deciders:** Platform owner (Yann), backend lead, security reviewer
**Related:** `argus_v4_spec.md` §7 (Security & Privacy), §12 (Resolved & Open Decisions)

## Context

Argus is a multi-tenant VMS targeting 5–50 sites and 25–250 cameras, sold to municipalities, transportation authorities, industrial worksites, and private-security integrators. Authentication requirements:

- **OIDC + PKCE** for the React SPA.
- **RBAC** with four roles (`viewer`, `operator`, `admin`, `superadmin`) and multi-tenant isolation — one realm per tenant, or tenant-scoped groups.
- **Scoped API keys / mTLS** for edge nodes (Jetson Orin Nano Super) registering over a Tailscale/WireGuard overlay.
- **SAML and LDAP** federation for the municipal buyer segment (some cities still require AD integration).
- **Audit log** of all authentication events.
- Operable by a small team: ideally one operator can keep it patched without a dedicated IAM specialist.

Non-functional requirements:
- Self-hostable (several prospects are air-gapped or have data-residency rules).
- Runs alongside the central node on a single k3s cluster or a mid-size VM; memory budget ≤ 1 GB.
- Known, auditable supply chain; upstream actively maintained in 2026.
- Permissively licensed (avoid copyleft pollution of our own services).

Two realistic open-source options dominate this space: **Keycloak** (Red Hat / CNCF Sandbox track, Java / Quarkus) and **Authentik** (goauthentik.io, Python / Django). Commercial alternatives (Auth0, Okta, Ping) are out of scope — the customer base and data-residency needs preclude them.

## Decision

**Adopt Keycloak** as the identity provider for V3. Run it in a dedicated Postgres-backed deployment, one realm per tenant. Document Authentik as a supported *alternative* in `docs/runbook.md` for operators who prefer it, but do not ship Authentik wiring in the default Helm chart.

## Options Considered

### Option A: Keycloak (chosen)

| Dimension              | Assessment                                                                 |
|------------------------|----------------------------------------------------------------------------|
| Complexity             | Medium — realm + client + role model is powerful but takes a day to learn  |
| Cost                   | Free (Apache 2.0); ~512–768 MB RSS per instance; Red Hat offers paid SSO   |
| Scalability            | High — proven at 10k+ users per realm; realm-per-tenant scales to 100s     |
| Team familiarity       | High — most backend engineers have touched Keycloak before                 |
| Protocol coverage      | OIDC, OAuth2, SAML 2.0, LDAP/AD federation, SCIM via extensions            |
| Ecosystem              | Quarkus rewrite is fast and lean; huge SDK coverage; many Helm charts      |
| Supply chain           | Red Hat upstream, CVE tracking mature; CNCF Sandbox as of 2023             |
| Multi-tenancy model    | Realms (hard isolation) or groups (soft) — both supported                  |
| Upgrade cadence        | Minor ~monthly, major ~yearly; LTS-style through Red Hat SSO              |

**Pros:**
- Procurement-safe: buyers in muni / enterprise recognize Keycloak; no pushback in RFPs.
- SAML + LDAP + AD federation work out of the box, essential for muni customers.
- Terraform provider (`keycloak/keycloak`) is mature for declarative realm config.
- Realm-per-tenant gives real isolation of users, clients, roles, and sessions.

**Cons:**
- Java / JVM memory footprint is higher than Authentik's (+~200 MB).
- Admin UI is functional but dated; some flows (e.g. per-realm theme) are fiddly.
- YAML realm export/import is slightly lossy; Terraform or `kcadm.sh` is the reliable path.

### Option B: Authentik

| Dimension              | Assessment                                                                 |
|------------------------|----------------------------------------------------------------------------|
| Complexity             | Low–Medium — modern flow-based model is intuitive                          |
| Cost                   | Free (MIT); paid Enterprise edition for RBAC at scale; ~300 MB RSS         |
| Scalability            | Medium — reported deployments in the low thousands; fewer proof points     |
| Team familiarity       | Low–Medium — more niche; newer engineers likely to meet it for first time  |
| Protocol coverage      | OIDC, OAuth2, SAML 2.0, LDAP/AD federation, SCIM, RADIUS                   |
| Ecosystem              | Growing; Helm chart official; Terraform provider exists but less mature    |
| Supply chain           | Single-vendor (goauthentik GmbH); smaller team; MIT licensed               |
| Multi-tenancy model    | Tenants are first-class, but nested-group RBAC is less battle-tested       |
| Upgrade cadence        | Active; minor releases frequent                                            |

**Pros:**
- Much nicer admin UX (React/Django); flow system maps to complex auth journeys well.
- Lower memory + faster cold start than Keycloak.
- Python codebase — easier for this team to patch if needed.

**Cons:**
- Smaller reference-customer set; some enterprise buyers flag it in security review.
- Enterprise RBAC features sit behind a paid license.
- Slightly thinner ecosystem: fewer community Helm charts, fewer Terraform modules.
- Bus-factor risk: single commercial vendor drives upstream.

### Option C (rejected): Roll our own with Authlib + Argon2

Cheap start, expensive middle. Writing an OIDC provider we have to secure, patch, and certify is a distraction from the core VMS. Rejected without scoring.

## Trade-off Analysis

The decisive axes are **procurement acceptability**, **federation coverage (SAML + LDAP for muni buyers)**, and **team familiarity**. Keycloak wins all three. Authentik's advantages (UX, memory) are real but don't outweigh the RFP risk and smaller reference base. The ~200 MB RAM delta on a mid-size central node is not a constraint.

Authentik remains attractive if the customer base shifts toward developer-native buyers (SaaS, B2B API) where modern UX matters more than procurement legibility. We leave the door open by abstracting the auth layer behind a thin OIDC client: swapping IdPs is a config change, not a code change.

## Consequences

**Becomes easier:**
- Winning muni / enterprise RFPs — Keycloak is a recognized name.
- Federating with customer AD / Azure AD / Google Workspace via built-in connectors.
- Finding hires who can operate the IdP without onboarding overhead.

**Becomes harder:**
- Operating lean on a memory-constrained central VM; budget an extra 512 MB.
- Customizing the login UX — Keycloak themes are workable but not great.
- Onboarding engineers to the realm/client/role mental model (mitigated by a `docs/auth.md` primer).

**To revisit:**
- If Keycloak's Quarkus footprint or UX becomes a real blocker in the field, re-evaluate Authentik at V3.2.
- If we end up shipping a true SaaS edition, compare managed options (Auth0, Keycloak-as-a-Service via Cloud-IAM, Zitadel) at that point.

## Action Items

1. [ ] Stand up Keycloak in `infra/docker-compose.dev.yml` with a seed realm `argus-dev` and four demo roles.
2. [ ] Commit `infra/keycloak/realm-export.json` covering clients for SPA (PKCE), backend (confidential), and edge-node registration.
3. [ ] Implement the FastAPI JWKS validator + `CurrentUser` dependency (see blueprint Prompt 2).
4. [ ] Add a `docs/auth.md` primer covering realms, clients, roles, and the tenant-onboarding runbook.
5. [ ] Add a Terraform module (`infra/terraform/keycloak/`) that provisions a realm per tenant from a YAML list.
6. [ ] Document the Authentik-as-alternative path in `docs/runbook.md` (pointer only; no code).
