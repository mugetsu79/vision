# Domain-Neutral Scene Authoring Canvas Design

Date: 2026-06-04
Status: Proposed
Branch: `codex/omnisight-ui-ux-polish`

## Product Brief

OmniSight is a general spatial intelligence platform. Scene authoring must not
look like a traffic counter, people counter, parking monitor, road system, or
floor-only product by default. It must be credible for boats on water, birds in
air, animals in a field, packages on a conveyor, tools on a bench, machines in
a yard, and any other tracked object class.

The current line/zone/include/exclude guidance improved geometry clarity, but
the sketch still includes a vehicle-like shape, a person-like marker, and
road-like guide lines. Those cues make the software feel narrower than the
runtime.

The design goal is to make the authoring canvas object-neutral and
geometry-first while preserving operator density, runtime truth, and visual
clarity.

## Design Decision

Use **abstract tracked anchors and motion paths**, not example objects.

The default authoring illustration should show:

- an `Analytics still` plane
- perspective frame geometry
- event line geometry
- polygon event-zone geometry
- include and exclusion polygon geometry
- generic tracked-object envelopes
- anchor dots
- short motion vectors or trail paths
- neutral labels such as `tracked anchor`, `object path`, `event trigger`,
  `include gate`, and `exclusion mask`

The default illustration should not show:

- cars, trucks, boats, birds, animals, people, packages, or any other category
- road lanes, sidewalks, water waves, sky, grass, shelves, or facility-specific
  scenery
- category-specific icons as examples
- decorative motion or animated object loops

This keeps the canvas scalable across domains without turning the guidance into
a gallery of possible classes.

## Interaction Scope

This is a visual and copy polish for scene authoring guidance only.

In scope:

- `CalibrationFlowIllustration` modes for `boundaries` and `regions`
- event boundary and detection region guidance copy
- Camera wizard helper/background text around event lines, polygon event zones,
  include regions, and exclusion regions
- tests that enforce object-neutral defaults

Out of scope:

- runtime event semantics
- detection-region filtering logic
- homography math
- measured-distance calibration behavior
- dynamic per-domain templates
- model vocabulary, class selection, or tracker behavior

## Runtime Truth Rules

The UI must not imply a different runtime model.

- Event line and polygon zone authoring is frame geometry on the analytics
  still.
- Detection regions are frame-geometry masks applied before event boundaries.
- Runtime anchors are class-dependent today: detection regions use bottom-center
  anchors for known movable ground classes and center anchors for other classes;
  event boundaries currently process tracked detections through the existing
  count-event pipeline.
- The default UI should use `tracked anchor` and `object path` language instead
  of `person`, `car`, `footpoint`, or `wheel` language.
- Calibration measured distance may still refer to the floor/world plane where
  speed calibration explicitly depends on a measured physical plane. That copy
  should not be broadened in a way that makes speed accuracy seem valid for
  non-planar scenes.

## Visual Direction

Use the existing dark dashboard language:

- off-black analytical surface
- fine neutral grid/perspective marks
- restrained blue/cyan geometry for event zone
- teal geometry for event line
- green geometry for include region
- amber geometry for exclusion region
- no extra hue families unless they encode state

The neutral track layer should feel like telemetry, not illustration:

- small translucent envelopes instead of silhouettes
- anchor dots connected to short trail vectors
- one or two dashed paths that pass through event geometry
- labels set in the existing compact data-label style
- no shadows or glows that compete with video/evidence clarity

Recommended visual grammar:

- `data-track-anchor`: anchor dots that represent where runtime evaluates a
  tracked object.
- `data-motion-path`: short dashed paths that represent movement through a
  line or zone.
- `data-object-envelope`: abstract rounded rectangle, capsule, diamond, or
  ring that suggests "tracked thing" without category.
- `data-scene-plane`: neutral frame geometry.

## Copy Direction

Replace domain-specific defaults:

- `Click two points across a door, lane, or threshold.`
- `Remove reflections, public road, screens, or background motion.`
- `Line boundaries for directional counts through doors, lanes, gates...`
- `Loading bay include`
- `Road exclusion`

With neutral defaults:

- `Click two points across the path where tracked anchors should cross.`
- `Remove reflections, screens, repeated background motion, or irrelevant
  scene areas.`
- `Use line boundaries for any transition path where crossing matters.`
- `Use polygon zones for bounded areas where enter and exit matters.`
- `Observation area include`
- `Noise pocket exclusion`

Specific examples can exist in documentation or future templates, but the
default wizard should not privilege one industry.

## Accessibility And Responsiveness

- SVGs keep `role="img"`, `aria-label`, `title`, and `desc`.
- Labels remain readable at the current help-panel size.
- The illustration remains static.
- The default canvas works at desktop and mobile help-panel widths.
- The shape colors remain distinguishable in grayscale through stroke style:
  solid event line, solid event-zone outline, solid include polygon, dashed
  exclusion polygon.

## Acceptance Criteria

- The boundary/region guidance illustration contains no car/person/boat/bird/
  animal/category silhouettes.
- The illustration exposes neutral testable markers for tracked anchors,
  object envelopes, and motion paths.
- Event boundary default copy avoids door/lane/road/traffic-specific language.
- Detection region default copy avoids public-road/loading-bay-specific
  language.
- Help examples use generic scenario names or a balanced cross-domain wording.
- Existing scene authoring runtime payload tests still pass.
- Production build still passes.
- No backend/runtime code changes are required.

## Files Expected To Change

- `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`
- `frontend/src/components/guidance/guidance.test.tsx`
- `frontend/src/components/cameras/scene-guidance.ts`
- `frontend/src/components/cameras/CameraWizard.tsx`
- `frontend/src/components/cameras/CameraWizard.test.tsx`

No new dependencies are needed.
