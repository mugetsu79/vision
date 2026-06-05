# Maritime FleetOps Runtime Pack Design

Date: 2026-06-05
Status: ready for review before implementation planning
Related blueprint: `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`
Related pack boundary spec: `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
Related manifests:

- `packs/maritime-fleet/pack.yaml`
- `packs/traffic-public-space/pack.yaml`

## Summary

Maritime FleetOps should become the first fully functional SceneOps pack. The
pack turns the current generic SceneOps engine into a product for
satellite-connected fleet operations: vessels, voyages, port calls, maritime
telemetry, link-aware evidence movement, maritime scene templates, and fleet
operator workflows.

The implementation must be product-complete enough to run a credible FleetOps
pilot without making core maritime-shaped. Core continues to own tenants, users,
generic sites, cameras, scene contracts, incidents, evidence artifacts, runtime
passports, link/runtime delivery primitives, operator configuration, and the
pack registry. The Maritime FleetOps pack owns maritime entities, maritime
telemetry context, scene template application, evidence enrichment, FleetOps UI
surfaces, and pack-specific billing labels.

This design expands beyond the read-only registry. It builds a real
`argus.maritime` runtime module and a frontend FleetOps workspace. It does not
activate traffic/public-space, does not create home-lab packs, and does not put
maritime nouns into core contracts.

## Product Goal

Build Vezor FleetOps as a usable pack for remote maritime operations:

> Live fleet signals, trusted evidence, built for bad links.

An operator should be able to create vessels, assign cameras, define voyages and
port calls, apply maritime scene templates, ingest maritime telemetry, review
evidence with vessel/voyage/position/link context, and monitor fleet exceptions
from one workspace.

## Scope

### In Scope

- A backend `argus.maritime` pack module.
- Pack-owned database tables for vessels, voyages, port calls, AIS positions,
  NMEA readings, carrier terminal state, maritime roles, and watch rotations.
- A minimum core `argus.link` baseline required by the FleetOps wedge:
  bandwidth budgets, priority lanes, evidence backlog, resume-on-interrupt,
  backpressure, link health probes, last sync, and link passport snapshots.
- A minimum core `argus.fleet` baseline required by the FleetOps workspace:
  site groups, site hierarchy nodes, site state, site assignments, rotation
  groups, and exception-first fleet summaries.
- Maritime APIs under `/api/v1/maritime`.
- Link-state APIs under `/api/v1/link` using domain-neutral core contracts.
- Fleet-state APIs under `/api/v1/fleet` using domain-neutral core contracts.
- Runtime contribution APIs connected to the existing pack registry.
- Maritime scene templates based on the `maritime-fleet` manifest.
- Template application that creates or updates core camera scene configuration
  using existing core primitives.
- Ingest APIs for AIS, NMEA, and carrier terminal telemetry.
- File or fixture import paths for pilot/demo telemetry when live integrations
  are unavailable.
- Evidence enrichment that links core incidents and artifacts to maritime
  context without changing core incident storage semantics.
- FleetOps frontend pages for fleet overview, vessel detail, voyage and port
  call timeline, telemetry state, maritime evidence context, and link-aware
  evidence queue.
- Governance tests that keep traffic/public-space manifest-only and prevent
  maritime nouns from entering core contracts.
- OpenAPI regeneration for typed frontend hooks once backend contracts exist.

### Out of Scope

- Traffic/public-space runtime code, APIs, UI, migrations, demos, or sales
  motion.
- A home-lab pack, home-lab dashboard, or home-lab customer demo.
- Billing migrations that create invoice or payment behavior.
- Proprietary carrier, AIS vendor, or NMEA hardware integrations that require
  unavailable credentials or closed protocol documents.
- Runtime detector semantics that bypass current scene contracts, camera
  configuration, evidence, or runtime passport behavior.
- Face recognition, biometric identification, or public-space surveillance
  features.
- Moving `Vessel`, `Voyage`, `PortCall`, AIS, NMEA, owner, manager, or
  charterer concepts into core contracts.

## Source Decisions

The prior one-pack boundary remains binding:

- `maritime-fleet` is the only pack authorized for implementation.
- `traffic-public-space` remains `designed_not_implemented`.
- Home/lab testing remains packless engine validation.
- Core must stay domain-neutral.
- Vertical entities live behind pack-owned contracts and tables.

The Maritime FleetOps pack is allowed to implement runtime code because its
manifest status is `planned_mvp` and `implementation_commitment` is true.
Traffic/public-space is not allowed to implement runtime code because its
manifest status is `designed_not_implemented` and `implementation_commitment`
is false.

## Blueprint Coverage

The FleetOps blueprint includes more than maritime pack entities. A credible
FleetOps runtime also requires the baseline `argus-link` layer and selected
support, edge, camera, and billing extension points. This spec includes those
items where they are required for the first functional product.

| Blueprint item | Owner | This spec |
|---|---|---|
| Pack registry and manifest enforcement | core | already implemented by prior branch; used as runtime gate |
| `argus.maritime` pack | maritime pack | in scope |
| Vessel, voyage, port-call entities | maritime pack | in scope |
| AIS, NMEA, carrier telemetry | maritime pack | in scope |
| Maritime scene templates | maritime pack using core scene primitives | in scope |
| Maritime evidence context | maritime pack plus core evidence seams | in scope |
| `argus-link` bandwidth budgets | core link layer | in scope as minimum baseline |
| Priority lanes: safety, evidence, telemetry, bulk | core link layer | in scope as minimum baseline |
| Evidence backlog and queue depth | core link layer | in scope as minimum baseline |
| Resume-on-interrupt and backpressure | core link layer | in scope as minimum baseline |
| Link probes and last successful sync | core link layer | in scope as minimum baseline |
| Runtime UI for degraded, dark, port WiFi, recovering | core link layer plus FleetOps UI | in scope |
| `argus.fleet` generic site hierarchy | core fleet layer | in scope as minimum baseline |
| Site state, site assignment, rotation groups | core fleet layer | in scope as minimum baseline |
| Fleet exception dashboard | core fleet layer plus FleetOps UI | in scope |
| Hash-linked evidence, signed artifacts, audit log | core chain-of-custody layer | already partly implemented; preserved and extended through metadata |
| Evidence pack export with scene contract context | core evidence/export layer plus maritime metadata | in scope |
| Time-source provenance and retention hooks | core chain-of-custody layer | in scope for evidence context/export metadata, not a full compliance suite |
| Remote support bundle, NOC tunnel, break-glass | core support layer | limited to diagnostics surfacing; tunnel implementation is follow-up |
| Shipboard support wording and install checklist | maritime pack | in scope as docs/UI copy |
| Marine-grade hardware recommendations | maritime pack docs | in scope as docs, not hardware certification |
| DNV or cybersecurity certification | maritime pack docs | out of scope beyond notes |
| Camera onboarding defaults and bandwidth assumptions | maritime pack plus core camera ecosystem | in scope |
| Billing node tree and invoices | core billing | out of scope for migrations/invoices |
| Maritime billing labels and meters | maritime pack | in scope as labels/counters |
| Traffic/public-space runtime | traffic pack | explicitly out of scope |

## Architecture

### Core Engine Boundary

Core owns the stable SceneOps platform:

- tenants, users, roles, and authentication
- generic `Site`, `Camera`, `Model`, `DetectionRule`, and `SceneContract`
- incidents, evidence artifacts, evidence ledger, and evidence export
- runtime passports, supervisor state, worker assignments, and deployment nodes
- operator configuration profiles
- model catalog and runtime artifacts
- pack registry and manifest validation
- `argus.fleet` site groups, hierarchy, site state, site assignments,
  rotation groups, and exception-first fleet summaries
- `argus.link` link passports, budgets, priority lanes, transfer queues,
  backpressure, probes, and last-sync state

Core may expose extension seams, but it must not contain maritime entity names
in shared contracts or route payloads unless they are opaque pack metadata
inside a pack-owned response.

### Core Argus-Link Baseline

`argus.link` is a core engine layer, not a maritime pack. It is still required
for the FleetOps product because the wedge depends on evidence movement over
bad links.

The minimum baseline owns these domain-neutral concepts:

- `LinkState`: `unknown`, `healthy`, `degraded`, `dark`, `recovering`,
  `port_wifi`
- `LinkPriorityLane`: `safety`, `evidence`, `telemetry`, `bulk`
- `LinkBudget`: tenant/site/camera bandwidth and byte-budget policy
- `LinkQueueItem`: queued transfer work with lane, byte size, status, attempts,
  and resume token
- `LinkTransferAttempt`: append-only transfer attempts with start/end time,
  bytes moved, error, and interruption reason
- `LinkHealthProbe`: latency, throughput, packet loss, reachability, and probe
  source
- `LinkPassportSnapshot`: immutable link posture attached to incidents,
  evidence exports, and runtime summaries

The baseline must support:

- site bandwidth budget checks before bulk transfer
- priority ordering: safety before evidence before telemetry before bulk
- evidence backlog and queue depth by site, vessel, camera, and priority lane
- resume-on-interrupt using byte offsets or object-part markers where the
  storage provider supports it
- backpressure decisions that pause lower-priority transfer work under degraded
  or exhausted budget conditions
- link health probes that mark state as healthy, degraded, dark, port WiFi, or
  recovering
- last sync and last successful evidence transfer timestamps
- UI-ready summaries for degraded, dark, port WiFi, and recovering states

Maritime pack code may contribute carrier terminal telemetry and vessel/port
context to link summaries. It must not own the core queue, budget, backpressure,
or link passport semantics.

### Core Argus-Fleet Baseline

`argus.fleet` is also a core engine layer, not the Maritime FleetOps pack. The
name "fleet" here means a generic deployed-site fleet, not vessels.

The minimum baseline owns these domain-neutral concepts:

- `SiteGroup`: a tenant-scoped grouping for deployed sites.
- `SiteHierarchyNode`: a generic adjacency node that can model reseller,
  operator, region, owner, fleet, or other product-neutral groupings.
- `SiteState`: latest runtime, link, evidence, and attention state for a site.
- `SiteAssignment`: assignment of sites to users, roles, groups, or support
  queues.
- `RotationGroup`: a generic operator/reviewer rotation primitive that packs can
  label for their domain.
- `FleetException`: a computed summary item for stale heartbeat, degraded link,
  evidence backlog, stopped worker, privacy mismatch, model/artifact mismatch,
  or active incident.

The baseline must support:

- grouping sites without maritime names
- resolving a site hierarchy without owner/manager/charterer hardcoding
- reporting site runtime state and link state through generic fields
- assigning sites to operator or support rotations
- producing an exception-first dashboard ordered by operational attention

Maritime pack code may project vessels, owners, managers, charterers, shipboard
roles, and watch rotations onto these generic primitives. It must not move those
labels into core fleet contracts.

### Maritime Pack Boundary

The pack owns a new Python package:

- `backend/src/argus/maritime/contracts.py`
- `backend/src/argus/maritime/tables.py`
- `backend/src/argus/maritime/service.py`
- `backend/src/argus/maritime/templates.py`
- `backend/src/argus/maritime/telemetry.py`
- `backend/src/argus/maritime/evidence.py`
- `backend/src/argus/maritime/api.py`
- `backend/src/argus/maritime/__init__.py`

The pack uses core IDs as references:

- `tenant_id` references `tenants.id`
- `site_id` references `sites.id`
- `camera_id` references `cameras.id`
- `incident_id` references `incidents.id`
- `evidence_artifact_id` references `evidence_artifacts.id` when needed
- `scene_contract_snapshot_id` references `scene_contract_snapshots.id` when
  evidence enrichment needs immutable context

The pack may import core models and services. Core services should not import
pack-specific contracts except through a narrow pack registration seam needed by
Alembic metadata, service construction, and router inclusion.

### Pack Registration

The existing `PackRegistry` remains the source of manifest truth. The Maritime
runtime module should expose a small registration object that validates:

- manifest exists
- manifest id is `maritime-fleet`
- status is `planned_mvp` or `active`
- implementation commitment is true
- required core capabilities are available

The API should include:

- `GET /api/v1/packs/maritime-fleet/runtime`
- `GET /api/v1/maritime/runtime`

Both may return the same runtime contribution payload. The pack-scoped endpoint
proves the pack boundary; the maritime endpoint gives product UI a stable home.

For `traffic-public-space`, any runtime endpoint must return a not-enabled
response or 404. No `argus.traffic_public_space` package should exist.

## Data Model

### Vessel

`Vessel` is the maritime projection of a generic core `Site`.

Required fields:

- `id`
- `tenant_id`
- `site_id`
- `name`
- `imo_number`
- `mmsi`
- `call_sign`
- `flag_state`
- `vessel_type`
- `owner_label`
- `manager_label`
- `charterer_label`
- `active`
- `metadata`
- `created_at`
- `updated_at`

Rules:

- `site_id` is required and tenant-scoped.
- `imo_number`, `mmsi`, and `call_sign` are optional individually but at least
  one vessel identifier or a name must be present.
- Uniqueness is tenant-scoped for non-null `imo_number`, non-null `mmsi`, and
  non-null `call_sign`.
- Deleting a vessel should be a soft deactivate operation unless no voyage,
  port call, telemetry, or evidence context exists.

### Voyage

`Voyage` is a time-bound maritime operating context for a vessel.

Required fields:

- `id`
- `tenant_id`
- `vessel_id`
- `name`
- `voyage_number`
- `origin`
- `destination`
- `status`
- `scheduled_departure_at`
- `scheduled_arrival_at`
- `actual_departure_at`
- `actual_arrival_at`
- `metadata`
- `created_at`
- `updated_at`

Statuses:

- `planned`
- `active`
- `completed`
- `cancelled`

Rules:

- Only one active voyage per vessel is allowed.
- A voyage cannot complete before it departs.
- Voyage time windows are used to resolve evidence context when an incident has
  no explicit voyage assignment.

### Port Call

`PortCall` attaches arrival, berth, departure, and link context to a voyage.

Required fields:

- `id`
- `tenant_id`
- `vessel_id`
- `voyage_id`
- `port_name`
- `un_locode`
- `terminal_name`
- `berth`
- `status`
- `eta`
- `ata`
- `etd`
- `atd`
- `link_profile`
- `metadata`
- `created_at`
- `updated_at`

Statuses:

- `scheduled`
- `arrived`
- `alongside`
- `departed`
- `cancelled`

Rules:

- Port calls are ordered by time within a voyage.
- Active or recent port calls should bias evidence export and backlog-drain
  views because high-bandwidth sync is expected near port.

### AIS Position

`AISPosition` stores normalized AIS context for a vessel.

Required fields:

- `id`
- `tenant_id`
- `vessel_id`
- `source`
- `received_at`
- `reported_at`
- `mmsi`
- `latitude`
- `longitude`
- `speed_over_ground`
- `course_over_ground`
- `heading`
- `navigational_status`
- `raw_payload`
- `created_at`

Rules:

- Positions are append-only.
- Latitude and longitude are validated.
- The service exposes latest position per vessel and a bounded recent track.
- Duplicate suppression uses tenant, source, MMSI, reported time, and position.

### NMEA Reading

`NMEAReading` stores normalized bridge telemetry attached to a vessel.

Required fields:

- `id`
- `tenant_id`
- `vessel_id`
- `source`
- `received_at`
- `sentence_type`
- `timestamp`
- `values`
- `raw_sentence`
- `created_at`

Rules:

- Supported first-pass sentence families are GPS and heading/speed-oriented
  fields that can enrich evidence context.
- Unsupported sentence types are stored as raw readings with parsed values empty
  rather than rejected, unless the payload is malformed.

### Carrier Terminal State

`CarrierTerminal` tracks satellite or managed-link terminal posture.

Required fields:

- `id`
- `tenant_id`
- `vessel_id`
- `terminal_id`
- `provider`
- `status`
- `link_state`
- `downlink_mbps`
- `uplink_mbps`
- `latency_ms`
- `packet_loss_percent`
- `last_seen_at`
- `raw_payload`
- `created_at`
- `updated_at`

Statuses:

- `unknown`
- `online`
- `degraded`
- `offline`
- `blocked`

Link states:

- `unknown`
- `satellite_good`
- `satellite_degraded`
- `port_wifi`
- `dark`
- `recovering`

Rules:

- Latest state is mutable by terminal id.
- Historical changes should be recorded through telemetry events or audit
  metadata if later product needs require timeline playback.

### Maritime Roles And Watch Rotations

`MaritimeRole` and `WatchRotation` provide reviewer and operations context.

Roles:

- `fleet_admin`
- `fleet_operator`
- `captain`
- `chief_engineer`
- `eto`
- `security_officer`
- `reviewer`

Watch rotations track named shifts and reviewer groups. The MVP needs enough
structure to attach role labels to evidence review and handover context without
replacing core authentication or authorization.

## API Design

All maritime routes are tenant-scoped and require normal authenticated access.
Viewer routes use viewer authorization; mutations require admin authorization
unless the route is explicitly an ingest route using a supervisor or API token.

### Runtime And Catalog

- `GET /api/v1/maritime/runtime`
- `GET /api/v1/packs/maritime-fleet/runtime`

Response includes:

- pack id and manifest version
- runtime enabled flag
- scene templates
- model presets
- evidence fields
- integration descriptors and implementation status
- UI labels and panels
- billing labels and meters

### Argus-Link

Link routes use core contracts and are available outside Maritime FleetOps:

- `GET /api/v1/link/sites/{site_id}/status`
- `GET /api/v1/link/sites/{site_id}/budget`
- `PUT /api/v1/link/sites/{site_id}/budget`
- `GET /api/v1/link/sites/{site_id}/queue`
- `GET /api/v1/link/sites/{site_id}/probes`
- `POST /api/v1/link/sites/{site_id}/probes`
- `GET /api/v1/link/evidence/{incident_id}/passport`
- `POST /api/v1/link/queue/{queue_item_id}/retry`
- `POST /api/v1/link/queue/{queue_item_id}/pause`
- `POST /api/v1/link/queue/{queue_item_id}/resume`

FleetOps routes may compose these into maritime summaries:

- `GET /api/v1/maritime/vessels/{vessel_id}/link-status`
- `GET /api/v1/maritime/vessels/{vessel_id}/evidence-backlog`

The maritime responses may include vessel, voyage, port-call, and carrier
terminal context. The core link responses must remain generic.

### Argus-Fleet

Fleet routes use core contracts and are available outside Maritime FleetOps:

- `GET /api/v1/fleet/site-groups`
- `POST /api/v1/fleet/site-groups`
- `GET /api/v1/fleet/hierarchy`
- `PUT /api/v1/fleet/hierarchy`
- `GET /api/v1/fleet/sites/{site_id}/state`
- `GET /api/v1/fleet/exceptions`
- `GET /api/v1/fleet/rotation-groups`
- `POST /api/v1/fleet/rotation-groups`
- `GET /api/v1/fleet/site-assignments`
- `POST /api/v1/fleet/site-assignments`

FleetOps routes may compose these into maritime summaries:

- `GET /api/v1/maritime/fleet-overview`
- `GET /api/v1/maritime/vessels/{vessel_id}/runtime-summary`

The maritime responses may label a site as a vessel and a site group as a fleet.
The core fleet responses must remain generic.

### Vessels

- `GET /api/v1/maritime/vessels`
- `POST /api/v1/maritime/vessels`
- `GET /api/v1/maritime/vessels/{vessel_id}`
- `PATCH /api/v1/maritime/vessels/{vessel_id}`
- `DELETE /api/v1/maritime/vessels/{vessel_id}`

Create behavior:

- Can create a generic core `Site` and vessel together.
- Can attach to an existing `Site`.
- Returns both vessel fields and the linked `SiteResponse`.

### Voyages And Port Calls

- `GET /api/v1/maritime/vessels/{vessel_id}/voyages`
- `POST /api/v1/maritime/vessels/{vessel_id}/voyages`
- `GET /api/v1/maritime/voyages/{voyage_id}`
- `PATCH /api/v1/maritime/voyages/{voyage_id}`
- `POST /api/v1/maritime/voyages/{voyage_id}/activate`
- `POST /api/v1/maritime/voyages/{voyage_id}/complete`

- `GET /api/v1/maritime/voyages/{voyage_id}/port-calls`
- `POST /api/v1/maritime/voyages/{voyage_id}/port-calls`
- `PATCH /api/v1/maritime/port-calls/{port_call_id}`
- `POST /api/v1/maritime/port-calls/{port_call_id}/arrive`
- `POST /api/v1/maritime/port-calls/{port_call_id}/depart`

### Scene Templates

- `GET /api/v1/maritime/scene-templates`
- `POST /api/v1/maritime/cameras/{camera_id}/apply-template`

Template application should use existing camera configuration primitives:

- active classes
- runtime vocabulary
- detection regions
- zones
- incident rules
- evidence recording policy
- privacy defaults
- scene contract snapshot generation through existing core service paths

Templates must not introduce a second scene execution engine. They are
opinionated setup payloads over the core camera and scene contract model.

### Telemetry Ingest

- `POST /api/v1/maritime/ingest/ais`
- `POST /api/v1/maritime/ingest/nmea`
- `POST /api/v1/maritime/ingest/carrier-terminal`
- `POST /api/v1/maritime/import/ais-file`
- `POST /api/v1/maritime/import/nmea-file`

The live ingest routes accept normalized JSON payloads. File import routes
support pilot fixtures and lab validation without vendor credentials.

Ingest behavior:

- validates tenant and vessel identity
- normalizes payloads into pack-owned telemetry tables
- updates latest vessel runtime summary
- records audit metadata for source, received time, and parsing status
- never blocks core incident ingestion if telemetry is delayed or missing

### FleetOps Dashboard

- `GET /api/v1/maritime/fleet-overview`
- `GET /api/v1/maritime/vessels/{vessel_id}/runtime-summary`
- `GET /api/v1/maritime/vessels/{vessel_id}/telemetry`
- `GET /api/v1/maritime/evidence-context`

Overview includes:

- vessel count
- active voyages
- active or recent port calls
- latest AIS state coverage
- latest link state coverage
- pending maritime evidence count
- degraded links
- cameras without scene templates
- vessels without recent telemetry

## Evidence Context

Core incidents remain core incidents. The pack enriches them by writing and
reading maritime context through pack-owned tables or derived views.

The pack should provide a `MaritimeEvidenceContext` response containing:

- `incident_id`
- `camera_id`
- `vessel_id`
- `vessel_name`
- `voyage_id`
- `voyage_name`
- `port_call_id`
- `port_name`
- `ais_position`
- `carrier_terminal_state`
- `link_state`
- `maritime_reviewer_role`
- `resolved_at`
- `resolution_source`

Resolution order:

1. Explicit maritime evidence context row for the incident.
2. Camera to vessel through camera site and vessel site.
3. Active voyage for vessel at incident time.
4. Port call overlapping or nearest to incident time.
5. Latest AIS and terminal state before incident time within configured
   freshness windows.

Missing telemetry should produce partial context with explicit freshness and
resolution source, not an error.

Evidence export should include maritime context as an additional metadata block
while preserving the existing core evidence artifact hashes, ledger entries,
and scene contract references.

The first FleetOps evidence pack export must include:

- incident and artifact IDs
- scene contract hash and privacy manifest hash
- runtime passport hash
- link passport hash
- evidence ledger summary
- vessel, voyage, port-call, AIS, terminal, and reviewer-role metadata when
  available
- time-source provenance fields where available
- retention/export policy fields where available

Adding maritime or link metadata must not recompute existing artifact hashes or
break evidence ledger chaining.

## Frontend Design

The frontend should add a FleetOps workspace without turning the whole product
into a maritime-only app.

Routes:

- `/fleetops`
- `/fleetops/vessels`
- `/fleetops/vessels/:vesselId`
- `/fleetops/evidence`

Navigation labels may be contributed from the pack runtime response:

- Site becomes Vessel inside FleetOps surfaces.
- Site group becomes Fleet inside FleetOps surfaces.
- Core pages may keep generic labels unless they are rendered inside FleetOps.

Primary surfaces:

- Fleet overview with active voyages, link state, evidence queue, and telemetry
  coverage.
- Vessel list with scene count, current voyage, latest AIS, latest link state,
  and pending evidence.
- Vessel detail with cameras, scene template status, voyage timeline, port
  calls, latest telemetry, and evidence context.
- Maritime evidence queue filtered to incidents that resolve to a vessel.
- Template application panel for camera setup.

The UI should reuse existing shell, query hooks, cards/surfaces, auth guards,
and generated OpenAPI types. It should not create a separate marketing landing
page.

## Billing Labels

The pack may expose billing labels and counters for product readiness:

- reseller
- fleet manager
- owner
- charterer
- vessel
- vessel month
- managed edge node
- camera capacity tier
- retained evidence GB
- evidence pack export
- support session hour
- managed link GB

This design does not implement invoices, payment flows, entitlement gates, or
billing migrations. Counters can be returned as product telemetry and future
billing inputs.

## Error Handling

Common behavior:

- Unknown vessel, voyage, port call, camera, or incident returns 404.
- Cross-tenant references return 404 rather than leaking existence.
- Invalid state transitions return 409 with a specific message.
- Payload validation returns 422 through FastAPI/Pydantic.
- Pack not enabled returns 404 or a typed not-enabled response depending on
  route family.
- Telemetry ingest accepts partial vendor payloads only when the normalized
  identity and timestamp are valid.
- Evidence enrichment returns partial context when telemetry is missing.

State transition examples:

- Activating a voyage cancels or rejects another active voyage for the same
  vessel.
- Completing a voyage requires an actual departure time or explicit completion
  time.
- Departing a port call requires an arrived or alongside state.

## Testing Strategy

Backend tests:

- core fleet service tests for site groups, hierarchy nodes, site state,
  rotation groups, assignments, and exception ordering
- core fleet API tests for hierarchy updates, state reads, assignments, rotation
  groups, exceptions, and cross-tenant isolation
- core link service tests for budgets, priority ordering, queue depth,
  backpressure, resume state, last sync, and link passport hashing
- core link API tests for site status, budget updates, probe reporting, queue
  pause/resume/retry, and cross-tenant isolation
- pack activation tests for `maritime-fleet`
- traffic/public-space non-activation tests
- table and migration smoke tests
- service tests for vessel CRUD and tenant scoping
- service tests for voyage and port-call state transitions
- telemetry parser and ingest tests
- scene template application tests proving generated payloads use core
  primitives
- evidence context resolution tests with complete and partial telemetry
- evidence export tests proving maritime/link metadata is added without
  changing artifact hashes or ledger chaining
- API route tests for auth, validation, and cross-tenant isolation
- governance tests proving maritime nouns stay out of core contracts

Frontend tests:

- generated API type usage compiles
- FleetOps route renders inside existing shell
- vessel list, vessel detail, and evidence queue render loading, empty, error,
  and populated states
- template application interactions call the correct API route
- navigation keeps traffic/public-space hidden

End-to-end smoke:

- create vessel with linked site
- place that site into a generic site group and hierarchy
- add camera to the vessel site
- read fleet exceptions ordered by attention
- set a site bandwidth budget
- queue evidence work in safety, evidence, telemetry, and bulk lanes
- simulate degraded link probes and verify lower-priority backpressure
- apply gangway template
- create active voyage and port call
- ingest AIS and carrier terminal state
- create or fixture an incident
- resolve maritime evidence context
- export an evidence pack with scene contract, runtime passport, link passport,
  maritime metadata, and intact chain-of-custody hashes
- view vessel dashboard, link posture, and maritime evidence queue
- simulate recovery and verify evidence transfer resumes with last-sync state

## Implementation Phases

### Phase 1: Core Argus-Link Baseline

Create a domain-neutral core link layer with tables, contracts, services, API
routes, and tests for bandwidth budgets, priority lanes, backlog/queue depth,
resume-on-interrupt, backpressure, link probes, last-sync state, and link
passport snapshots. This phase is required before the FleetOps UI can honestly
claim link-aware evidence movement.

### Phase 2: Core Argus-Fleet Baseline

Create a domain-neutral core fleet layer with tables, contracts, services, API
routes, and tests for site groups, site hierarchy nodes, site state, site
assignments, rotation groups, and exception-first fleet summaries. This phase
gives Maritime FleetOps a real operational workspace without putting vessel,
owner, manager, charterer, or voyage labels in core.

### Phase 3: Pack Runtime Skeleton

Create `argus.maritime` with contracts, tables imported into metadata, service
construction, router inclusion, runtime contribution response, and governance
tests. No UI depends on this phase yet.

### Phase 4: Vessels, Voyages, And Port Calls

Add migrations, models, service methods, APIs, and tests for FleetOps domain
entities. Vessel creation supports linked core site creation.

### Phase 5: Scene Templates

Expose templates from the manifest, map them into core camera configuration
payloads, and apply them through existing camera/scene contract behavior.

### Phase 6: Telemetry Ingest

Implement AIS, NMEA, and carrier terminal normalized ingest plus pilot fixture
imports. Add latest-state and recent-track APIs.

### Phase 7: Evidence Enrichment And Export

Resolve maritime and link context for incidents, attach metadata to
evidence/export responses, create link passport snapshots where needed, and
render partial-context freshness information. The first FleetOps evidence pack
export must include scene contract, runtime passport, link passport, maritime
context, and chain-of-custody metadata without changing existing artifact hashes.

### Phase 8: FleetOps UI

Add frontend routes, hooks, dashboard, vessel pages, template panel, and
maritime evidence queue using generated OpenAPI types. The dashboard must show
degraded, dark, port WiFi, and recovering link states, evidence backlog, queue
depth, fleet exceptions, site/vessel hierarchy, and last successful evidence
transfer.

### Phase 9: Support, Installer, And Product Hardening

Add support diagnostics surfacing, shipboard install checklist/docs, end-to-end
smoke tests, installer packaging checks, operational fixtures, and performance
checks for fleet hierarchy, telemetry, link queues, and dashboard queries.

## Acceptance Criteria

The pack is functionally complete when:

- `GET /api/v1/maritime/runtime` shows Maritime FleetOps runtime enabled.
- `GET /api/v1/fleet/exceptions` returns domain-neutral site exceptions ordered
  by attention.
- `GET /api/v1/link/sites/{site_id}/status` returns budget, queue depth, probes,
  last sync, and link state using generic core contracts.
- Traffic/public-space has no runtime module or UI route.
- A tenant admin can create a vessel and linked site.
- A tenant admin can create and transition voyages and port calls.
- A camera assigned to a vessel site can receive a maritime scene template.
- Link queue behavior prioritizes safety, evidence, telemetry, and bulk lanes in
  that order.
- Degraded or exhausted link budgets backpressure lower-priority transfers.
- Interrupted evidence movement can resume and records last successful transfer.
- AIS, NMEA, and carrier terminal state can be ingested through documented
  routes or fixture imports.
- FleetOps evidence export includes scene contract, runtime passport, link
  passport, maritime context, and evidence ledger summary without changing
  existing artifact hashes.
- A vessel dashboard shows current voyage, port call, telemetry, link posture,
  budget state, evidence backlog, queue depth, camera/template coverage, and
  pending evidence.
- Evidence context resolves vessel, voyage, port call, latest AIS, latest link
  state, link passport, and reviewer role where available.
- Missing telemetry degrades gracefully and visibly.
- Core contracts do not contain maritime entities.
- Core fleet contracts remain domain-neutral and reusable outside maritime.
- Core link contracts remain domain-neutral and reusable for home/lab validation.
- Home/lab validation remains packless.
- All targeted backend, frontend, and smoke tests pass.

## Open Risks

- `argus.link` is core work, not pack work, so the implementation plan must keep
  the link layer generic while still delivering the FleetOps wedge.
- Vendor-specific carrier telemetry will likely require adapter-specific follow
  up work once credentials and protocol documents exist.
- Exact AIS/NMEA parser depth may need to grow after pilot data is captured.
- Current core services are concentrated in `argus.services.app`; the plan must
  keep maritime service code in the pack and avoid worsening that file.
- Evidence export integration needs careful testing so maritime metadata does
  not alter existing artifact hashes or ledger semantics.
- Resume-on-interrupt support may vary by storage provider. The first
  implementation should record resumable offsets when supported and fall back to
  retry-from-start with an explicit capability flag when not supported.
- UI navigation must avoid making the whole product look maritime-only when the
  user is outside FleetOps routes.
