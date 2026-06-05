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
- Maritime APIs under `/api/v1/maritime`.
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

Core may expose extension seams, but it must not contain maritime entity names
in shared contracts or route payloads unless they are opaque pack metadata
inside a pack-owned response.

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

- pack activation tests for `maritime-fleet`
- traffic/public-space non-activation tests
- table and migration smoke tests
- service tests for vessel CRUD and tenant scoping
- service tests for voyage and port-call state transitions
- telemetry parser and ingest tests
- scene template application tests proving generated payloads use core
  primitives
- evidence context resolution tests with complete and partial telemetry
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
- add camera to the vessel site
- apply gangway template
- create active voyage and port call
- ingest AIS and carrier terminal state
- create or fixture an incident
- resolve maritime evidence context
- view vessel dashboard and maritime evidence queue

## Implementation Phases

### Phase 1: Pack Runtime Skeleton

Create `argus.maritime` with contracts, tables imported into metadata, service
construction, router inclusion, runtime contribution response, and governance
tests. No UI depends on this phase yet.

### Phase 2: Vessels, Voyages, And Port Calls

Add migrations, models, service methods, APIs, and tests for FleetOps domain
entities. Vessel creation supports linked core site creation.

### Phase 3: Scene Templates

Expose templates from the manifest, map them into core camera configuration
payloads, and apply them through existing camera/scene contract behavior.

### Phase 4: Telemetry Ingest

Implement AIS, NMEA, and carrier terminal normalized ingest plus pilot fixture
imports. Add latest-state and recent-track APIs.

### Phase 5: Evidence Enrichment

Resolve maritime context for incidents, attach metadata to evidence/export
responses, and render partial-context freshness information.

### Phase 6: FleetOps UI

Add frontend routes, hooks, dashboard, vessel pages, template panel, and
maritime evidence queue using generated OpenAPI types.

### Phase 7: Product Hardening

Add end-to-end smoke tests, installer packaging checks, docs, operational
fixtures, and performance checks for telemetry and dashboard queries.

## Acceptance Criteria

The pack is functionally complete when:

- `GET /api/v1/maritime/runtime` shows Maritime FleetOps runtime enabled.
- Traffic/public-space has no runtime module or UI route.
- A tenant admin can create a vessel and linked site.
- A tenant admin can create and transition voyages and port calls.
- A camera assigned to a vessel site can receive a maritime scene template.
- AIS, NMEA, and carrier terminal state can be ingested through documented
  routes or fixture imports.
- A vessel dashboard shows current voyage, port call, telemetry, link posture,
  camera/template coverage, and pending evidence.
- Evidence context resolves vessel, voyage, port call, latest AIS, latest link
  state, and reviewer role where available.
- Missing telemetry degrades gracefully and visibly.
- Core contracts do not contain maritime entities.
- Home/lab validation remains packless.
- All targeted backend, frontend, and smoke tests pass.

## Open Risks

- Vendor-specific carrier telemetry will likely require adapter-specific follow
  up work once credentials and protocol documents exist.
- Exact AIS/NMEA parser depth may need to grow after pilot data is captured.
- Current core services are concentrated in `argus.services.app`; the plan must
  keep maritime service code in the pack and avoid worsening that file.
- Evidence export integration needs careful testing so maritime metadata does
  not alter existing artifact hashes or ledger semantics.
- UI navigation must avoid making the whole product look maritime-only when the
  user is outside FleetOps routes.
