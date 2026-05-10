# Open-Vocab Hybrid Detector Design

**Date:** 2026-04-26  
**Status:** Implemented in stages; control-plane foundation, model catalog registration, and experimental Ultralytics `.pt` open-vocab runtime have landed
**Scope:** Product behavior, backend contracts, worker runtime design, UI behavior, and rollout boundaries for adding first-class open-vocabulary detector support alongside the current fixed-vocabulary model path.

## 0. Implementation Checkpoint

This design was implemented in two stages.

The first stage landed the control-plane and UI foundation:

- `Model.capability` supports `fixed_vocab` and `open_vocab`.
- camera runtime vocabulary state is persisted.
- vocabulary snapshot attribution exists for history/count explainability.
- query resolution can produce `fixed_filter` or `open_vocab` results.
- worker commands include `runtime_vocabulary`, source, and version fields.
- the detector factory has fixed-vocab and open-vocab branches.
- Camera setup and Live query UI expose capability-aware behavior.
- the Evidence Desk review queue has landed as the incident review surface.

The follow-up model catalog/open-vocab runtime stream closed the original runtime gap:

- `ModelFormat.PT` supports `.pt` open-vocab model records.
- the recommended model catalog exposes YOLOE and YOLO-World presets.
- `backend/scripts/register_model_preset.py` registers local artifacts from catalog defaults.
- the worker can load an Ultralytics-backed YOLOE or YOLO-World adapter instead of wrapping the fixed-vocab detector.
- Live query updates can hot-swap detector vocabulary without restarting the worker.

Remaining validation work is operational, not a missing product contract:

- soak the experimental `.pt` path on the production central GPU profile.
- soak the experimental `.pt` path on Jetson when model size, memory, and provider support are acceptable.
- implement supervisor-backed lifecycle reporting before treating open-vocab as fleet-safe production behavior.
- keep raw TensorRT `.engine` support planned until validated runtime artifacts are implemented. The active follow-up is `docs/superpowers/plans/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-implementation-plan.md`, which adds both fixed-vocab Jetson artifacts and compiled per-scene open-vocab artifacts.

Production dependency:

- central and edge workers need supervisor-backed lifecycle management before this becomes an operator-safe production feature at fleet scale.

## 1. Goal

Add first-class support for two detector capability modes:

- `fixed_vocab`
- `open_vocab`

The system must continue to support today's COCO/custom fixed-label ONNX models while also allowing models whose useful runtime vocabulary is supplied dynamically through natural language or explicit prompt lists.

This support must apply to both:

- central processing
- edge processing

Jetson is the first validated edge target, but the architecture must remain portable enough for future ARM64 and x86 edge workers with suitable inference hardware.

## 2. Why This Change Is Needed

Before this track, the system was good at:

- closed-label COCO detectors
- closed-label custom ONNX detectors
- natural-language to class-subset resolution within an already known model taxonomy

The remaining work after the model catalog stream is production proof, not basic runtime capability:

- performance and memory validation for central and Jetson open-vocab profiles
- operational visibility for which runtime vocabulary and backend are active
- supervisor-backed restart/recovery when an experimental model fails

The old architecture assumed:

- `Model.classes` is canonical and complete
- `Camera.active_classes` is a subset of `Model.classes`
- natural-language query resolves to `active_classes`
- the detector itself remains fixed and unchanged

That design works for COCO and custom fixed-label detectors, but blocks true open-vocabulary detection.

## 3. Product Behavior

### 3.1 Detector Modes

The product supports two detector capability modes:

- `fixed_vocab`
  A detector with a closed inventory of labels known at model registration time.
- `open_vocab`
  A detector whose active label space is supplied or refined at runtime through a detector vocabulary or prompt set.

### 3.2 Live Query Behavior

The existing live natural-language query surface remains, but its effect depends on camera capability.

For `fixed_vocab` cameras:

- natural-language resolves to a subset of known model classes
- the backend updates camera `active_classes`
- the detector still runs against its fixed model inventory

For `open_vocab` cameras:

- natural-language resolves to a detector runtime vocabulary
- the backend updates detector-side runtime vocabulary
- the worker actually changes what the detector is looking for

### 3.3 Vocabulary Versus Filter

The product must distinguish between:

- `runtime vocabulary`
  What the detector is currently allowed or instructed to detect.
- `operator filter`
  What the UI/operator wants emphasized or shown from the current detections.

For fixed-vocab detectors these may overlap heavily.

For open-vocab detectors they must remain separate concepts. Collapsing them into one field would reproduce the current limitation where the UI narrows display but the detector vocabulary never changes.

### 3.4 History And Counting Semantics

History remains metric-aware and durable.

The existing split stays:

- `occupancy`
- `count_events`
- `observations`

Open-vocab detections still flow into:

- tracking
- occupancy
- count events
- rules
- history
- export

The downstream system continues to operate on normalized emitted `class_name` values, even when those labels came from a runtime vocabulary instead of a permanently fixed global model inventory.

### 3.5 Incidents Page Direction

The Incidents page remains an evidence-first workspace, not a generic event timeline.

Approved UX direction: `Evidence Desk`

Key behavior:

- one selected incident becomes the hero artifact
- large evidence preview is primary
- signed clip/snapshot actions remain immediate and obvious
- a visible queue stays available for rapid review throughput
- trust facts remain explicit:
  - source camera
  - incident type
  - timestamp
  - storage status
  - signed evidence availability

In this phase, Incidents still represents persisted incident records and alert evidence. It does not yet become a unified timeline for all count events, query events, or raw detections.

## 4. Platform Scope

### 4.1 Central And Edge

Open-vocab must be available in both:

- `central`
- `edge`

The architecture must not treat open-vocab as an edge-only or central-only feature.

### 4.2 Edge Portability

`Edge` is a portable worker class, not a synonym for Jetson.

Jetson is the first validated edge target, but the design must leave room for:

- Jetson
- Raspberry Pi–class ARM64 devices with AI accelerators
- generic ARM64 boxes with NPU/GPU support
- x86 edge appliances or VMs with suitable inference hardware

The design must separate:

- deployment location
- detector capability
- execution profile

so that future hardware support does not require another schema rewrite.

## 5. Backend And Worker Architecture

### 5.1 Capability-Aware Detector Interface

The worker runtime should stop assuming every primary detector is the current fixed-vocab YOLO decoder.

Instead, it should depend on a capability-aware detector interface that can support both detector families.

Responsibilities of the detector interface:

- load fixed-vocab or open-vocab detectors
- expose detector capability metadata
- apply runtime vocabulary updates when supported
- perform inference and emit normalized `Detection` objects
- describe current runtime state for diagnostics and observability

### 5.2 Normalized Detection Contract

Both detector families must emit the same normalized internal shape so the rest of the pipeline stays reusable.

Current internal shape should remain conceptually intact:

- `class_name`
- `confidence`
- `bbox`
- optional `class_id`
- optional `track_id`
- optional `attributes`
- optional `zone_id`
- optional `speed_kph`
- optional `direction_deg`

This preserves downstream reuse for:

- tracking
- zones
- speed
- attributes
- count events
- rules
- incidents
- telemetry
- history persistence

### 5.3 Fixed-Vocab Path

The fixed-vocab path remains the fast/default route for:

- COCO models
- custom closed-label ONNX models

Behavior:

- `Model.classes` is canonical
- `active_classes` remains valid
- worker can keep using the current fixed-vocab narrowing behavior

### 5.4 Open-Vocab Path

The open-vocab path must treat detector vocabulary as mutable runtime state.

Behavior:

- detector accepts runtime vocabulary or prompt state
- worker updates detector-side prompt/text state without full worker restart
- detector emits resolved label strings as normal detections
- the product does not pretend the model has a globally complete closed inventory

### 5.5 Worker Runtime State

Worker state must split into:

- `runtime_vocabulary`
- `operator_filter`
- `runtime_vocabulary_version`
- `runtime_vocabulary_hash`
- `runtime_vocabulary_updated_at`
- `runtime_vocabulary_source`

For fixed-vocab cameras:

- runtime vocabulary may simply mirror the fixed inventory or remain implicit

For open-vocab cameras:

- runtime vocabulary is first-class mutable worker state

### 5.6 Worker Commands

The `cmd.camera.<id>` control-plane payload must evolve from a fixed `active_classes` message to a capability-aware command contract.

It should support:

- `active_classes` for fixed-vocab cameras
- `runtime_vocabulary` for open-vocab cameras
- shared updates for:
  - tracker type
  - privacy
  - zones
  - attribute rules
- metadata such as:
  - vocabulary version/hash
  - update source

### 5.7 Worker Config

Worker config returned by the control plane should expose the richer detector contract consistently for both central and edge workers.

It should include:

- detector capability
- model inventory when closed-label
- default runtime vocabulary when applicable
- current runtime vocabulary when applicable
- capability-specific limits
- whether hot-swapping vocabulary is supported
- execution profile requirements

### 5.8 Execution Profiles

Execution profile should be modeled as a first-class runtime concern, separate from location and detector capability.

Examples:

- `x86_64_gpu`
- `x86_64_cpu`
- `arm64_jetson`
- `arm64_npu`
- `arm64_cpu`

Open-vocab support should be understood as a capability of the worker/model/runtime combination, not “Jetson mode”.

### 5.9 Scheduling Rule

A camera can be assigned to any worker whose runtime profile satisfies the selected model’s capability requirements.

The scheduler must not encode a rule like “open-vocab means Jetson”.

Phase 1 may validate only a subset of profiles, but the contract must already allow future expansion cleanly.

## 6. Data Model And API Contract Changes

### 6.1 Model Contract

`Model` must explicitly describe detector capability instead of overloading `classes`.

Add a capability field such as:

- `fixed_vocab`
- `open_vocab`

For `fixed_vocab` models:

- `classes` remains required and canonical

For `open_vocab` models:

- `classes` is optional or treated as a seed/default vocabulary
- capability-specific metadata should live in structured model capability config

Recommended metadata:

- supports runtime vocabulary updates
- max runtime terms
- vocabulary mode / prompt format
- execution profile requirements

### 6.2 Camera Contract

`Camera` needs explicit detector runtime state.

Keep:

- `active_classes`

Add:

- `runtime_vocabulary`
- `runtime_vocabulary_source`
- `runtime_vocabulary_updated_at`
- `runtime_vocabulary_version`

This state must live in the database, not only in Redis or process memory, so:

- workers can restart safely
- central and edge workers can stay consistent
- the UI can display current camera state
- auditability is preserved

### 6.3 Query Contract

The query API must become capability-aware.

Today it only returns resolved classes.

It should evolve to describe:

- whether the resolution updated `active_classes` or `runtime_vocabulary`
- resolved class/filter results for fixed-vocab cameras
- resolved runtime vocabulary for open-vocab cameras
- provider/model/latency as today
- the targeted camera set

### 6.4 Vocabulary Snapshot Attribution

History and count persistence should remain explainable across vocabulary changes.

Do not store the full runtime vocabulary blob on every tracking row.

Recommended design:

- store `vocabulary_version` and/or `vocabulary_hash` on tracking/count rows
- store full vocabulary payloads in a separate `camera_vocabulary_snapshots` table

This allows the system to explain which detector vocabulary produced a detection window without inflating high-volume event tables.

### 6.5 Worker Capability Reporting

Worker registration or heartbeat should advertise:

- supported detector capabilities
- supported execution profiles/backends
- whether hot runtime vocabulary updates are supported
- vocabulary limits and hints

This lets the control plane place compatible camera workloads without baking hardware-specific assumptions into camera config itself.

## 7. Query Resolution Behavior

### 7.1 Fixed-Vocab Query Flow

- load allowed classes from selected cameras’ model inventories
- resolve NL into known class subset
- publish updated `active_classes`
- return response describing resolved classes

### 7.2 Open-Vocab Query Flow

- resolve NL into detector runtime vocabulary
- validate vocabulary against model/runtime limits
- publish updated `runtime_vocabulary`
- return response describing applied vocabulary

### 7.3 Mixed-Camera Query Rules

A multi-camera query should only be allowed when the selected cameras have compatible semantics.

Allowed:

- fixed-vocab groups with compatible closed inventories
- open-vocab groups with compatible open-vocab model/runtime family

Rejected:

- incompatible mixtures where the same query would need to be interpreted in different ways

Failures should be operator-readable and explicit.

## 8. UI Changes

### 8.1 Camera Setup

Camera setup must branch by model capability.

For fixed-vocab models:

- preserve today’s class-selection UX

For open-vocab models:

- replace the fake closed-label class picker with runtime vocabulary controls
- allow setting:
  - default detector vocabulary
  - current applied vocabulary
  - optional operator filter

### 8.2 Models UI

Model inventory must surface:

- capability mode
- fixed-vocab vs open-vocab behavior
- runtime vocabulary limits
- validated execution profile hints

### 8.3 Live Query UI

The live query surface should make the result type explicit:

- “resolved classes” for fixed-vocab cameras
- “applied detector vocabulary” for open-vocab cameras

If a query is rejected because the selected camera set is incompatible, the error must say that directly.

### 8.4 History UI

History remains the main analytics workspace.

For open-vocab cameras:

- charts still operate on normalized `class_name`
- the UI should surface when labels came from a runtime vocabulary snapshot if that context matters

### 8.5 Incidents UX

The Incidents page should move to the approved `Evidence Desk` direction:

- selected incident hero view
- large evidence preview
- side queue for rapid review
- obvious signed evidence actions
- calmer, high-trust facts panel

In this phase, incidents stay evidence-first and alert-first, not a full generic event timeline.

## 9. Rules And Persistence

### 9.1 Rules

Rules remain `class_name` based in phase 1.

Open-vocab detections can still participate in:

- count rules
- alert rules
- clip capture rules
- webhooks

as long as they emit normalized `class_name`.

We do not introduce a second prompt-specific rule language in this phase.

### 9.2 Count Events

Count events continue to work on normalized detections:

- `line_cross`
- `zone_enter`
- `zone_exit`

Open-vocab labels should be carried through exactly like fixed-vocab labels, with vocabulary snapshot references available for explainability.

### 9.3 Incident Generation

Incident generation remains:

- evidence-first
- rule-driven
- ANPR-driven where applicable

Open-vocab support should not require a separate incident subsystem. It should simply enable rules/incidents to operate on normalized labels produced by open-vocab detectors.

## 10. Phase 1 Delivery Boundaries

### 10.1 In Scope

Phase 1 should include:

- capability-aware model schema
- capability-aware camera runtime state
- capability-aware worker config
- capability-aware query command path
- detector abstraction split
- fixed-vocab compatibility path
- open-vocab runtime vocabulary path
- central and Jetson support
- future edge-profile extensibility in schema/control-plane design
- History/count/incidents compatibility
- Camera/Model/Live/Incidents UI updates
- Evidence Desk incidents redesign

### 10.2 Not Required In Phase 1

Phase 1 should not require:

- generic incident case management
- unified all-events incident timeline
- arbitrary free-text historical relabeling
- a second prompt-native rule language
- full support for every future edge hardware family on day one
- action-recognition or full VLM scene understanding

### 10.3 Minimum Validation Matrix

Phase 1 should validate at least:

- central fixed-vocab
- central open-vocab
- edge Jetson fixed-vocab
- edge Jetson open-vocab

The schema and control-plane should still be designed so later support can be added for:

- ARM64 non-Jetson edge
- x86 edge VM/appliance

without another contract redesign.

## 11. Success Criteria

The design is successful if:

- fixed-vocab cameras continue to work without regression
- open-vocab models can be registered honestly without pretending to have a complete static inventory
- a live query on an open-vocab camera changes actual detector vocabulary, not just UI filtering
- detections from open-vocab cameras flow through tracking, occupancy, count events, history, rules, and incidents as normalized labels
- central and Jetson deployments share the same product semantics
- the contract leaves room for broader ARM64/x86 edge hardware in future updates
