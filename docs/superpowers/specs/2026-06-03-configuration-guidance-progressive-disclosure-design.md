# Configuration Guidance Progressive Disclosure Design

Date: 2026-06-03
Status: Implemented on `codex/guidance-progressive-disclosure`

## Product Goal

Keep OmniSight configuration understandable without making the interface feel
heavy. The previous guidance pass added useful content, but too much of it is
visible by default. Operators should see compact forms first, then open richer
explanations only when they need help.

The target operator promise is:

1. Experienced operators can move through Scene setup and Control Plane
   Configuration without reading instructional panels.
2. New operators can still discover the same guidance through a familiar
   circular `i` info affordance.
3. Calibration gets a clear graphical explanation for source points,
   destination points, measured distance, event boundaries, and regions without
   crowding the primary workflow.
4. Help remains accessible from keyboard and touch devices, and animations
   respect reduced-motion preferences.

## Recommendation

Do this as a focused guidance-density correction now, not as part of the broader
UI/UX polish bucket.

This is a direct follow-up to a recent implementation and has clear boundaries:
replace always-visible guidance with on-demand help, add a calibration visual
explainer, and keep runtime semantics unchanged. Broader UI/UX polish can still
cover Live density, visual hierarchy, and overall product polish later.

## Approach Options

### Option A: Focused Progressive Disclosure Pass

Replace visible guidance panels and long field descriptions with compact info
buttons. Add a reusable info disclosure component and a calibration illustration
that appears inside the disclosure panel.

This is the recommended option because it fixes the current pain directly while
preserving the guidance content already written.

Trade-offs:

- Lowest product risk.
- Clear implementation scope.
- Requires some component reshaping in Scene setup and Configuration editor.
- Does not attempt broader redesign.

### Option B: Fold Into Broader UI/UX Polish

Leave the current guidance in place until a wider UI polish pass redesigns the
configuration surfaces.

Trade-offs:

- Allows a more holistic redesign later.
- Keeps the heavy interface in the product while field testing continues.
- Increases the chance the guidance correction becomes tangled with unrelated
  layout and visual hierarchy work.

### Option C: Copy Reduction Only

Shorten all visible text but leave the current panel structure.

Trade-offs:

- Fastest implementation.
- Does not solve the core density problem.
- Loses useful explanations instead of moving them behind an affordance.

## UX Principles

- Default view should be compact: labels, controls, validation states, and only
  critical one-line hints.
- Rich guidance should live behind a circular `i` icon button with an accessible
  name such as "Show calibration help".
- Popovers must open on click or tap. Do not rely on hover for essential help.
- Popovers must be keyboard reachable, closable with Escape, and restore focus
  to the trigger.
- On narrow screens, the same trigger may open a full-width floating panel or
  modal-like drawer so text does not overflow.
- Animation should explain a concept, not decorate the page.
- Animation should use opacity and transform, stay under roughly 300 ms per
  transition, and stop rather than looping forever.
- Respect `prefers-reduced-motion: reduce` by showing a static diagram with the
  same labels and relationships.

## Information Architecture

### Field Help

Field labels should own their help trigger:

```text
Transport mode  (i)
[ select control ]
```

The always-visible field help row should disappear except where a short hint is
needed to prevent a mistake. The current detailed content remains available in
the popover:

- details
- safe default
- runtime effect
- examples
- common mistakes

### Section Help

Section-level guidance should move from full cards to a compact header trigger:

```text
Calibration  (i)
```

The existing `GuidancePanel` content can become the popover body. The Step
context sidebar should keep progress and readiness information visible, but the
long section explanation should be behind the `i` trigger.

### Calibration Visual Help

Calibration deserves a visual explainer because source and destination points
are spatial concepts. The graphical explanation should live in the calibration
info disclosure and be reusable in the Homography editor.

The primary visual should show:

- a left "camera image" plane with perspective
- a right "top-down" plane
- four numbered source points `S1-S4`
- four matching destination points `D1-D4`
- faint connector lines from source to destination
- a measured-distance ruler on the destination plane
- optional mini states for event line, polygon zone, include region, and
  exclusion region

The animation should be stepped:

1. Source points appear in order.
2. Matching destination points appear in the same order.
3. Connectors briefly emphasize that `S1` maps to `D1`, `S2` maps to `D2`, and
   so on.
4. The measured-distance ruler appears.
5. Optional overlays show where event boundaries and detection regions belong
   after calibration.

The v1 interaction should play a short explanatory motion when the help opens.
The static reduced-motion version should show all labels and relationships at
once. Manual step controls can be added later if field testing shows operators
need them.

## Component Model

Create a reusable guidance disclosure component:

```ts
type GuidanceDisclosureProps = {
  id: string;
  label: string;
  guidance: FieldGuidance | SectionGuidance;
  tone?: "info" | "warning";
  children?: React.ReactNode;
};
```

Responsibilities:

- render the circular `i` trigger
- manage open/closed state
- expose an accessible button label
- render title, summary, details, examples, safe default, runtime effect, and
  common mistakes
- close on Escape and outside click
- use click/tap, not hover
- support embedded custom content such as the calibration illustration

Create a reusable calibration illustration:

```ts
type CalibrationFlowIllustrationProps = {
  mode?: "source-destination" | "boundaries" | "regions";
  animated?: boolean;
};
```

Responsibilities:

- render SVG planes, points, connectors, ruler, and optional boundary/region
  overlays
- expose meaningful text labels for tests and screen readers
- use CSS motion only when reduced motion is not requested
- avoid external image or video assets

## Scene Setup Changes

### Camera Wizard

- Keep calibration still status, readiness checklist, validation errors, and
  primary controls visible.
- Move the large "Speed accuracy" explanatory card behind a calibration `i`
  trigger.
- Replace the Step context `GuidancePanel` with a compact info trigger.
- Keep readiness checklist visible for Calibration because it is actionable
  status, not descriptive help.

### Homography Editor

- Put info triggers beside "Source points", "Destination points", and
  "Reference distance (m)" labels.
- Remove always-visible explanatory paragraphs that duplicate the info content.
- Add the calibration visual explainer inside the "Source points" and
  "Destination points" help disclosure, or provide one shared "How calibration
  maps points" info trigger at the Homography editor header.

### Event Boundaries And Detection Regions

- Keep empty states and validation messages visible.
- Move explanatory examples and common mistakes behind the section `i`.
- Add optional static/animated mini diagrams in the section help for:
  - line crossing
  - polygon zone
  - include region
  - exclusion region

## Control Plane Configuration Changes

### Profile Editor

- Replace the full `GuidancePanel` near the top of the editor with a compact
  info trigger beside the profile kind/title.
- Move field help into label rows, using the circular `i`.
- Keep capability warnings, validation status, missing-secret warnings, and
  runtime impact visible because they are state, not help copy.

### Bindings And Effective Runtime Panels

- Keep actual binding rows, desired/applied hashes, and runtime status visible.
- Move explanatory text about scope precedence, desired state, applied state,
  and diagnostics behind section-level info triggers.

## Accessibility

- Info triggers are real `<button>` elements.
- Triggers have explicit accessible names.
- Popover panels have stable ids and `aria-controls`.
- Use `aria-expanded` on triggers.
- Escape closes the panel.
- Keyboard focus returns to the trigger after close.
- If a popover contains step controls, those controls are keyboard reachable.
- Text in panels must wrap at mobile widths.
- The calibration illustration includes text alternatives and does not rely on
  color alone.
- Reduced motion users get a static diagram.

## Visual Direction

The product remains dark, operational, and compact. Use the existing OmniSight
surface vocabulary:

- dark panel backgrounds
- thin borders
- blue/cyan for source/camera image
- violet for destination/top-down plane
- green for ready/healthy/calibrated states
- amber only for caution
- lucide `Info` icon for the trigger

Avoid:

- big instructional cards in the primary form flow
- hover-only tooltips for essential guidance
- looping decorative animation
- animated width, height, top, or left properties
- new color themes or broad redesign

## Testing

Frontend tests should verify:

- field hints are not visible by default when compact mode is used
- clicking an info trigger reveals the details
- Escape closes the disclosure
- section guidance no longer renders as an always-visible heavy card
- calibration illustration renders source points, destination points,
  connectors, and measured distance
- reduced-motion mode renders a static complete diagram
- Camera Wizard still shows readiness checklist and validation state
- Profile Editor still exposes `aria-describedby` for helped fields
- build passes

## Out Of Scope

- Runtime behavior changes.
- New backend schema.
- A full redesign of Scene setup or Configuration.
- Rewriting all guidance copy.
- Real camera-frame animation or generated bitmap/video assets.
