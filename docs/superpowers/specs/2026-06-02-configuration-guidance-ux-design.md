# Configuration Guidance UX Design

Date: 2026-06-02
Status: Proposed

## Product Goal

Make OmniSight configuration understandable without requiring the operator to
already know the product internals. Scene setup and Control Plane Configuration
should explain what each choice controls, when to use it, how it affects
runtime behavior, and what a safe starting value looks like.

The target operator promise is:

1. A new operator can add a camera and understand source points, destination
   points, event boundaries, include regions, and exclusion regions without
   external documentation.
2. A power operator can still move quickly through compact controls after they
   understand the concepts.
3. Every configuration profile kind explains its runtime effect, prerequisites,
   safe defaults, and binding consequences before the operator saves or binds it.
4. Help is contextual, concrete, and testable; it is not marketing copy, vague
   tooltips, or a separate manual that drifts away from the UI.

## Current State

The current UI has the right primitives but not enough explanation:

- `CameraWizard` has five setup steps and a calibration step with source points,
  destination points, event boundaries, and detection regions.
- `HomographyEditor` lets operators place source and destination points, but it
  does not clearly define the relationship between the two planes or the point
  ordering requirement.
- `BoundaryAuthoringCanvas` handles point placement and dragging, but the
  surrounding copy does not fully explain when to use a line, polygon zone,
  include region, or exclusion region.
- `ProfileEditor` exposes six configuration profile kinds: Evidence storage,
  Transport, Runtime, Privacy and retention, LLM and policy, and Operations.
  Most fields have only labels, not operator-oriented meaning, examples,
  prerequisites, or risk notes.
- `RuntimeImpactPanel` and the backend capability catalog are a strong start,
  but the catalog currently answers "is this supported?" more than "how do I
  choose correctly?"

The result is a high-power interface that feels correct to the system builder
and opaque to an operator.

## Scope

In scope:

- Scene camera setup guidance across Identity, Models & Tracking, Privacy,
  Processing & Delivery, Calibration, and Review.
- Clear conceptual explanations for:
  - camera source
  - processing mode
  - source points
  - destination points
  - reference distance
  - event line boundaries
  - polygon event zones
  - detection include regions
  - detection exclusion regions
  - class scoping
  - transport profile vs live rendition
  - event clip recording
- Field-level guidance for every Control Plane Configuration profile kind.
- Binding guidance that explains tenant, site, edge node, and camera scope
  precedence.
- Effective configuration guidance that distinguishes desired, inherited,
  bound, tested, and runtime-applied state.
- Reusable UI primitives for hints, examples, warnings, readiness checklists,
  field explanations, and compact glossary links.
- Tests that assert key guidance is present and remains mapped to the right
  controls.

Out of scope:

- A full visual redesign of OmniSight.
- A standalone documentation portal.
- A video tutorial system.
- AI-generated live help.
- Reworking the underlying configuration schemas unless a field needs a
  display-only unit conversion.
- Replacing the existing CameraWizard or ConfigurationWorkspace architecture.

## Product Rules

### 1. Guidance Must Be Operational

Every help item must answer at least one of:

- What does this control?
- When should I use it?
- What value should I start with?
- What can go wrong?
- What changes at runtime after I save or bind it?

Avoid generic copy such as "configure this setting" or "select an option."

### 2. Progressive Disclosure, Not Clutter

Use a three-layer model:

- **Inline hint:** one short sentence under the field or section.
- **Details popover/drawer:** definitions, examples, and consequences.
- **Readiness panel:** summary of blockers, warnings, and next actions.

The default view stays calm and dense. The operator can open deeper help when
needed.

### 3. Same Terms Everywhere

Use the same vocabulary in Scenes, Live, Operations, Evidence, and
Configuration:

- `camera source`: the physical or network input stream
- `analytics frame`: the frame dimensions used for detection and geometry
- `source points`: points on the camera image
- `destination points`: matching points on an abstract top-down world plane
- `event boundary`: line or polygon that emits crossing or enter/exit events
- `detection region`: include/exclude mask applied before event rules
- `transport profile`: how browsers reach a stream
- `live rendition`: which visual stream variant the operator watches
- `binding`: assignment of a profile to tenant, site, edge node, or camera
- `effective configuration`: the profile set resolved for a target

### 4. Explain Consequences Before Action

Save, Test, Bind, Delete, Unbind, Normalize, and Create Camera actions should
make the consequences visible near the action:

- what runtime will read the setting
- whether a worker restart or heartbeat is needed
- which camera/site/edge node will be affected
- whether the change is desired-only or already applied
- whether a fallback will occur

### 5. Geometry Guidance Must Be Visual And Validated

Geometry controls should show:

- point count and completion state
- point ordering guidance
- a small legend for source, destination, boundary, include, and exclusion
- live warnings for impossible or risky shapes
- examples such as doorway crossing, restricted zone, ignore road/background,
  and loading bay include region

Text alone is not enough for source/destination point setup.

## UX Design

### Guidance Surfaces

Add reusable surfaces rather than one-off paragraphs:

- `FieldHelp`: inline description plus an info button that opens more detail.
- `GuidancePanel`: right-side or in-flow panel for the current wizard step or
  profile kind.
- `GuidanceCallout`: compact warning/info/success rows with a specific next
  action.
- `ReadinessChecklist`: rows for complete, warning, and blocked states.
- `ExampleChips`: quick examples that fill or explain common values without
  hiding the real form fields.
- `GlossaryTerm`: consistent term labels with accessible descriptions.

Use existing dark operational styling. Cards remain compact, with no marketing
hero treatment.

### Scene Setup Guidance

#### Identity

Explain that:

- the camera name is the operator-facing scene label
- site controls grouping and default profile inheritance
- processing mode decides where inference runs
- source type decides whether the stream is pulled from RTSP or captured from
  an edge USB device
- USB sources must run on an edge node

Show one-line recommendations:

- `central`: simplest when the master can pull the stream reliably
- `edge`: best for weak uplink, privacy, or USB capture
- `hybrid`: use only when an edge node exists but central downstream analytics
  may also consume results

#### Models & Tracking

Explain:

- primary model drives persistent detections
- secondary model is optional refinement
- active classes narrow fixed-vocabulary model output
- runtime vocabulary defines the open-vocabulary terms for open-vocab models
- tracker type affects object continuity, not which classes are detected

Show runtime status as:

- `Ready compiled artifact`
- `Dynamic fallback`
- `Compiled stale`
- `Blocked by runtime profile`

#### Privacy, Processing & Delivery

Split the mental model:

- `Privacy`: redaction on produced visual evidence and rendered streams.
- `Processing`: frame skip, FPS cap, and vision profile affect inference load.
- `Evidence recording`: event clips only, not continuous recording.
- `Transport`: how the browser connects to streams.
- `Live rendition`: which stream variant the operator sees.

Add examples:

- weak network: HLS or reduced processed rendition
- low latency operator view: WebRTC when reachable
- evidence audit: event clips with central or local-first storage
- privacy-heavy site: blur faces, blur plates, edge/local-first storage

#### Calibration

Add a visible "How to configure geometry" primer at the top:

1. Confirm the analytics still matches the camera view.
2. Add four source points on a flat reference plane in the camera image.
3. Add four destination points in the same order on the top-down world plane.
4. Enter a known reference distance in meters.
5. Draw event boundaries.
6. Add include/exclusion regions only when detector attention needs masking.

Source points:

- are placed on the camera image
- should land on known ground-plane corners or stable reference marks
- must match the destination point order
- should avoid moving objects, shadows, and vertical surfaces

Destination points:

- represent the same four real-world points on a top-down plane
- do not need to be geographic coordinates
- should preserve the physical shape proportion well enough for distance and
  direction estimates

Reference distance:

- is a known real-world distance between two reference marks
- is required before speed or distance logic should be trusted
- should be measured in meters

Event boundaries:

- line boundary: use for directional crossing counts
- polygon zone: use for enter/exit events around an area
- class scope on line boundaries narrows which tracked classes emit events
- polygon zones currently apply to all tracked classes

Detection regions:

- include region: when at least one exists, detections outside include regions
  are ignored
- exclusion region: detections inside it are ignored before event rules
- use include regions to focus on operational areas
- use exclusion regions to mask false-positive zones such as screens,
  reflections, public roads, or non-operational background

Add validation messages:

- source and destination points must both have four points to complete
  homography
- source and destination point counts must match
- point order must be consistent
- polygon regions need at least three points
- line boundaries need exactly two points
- warn when an include region exists and a boundary sits fully outside it
- warn when exclusion regions overlap most of an event boundary

#### Review

Review should not merely summarize raw values. It should show a readiness list:

- source reachable or not inspected
- model/runtime state
- privacy posture
- delivery profile and live rendition
- calibration complete/incomplete
- boundaries and detection regions configured
- evidence recording destination
- next expected runtime action after save

### Control Plane Configuration Guidance

Each profile kind gets a persistent guidance panel with:

- what the profile controls
- when to create a separate profile
- required fields
- secrets used
- runtime effect
- binding advice
- common mistakes

Each field gets:

- description
- safe default
- examples
- validation message
- runtime consequence

#### Evidence Storage

Explain:

- provider: local filesystem, MinIO, S3-compatible, or local-first strategy
- storage scope: where evidence should live first
- local root: host/container path for local filesystem storage
- endpoint/region/bucket: object store connection target
- secure TLS: whether object store calls use HTTPS/TLS
- path prefix: namespace inside the bucket
- access key/secret key: stored write-only, not displayed after save

Common mistakes:

- cloud provider selected without bucket/credentials
- local-first selected but no local storage path
- privacy residency conflicts with storage scope

#### Transport Profile

Explain:

- native/direct: clean passthrough route
- WebRTC: low-latency browser route, requires reachable WebRTC host/UDP
- HLS: resilient browser route, higher latency
- MJPEG: compatibility fallback, higher bandwidth
- public base URL: browser-facing base when backend proxy is not enough
- edge override URL: edge-specific stream host override

Make the distinction visible:

- Transport profile = connection route
- Live rendition = clean/annotated/reduced video variant selected per camera

Common mistakes:

- using localhost in public URLs when browser is remote
- selecting WebRTC when UDP 8189 is blocked
- expecting transport profile to change resolution/FPS

#### Runtime Selection

Explain:

- preferred backend ranks ONNX/TensorRT/open-vocab execution
- artifact preference chooses compiled vs portable model artifact order
- allow fallback decides whether workers may use a slower or more portable
  runtime when the preferred runtime is unavailable

Common mistakes:

- disabling fallback before a valid TensorRT artifact exists
- selecting TensorRT-first on hardware with no compatible engine
- expecting runtime selection to change detector classes

#### Privacy And Retention

Explain:

- retention days: how long evidence remains eligible for storage
- storage quota: maximum storage budget; display human-readable units
- plaintext plate posture: whether unredacted plate text may be stored
- residency guardrail: where sensitive evidence is allowed to live

Common mistakes:

- cloud residency selected for a privacy-sensitive edge-only site
- very short retention with evidence review workflows
- bytes-only quota values that are hard to reason about

#### LLM Provider

Explain:

- provider/model/base URL decide which service drafts policy text
- API key is stored as a secret and never redisplayed
- deterministic fallback may still produce basic drafts when provider calls
  fail, but provider-backed drafts require credentials

Common mistakes:

- model name not available at the configured provider
- base URL omitted for local or custom providers
- expecting LLM settings to affect detector inference

#### Operations Mode

Explain:

- lifecycle owner decides who starts/stops/restarts workers
- supervisor mode decides how lifecycle commands are delivered
- restart policy decides recovery after failure

Recommended meanings:

- manual: operator handles lifecycle outside OmniSight
- edge supervisor: edge node owns local camera worker lifecycle
- central supervisor: master owns central worker lifecycle
- disabled: no automated lifecycle actions
- polling: supervisor checks desired state periodically
- push: control plane dispatches lifecycle requests immediately when the
  supporting service is available
- never: no automatic restart
- on failure: restart after crash or unhealthy exit
- always: restart even after intentional exits, for appliance-like workers

Common mistakes:

- selecting edge supervisor for a camera with no edge node assignment
- selecting push when NATS push support is not healthy
- using always restart during debugging when manual stop should remain stopped

### Binding Guidance

The binding panel should explain precedence:

1. Camera binding wins.
2. Edge node binding applies to cameras on that node.
3. Site binding applies to cameras in that site.
4. Tenant default is the fallback.

Add a live "will affect" preview before binding:

- profile name and validation state
- selected scope and target
- direct replacement if one exists
- affected camera count when available
- whether runtime workers will need to report a new applied hash

### Effective Configuration Guidance

The effective configuration panel should explain:

- `resolved`: desired profile for the selected target
- `runtime-wired now`: runtime has the desired hash or worker config carries it
- `desired only`: saved/bound but not yet applied by a worker
- `fallback`: runtime used another profile or backend
- `blocked`: validation or prerequisite prevents use

## Information Architecture

Create two frontend copy maps:

- `scene-guidance.ts`: wizard step guidance, geometry guidance, examples, and
  readiness messages.
- `configuration-guidance.ts`: profile-kind guidance, field guidance, value
  descriptions, common mistakes, and binding guidance.

The UI should render from these maps. Tests can assert key entries exist and are
connected to controls.

## Accessibility

- Info buttons must have accessible names.
- Popovers/drawers must be keyboard reachable and dismissible.
- Inline help should be associated with fields through `aria-describedby`.
- Guidance icons should not be the only signal; use text labels and tone.
- Canvases need text equivalents for point counts and validation status.
- No critical instruction should be hidden only in hover tooltips.

## Acceptance Criteria

- Camera Calibration explicitly explains source points, destination points,
  point order, reference distance, event boundaries, include regions, and
  exclusion regions in the UI.
- Source/destination and region canvases show actionable validation or readiness
  state while editing.
- Configuration profile editor renders field-level guidance for all visible
  fields in all six profile kinds.
- Binding panel explains scope precedence and shows a consequence preview before
  binding.
- Effective configuration explains inherited vs direct vs applied state.
- Tests fail if key guidance for geometry or any profile kind disappears.
- The UI remains compact enough for repeated expert use; detailed guidance can
  be collapsed or opened on demand.

## Recommended Execution Mode

Use a single implementation plan with sequential foundation tasks, then split
scene guidance and configuration guidance into two parallel implementation
tracks if subagents are available. The shared copy model and reusable guidance
components must land first so both tracks use the same UX language and styling.
