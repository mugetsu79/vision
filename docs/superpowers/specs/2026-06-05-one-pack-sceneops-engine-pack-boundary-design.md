# One-Pack SceneOps Engine Pack Boundary Design

Date: 2026-06-05
Status: approved working design for implementation planning
Related blueprint: `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`

## Summary

Vezor should sell one focused product first: FleetOps for
satellite-connected fleet operations. Under that product, the platform should
build a domain-neutral SceneOps Engine that can later support additional packs
without rewriting core runtime concepts.

The implementation goal is not to build a second vertical. The goal is to make
the engine/pack boundary real enough that Maritime FleetOps can move fast
without baking maritime nouns into core. The traffic/public-space pack exists as
a manifest-only architectural target. It pressure-tests whether the engine can
support roads, crossings, curbs, queues, public-space privacy, and traffic-study
exports through generic primitives, but it does not authorize implementation or
sales motion.

## Product Decision

### External Product

Vezor FleetOps:

> AI video for satellite-connected fleet operations. Live fleet signals, trusted
> evidence, built for bad links.

The external buyer story is fleet operations, vessel visibility, evidence, and
link-aware runtime truth. The public category should not be "detect anything",
"generic AI video analytics", "smart city platform", or "SceneOps".

### Internal Platform

Vezor SceneOps Engine:

- Scene
- Scene Contract
- Signal
- Evidence
- Runtime Passport
- Link Passport
- Pack Manifest
- Pack Registry

This is internal architecture language. It gives engineering clean boundaries
without making the sales story abstract.

### Built Pack

`maritime-fleet`

- Status: `planned_mvp`
- Commercial role: first and only pack authorized for year-one implementation
- Purpose: convert the engine into a sellable FleetOps product

### Designed-Only Pack

`traffic-public-space`

- Status: `designed_not_implemented`
- Commercial role: none
- Purpose: architectural pressure-test for future generality
- Activation rule: no implementation until Maritime FleetOps has renewal proof,
  a named traffic/public-space customer has budget and timeline, and a dated
  strategy decision records the scope change

## Problem

The current product has a strong Scene Contract, evidence, runtime passport,
open-vocabulary, and link-aware foundation. The strategic risk is not that the
engine is too narrow. The risk is that vertical nouns enter core casually:
`Vessel`, `Voyage`, `PortCall`, `Intersection`, `Approach`, `CurbZone`, and
similar concepts can look harmless when added quickly, but they turn the engine
into a hidden vertical monolith.

The second risk is the opposite: over-generalizing the sales story. A product
that can count people, cars, boats, animals, and objects is technically flexible
but commercially mushy. Buyers pay for operational outcomes, evidence, and
workflow confidence, not for a raw list of detectable classes.

This design resolves both risks:

- sell one narrow maritime wedge
- keep the engine primitives domain-neutral
- force every vertical-specific concept through a manifest
- keep traffic/public-space as a designed target, not a second product

## Goals

1. Make the strategy document canonical, precise, and factual.
2. Add actual pack manifest artifacts so the blueprint does not claim files that
   do not exist.
3. Define a registry shape that can load pack manifests without executing pack
   code.
4. Expose pack status through a small API so future UI/admin surfaces can show
   the difference between `planned_mvp` and `designed_not_implemented`.
5. Add governance tests that fail if vertical nouns drift into core contracts.
6. Keep all runtime semantics unchanged during the documentation and manifest
   step.
7. Preserve open-world model flexibility while requiring every production use to
   be framed as a scene outcome.
8. Preserve home/lab road, driveway, car, person, and object testing as
   packless engine validation.

## Non-Goals

- Do not implement maritime runtime entities yet.
- Do not implement traffic/public-space runtime entities.
- Do not add public-agency sales flows, pricing, demos, or UI routes.
- Do not add AIS, NMEA, ATSPM, CDS, GTFS, V2X, or GIS adapters in this step.
- Do not change detection, streaming, evidence, runtime passport, or scene
  execution semantics.
- Do not present the 80-class model or open vocabulary as the product itself.
- Do not create a `home-lab` pack. Home/lab testing must use core engine
  primitives without adding a pack manifest, pack status, UI surface, or
  product route.

## Design Principles

### 1. One Wedge, General Engine

The commercial story is narrow. The architecture is not. This is the important
distinction.

Maritime FleetOps should be specific enough to sell: constrained links, vessel
and remote-site cameras, evidence movement, link-state truth, and NOC exception
workflows.

The engine should remain abstract enough to reuse: camera input, scene contract,
signals, evidence, runtime truth, and link-aware delivery are not maritime-only.

### 2. Manifest Before Code

Every pack starts as a manifest. The manifest declares vertical entities,
templates, integrations, model presets, UI extensions, evidence fields, billing
meters, and forbidden dependencies.

The registry loads manifests as data. It does not import pack runtime modules.
This keeps a designed-only pack visible without accidentally enabling it.

### 3. Status Is Semantics

Pack status controls what the rest of the product may assume.

| Status | Meaning | Runtime code allowed | Sales motion allowed |
|---|---|---|---|
| `planned_mvp` | First pack approved for implementation | yes, once tasks begin | yes |
| `designed_not_implemented` | Architectural target only | no | no |
| `active` | Built and enabled for customers | yes | yes |
| `retired` | No longer offered; manifest kept for migrations | limited migrations only | no |

For now, only two statuses are used:

- `maritime-fleet`: `planned_mvp`
- `traffic-public-space`: `designed_not_implemented`

### 4. Model Classes Are Ingredients, Not Positioning

The 80-class COCO model and open-vocabulary models remain important because
they let operators configure scenes flexibly. They are not the offer.

Production wording should be:

- "Gangway boarding signal"
- "Deck presence evidence"
- "Loading-zone occupancy"
- "Multimodal count"
- "Queue and spillback proxy"

Production wording should not be:

- "Detect any object"
- "Use all 80 classes"
- "Open-world surveillance"
- "AI camera for everything"

### 5. Traffic/Public-Space Is Future-Proofing, Not Product Dilution

The traffic/public-space manifest should reflect where the vertical is likely
to matter by 2027:

- multimodal counts, not only vehicle counts
- vulnerable road user exposure and conflict candidates
- queue, spillback, curb, loading, and lane blockage
- ATSPM-style performance exports later
- V2X/SPaT/MAP as future context, not initial wedge
- GIS/GeoJSON and study exports
- privacy, retention, redaction, and transparency as first-class requirements

That manifest prevents the engine from becoming maritime-shaped while still
protecting the company from a premature second market.

## Current Artifacts

### Strategy Blueprint

Path:

- `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`

Role:

- canonical product and architecture decision
- supersedes prior two-pack draft and Claude v4 draft
- records the one-pack commercial wedge and manifest-only traffic target

### Pack Directory

Path:

- `packs/README.md`
- `packs/maritime-fleet/pack.yaml`
- `packs/traffic-public-space/pack.yaml`

Role:

- repo-native pack boundary artifacts
- data source for the future pack registry
- governance record for what packs may own

## Manifest Contract

The initial manifest contract is YAML. It is intentionally static and readable
so product, design, engineering, and commercial stakeholders can inspect it in
code review.

### Required Top-Level Fields

| Field | Type | Purpose |
|---|---|---|
| `api_version` | string | manifest schema version, currently `vezor.io/v1alpha1` |
| `kind` | string | must be `Pack` |
| `metadata` | object | identity, status, owner, sales posture |
| `engine` | object | minimum engine version and required capabilities |
| `entities` | list | vertical data models contributed by the pack |
| `scene_templates` | list | setup templates contributed by the pack |
| `model_presets` | object | fixed-vocab and open-vocab presets |
| `integrations` | list | declared external integrations |
| `evidence_context` | object | context fields the pack contributes to evidence |
| `billing` | object | hierarchy labels and usage meters |
| `ui_extensions` | object | optional labels and panels |
| `allowed_core_dependencies` | list | positive allowlist of core primitives |
| `forbidden_dependencies` | list | negative list used by review and tests |

### Metadata Fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | stable URL-safe pack id |
| `name` | yes | human-readable pack name |
| `product_name` | yes | external or future external product name |
| `owner` | yes | owning function or team |
| `status` | yes | one of the allowed pack statuses |
| `wedge` | yes | concise market/use-case definition |
| `sales_motion` | yes | sales channel or `none` |
| `implementation_commitment` | yes | boolean, true only when implementation is authorized |

### Entity Rules

Each entity must declare:

- `name`
- `extends`
- `storage`
- `purpose`

`extends` must reference a generic core primitive, such as `Site`, `Scene`,
`Signal`, `EvidenceExport`, `PrivacyPolicy`, or `BillingNode`.

`storage` must be `pack` for vertical-specific entities. Core storage is not
allowed for vertical entities.

For Phase 1, `extends` is a validated relationship label, not ORM inheritance
and not a Python base class. The registry should verify that every entity's
`extends` value appears in `allowed_core_dependencies` and in the known core
extension-point allowlist. Phase 3 maritime runtime work must then decide how
each extension point is represented in code: relationship contract, adapter
interface, database relationship, or service-level projection. Runtime work
must not reinterpret `extends` as permission to add vertical columns to core
tables.

`pack_registry` appearing in `engine.required_capabilities` is intentionally
self-referential. It means "this manifest requires an engine version that has a
pack registry before the pack can be understood." The registry may still load
the manifest because manifest parsing is the bootstrap operation that makes
that capability visible.

### Forbidden Dependency Enforcement

`forbidden_dependencies` are a mix of enforceable code boundaries and strategic
guardrails. The implementation must make that distinction explicit.

| Token family | Examples | Phase 1 enforcement |
|---|---|---|
| Vertical entity in core | `maritime_entity_in_core_contract`, `traffic_entity_in_core_contract`, `vessel_schema_in_core`, `voyage_schema_in_core` | automated boundary test scans scoped core files for vertical nouns |
| Accidental runtime pack creation | `traffic_runtime_code_before_activation` | automated boundary test asserts `backend/src/argus/maritime` and `backend/src/argus/traffic_public_space` do not exist in Phase 1 |
| Core depends on vertical integrations | `ais_required_by_core`, `nmea_required_by_core`, `atspm_required_by_core`, `cds_required_by_core`, `v2x_required_by_core` | plan scope forbids adding adapters; future adapter work must add import/dependency tests |
| Commercial or hierarchy drift | `speedcast_hierarchy_in_core`, `public_agency_sales_motion_before_activation` | documented decision rule and code review in Phase 1; future billing/UI work must add tests before these surfaces exist |
| Public-space privacy defaults | `face_recognition`, `biometric_identification_default`, `plate_recognition_enabled_by_default` | manifest default review in Phase 1; future activated pack work must add privacy-policy and UI tests |

The Phase 1 noun-boundary test is a denylist because it protects the specific
entities in the two current manifests. A broader import/module allowlist should
be added when real pack runtime modules exist; adding it too early risks noisy
false positives against the current backend structure. The directory-absence
assertion makes Phase 1 fail closed for accidental pack implementation.

### Designed-Only Pack Rules

When `metadata.status` is `designed_not_implemented`:

- `metadata.implementation_commitment` must be false.
- `metadata.sales_motion` must be `none`.
- integrations must be `design_only` or `research_only`.
- billing must be marked design-only.
- UI extensions must be marked design-only.
- activation conditions must be present.
- no backend module may be created for this pack.
- no frontend route may be created for this pack.
- no public-facing pricing or demo may reference this pack as available.

## Registry Design

### Responsibility

The registry loads YAML manifests from `packs/*/pack.yaml`, validates them, and
returns typed pack records. It should not execute pack code or import pack
runtime modules.

### Backend Service

Future path:

- `backend/src/argus/services/pack_registry.py`

Responsibilities:

- find the repository pack directory
- load YAML manifest files
- validate required fields with Pydantic
- expose `list_packs()`
- expose `get_pack(pack_id)`
- expose `list_enabled_runtime_packs()`
- keep `designed_not_implemented` packs visible but disabled

### API Contracts

Future path:

- `backend/src/argus/api/contracts.py`

New response contracts:

- `PackStatus`
- `PackMetadataResponse`
- `PackEntityResponse`
- `PackTemplateResponse`
- `PackManifestResponse`
- `PackListResponse`

The API should expose enough manifest information for an admin/settings UI to
show what is planned, designed-only, or active. It should not expose every
manifest field if doing so creates unnecessary public API commitments.

### API Route

Future path:

- `backend/src/argus/api/v1/packs.py`

Endpoints:

- `GET /api/v1/packs`
- `GET /api/v1/packs/{pack_id}`

Expected behavior:

- `GET /api/v1/packs` returns both manifests with status and implementation
  commitment.
- `GET /api/v1/packs/maritime-fleet` returns a planned MVP pack.
- `GET /api/v1/packs/traffic-public-space` returns a designed-only pack.
- unknown pack ids return 404.

### App Service Wiring

Future path:

- `backend/src/argus/services/app.py`

The existing `AppServices` container should receive a `packs` service. This
matches the current backend pattern where shared services are injected through
dependencies rather than constructed inside routers.

## Governance Tests

### Manifest Tests

Tests should prove:

- both manifest files load successfully
- pack ids are unique
- `maritime-fleet` is `planned_mvp`
- `traffic-public-space` is `designed_not_implemented`
- `traffic-public-space` has implementation commitment false
- designed-only pack integrations are not marked as implemented

### Boundary Tests

Tests should prove core contracts do not gain vertical nouns.

Initial forbidden nouns:

- `Vessel`
- `Voyage`
- `PortCall`
- `AISPosition`
- `NMEAReading`
- `CarrierTerminal`
- `Intersection`
- `Approach`
- `Movement`
- `CurbZone`
- `SignalPhase`
- `TrafficStudy`
- `ConflictEvent`

The test should scan carefully scoped core files, not the entire repository.
Docs and manifest files are allowed to contain these nouns. Future pack modules
are allowed to contain their own nouns. Core API contracts and generic service
containers are not.

### API Tests

Tests should prove:

- the router includes pack routes
- list response includes both packs
- detail response returns a single pack
- designed-only traffic pack remains visible but not runtime-enabled

## UI And UX Implications

No UI implementation is required in this step, but future UI should follow these
rules:

1. Operators see product outcomes, not pack mechanics.
2. Admins may see pack status in a settings/admin surface.
3. Maritime labels may appear in FleetOps product surfaces after the pack is
   implemented.
4. Traffic/public-space labels must not appear in customer-facing UI unless a
   dated activation decision exists.
5. Open vocabulary UI should frame terms as scene-level discovery with hashes
   attached to scene contracts.
6. Model catalog UI should not market the raw 80-class list as the product.

## Open-World Model Guidance

### Fixed-Vocab COCO

The 80-class model stays available as a runtime ingredient. The product should
surface curated presets tied to scenes.

Maritime examples:

- Gangway Access: `person`
- Deck Presence: `person`, optionally `boat`, `car`, `truck` in port/yard scenes
- Cargo Or Work Area: `person`, `truck`, `car`, `boat` when context supports it

Engine validation examples:

- Home/lab street count: `person`, `bicycle`, `car`, `motorcycle`, `bus`, `truck`
- Driveway presence: `person`, `car`, `truck`

Traffic/public-space designed-only examples:

- Multimodal Counts: `person`, `bicycle`, `car`, `motorcycle`, `bus`, `truck`
- Vulnerable Road User Safety: `person`, `bicycle`, `motorcycle`

### Open Vocabulary

Open vocabulary should be treated as controlled discovery:

1. constrain the scene with include regions and event boundaries
2. use a small vocabulary
3. save the vocabulary hash in the scene contract
4. review telemetry and false positives
5. promote only stable terms into a pack preset or custom model path

Open vocabulary should not be sold as "detect anything." It is a way to find
domain-specific terms before deciding whether they deserve product support.

## Home-Lab Engine Validation

Home/lab testing is the positive proof that the SceneOps Engine can handle
non-maritime scenes through generic primitives. The canonical engineering note
is:

- `docs/engineering/home-lab-engine-validation.md`

Cars, people, bicycles, trucks, and similar local test objects may be used today
with the current COCO model, line crossings, detection regions, include/exclude
polygons, count events, scene contracts, and runtime passports.

No pack is required for this. The absence of a home-lab pack is intentional:
home/lab validation should not become a third product-shaped artifact in the
registry. The future automated harness should prove that generic scenes produce
signals with no traffic, public-space, maritime, or lab pack registered.

The registry implementation plan stays scoped to pack manifests and governance.
The home-lab harness should be a follow-up implementation slice after the
registry exists.

## 2027 Traffic/Public-Space Feature Direction

The designed-only traffic/public-space pack should be optimized for the likely
shape of the vertical in 2027:

| Capability | Why it matters | Build status |
|---|---|---|
| Multimodal counts | agencies increasingly need person, bicycle, vehicle, transit, and micromobility views | manifest only |
| Vulnerable road user exposure | safety programs prioritize people outside vehicles | manifest only |
| Conflict candidates | near-miss and conflict review can create value before crash statistics mature | manifest only |
| Queue and spillback proxies | useful for operations even without full signal control integration | manifest only |
| Curb and loading-zone occupancy | curb is becoming managed operating space | manifest only |
| ATSPM-style exports | signal performance is increasingly measured, not manually observed | manifest only |
| V2X/SPaT/MAP context | important future context, too heavy for first wedge | research only |
| GIS/GeoJSON/study exports | procurement-friendly output format | manifest only |
| Privacy/transparency reports | public-space AI requires trust controls by default | manifest only |

This pack should not begin with enforcement, facial recognition, biometric
identification, or plate recognition. Plate recognition, if ever needed, should
be disabled by default and require a separate legal/commercial decision.

## Research Inputs

The following inputs anchor the traffic/public-space design direction. They do
not authorize implementation.

- FHWA Safe System Approach:
  `https://highways.dot.gov/safety/zero-deaths/safe-system-approach-toward-zero-traffic-deaths`
- FHWA arterial management and traffic signal performance measures:
  `https://ops.fhwa.dot.gov/arterial_mgmt/performance_measures.htm`
- U.S. DOT V2X:
  `https://www.transportation.gov/v2x`
- U.S. DOT Complete Streets:
  `https://www.transportation.gov/mission/health/complete-streets`
- Open Mobility Foundation Curb Data Specification:
  `https://github.com/openmobilityfoundation/curb-data-specification`
- European Commission AI Act regulatory framework:
  `https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai`
- NIST AI Risk Management Framework:
  `https://www.nist.gov/itl/ai-risk-management-framework`

## Rollout Shape

### Phase 0: Documentation And Manifest Artifacts

Deliver:

- final canonical blueprint
- pack manifests
- design spec
- implementation plan

No runtime changes.

### Phase 1: Pack Registry

Deliver:

- manifest loader
- typed validation
- API contracts
- read-only pack routes
- tests

Still no maritime entity implementation and no traffic implementation.

### Phase 2: Boundary Enforcement

Deliver:

- governance tests for vertical nouns
- CI-visible validation command
- design-doc references updated to treat manifests as the extension boundary

### Phase 3: Maritime MVP Pack Workstream

Deliver in a future spec/plan:

- generic fleet/site refactor
- maritime pack runtime module
- maritime scene templates
- maritime evidence context
- maritime billing labels
- AIS/NMEA/carrier integrations

Traffic remains manifest-only.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| The team starts building traffic because the manifest exists | Status semantics, activation conditions, and governance tests make designed-only explicit. |
| Maritime nouns leak into core during FleetOps implementation | Boundary tests fail when core contracts include vertical terms. |
| Open vocabulary makes the product feel unfocused | Curated scene presets and outcome-led copy keep model classes behind the workflow. |
| The manifest schema becomes too heavy too early | Keep registry read-only and static for Phase 1. Defer dynamic pack loading. |
| Traffic/public-space assumptions age quickly | Keep research references dated and require reassessment before activation. |
| Sales asks for a second market too early | Decision rules require renewal proof plus named customer budget/timeline. |

## Acceptance Criteria

1. The canonical blueprint states one implementation-authorized pack and one designed-only pack.
2. `packs/maritime-fleet/pack.yaml` exists and is marked `planned_mvp`.
3. `packs/traffic-public-space/pack.yaml` exists and is marked `designed_not_implemented`.
4. The implementation plan defines a read-only pack registry and API.
5. The implementation plan includes tests that protect core from vertical nouns.
6. No runtime behavior changes are required by this design.
7. The traffic/public-space direction is represented as 2027-aware manifest
   content, not as a year-one roadmap commitment.

## Self-Review

- Completeness scan: no unresolved section remains.
- Consistency check: strategy, pack statuses, and activation conditions match
  the canonical blueprint.
- Scope check: this is one implementation unit: read-only registry plus
  governance. Maritime runtime implementation is deliberately deferred.
- Ambiguity check: traffic/public-space is visible as data but disabled as
  implementation and sales motion.
