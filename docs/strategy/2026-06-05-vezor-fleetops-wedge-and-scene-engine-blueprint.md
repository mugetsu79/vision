# Vezor One-Pack Wedge And Scene Engine Blueprint

Date: 2026-06-05
Status: canonical v5 blueprint
Supersedes:
- `docs/strategy/2026-06-04-vezor-unique-proposition-blueprint.md`
- v3 two-pack draft in this file
- `/Users/yann.moren/Downloads/2026-06-05-vezor-fleetops-blueprint-v4.md`

Source baseline: original fleet-ops blueprint, current Vezor model/runtime docs,
follow-up strategic reviews, and traffic/public-space research from 2026-06-05.

## What Changed From v3

| v3 two-pack draft | v5 one-pack, two-pack-ready blueprint |
|---|---|
| Build Maritime Fleet Pack and Traffic/Public-Space Pack in parallel | Build Maritime Fleet Pack only. Traffic/Public-Space exists as a written manifest, not code. |
| Second pilot in 180-365 days | No second pilot until the first pack has paying renewal proof. |
| Two demo narratives and two pricing tracks | One demo narrative and one pricing track. Traffic pricing meters remain design artifacts. |
| Home/lab testing with roads and cars could bleed into pack 2 | Home/lab testing is engine validation. It exercises core, never a pack. |
| No third pack before renewal proof | No second pack before renewal proof. The bar is higher. |

Everything architectural in v3 is preserved. The discipline change is go-to-market
and roadmap.

## Executive Decision

> Sell one focused pack: Maritime FleetOps. Build a domain-neutral SceneOps
> Engine underneath. Treat Traffic And Public-Space as a documented
> architectural target, not a build commitment. Do not ship a second pack until
> Maritime FleetOps has paying renewal proof.

| Layer | Decision | Why |
|---|---|---|
| Wedge | Satellite-connected fleet operations, sold through or alongside Speedcast-style channels | Sharp buyer, budget, distribution, urgency, and deployment pain. Maritime is relatively uncontested in this exact form. |
| Architecture | Domain-neutral SceneOps Engine | Prevents a rewrite when the product later expands beyond maritime. The discipline is the deliverable. |
| First and only pack authorized for year-one implementation | Maritime Fleet Pack | Converts the engine into a sellable fleet product. |
| Second pack | Traffic And Public-Space, designed-not-built | Manifest exists as a forcing function on engine generality. No code, no roadmap commitment, no second sales motion. |
| Engine validation | Home/lab testing with road and cars using core engine plus COCO/open vocab | Exercises the engine without contributing to any pack. This is the architectural unit test. |
| Expansion rule | No second pack ships until Maritime FleetOps has paying renewal proof | Protects focus. Strategy is what Vezor says no to. |

The external lead is fleet operations, vessel visibility, evidence, and
link-aware video intelligence. "SceneOps Engine" is internal architecture
language only.

## Positioning

### External Positioning

> Vezor FleetOps is AI video for satellite-connected fleet operations. It turns
> existing vessel and remote-site cameras into link-aware live signals, trusted
> evidence, and fleet runtime truth.

### Short Version

AI video for fleets that cannot rely on perfect links.

### One-Liner

Live fleet signals. Trusted evidence. Built for bad links.

### What To Avoid Externally

- Sovereign SceneOps as the main category.
- Generic AI video analytics.
- Detect anything.
- VMS replacement.
- Cloud camera suite.
- Two active packs.
- Broad constrained multi-site operations as the wedge.
- Traffic, public space, or smart-city positioning before maritime renewal.
- Facial recognition or biometric surveillance language.

### Internal Architecture Phrase

> Vezor SceneOps Engine

Use this only inside product and engineering docs to describe the reusable
engine: Scene, Scene Contract, Signal, Evidence, Runtime Passport, Link
Passport, and Pack contracts.

## Strategic Thesis

1. Win one narrow, painful market. Not a broad category. Not two markets in parallel.
2. Build the core engine as if expansion will eventually happen.
3. Force every vertical-specific concern through a pack manifest, including ones not currently built.
4. Treat link-awareness as the moat and the floor.
5. Treat open vocabulary as discovery, not the product promise.
6. Treat evidence and chain of custody as the pricing power.
7. Validate engine generality through home/lab testing with roads and cars, never by starting a second pack.
8. A real customer with budget can override rule 1 only by an explicit, dated, recorded decision. Drift cannot.

This is the Stripe/Shopify lesson applied properly: narrow sales, general
engine.

## Product Primitive Stack

These primitives remain vertical-agnostic and live in the core engine.

| Primitive | Core meaning | Maritime pack example | Home/lab engine validation example |
|---|---|---|---|
| Scene | one camera view plus operational intent | gangway, deck, engine room, cargo area | driveway, street corner, side street |
| Scene Contract | saved runtime contract: source, model, vocabulary/classes, zones, regions, privacy, evidence, homography, artifact hashes | Gangway after-hours boarding v3 | Street corner vehicle count v1 |
| Signal | normalized operational event or metric | person on deck, zone enter, line crossing, occupancy | vehicle count by class, pedestrian crossings, dwell time |
| Evidence | signed or hash-linked incident material plus context | clip, voyage, vessel, position, scene contract | clip, location, scene contract, time-source attestation |
| Runtime Passport | worker truth and runtime state | model artifact, vocabulary hash, heartbeat, delivery profile | same primitive exercised identically at home |
| Link Passport | link health and data movement state | satellite degraded, port WiFi, evidence backlog | home WAN healthy; code path exercised but not stressed |
| Pack | vertical extension boundary | Maritime Fleet Pack, built after the registry exists | no pack; optional local validation profile only |

The engine should know how these primitives behave. It should not know that a
`Vessel`, `Voyage`, `Charterer`, AIS sentence, `Intersection`, `CurbZone`, or
`SignalPhase` exists unless a pack contributes that model.

## Engine And Pack Boundary

### Core Engine Owns

- tenants, users, roles, permissions, and generic billing relationships
- site hierarchy and generic site state
- cameras, camera discovery, source streams, and delivery profiles
- scenes and scene contracts
- model catalog, fixed-vocab class scope, open-vocab runtime vocabulary, and runtime artifacts
- homography, detection regions, event boundaries, and rule execution
- signals, count events, observations, occupancy, speed, and incident creation
- evidence storage, hashes, export mechanics, privacy manifest, and review workflow
- runtime passports, worker health, supervisor state, heartbeats, and last errors
- link passports, priority queues, backpressure, resume-on-interrupt, and link budgets
- remote support, pairing, diagnostics, and local break-glass flows
- pack registry, pack manifest validation, and extension hooks

### Packs Own

- vertical-specific entities
- vertical-specific integrations
- scene templates with vertical labels
- default model/class/vocabulary presets
- rule presets and evidence policies
- vertical UI labels, panels, and onboarding text
- vertical evidence context fields
- vertical billing hierarchy semantics
- vertical compliance and retention defaults

### Core Must Not Depend On

- `Vessel`
- `Voyage`
- `PortCall`
- `Intersection`
- `Approach`
- `Movement`
- `CurbZone`
- `SignalPhase`
- `BusLane`
- `ConflictEvent`
- AIS/NMEA/VDR concepts
- ATSPM/CDS/V2X concepts
- Speedcast-specific hierarchy
- maritime-specific scene templates
- traffic-specific scene templates
- shipboard crew roles
- charterer/owner/manager meanings
- public-agency policy labels

Core exposes generic extension points that packs use to add these concepts.

## The Pack: Maritime Fleet Pack

### External Product Name

Vezor FleetOps

### Pack Name

`maritime-fleet`

### Status

First pack authorized for implementation. The manifest is now a repo artifact.
Implementation code still needs to be built through the pack registry and
maritime pack workstream.

### First Buyer

Fleet operators, vessel managers, offshore operators, and satellite-managed
service customers with existing cameras and constrained links.

### Channel

Speedcast-style managed connectivity and fleet operations channels.

### Pain

- vessel cameras exist but do not produce useful operational signals
- satellite links are expensive, intermittent, and shared
- evidence is hard to move, trust, and explain
- NOC operators need exceptions, not live video walls
- incidents need voyage, time, position, link, and scene context
- onboard setup must work without a sysadmin

### Maritime Pack Owns

- `Vessel`
- `Voyage`
- `PortCall`
- `AISPosition`
- `NMEAReading`
- `CarrierTerminal`
- `MaritimeRole`
- `WatchRotation`
- maritime scene templates
- maritime evidence cover-sheet fields
- maritime retention defaults
- maritime billing hierarchy labels
- carrier and maritime integrations

### Maritime Pack Templates (MVP)

| Template | Outcome | Notes |
|---|---|---|
| Gangway Access | boarding/exit events, after-hours activity, evidence | first demo template |
| Deck Presence | person/vehicle/asset presence on exposed deck | safety and security |
| Engine Room Safety | person presence, restricted zone, anomaly/evidence trigger | keep conservative |
| Cargo Or Work Area | zone occupancy, movement, restricted access | flexible across vessel and remote sites |
| Port Call Evidence | high-bandwidth sync posture, backlog drain, evidence context | ties directly to link moat |

Hold back bridge watchkeeping, anti-piracy, bunkering, cargo shift, gauge
reading, and VDR-heavy use cases until first renewal. They are valuable but each
adds validation and sales load.

## Designed-For Target: Traffic And Public-Space

Status: architectural target, not a build commitment.

This section exists to prove the engine generalizes, provide a forcing function
on engine domain-neutrality, and record a deliberate strategic choice so it
cannot drift back in as scope creep.

### What Exists As Strategy Artifacts

- A `pack.yaml` manifest for `traffic-public-space`, marked `status: designed_not_implemented`.
- An entity catalog: `Intersection`, `Approach`, `Movement`, `Crosswalk`, `BikeLane`, `BusLane`, `CurbZone`, `TransitStop`, `SignalPhase`, `TrafficStudy`, `ConflictEvent`, `PublicSpacePolicy`, `CivicTransparencyReport`.
- A privacy contract draft: no face recognition, no biometric identification, plate recognition off by default, redacted evidence default, transparency reports required.
- A scene template catalog: multimodal counts, VRU safety, curb and loading zone, bus/bike lane priority, queue and spillback, work zone awareness.

### What Does Not Exist And Will Not In Year One

- Implementation code for any traffic entity.
- Sales motion targeting public agencies, DOTs, transit, ITS integrators, or smart-city procurement.
- Demos focused on traffic or street operations.
- Pricing meters for intersection-month, corridor-mile-month, or traffic-study-export.
- ATSPM, CDS, GTFS, Open311, V2X/SPaT/MAP, or GIS integration adapters.
- Public transparency reporting infrastructure.

### Why The Manifest Exists

Writing the traffic-public-space manifest is the architectural unit test for
engine generality. Every entity in the manifest must extend a generic core
primitive such as `Site`, `SiteGroup`, `Scene`, or `Signal` without modifying
core. If any traffic entity requires a core schema change, the engine is not
actually domain-neutral and the maritime pack is also at risk.

The traffic manifest is in the repo, reviewed as a strategy artifact, and
version-controlled. Code for it is not.

### Conditions Under Which Traffic/Public-Space Ships

All three must hold:

1. Maritime FleetOps has at least one paying customer that has renewed at least once.
2. A specific traffic or public-space customer exists with named budget, named procurement path, and named timeline, not just a market read.
3. An explicit, dated, recorded decision to start the pack is made. Drift is not authorization.

Absent all three, the pack remains a manifest. This is not a deferral; it is a
deliberate strategic choice that requires equal deliberateness to reverse.

### Traffic/Public-Space 2027 Research Summary

The 2027 opportunity is not generic vehicle detection. It is privacy-governed,
multimodal street truth:

- multimodal counts by class, approach, movement, and time bin
- pedestrian/cyclist exposure and conflict candidates
- queue, spillback, and delay proxies
- curb, loading-zone, bus-lane, and bike-lane blockage
- ATSPM-style exports and signal-phase context later
- GIS/GeoJSON, CSV, and study export packages later
- V2X/SPaT/MAP context as a research path, not the first wedge
- public-space privacy contract, redaction, retention, and transparency report

Research references from 2026-06-05:

- FHWA Safe System Approach: https://highways.dot.gov/safety/zero-deaths/safe-system-approach-toward-zero-traffic-deaths
- FHWA arterial management and traffic signal performance measures: https://ops.fhwa.dot.gov/arterial_mgmt/performance_measures.htm
- U.S. DOT V2X deployment: https://www.transportation.gov/v2x
- U.S. DOT Complete Streets: https://www.transportation.gov/mission/health/complete-streets
- Open Mobility Foundation Curb Data Specification: https://github.com/openmobilityfoundation/curb-data-specification
- European Commission AI Act regulatory framework: https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- Miovision traffic solutions: https://miovision.com/
- NoTraffic AI traffic management: https://notraffic.tech/
- Rekor roadway intelligence: https://www.rekor.ai/
- Hayden AI traffic and transit enforcement: https://www.hayden.ai/
- VivaCity transport data and street analytics: https://vivacitylabs.com/

## Engine Validation Through Home Testing

Home/lab testing with roads, cars, pedestrians, and bicycles is engine
validation, not a second product. It is the cheapest and most honest test of the
engine/pack boundary.

### Setup

| Component | What runs |
|---|---|
| Edge | Existing Jetson Orin Nano, or x86 with generic Linux HAL |
| Camera | Any RTSP IP camera or USB webcam pointed at driveway, street, or corner |
| Master | Local docker-compose stack, same as dev environment |
| Models | Existing COCO 80-class model. No training. |
| Scenes | Line across the street for vehicle count; zone on driveway for presence; region on sidewalk for person/bicycle traffic. |
| Pack loaded | None. Optional local validation profile/config only. |

### Rules For Home Testing

1. No traffic-specific entities. No `Intersection`, no `Approach`, no `Movement`. If a home scene needs them, the engine has a generality gap to fix, not a traffic pack to start.
2. No traffic-specific code in core. Generic line crossing, zone occupancy, and count event primitives handle every home scene.
3. Open vocabulary is allowed for discovery, for example `delivery van`, `e-scooter`, or `school bus`, but stays discovery. No promotion to a stable pack.
4. Link-aware data plane runs at home unchanged. It will never trigger satellite-rain-fade behavior, but the code paths get exercised.
5. Chain of custody runs at home unchanged. Driveway clips get the same evidentiary treatment as vessel gangway clips. This validates Layer 4 outside maritime context.
6. If a home test produces interesting results, it is an engine improvement opportunity. Generalize the primitive that helped; do not start a pack.

### What This Proves

Every home-lab session is a passive architectural unit test. If the engine works
for roads and cars at home with no pack, the maritime pack is genuinely
additive. If home testing requires core concessions for road concepts, the
maritime pack will accumulate the same concessions and the engine/pack split is
theater.

### What This Is Not

- A traffic prototype.
- A demo for traffic or smart-city customers.
- A reason to write traffic-specific UI panels.
- An on-ramp to building the second pack early.

If a traffic-adjacent person sees the home setup and gets interested, the answer
is: "the engine generalizes; we are not selling this." That is the signal the
architecture is working, not the signal to start the second pack.

## Updated Layer Blueprint

### Layer 1: `argus-link`

Status: core engine. Baseline for the fleet wedge, not a premium add-on.

Core must include:

- site bandwidth budget
- priority lanes: safety, evidence, telemetry, bulk
- evidence backlog and queue depth
- resume-on-interrupt
- backpressure protocol
- link health probes
- last sync and last successful evidence transfer
- runtime UI for degraded, dark, port WiFi, and recovering states

Premium expansion can include carrier-specific steering, billing-grade cost
analytics, advanced scheduling, and partner APIs.

### Layer 2: `argus.fleet`

Status: core engine, refactor needed.

Core owns:

- `Site`
- `SiteGroup`
- `SiteHierarchyNode`
- `SiteState`
- `LinkState`
- `RuntimeState`
- `SiteAssignment`
- `RotationGroup`
- exception-first dashboard

Core must not own:

- `Vessel`
- `Voyage`
- `PortCall`
- `Owner`
- `Manager`
- `Charterer`
- AIS-derived state

Maritime pack extends the generic site model:

- vessel is a maritime projection of `Site`
- voyage is maritime context over time on a `Site`
- port call is maritime context attached to a voyage and link state
- owner/manager/charterer are pack-specific labels over generic relationship nodes

Estimated refactor: 2-3 weeks if done before fleet code hardens further.

### Layer 3: `argus.maritime`

Status: first pack to build. The manifest exists; code does not yet.

Owns:

- AIS ingest
- NMEA bridge
- carrier telemetry adapters
- VDR/ECDIS export alignment later
- vessel/voyage/port-call entities
- maritime evidence context
- maritime scene templates
- maritime UI labels and onboarding

This pack proves the engine/pack boundary in production.

### Layer 3B: `argus.traffic_public_space`

Status: manifest only. Not built.

Exists as `pack.yaml`, entity catalog, scene template catalog, and privacy
contract draft. No code. No roadmap commitment. It functions as an architectural
unit test.

### Layer 4: `argus.coc`

Status: core engine.

Core owns hash-linked evidence, signed artifacts, audit log, evidence pack
export, privacy manifest, time-source provenance, and retention engine hooks.

Maritime pack contributes voyage fields, position fields, vessel identity,
port-call context, maritime role/reviewer context, and maritime retention
defaults.

### Layer 5: `argus-support`

Status: core engine.

Core owns captive portal, QR/BLE pairing, remote diagnostic bundle, NOC tunnel,
local break-glass, and disconnected runbook.

Maritime pack contributes ETO-oriented wording, vessel install checklist,
satellite-link diagnostics view, and shipboard support roles.

### Layer 6: Edge Platform

Status: core engine.

Core owns Jetson path, generic x86 path, platform abstraction, signed updates,
model-only updates, A/B rollback, and runtime artifact lifecycle.

Maritime pack contributes marine-grade hardware recommendations,
DNV/cybersecurity notes, and shipboard deployment constraints.

### Layer 7: Camera Ecosystem

Status: core engine.

Core owns ONVIF discovery, RTSP ingest, analog encoder support, camera quirks
library, substream/mainstream switching, and per-camera bandwidth budget hooks.

Maritime pack contributes vessel camera onboarding defaults, shipboard network
assumptions, and maritime camera template names.

### Layer 8: `argus.billing`

Status: core engine, abstraction needed.

Core owns:

- `BillingNode` adjacency tree
- billing account
- entitlement
- usage meter
- invoice line item
- pack type discriminator
- evidence/export/support/link usage meters

Maritime pack populates Speedcast-style reseller tree, owner/manager/charterer
labels, vessel account rollups, and charter handover rules.

Pricing does not lead with commodity per-camera SaaS. Per-camera is a capacity
meter; the value meters are evidence, link-governed operation, fleet runtime
health, and operational incidents resolved.

## Pack Manifest

Define `pack.yaml` early. Two manifests live in the repo:

- `maritime-fleet`, status `planned_mvp`
- `traffic-public-space`, status `designed_not_implemented`

The second exists as a forcing function on engine domain-neutrality.

### Required Fields

- pack metadata: id, name, owner, status, wedge
- engine requirements: minimum version and required capabilities
- entities contributed, each extending a core type with `storage: pack`
- scene templates contributed
- model presets, both fixed-vocab and open-vocab
- integrations declared
- evidence context fields contributed
- billing hierarchy labels and meters contributed
- UI extensions declared
- `allowed_core_dependencies` positive allowlist
- `forbidden_dependencies` negative list

### Pack Interface Contract

| Interface | Purpose |
|---|---|
| `register_pack()` | makes manifest visible to engine |
| `register_entities()` | contributes pack-owned data models without changing core schemas |
| `register_scene_templates()` | contributes setup presets and operator copy |
| `register_model_presets()` | contributes class scopes and open-vocab discovery terms |
| `register_integrations()` | contributes adapters and telemetry sources |
| `enrich_evidence_context()` | attaches pack context to evidence exports |
| `resolve_billing_hierarchy()` | maps generic billing nodes to pack labels |
| `contribute_ui_extensions()` | contributes optional panels without hardcoding pack fields in core UI |

A PR that adds `Vessel` or `Voyage` to a core contract fails review. A PR that
adds `Intersection` or `Approach` to a core contract fails review. The manifest
is the governance tool.

## Model Strategy

The 80-class model and open-vocabulary runtime are important. They serve pack
outcomes rather than define the product.

### Maritime Fixed-Vocab COCO

- `person` for gangway, deck, engine room, restricted zone, after-hours presence
- `boat` for dock/quay scenes where useful
- `car`, `truck`, and related classes for port, ramp, and yard scenes
- object classes only when tied to a specific scene outcome

Do not present the full 80-class list as the sales story.

### Engine Validation Fixed-Vocab COCO (Home/Lab)

- `person`, `bicycle`, `car`, `motorcycle`, `bus`, and `truck` for road/street scenes
- used to exercise the engine, not to support a pack

### Open Vocabulary

Controlled discovery only:

1. constrain the scene with include regions and event boundaries
2. use a small vocabulary
3. review telemetry and false positives
4. promote stable terms into a pack preset or a custom model path
5. attach vocabulary hash to the scene contract

Open vocabulary discovers domain-specific objects; it does not promise "detect
anything."

## Demo Narrative

One demo. Maritime.

### Title

Vezor FleetOps: AI video that survives bad links.

### Flow

1. Fleet exception view: vessels/sites by attention, not a camera wall. Highlight degraded link, stale heartbeat, evidence backlog, and active incident.
2. Gangway Access scene: source camera, scene contract, line/zone event, person count or boarding event.
3. Link-aware evidence: evidence priority lane, queue and resume state, clip/pack arriving after degraded link recovers.
4. Evidence Desk: clip/still, scene contract hash, vessel/voyage/position context, reviewer action.
5. Runtime truth: model artifact, heartbeat, privacy state, link state, supervisor state.

Close with:

> This is not a camera wall. It is a fleet operations signal layer with evidence.

A traffic demo does not exist. If asked, the answer is: "we are focused on
fleet operations; the engine can support traffic in time, but that is not what
we sell."

## Pricing Direction

Avoid commodity per-camera positioning.

| Meter | Role |
|---|---|
| vessel or remote-site month | base commercial unit |
| camera tier | capacity guardrail, not value story |
| managed edge node | runtime footprint |
| retained evidence GB | storage cost recovery |
| evidence pack export | value meter |
| support session hour | operational service meter |
| managed link GB or bandwidth budget tier | link-aware value meter |
| premium carrier adapter | partner/integration value meter |

Traffic meters such as intersection-month, corridor-mile-month, and
traffic-study-export exist in the traffic manifest as design artifacts. They are
not in the price book.

## Roadmap

### 0 To 30 Days: Strategy Lock

- Adopt one external wedge: AI video for satellite-connected fleet operations.
- Use "SceneOps Engine" only as internal architecture language.
- Mark v3 two-pack blueprint as superseded.
- Write `pack.yaml` manifest contract.
- Write `maritime-fleet` manifest draft.
- Write `traffic-public-space` manifest draft with `status: designed_not_implemented`.
- Decide where pack manifests live in the repo.
- Update design docs to reflect engine/pack separation.
- Set up home/lab engine validation environment.

### 30 To 90 Days: Engine/Pack Guardrails

- Implement pack registry shape.
- Refactor Layer 2: extract generic site hierarchy and site state into `argus.fleet`; move maritime entities into `argus.maritime`.
- Refactor Layer 8: generalize to `BillingNode` tree in `argus.billing`; move maritime labels into `maritime-fleet` pack.
- Define Maritime Fleet Pack MVP templates: Gangway Access, Deck Presence, Engine Room Safety, Cargo Or Work Area, Port Call Evidence.
- Run home/lab engine validation continuously. Any test that requires touching core for a non-maritime entity is a generality bug, not a pack opportunity.
- Keep `argus-link` as core for the wedge.

### 90 To 180 Days: Pilot Proof

- Build minimum link-aware data plane: priority lanes, backlog, resume-on-interrupt, last sync, degraded/dark/port-WiFi states.
- Ship first fleet exception dashboard.
- Ship first evidence pack export with scene contract context.
- Ship first maritime pack templates.
- Run one vessel or remote fleet pilot.
- Continue home/lab validation. Document every case where the engine handled a non-maritime scene cleanly. These are sales-conversation material for the engine story even though no second pack ships.

### 180 To 365 Days: Renewal Proof

- Finish carrier-aware link selection.
- Add AIS ingest and at least one carrier telemetry adapter.
- Harden chain-of-custody.
- Add no-laptop onboarding and support tunnel.
- Land the maritime pilot's first renewal.
- Only after at least one paying renewal, evaluate a second pack. If evaluated, require a named customer with budget and timeline, not a market read.

### Beyond Year One

- Maritime expansion to offshore energy is a natural adjacent: same Speedcast-style channel and high pack reuse.
- Traffic-public-space pack ships only under the three conditions documented above.
- Manifest-only target list may grow as architectural targets, but built packs stay rare and deliberate.

## Design Doc Updates Needed

| Existing layer | Change |
|---|---|
| Layer 1 `argus-link` | keep domain-neutral; baseline for fleet wedge |
| Layer 2 `argus.fleet` | split generic site/fleet core from maritime entities |
| Layer 3 `argus.maritime` | first pack to build; add manifest and pack-owned entities |
| Layer 3B `argus.traffic_public_space` | manifest only; no code |
| Layer 4 `argus.coc` | keep core; maritime pack contributes evidence context |
| Layer 5 `argus-support` | keep core; maritime pack contributes shipboard support copy |
| Layer 6 edge platform | keep core; maritime pack contributes marine-grade notes |
| Layer 7 cameras | keep core; maritime pack contributes vessel camera defaults |
| Layer 8 `argus.billing` | generalize to `BillingNode`; maritime pack contributes hierarchy labels |

## Decision Rules

1. If it describes how cameras become governed signals, it belongs in the engine.
2. If it describes a vessel, voyage, port, carrier terminal, or maritime regulation, it belongs in the maritime pack.
3. If it describes an intersection, approach, crosswalk, curb zone, signal phase, or traffic study, it belongs in the traffic-public-space pack manifest only. No code.
4. If it is required for fleet buyers to believe the product works over satellite links, it is baseline.
5. If it exposes 80 classes or open vocabulary, it must be framed through a scene outcome.
6. No second pack ships until Maritime FleetOps has paying renewal proof. Drift does not authorize a second pack; an explicit dated decision does.
7. Home/lab testing with road, cars, pedestrians, and bicycles is engine validation. It does not seed a second pack. If a home scene cannot be served by core primitives, the engine has a generality gap to fix, not a traffic pack to start.
8. If a PR adds maritime or traffic-public-space nouns to core contracts, the pack boundary has failed.
9. If a real traffic-public-space customer appears with budget and timeline, that is grounds for an explicit reassessment, not silent scope creep. The reassessment must be a dated, recorded decision.

## Final Recommendation

> Vezor sells one focused product on one engine: FleetOps for
> satellite-connected fleet operations. Underneath, Vezor builds a
> domain-neutral SceneOps Engine. Maritime is the only pack authorized for
> year-one implementation.
> Traffic-and-public-space exists as a pack manifest, a forcing function on
> engine generality, not a build commitment. Home/lab testing with road and cars
> validates the engine without diluting the product. Link-awareness is the
> floor. Evidence and operational incidents are the pricing power. Open
> vocabulary is discovery. No second pack ships until the first one renews.

This gives Vezor a defensible position without giving up the option to expand
later.
