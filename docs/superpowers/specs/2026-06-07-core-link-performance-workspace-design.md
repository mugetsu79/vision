# Core Link Performance Workspace Design

Date: 2026-06-07
Status: implemented on branch `codex/sceneops-pack-registry`; retained as product trace. Reflector and edge-agent additions are covered by the linked follow-up specs and `docs/core-link-performance-guide.md`.
Related FleetOps runtime spec: `docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md`
Related FleetOps operator plan: `docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md`
Related operator focus spec: `docs/superpowers/specs/2026-06-07-operator-focus-consistency-design.md`

## Product Design Playback

Core `argus.link` is now real infrastructure: it owns generic site
connectivity, budgets, queues, probes, policies, connection selection, and link
passports. FleetOps consumes that infrastructure, but link performance should
not be hidden inside FleetOps. Operators need one core workspace that shows the
health and throughput posture of every site link, regardless of whether a site
belongs to a vessel, a warehouse, a depot, or a future pack.

The visual source is the current Vezor dark command workspace. The page should
reuse `AppShell`, `WorkspaceBand`, `WorkspaceSurface`, existing form/button
patterns, Lucide icons, TanStack Query hooks, generated OpenAPI types, and the
shared 10/25/50 pagination control. UI/UX guidance for this workspace is:
explicit site selection, search-first navigation, no silent default detail,
clear empty states, keyboard-reachable controls, compact operational density,
and visible feedback for every mutation.

Interactivity level is full interactivity. This is not a static mock.

## Problem

The product currently has a core link layer without a core link workspace.
FleetOps vessel detail can show connection and queue state, and FleetOps
Evidence can retry queued link work, but operators cannot inspect all site link
performance from a domain-neutral page.

This creates three product gaps:

1. FleetOps makes link health feel maritime-specific even though `argus.link`
   is a core engine layer.
2. Operators cannot compare sites by degraded links, queue backlog, latest
   probe, budget posture, or connection coverage without visiting individual
   FleetOps vessel screens.
3. Existing frontend link mutations for connections, budgets, policies, probes,
   and queue actions are not exposed through a complete core workflow.

## Goals

1. Add a domain-neutral Link Performance workspace outside FleetOps.
2. Preserve `CC-4 Link Is Core`: no maritime nouns in core link contracts,
   routes, components, tests, or copy.
3. Let operators search, select, and page through generic sites with 10, 25, or
   50 entries per page.
4. Do not show link detail until the operator explicitly selects a site.
5. Show whole-link posture for a selected site: status, active connection,
   candidate connections, budget, queue lanes, latest probe, probe history,
   transfer queue, policies, and passport hash.
6. Expose existing link mutations in one coherent workspace:
   connection create/edit/delete, budget edit, policy edit, synthetic probe
   record, and queue pause/resume/retry.
7. Give FleetOps pages a generic deep link into the core workspace by `site_id`
   while keeping FleetOps-specific wording in FleetOps only.
8. Keep the implementation packless and usable for generic sites with no active
   product pack.

## Non-Goals

- Do not implement traffic/public-space runtime, UI, demos, or migrations.
- Do not add home-lab packs, home-lab status, or lab-only UI.
- Do not add proprietary carrier SDK integrations.
- Do not add payment processor or accounting integrations.
- Do not move vessel, voyage, port-call, AIS, NMEA, carrier terminal, owner,
  manager, charterer, or any vertical noun into core link.
- Do not change runtime detector semantics, evidence hashes, or link passport
  hashing semantics except to include already-modeled link fields.
- Do not build live charts from websocket telemetry in this pass. The page may
  show probe history from the existing persisted probe list.

## Information Architecture

Add one Control nav entry:

- Label: `Links`
- Route: `/links`
- Page title: `Link Performance`
- Eyebrow: `Core Link`

The route is outside `/fleetops`. FleetOps may link to `/links?site=<site_id>`
from vessel detail, evidence, support, and onboarding pages when a site is in
scope. The Link page should read the query parameter and preselect that site
only when the URL explicitly contains it. With no query parameter, no site is
selected.

## Operator Focus Rule

The page follows the existing operator focus rule:

- Empty search plus no selected site shows overview counts and a choose-site
  empty state.
- Search filters the visible site list but does not auto-select the first row.
- Selecting a site opens the detail panels.
- Clearing selection returns detail panels to empty guidance.
- Mutation controls are disabled until a site is selected.
- URL query state mirrors explicit selection: `?site=<site_id>` when selected,
  no `site` parameter when cleared.

## Page Layout

### Header

Use `WorkspaceBand` with a compact action row:

- Refresh
- Record probe, disabled until a site is selected
- Add connection, disabled until a site is selected
- Edit budget, disabled until a site is selected

The header should not use a landing-page hero. This is a repeated-use command
workspace.

### Summary Strip

Show four compact metrics derived from the currently loaded site summary list:

- Sites monitored
- Degraded or dark sites
- Queued transfer bytes
- Metered connections

If the summary API is still loading, show skeleton rows. If it fails, show a
recoverable error with retry.

### Site Selector

Use a searchable list/table with 10/25/50 pagination:

- Site name
- Time zone
- Link state
- Active connection label and transport kind
- Latest probe latency, throughput, and packet loss
- Queue depth summary
- Budget summary
- Last sync or latest probe timestamp

Rows are buttons or table rows with a real button inside, with visible focus and
selected state. Search matches site name, time zone, active connection,
transport kind, provider, link state, and connection label.

Mobile uses the same data in compact site cards. It does not render a long
unbounded list.

### Detail Panels

When a site is selected, show:

1. **Current Posture**
   - Link state
   - Passport hash
   - Active connection
   - Latest probe
   - Last sync
   - Backpressure state when available

2. **Connections**
   - Candidate connections sorted by status and priority
   - Transport kind, provider, status, scope, metered flag, expected
     downlink/uplink, expected latency, expected packet loss, last seen
   - Add/edit/delete controls

3. **Budget And Policy**
   - Monthly byte budget
   - Bulk daily byte budget
   - Policy JSON editor or structured key/value editor
   - Save feedback and validation errors

4. **Probe History**
   - Latest persisted probes for the selected site
   - Latency, throughput, packet loss, reachable, source, timestamp, optional
     connection
   - Manual record-probe dialog for admin users

5. **Transfer Queue**
   - Items grouped or filtered by priority lane: safety, evidence, telemetry,
     bulk
   - Status, byte size, source object, pause reason, last successful transfer
   - Retry, pause, resume actions

6. **Link Passport**
   - Read-only payload summary: active connection, candidates, queue depth,
     latest probe, budget, and hash
   - Copy hash action

## Backend Requirements

Existing routes remain the source of truth for selected-site detail:

- `GET /api/v1/link/sites/{site_id}/status`
- `GET /api/v1/link/sites/{site_id}/budget`
- `PUT /api/v1/link/sites/{site_id}/budget`
- `GET /api/v1/link/sites/{site_id}/connections`
- `POST /api/v1/link/sites/{site_id}/connections`
- `PATCH /api/v1/link/sites/{site_id}/connections/{connection_id}`
- `DELETE /api/v1/link/sites/{site_id}/connections/{connection_id}`
- `GET /api/v1/link/sites/{site_id}/queue`
- `GET /api/v1/link/sites/{site_id}/probes`
- `POST /api/v1/link/sites/{site_id}/probes`
- `GET /api/v1/link/sites/{site_id}/policies`
- `PUT /api/v1/link/sites/{site_id}/policies`
- `POST /api/v1/link/queue/{queue_item_id}/retry`
- `POST /api/v1/link/queue/{queue_item_id}/pause`
- `POST /api/v1/link/queue/{queue_item_id}/resume`

Add one aggregate list route so the Link page does not fan out across every
site:

- `GET /api/v1/link/sites/summary`

Response item fields:

- `site_id`
- `site_name`
- `site_tz`
- `link_state`
- `active_connection`
- `connection_count`
- `metered_connection_count`
- `latest_probe`
- `queue_depth`
- `queued_bytes`
- `budget`
- `last_sync_at`
- `passport_hash`

The summary route must remain packless and domain-neutral. It may join against
generic `sites`, `link_connections`, `link_health_probes`, `link_queue_items`,
`link_budgets`, and `link_passport_snapshots`. It must not import or reference
`argus.maritime`.

The summary route must expose a named OpenAPI response model so the frontend can
use generated TypeScript instead of a hand-written parallel DTO.

## Monitored And Recorded Values

The workspace displays values already recorded by `argus.link`:

- Connection inventory: label, transport kind, provider, status, priority rank,
  availability scope, metered flag, monthly bytes, bulk daily bytes, expected
  downlink Mbps, expected uplink Mbps, expected latency ms, expected packet
  loss percent, last seen, metadata.
- Probe measurements: connection id, latency ms, throughput Mbps, packet loss
  percent, reachable, source, recorded time.
- Queue state: priority lane, byte size, source object type/id, status, camera
  id, incident id, evidence artifact id, pause reason, paused time, last
  successful transfer.
- Budget and policy: monthly bytes, bulk daily bytes, policy JSON.
- Passport state: link state, passport hash, active connection, candidate
  connections, queue depth, latest probe, budget, last sync.

Derived values for UI:

- degraded/dark site count
- total queued bytes
- queue depth by lane
- metered connection count
- active transport label
- latest probe age

## Frontend Requirements

Add:

- `frontend/src/pages/Links.tsx`
- `frontend/src/pages/Links.test.tsx`
- `frontend/src/components/link/LinkSiteSelector.tsx`
- `frontend/src/components/link/LinkPosturePanel.tsx`
- `frontend/src/components/link/LinkConnectionsPanel.tsx`
- `frontend/src/components/link/LinkBudgetPolicyPanel.tsx`
- `frontend/src/components/link/LinkProbePanel.tsx`
- `frontend/src/components/link/LinkQueuePanel.tsx`
- `frontend/src/components/link/LinkActionDialogs.tsx`

Extend:

- `frontend/src/hooks/use-link.ts`
- `frontend/src/app/router.tsx`
- `frontend/src/components/layout/workspace-nav.ts`
- `frontend/src/components/layout/AppShell.test.tsx`
- FleetOps pages/components that should deep-link into core link detail.

Use generated OpenAPI types for all payloads. Do not create hand-written
parallel DTOs when generated schemas exist.

## Error Handling

- Selected-site queries should show panel-level loading and error states rather
  than blanking the full page.
- Mutation errors should appear near the triggering dialog or panel.
- A failed summary load should not prevent a deep-linked selected site from
  loading if `?site=` is present.
- Missing or deleted selected sites should clear the URL parameter and show
  neutral empty guidance.

## Access Control

Viewers can read link summaries and selected-site detail. Admin-only controls
remain protected by backend authorization. The frontend should disable or hide
admin mutation controls for non-admin users if the local role is available, but
backend role checks are authoritative.

## Testing Requirements

Backend:

- Summary service/API tests with no packs active.
- Tenant isolation tests.
- Summary response includes selected active connection, queue depth, latest
  probe, budget, and passport hash.
- Summary route does not import maritime or require maritime fixtures.

Frontend:

- Route and nav tests for `/links`.
- Link page starts with no selected site.
- Search filters sites without selecting the first result.
- Pagination limits visible rows to 10, 25, or 50.
- `?site=<site_id>` explicitly selects a site.
- Selected-site panels call existing link hooks and render status, connections,
  probes, budget/policy, queue, and passport data.
- Add/edit/delete connection, budget save, policy save, record probe, and queue
  actions call the correct hooks and show feedback.
- FleetOps deep links point to `/links?site=<site_id>` without changing
  FleetOps page semantics.

## Scope Safety

This work strengthens the core link layer without widening pack scope. It must
preserve all existing `CC-*` constraints:

- `CC-1 Packless Core Compatibility`: summary and UI work with generic sites.
- `CC-2 Pack Boundary`: no pack-specific routes or imports in core link.
- `CC-3 Traffic Boundary`: no traffic/public-space runtime or UI.
- `CC-4 Link Is Core`: link remains generic and outside FleetOps.
- `CC-8 Evidence Integrity`: queue/passport display does not recompute evidence
  hashes.
- `CC-9 Frontend Reuse`: reuse shell, workspace primitives, generated types,
  TanStack Query, shared pagination, and existing hooks.
