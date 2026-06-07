# FleetOps Operator Completion Design

Date: 2026-06-06
Status: draft plan-ready design
Related runtime spec: `docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md`
Related pack boundary spec: `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
Related implementation plan: `docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md`

## Product Design Playback

FleetOps now installs and exposes runtime pages, but it still behaves like a
read-only pack summary. The user expectation is a fully operational workspace:
operators can add a vessel, configure the vessel's site and connectivity, move
between FleetOps pages from the primary rail, and use distinct Vessels,
Evidence, Billing, Support, and Onboarding pages that are all backed by real
backend APIs.

The visual source is the current Vezor dark command workspace and the supplied
FleetOps screenshots. Product Design saved context has no persisted references,
so this design uses the existing app shell, surfaces, routes, hooks, and
components as the design system. UI/UX guidance for this work is: explicit
active navigation, deep links for every page, accessible labelled forms,
keyboard-reachable controls, helpful empty states with actions, and submit
feedback for every mutation.

Interactivity level is full interactivity. This is not a static mock or copy
polish pass.

## Problem

The current FleetOps UI has three operator-facing gaps:

1. The left rail exposes only a single FleetOps icon. The five FleetOps pages
   exist as routes, but they are hidden in a hero band, so navigation feels
   stuck.
2. Vessels can be created through `POST /api/v1/maritime/vessels`, but the
   frontend only lists vessels. Empty state says no vessels exist and gives no
   way to create one.
3. Connectivity language and runtime decisions are too satellite-shaped. Real
   vessels may use satellite offshore, LTE or 5G near shore, Wi-Fi or ethernet
   through shipboard networks, and fiber while in port.

There are also product completeness gaps:

- Support and onboarding currently share the same panel shape, so they feel
  duplicated.
- "Diagnostic groups" is implementation vocabulary. Operators need visible
  support readiness checks with labels, status, source, and next action.
- Several FleetOps pages read one summary endpoint but do not expose the full
  backend actions already present for support, billing, evidence, link queue,
  and onboarding.

## Goals

1. Make FleetOps navigable from the primary left rail.
2. Add a working vessel creation and edit flow.
3. Treat link transport as a domain-neutral core link capability, not as a
   maritime or satellite-only feature.
4. Split Support and Onboarding into distinct workflows.
5. Rename and enrich diagnostics so support readiness is visible and useful.
6. Fully plumb each current FleetOps page to backend contracts and mutations.
7. Preserve all `CC-*` constraints from the FleetOps runtime plan.
8. Keep traffic/public-space, home-lab packs, payment processors, accounting
   integrations, and proprietary carrier SDKs out of scope.

## Non-Goals

- Do not implement traffic/public-space runtime, routes, migrations, UI, demos,
  or tests beyond existing boundary guards.
- Do not create a home-lab pack, home-lab status, or home-lab product UI.
- Do not integrate proprietary carrier SDKs. Generic HTTP, webhook, and file
  ingest seams remain the allowed integration mechanism.
- Do not integrate card payments, accounting systems, or external invoicing.
- Do not change detector/runtime semantics outside the existing SceneOps pack
  plan.
- Do not move `Vessel`, `Voyage`, `PortCall`, AIS, NMEA, `CarrierTerminal`,
  owner, manager, or charterer concepts into core.

## Approach Decision

### Option A: Frontend-Only Patch

Add a local vessel form and hard-code extra pages around current payloads.

This is fast, but it would leave transport modeling wrong and would produce UI
controls that are not backed by durable contracts.

### Option B: Maritime-Specific Link Types

Add `satellite`, `lte`, and `fiber` to `argus.maritime` only and map them into
the FleetOps UI.

This would solve the screenshot complaint but violates the spirit of `CC-4 Link
Is Core`. LTE, fiber, Wi-Fi, and satellite are connectivity primitives used by
any remote site, not maritime entities.

### Option C: Core Link Connections Plus FleetOps UI Completion

Add a domain-neutral core link connection model in `argus.link`, then map
maritime carrier terminal telemetry into those core connections. Complete the
FleetOps UI on top of real core and maritime APIs.

This is the recommended approach. It keeps core domain-neutral, fixes the
product gap properly, and makes FleetOps a working product workspace rather
than a read-only pack shell.

## Information Architecture

The left rail should expose FleetOps as a parent entry with nested links:

- FleetOps overview: `/fleetops`
- Vessels: `/fleetops/vessels`
- Evidence: `/fleetops/evidence`
- Billing: `/fleetops/billing`
- Support: `/fleetops/support`
- Onboarding: `/fleetops/onboarding`

The icon rail continues to show one vessel icon for FleetOps. When the current
route starts with `/fleetops`, that icon is active. When the section rail is
expanded, the FleetOps group shows child links with active state and prefetch
behavior. The page hero can keep compact page links if useful, but primary
navigation must not depend on the hero.

FleetOps pages should feel like operational screens, not landing pages:

- Use existing `WorkspaceBand` and existing dark surface tokens.
- Keep forms in drawers or focused panels, not nested cards.
- Use Lucide icons in action buttons.
- Empty states must include the next valid action.
- Every page must deep-link to its state through the URL where practical.

## Vessel Workflow

The Vessels page owns the first operator action: add a vessel.

### Vessel List Triage

The Vessels page is also the fleet-level triage surface for operators who need
to find a specific vessel without scrolling through every row. It must keep the
same behavior conventions as the rest of the workspace:

- no implicit detail selection on load
- search and filters before the list
- bounded result sets
- clear empty states for no data versus no matching filters
- query-string backed controls so views can be shared

The list controls must include:

- a search input labelled `Search vessels`
- a link-state filter labelled `Link state`
- a vessel-status filter labelled `Status`
- a page-size selector labelled `Rows per page`
- pagination controls that show 10, 25, or 50 rows per page

Search must match:

- vessel name
- IMO number
- MMSI
- call sign
- site ID
- site name when the response includes the embedded site payload
- link state
- active or inactive status

The link-state filter is derived from the loaded vessel rows. The status filter
offers `All statuses`, `Active`, and `Inactive`. The page-size selector offers
only `10`, `25`, and `50`, with `10` as the default. Changing search, link
state, status, or page size resets the page to `1`.

The URL query parameters are:

- `q`
- `link`
- `status`
- `page`
- `pageSize`

Invalid `page` and `pageSize` query values are normalized in the UI. The
frontend continues to call `GET /api/v1/maritime/vessels`; this pass does not
add server-side vessel search or pagination. If fleet sizes later make
client-side filtering too expensive, a separate backend pagination plan is
required.

### Add Vessel Form

Required:

- Vessel name
- Site binding mode:
  - create a site for this vessel
  - bind an existing site

Default site creation fields:

- Site name defaults to the vessel name.
- Time zone defaults to `UTC`.
- Description defaults to `FleetOps vessel site for <vessel name>`.

Optional vessel identifiers:

- IMO number
- MMSI
- Call sign
- Flag state
- Vessel type
- Owner label
- Manager label
- Charterer label

Optional metadata:

- Home port
- Notes

The form submits to `POST /api/v1/maritime/vessels` with either `create_site`
or `site_id`, never both. On success it invalidates maritime vessel queries,
site queries, fleet summaries, and navigates to `/fleetops/vessels/{vessel_id}`.

### Edit Vessel

The detail page should expose edit and deactivate actions backed by:

- `PATCH /api/v1/maritime/vessels/{vessel_id}`
- `DELETE /api/v1/maritime/vessels/{vessel_id}`

Identifier edits remain out of this UI pass unless the backend update contract
is widened. If identifier updates are required later, the backend must first
add explicit tests for uniqueness and tenant isolation.

## Core Link Connection Model

`argus.link` should add a domain-neutral `LinkConnection` concept. A connection
is a named path a site may use to reach central services or move evidence.

Transport kinds:

- `satellite`
- `lte`
- `5g`
- `wifi`
- `fiber`
- `ethernet`
- `other`

Connection fields:

- `id`
- `tenant_id`
- `site_id`
- `label`
- `transport_kind`
- `provider`
- `status`
- `priority_rank`
- `availability_scope`
- `metered`
- `monthly_bytes`
- `bulk_daily_bytes`
- `expected_downlink_mbps`
- `expected_uplink_mbps`
- `expected_latency_ms`
- `packet_loss_percent`
- `last_seen_at`
- `metadata`
- `created_at`
- `updated_at`

Allowed statuses:

- `unknown`
- `online`
- `degraded`
- `offline`
- `blocked`
- `recovering`

Availability scopes:

- `always`
- `at_sea`
- `near_shore`
- `in_port`
- `maintenance`

The core link passport should include:

- active connection summary
- candidate connections sorted by rank and status
- queue depth by lane
- latest probe
- budget state
- backpressure decision

The existing `LinkHealthProbe` should gain an optional `connection_id` so
probes can be attached to a specific satellite, LTE, fiber, or other path while
remaining valid for generic packless sites.

## Maritime Carrier Mapping

Maritime carrier terminal telemetry remains pack-owned. It maps into core link
connections without moving maritime nouns into core.

Generic carrier payloads may include:

- `terminal_id`
- `provider`
- `transport_kind`
- `status`
- `link_state`
- `downlink_mbps`
- `uplink_mbps`
- `latency_ms`
- `packet_loss_percent`
- `last_seen_at`

If `transport_kind` is omitted, the maritime adapter may infer it from generic
payload values:

- legacy `satellite_good` and `satellite_degraded` map to `satellite`
- legacy `port_wifi` maps to `wifi` with `availability_scope = "in_port"`
- unknown values map to `other`

Carrier selection should return the best usable core connection for the
requested priority lane. It should prefer unmetered or high-capacity in-port
connections for bulk transfer, keep safety/evidence lanes available on degraded
metered links when budget permits, and defer bulk movement when only expensive
or degraded links remain.

## Page Plumbing Requirements

### FleetOps Overview

The overview page should summarize real data:

- vessel count and exceptions
- active link connection posture
- evidence queue depth
- current billable usage
- support readiness
- onboarding readiness

The overview should link into each page and should not be the only way to
navigate.

### Vessels

Backed by:

- `GET /api/v1/maritime/vessels`
- `POST /api/v1/maritime/vessels`
- `PATCH /api/v1/maritime/vessels/{vessel_id}`
- `DELETE /api/v1/maritime/vessels/{vessel_id}`
- `GET /api/v1/sites`

The empty state must show an Add Vessel action.

The non-empty state must not render every vessel by default. It renders the
current filtered page only, with a result count and pagination controls. A
filtered zero-result state shows `No vessels match these filters` and a clear
filters action; it does not reuse the add-vessel empty state.

### Vessel Detail

Backed by:

- vessel detail, telemetry, link status, carrier selection
- core link connections
- core link budget, queue, probes, and policies
- voyages and port calls
- evidence context and exports

The detail page should have clear sections for overview, connectivity,
telemetry, voyage/port call timeline, evidence, and actions.

### Evidence

Backed by:

- `GET /api/v1/maritime/evidence-context`
- `GET /api/v1/maritime/evidence-exports`
- `POST /api/v1/maritime/evidence-exports`
- `GET /api/v1/link/sites/{site_id}/queue`
- queue pause/resume/retry actions where available

The page should show pending work, completed exports, link posture, and the
reason work is deferred.

### Billing

Backed by:

- `GET /api/v1/maritime/billing/usage`
- `GET /api/v1/maritime/billing/rollups`
- `GET /api/v1/billing/meters?pack_id=maritime-fleet`
- `GET /api/v1/billing/usage?pack_id=maritime-fleet`
- invoice runs and billing exports if data exists

The page must not claim payment or accounting integration.

### Support

Support is for diagnosis and assistance after or during operation.

Backed by:

- maritime support readiness diagnostics
- support bundles
- support sessions
- tunnel requests and revocation
- break-glass open/close records

"Diagnostic groups" should be renamed in the UI to "Support readiness" or
"Readiness groups." Each group should display label, status, checks, evidence
source, and next action.

### Onboarding

Onboarding is for getting a vessel operational.

Backed by:

- `GET /api/v1/support/onboarding-checks?site_id=...`
- `POST /api/v1/support/onboarding-checks/run`
- maritime onboarding checklist contribution
- vessel/site/link configuration state

The page should show a checklist with actionable states:

- vessel created
- site bound
- connectivity profile configured
- camera templates available
- evidence storage available
- billing entitlement present
- support path ready

Onboarding should not render the support diagnostics panel.

## Backend Completeness Definition

A FleetOps UI control is fully plumbed only when:

- the backend route exists
- the OpenAPI schema includes the route
- the frontend hook uses the generated typed client
- loading, error, empty, and success states are visible
- mutations invalidate the affected TanStack Query keys
- unit tests cover success and at least one failure or empty state
- Playwright covers the happy path for the primary operator workflow

If a page has a visible command but the backend route does not exist, either add
the route with TDD or remove the command from the page.

## Cross-Cutting Constraints

This design inherits all constraints from
`docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md`.

Additional stop conditions:

- Stop if a core API, table, or contract needs `Vessel`, `Voyage`, `PortCall`,
  AIS, NMEA, `CarrierTerminal`, owner, manager, or charterer fields.
- Stop if traffic/public-space runtime code becomes necessary.
- Stop if proprietary carrier SDK code becomes necessary.
- Stop if payment processor or accounting integration becomes necessary.
- Stop if support tunnel work requires bypassing existing credential reference
  and supervisor dispatch boundaries.

## Testing Strategy

Backend tests:

- core link connection service and API tests
- packless empty registry tests for link connections
- maritime carrier mapping tests for satellite, LTE, 5G, Wi-Fi, fiber,
  ethernet, and other
- support diagnostics/checklist split tests
- evidence, billing, and support API plumbing tests
- OpenAPI export tests

Frontend tests:

- left rail active and expanded FleetOps child navigation
- vessel create form validation and submit
- empty state Add Vessel action
- link connection panels for multiple transport kinds
- evidence queue actions
- billing page data states
- support readiness group rendering
- onboarding checklist run states

Real-stack tests:

- install or run master stack locally
- create a vessel from the UI
- create or ingest multiple link connection types
- navigate all FleetOps pages from the rail
- verify support and onboarding differ
- verify evidence and billing pages render backend data

Installer tests:

- macOS master artifact tests
- Linux master artifact tests
- Jetson Orin edge artifact tests

Installer code should change only if the implementation adds required
configuration, migration packaging, generated assets, or runtime files not
already included by the existing installers.
