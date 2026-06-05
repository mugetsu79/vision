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

The implementation must be product-complete enough to install, operate,
support, bill, and renew FleetOps without making core maritime-shaped. Core
continues to own tenants, users, generic sites, cameras, scene contracts,
incidents, evidence artifacts, runtime passports, link/runtime delivery
primitives, operator configuration, billing primitives, support primitives, and
the pack registry. The Maritime FleetOps pack owns maritime entities, maritime
telemetry context, scene template application, evidence enrichment, FleetOps UI
surfaces, shipboard support contributions, and pack-specific billing labels,
meters, and rollups.

This design expands beyond the read-only registry. It builds a real
`argus.maritime` runtime module and a frontend FleetOps workspace. It does not
activate traffic/public-space, does not create home-lab packs, and does not put
maritime nouns into core contracts.

## Product Goal

Build Vezor FleetOps as a usable pack for remote maritime operations:

> Live fleet signals, trusted evidence, built for bad links.

An operator should be able to create vessels, assign cameras, define voyages and
port calls, apply maritime scene templates, ingest maritime telemetry, review
evidence with vessel/voyage/position/link context, monitor fleet exceptions,
export evidence packs, generate support diagnostics, and inspect billable usage
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
- A core `argus.billing` baseline required by a working product: billing nodes,
  accounts, entitlements, usage meters, invoice line items, pack discriminators,
  and billable usage exports.
- A core `argus.support` baseline required by a working product: diagnostic
  bundles, support sessions, NOC tunnel lifecycle, break-glass access records,
  and no-laptop onboarding checks.
- Maritime APIs under `/api/v1/maritime`.
- Link-state APIs under `/api/v1/link` using domain-neutral core contracts.
- Fleet-state APIs under `/api/v1/fleet` using domain-neutral core contracts.
- Billing APIs under `/api/v1/billing` using domain-neutral core contracts.
- Support APIs under `/api/v1/support` using domain-neutral core contracts.
- Runtime contribution APIs connected to the existing pack registry.
- Maritime scene templates based on the `maritime-fleet` manifest.
- Template application that creates or updates core camera scene configuration
  using existing core primitives.
- Ingest APIs for AIS, NMEA, and carrier terminal telemetry.
- File or fixture import paths for operational bootstrap, demos, support
  reproduction, and offline telemetry loading when live integrations are
  unavailable.
- Generic carrier telemetry adapters that work without proprietary SDKs: HTTP
  polling, webhook ingest, and file import.
- Carrier-aware link selection policies that choose direct, satellite, port WiFi,
  or deferred transfer lanes based on link state and budget.
- Evidence enrichment that links core incidents and artifacts to maritime
  context without changing core incident storage semantics.
- Evidence pack export with scene contract, runtime passport, link passport,
  maritime context, ledger summary, and retention/time-source metadata.
- Shipboard install checklist, support diagnostics, and FleetOps runbook
  surfaces.
- FleetOps frontend pages for fleet overview, vessel detail, voyage and port
  call timeline, telemetry state, maritime evidence context, and link-aware
  evidence queue, billing usage, and support diagnostics.
- Governance tests that keep traffic/public-space manifest-only and prevent
  maritime nouns from entering core contracts.
- OpenAPI regeneration for typed frontend hooks once backend contracts exist.

### Out of Scope

- Traffic/public-space runtime code, APIs, UI, migrations, demos, or sales
  motion.
- A home-lab pack, home-lab dashboard, or home-lab customer demo.
- Payment collection through a card processor or accounting-system integration.
- Proprietary carrier, AIS vendor, or NMEA hardware integrations that cannot be
  implemented from available protocol documentation, sample payloads, or generic
  HTTP/file ingest contracts. The product must still ship working generic
  adapters and documented adapter seams.
- Runtime detector semantics that bypass current scene contracts, camera
  configuration, evidence, or runtime passport behavior.
- Face recognition, biometric identification, or public-space surveillance
  features.
- Moving `Vessel`, `Voyage`, `PortCall`, AIS, NMEA, owner, manager, or
  charterer concepts into core contracts.
- Formal maritime regulatory certification. The product must provide
  certification-ready notes, evidence/export metadata, and audit trails, but
  external certification itself is not a software feature.

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
| Time-source provenance and retention hooks | core chain-of-custody layer | in scope |
| Remote support bundle, NOC tunnel, break-glass | core support layer | in scope as working support primitives |
| No-laptop onboarding checks | core support/deployment layer plus maritime checklist | in scope |
| Shipboard support wording and install checklist | maritime pack | in scope as docs/UI copy |
| Marine-grade hardware recommendations | maritime pack docs | in scope as docs, not hardware certification |
| DNV or cybersecurity certification | maritime pack docs | certification-ready notes, audit metadata, and evidence exports in scope; external certification is not a software deliverable |
| Camera onboarding defaults and bandwidth assumptions | maritime pack plus core camera ecosystem | in scope |
| Carrier-aware link selection | core link layer plus maritime carrier telemetry | in scope |
| Billing node tree, accounts, entitlements, usage meters, invoice line items | core billing | in scope |
| Maritime billing labels, meters, and rollups | maritime pack | in scope |
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
- `argus.billing` billing nodes, accounts, entitlements, usage meters, invoice
  line items, pack discriminators, and usage exports
- `argus.support` diagnostic bundles, support sessions, NOC tunnel lifecycle,
  local break-glass records, and no-laptop onboarding checks
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

### Core Argus-Billing Baseline

`argus.billing` is a core engine layer. It must be generic enough to support
future packs, while FleetOps supplies maritime labels and rollups.

The working-product baseline owns these domain-neutral concepts:

- `BillingNode`: adjacency-tree node with tenant, parent, label, kind, and pack
  discriminator.
- `BillingAccount`: bill-to entity linked to one or more billing nodes.
- `Entitlement`: enabled pack, feature, usage limit, and effective time window.
- `UsageMeter`: typed meter definition with unit, aggregation cadence, and pack
  discriminator.
- `PriceBook`: active pricing catalog with currency, effective time window, and
  meter prices.
- `UsageRecord`: append-only usage event with source object, quantity, time
  window, and metadata.
- `InvoiceLineItem`: generated line item with meter, quantity, unit label,
  unit price, currency, account, billing period, and source records.
- `BillingExport`: CSV/JSON export of accounts, usage, and line items for manual
  invoicing or accounting-system import.

The baseline must support:

- generic billing hierarchy without maritime labels in core contracts
- entitlement checks for pack availability and feature access
- usage recording for vessel months, managed edge nodes, camera capacity tiers,
  retained evidence GB, evidence exports, support sessions, and managed link GB
- price-book configuration for FleetOps meters
- invoice line item generation for a billing period
- usage and invoice export without payment collection

Maritime pack code contributes labels such as reseller, fleet manager, owner,
charterer, vessel, and meter names. Payment processing, tax calculation, and
accounting-system sync are external commercial integrations, but the product
must generate priced billable records, invoice lines, and exports.

### Core Argus-Support Baseline

`argus.support` is a core engine layer. FleetOps needs it because shipboard
deployments must be operable without a developer terminal.

The working-product baseline owns these domain-neutral concepts:

- `SupportBundle`: redacted diagnostic package with node, camera, runtime,
  link, evidence queue, configuration, logs summary, and artifact manifests.
- `SupportSession`: support case/session record with tenant, site, node,
  operator, status, timestamps, and billable duration.
- `SupportTunnel`: lifecycle state for a NOC tunnel or remote diagnostic
  channel, including requested, active, expired, revoked, and failed states.
- `SupportTunnelTransport`: configured transport adapter that can open and stop
  an approved reverse tunnel command or managed tunnel endpoint.
- `BreakGlassAccessRecord`: local emergency access record with reason,
  approver/operator, scope, started/ended times, and audit payload.
- `OnboardingCheck`: install validation check for master, edge, camera,
  identity, model, link, evidence storage, and support readiness.

The baseline must support:

- generating a redacted support bundle from installed product state
- opening, expiring, and revoking a support tunnel through a configured
  transport and lifecycle record
- recording local break-glass access without weakening normal auth flows
- running no-laptop onboarding checks after install
- recording billable support session duration for billing usage

Maritime pack code contributes shipboard wording, ETO-oriented troubleshooting
labels, satellite-link diagnostic grouping, vessel install checklist sections,
and maritime support roles.

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
- Historical changes are recorded through telemetry events so the vessel detail
  page, support bundle, evidence context, and billing/export logic can explain
  link posture over time.

### Maritime Integration Adapters

The working product must ship with adapter seams and generic adapters that can
run without proprietary SDKs:

- `AISJsonAdapter`: accepts normalized AIS JSON from HTTP, webhook, or file
  import.
- `AisCsvFileAdapter`: imports common CSV exports containing MMSI, position,
  timestamp, course, speed, and heading.
- `Nmea0183Adapter`: parses core NMEA 0183 sentences needed for position,
  heading, and speed context.
- `CarrierWebhookAdapter`: accepts normalized carrier terminal state via
  authenticated webhook.
- `CarrierHttpPollingAdapter`: polls a configured HTTP JSON endpoint for
  terminal state where a partner exposes one.
- `CarrierFileImportAdapter`: imports fixture or operational CSV/JSON carrier
  state exports.

Adapter rules:

- All adapters normalize into pack-owned telemetry tables.
- Adapter credentials must use existing secret/profile mechanisms, not plain
  fields in maritime tables.
- Unsupported vendor-specific fields are preserved in `raw_payload`.
- Failed parses are visible in ingest results and support bundles.
- No proprietary SDK is required for the product to work end to end.
- Adding a partner-specific adapter later must not change the core link or
  maritime evidence contracts.

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
- `GET /api/v1/link/sites/{site_id}/policies`
- `PUT /api/v1/link/sites/{site_id}/policies`
- `GET /api/v1/link/evidence/{incident_id}/passport`
- `POST /api/v1/link/queue/{queue_item_id}/retry`
- `POST /api/v1/link/queue/{queue_item_id}/pause`
- `POST /api/v1/link/queue/{queue_item_id}/resume`

FleetOps routes may compose these into maritime summaries:

- `GET /api/v1/maritime/vessels/{vessel_id}/link-status`
- `GET /api/v1/maritime/vessels/{vessel_id}/evidence-backlog`
- `GET /api/v1/maritime/vessels/{vessel_id}/carrier-selection`

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

### Argus-Billing

Billing routes use core contracts and are available outside Maritime FleetOps:

- `GET /api/v1/billing/nodes`
- `POST /api/v1/billing/nodes`
- `GET /api/v1/billing/accounts`
- `POST /api/v1/billing/accounts`
- `GET /api/v1/billing/entitlements`
- `POST /api/v1/billing/entitlements`
- `GET /api/v1/billing/meters`
- `GET /api/v1/billing/price-books`
- `POST /api/v1/billing/price-books`
- `GET /api/v1/billing/usage`
- `POST /api/v1/billing/usage`
- `POST /api/v1/billing/invoice-runs`
- `GET /api/v1/billing/invoice-runs/{invoice_run_id}`
- `GET /api/v1/billing/exports/{export_id}`

FleetOps routes may compose these into maritime billing summaries:

- `GET /api/v1/maritime/billing/usage`
- `GET /api/v1/maritime/billing/rollups`

The maritime responses may label billing nodes as reseller, fleet manager,
owner, charterer, or vessel. The core billing responses must remain generic.

### Argus-Support

Support routes use core contracts and are available outside Maritime FleetOps:

- `POST /api/v1/support/bundles`
- `GET /api/v1/support/bundles/{bundle_id}`
- `POST /api/v1/support/sessions`
- `PATCH /api/v1/support/sessions/{session_id}`
- `POST /api/v1/support/tunnels`
- `POST /api/v1/support/tunnels/{tunnel_id}/revoke`
- `POST /api/v1/support/break-glass`
- `POST /api/v1/support/break-glass/{record_id}/close`
- `GET /api/v1/support/onboarding-checks`
- `POST /api/v1/support/onboarding-checks/run`

FleetOps routes may compose these into maritime support summaries:

- `GET /api/v1/maritime/support/checklist`
- `GET /api/v1/maritime/support/diagnostics`

The maritime responses may group checks by vessel, shipboard network, satellite
link, camera deck/space, or ETO task. The core support responses must remain
generic.

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
support operational fixtures, demos, support reproduction, and offline loading
without vendor credentials.

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
- `GET /api/v1/maritime/evidence-exports`
- `POST /api/v1/maritime/evidence-exports`

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
- evidence export queue
- open support sessions
- current billable usage summary

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
- `/fleetops/billing`
- `/fleetops/support`
- `/fleetops/onboarding`

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
- Link operations panel with budget, lane, queue, backpressure, recovery, and
  carrier-selection state.
- Evidence export builder with scene contract, runtime passport, link passport,
  and maritime metadata preview.
- Billing usage surface with account hierarchy, entitlement state, usage meters,
  invoice-run line items, and export actions.
- Support diagnostics surface with onboarding checks, support bundles, tunnel
  lifecycle, break-glass records, and shipboard checklist.

The UI should reuse existing shell, query hooks, cards/surfaces, auth guards,
and generated OpenAPI types. It should not create a separate marketing landing
page.

## Billing And Entitlements

The product must produce billable usage records and invoice line items. It does
not need to collect payment inside the app.

Core billing entities:

- billing node
- billing account
- entitlement
- usage meter
- price book
- usage record
- invoice run
- invoice line item
- billing export

Maritime labels and counters:

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

FleetOps billing behavior:

- Entitlements enable `maritime-fleet` per tenant or billing account.
- Usage records are generated from vessel activity, camera capacity, managed
  edge nodes, retained evidence, evidence exports, support sessions, and managed
  link transfer.
- Invoice runs aggregate usage records into line items for a billing period.
- Price books provide currency and unit prices for FleetOps meters.
- Billing exports produce CSV and JSON artifacts suitable for manual invoice
  review or accounting-system import.
- Charter handover can close one billing window and open another for the same
  vessel without moving core site ownership.
- Billing hierarchy labels stay in maritime responses; core billing records
  keep generic node kinds plus pack discriminator metadata.

## Support And Onboarding

FleetOps must be installable and supportable without requiring a developer to
run foreground terminal commands after installation.

Support behavior:

- Support bundles redact secrets and include master, edge, camera, model,
  runtime, link, evidence, configuration, and maritime context summaries.
- Support sessions record status, duration, operator, tenant, site, and linked
  vessel where FleetOps context exists.
- NOC tunnel lifecycle can be requested, activated through configured transport,
  expired, revoked, and audited.
- Break-glass records capture reason, scope, actor, approver, start/end time,
  and closure notes.
- Onboarding checks verify identity, master readiness, edge pairing, camera
  reachability, model/runtime readiness, evidence storage, link state, billing
  entitlement, and support readiness.
- Maritime checklist sections cover vessel network assumptions, satellite-link
  notes, ETO handoff, camera naming defaults, and shipboard support roles.

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
- core billing service tests for billing node trees, entitlements, usage record
  aggregation, price books, invoice line item generation, billing exports, and
  cross-tenant isolation
- core support service tests for redacted bundles, support sessions, tunnel
  lifecycle, tunnel transport adapter, break-glass records, onboarding checks,
  and cross-tenant isolation
- pack activation tests for `maritime-fleet`
- traffic/public-space non-activation tests
- table and migration smoke tests
- service tests for vessel CRUD and tenant scoping
- service tests for voyage and port-call state transitions
- telemetry parser and ingest tests
- generic carrier adapter tests for HTTP polling, webhook ingest, file import,
  parse failures, and credential redaction
- carrier-aware link selection tests for direct, satellite, port WiFi, deferred,
  and degraded states
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
- billing usage, invoice-run, and export views render populated, empty, and
  error states
- support diagnostics, support bundle, tunnel, break-glass, and onboarding
  surfaces render populated, empty, and error states
- navigation keeps traffic/public-space hidden

End-to-end smoke:

- create vessel with linked site
- place that site into a generic site group and hierarchy
- create billing account, entitlement, and billing hierarchy for the vessel
- add camera to the vessel site
- read fleet exceptions ordered by attention
- set a site bandwidth budget
- queue evidence work in safety, evidence, telemetry, and bulk lanes
- simulate degraded link probes and verify lower-priority backpressure
- evaluate carrier-aware link selection
- apply gangway template
- create active voyage and port call
- ingest AIS and carrier terminal state
- create or fixture an incident
- resolve maritime evidence context
- export an evidence pack with scene contract, runtime passport, link passport,
  maritime metadata, and intact chain-of-custody hashes
- generate usage records and an invoice run for vessel, evidence, support, and
  link meters
- create support bundle, run onboarding checks, open and revoke configured
  support tunnel, and record break-glass access
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

Implement AIS, NMEA, and carrier terminal normalized ingest plus operational
fixture imports. Add latest-state and recent-track APIs.

### Phase 7: Evidence Enrichment And Export

Resolve maritime and link context for incidents, attach metadata to
evidence/export responses, create link passport snapshots where needed, and
render partial-context freshness information. The first FleetOps evidence pack
export must include scene contract, runtime passport, link passport, maritime
context, and chain-of-custody metadata without changing existing artifact hashes.

### Phase 8: Billing And Entitlements

Create the core billing layer and Maritime FleetOps billing contribution:
billing nodes, billing accounts, entitlements, usage meters, price books, usage
records, invoice runs, invoice line items, CSV/JSON exports, maritime hierarchy
labels, vessel rollups, charter handover windows, and tests.

### Phase 9: Support And Onboarding

Create the core support layer and Maritime FleetOps support contribution:
redacted support bundles, support sessions, NOC tunnel lifecycle records,
configured support tunnel transport, break-glass access records, onboarding
checks, shipboard install checklist, satellite-link diagnostics grouping,
support usage meters, and tests.

### Phase 10: FleetOps UI

Add frontend routes, hooks, dashboard, vessel pages, template panel, and
maritime evidence queue using generated OpenAPI types. The dashboard must show
degraded, dark, port WiFi, and recovering link states, evidence backlog, queue
depth, fleet exceptions, site/vessel hierarchy, and last successful evidence
transfer. The workspace must also include billing usage, invoice-run exports,
support diagnostics, onboarding checks, tunnel lifecycle, and break-glass
records.

### Phase 11: Installer And Product Hardening

Add end-to-end smoke tests, installer packaging checks, operational fixtures,
runbooks, API docs, product docs, generated OpenAPI/client artifacts, and
performance checks for fleet hierarchy, telemetry, link queues, evidence export,
billing runs, support bundles, and dashboard queries.

## Acceptance Criteria

The pack is functionally complete when:

- `GET /api/v1/maritime/runtime` shows Maritime FleetOps runtime enabled.
- `GET /api/v1/fleet/exceptions` returns domain-neutral site exceptions ordered
  by attention.
- `GET /api/v1/link/sites/{site_id}/status` returns budget, queue depth, probes,
  last sync, and link state using generic core contracts.
- `POST /api/v1/billing/invoice-runs` generates invoice line items from
  FleetOps usage records.
- `POST /api/v1/support/bundles` generates a redacted support bundle for a
  FleetOps deployment.
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
- Generic carrier telemetry adapters work for authenticated HTTP polling,
  webhook ingest, and file import.
- Carrier-aware link selection chooses direct, satellite, port WiFi, or deferred
  transfer posture from budget, probe, and terminal state.
- FleetOps evidence export includes scene contract, runtime passport, link
  passport, maritime context, and evidence ledger summary without changing
  existing artifact hashes.
- Entitlements gate FleetOps availability and feature access.
- Usage records, price books, and invoice line items cover vessel month, managed
  edge node, camera capacity tier, retained evidence GB, evidence export,
  support session hour, and managed link GB.
- Billing exports are available as CSV and JSON.
- Support sessions, support tunnels, break-glass records, and onboarding checks
  are visible and auditable.
- A vessel dashboard shows current voyage, port call, telemetry, link posture,
  budget state, evidence backlog, queue depth, camera/template coverage, and
  pending evidence.
- FleetOps UI exposes billing usage, invoice exports, support diagnostics,
  onboarding checks, support tunnel lifecycle, and break-glass records.
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
- Partner-specific carrier SDKs may still require future adapters, but the
  product must ship with working generic HTTP/webhook/file carrier telemetry.
- Exact AIS/NMEA parser depth may need to grow as more vessel data is captured.
- Current core services are concentrated in `argus.services.app`; the plan must
  keep maritime service code in the pack and avoid worsening that file.
- Evidence export integration needs careful testing so maritime metadata does
  not alter existing artifact hashes or ledger semantics.
- Resume-on-interrupt support may vary by storage provider. The first
  implementation should record resumable offsets when supported and fall back to
  retry-from-start with an explicit capability flag when not supported.
- Billing produces priced invoice line items and exports, but payment collection
  and accounting-system sync remain external commercial integrations.
- NOC tunnel lifecycle must be implemented safely around the existing deployment
  model. A configured tunnel transport must be testable without storing secrets
  in tunnel records.
- UI navigation must avoid making the whole product look maritime-only when the
  user is outside FleetOps routes.
