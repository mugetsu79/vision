# Vezor OmniSight UI Redesign Design

Date: 2026-04-28
Branch: `codex/source-aware-delivery-calibration-fixes`
Status: Design approved for specification; implementation not started.

## Purpose

Vezor should read as an OmniSight platform: a spatial intelligence layer for many live environments, not a traffic counter or camera configuration tool. Cameras, detections, counting, evidence, history, and edge workers are capabilities underneath a broader product promise: Vezor sees, connects, interprets, and helps operators act across scenes.

The current UI is coherent and usable, but it is too flat. Most surfaces use similar dark panels, soft borders, and blue-gray copy, so the product feels like a generic dark SaaS console. The redesign should introduce a distinctive Vezor visual language without weakening operational clarity.

## North Star

Use the product mark as the visual metaphor: an OmniSight lens. The UI should feel like the operator is navigating around one spatial intelligence object whose layers include live scenes, evidence, history, configuration, and fleet operations.

The accepted direction is **Luminous Spatial Intelligence**:

- Obsidian canvas with cerulean-to-violet lens light from the logo.
- Dimensional glass and depth, not flat card stacks.
- Bold 3D brand moment at entry and overview.
- A faint living hint of the OmniSight lens in the app shell.
- Quiet, crisp workflow panels for real operator tasks.

The tone should be premium, watchful, and precise. It should not become a sci-fi toy, neon dashboard, or traffic-specific visualization.

## Depth Model

### Entry

The sign-in and future overview experience may use the full brand expression:

- 3D OmniSight lens inspired by the logo.
- Orbital rings and spatial light fields.
- Environmental scene hints around the lens.
- Strong product promise and minimal sign-in friction.

This is where Vezor can feel bold and memorable.

### Overview

Overview surfaces should retain dimensionality while becoming more product-like:

- Faint orbital lens field in the top/right background.
- Layered modules for Live Intelligence, Evidence, History, Scene Setup, and Edge Fleet.
- Cards that feel like surfaces in space, not separate marketing tiles.
- Route transitions that suggest moving around the same intelligence layer.

### Workflows

Dense operational workflows should stay calm:

- The lens motif should be barely visible, if present.
- Depth should come from elevation, contrast, focus, and state transitions.
- Tables, forms, calibration canvases, evidence review, and command output must remain readable.
- No decorative animation behind dense text or critical controls.

## Product Language

Use broad OmniSight vocabulary by default. Use hardware or traffic-specific words only where they are technically necessary.

Preferred terms:

- OmniSight Platform
- Live Intelligence
- Scenes
- Signals
- Events
- Evidence
- Review Queue
- Patterns
- Edge Fleet
- Models
- Spatial intelligence
- Operational awareness

Terms to reduce or avoid in prominent UI:

- Car counting
- Traffic analytics
- Camera management as the primary product frame
- Delivery truth
- Dynamic stats
- Command surface
- Raw scene
- Native unavailable
- Desired state

These technical terms may still appear in diagnostics, tooltips, or advanced sections when the operator needs exact runtime detail.

## Naming Changes

Recommended route and page naming:

- `Live` remains in nav, but page title becomes **Live Intelligence**.
- `History` becomes **Patterns** or **History & Patterns** in page title.
- `Incidents` becomes **Evidence Desk** in nav and page title.
- `Cameras` becomes **Scenes** in nav and **Scene Setup** in page title, with camera-specific fields inside.
- `Settings` should become **Operations** in nav and eventually route naming.

Recommended component copy:

- “Live command surface” -> “Live Intelligence”
- “Dynamic stats” -> “Signals in View”
- “Command query” -> “Ask Vezor”
- “Query scope” -> “Scope”
- “Query Vezor” -> “Ask Vezor”
- “Apply query” -> “Apply”
- “Current command resolution” -> “Resolved Intent”
- “No cameras are configured yet.” -> “No scenes are connected yet.”
- “No cameras yet.” -> “No scenes connected yet.”
- “Count boundaries” -> “Event boundaries”
- “Line for pass-by counting” -> “Line boundary for crossing events”
- “Polygons count entries and exits” -> “Zones create enter and exit events”
- “Native unavailable” -> “Direct stream unavailable”
- “Delivery truth” -> “Stream diagnostics”
- “Desired workers” -> “Planned workers”
- “Running workers” remains acceptable.

Placeholders should be realistic and product-neutral:

- `only show cars` -> `show people near restricted zones`
- `forklift, pallet jack` can stay as an industrial example, but should not be the only suggested vocabulary.
- `edge-kit-01` can stay in edge bootstrap because it is practical.
- `rtsp://camera.local/live` can stay in technical setup fields.

## Visual System

### Color

The current palette is close but too one-note. Keep the dark foundation, but define stronger roles:

- Canvas: near-black obsidian, not pure black.
- Surface: deep navy/graphite with transparency only where it supports depth.
- Primary light: cerulean from the logo.
- Secondary light: violet from the logo.
- Operational success: soft green.
- Attention: amber.
- Risk: muted red/rose.
- Neutral text: cool off-white, blue-gray secondary, lower-contrast tertiary.

Avoid making every page blue-purple. The accent should act like lens light, not a wash over all components.

### Shape and Elevation

The app currently uses many large rounded rectangles. Tighten this:

- Shell and hero objects may use larger radii.
- Dense cards, tables, and panels should use 8-16px radii.
- Buttons should be compact and clear, with icons where useful.
- Repeated items should feel structured, not pill-heavy.
- Elevation should use layered shadows and subtle borders, not only border opacity.

### Background

Introduce a reusable `OmniSightField` visual primitive:

- Bold mode for sign-in and overview.
- Subtle mode for app shell background.
- Disabled or near-invisible mode for dense workflows.
- Respects `prefers-reduced-motion`.
- Does not sit behind form text, tables, command output, or evidence media.

This should be implemented with code-native CSS/Canvas/WebGL where possible. If a 3D rendered asset is used, it should be a supporting asset, not baked UI text.

### 3D Rendering

Use 3D selectively:

- A central lens object inspired by the logo.
- Orbital rings with slow, faint motion.
- Floating scene/evidence/history surfaces in overview states.
- Light glints and depth tied to user navigation.

Do not use 3D for every page. Workflow screens should preserve speed, clarity, and text legibility.

## Motion Model

Motion should make the app feel navigable, not decorative.

Recommended interactions:

- Route transitions: subtle fade/slide/depth shift between workspaces.
- Active nav: lens-light sweep or glow that follows the selected workspace.
- Overview cards: hover reveals depth and small parallax.
- Live scene tiles: selected scene expands or raises into focus.
- Evidence queue: selected record transitions into evidence detail.
- Command/intent results: resolve with a short reveal, then settle.

Rules:

- Respect `prefers-reduced-motion`.
- Avoid constant movement near dense text.
- Keep animation duration short and easing calm.
- No layout shift during route changes.

## Page-by-Page Design

### Sign-In

Make the entry page the strongest brand surface:

- Product lockup and OmniSight lens are first-viewport signals.
- Headline should make the broad promise clear.
- Suggested headline: “OmniSight for every live environment.”
- Supporting copy: “Vezor connects scenes, models, events, evidence, and edge operations into one spatial intelligence layer.”
- Sign-in panel stays simple and secure.

### App Shell

The shell should become the stable cockpit:

- Left rail remains the primary anchor.
- Context rail stays useful but should feel lighter and more spatial.
- Add a faint living OmniSight field in the top/right background.
- Page container should not feel like a card inside another card.
- Use full-width page bands or layered surfaces rather than nested large cards.

### Live Intelligence

Live should sell the product promise without losing operational utility:

- Page title: “Live Intelligence”
- Agent input becomes “Ask Vezor”.
- Right panel becomes “Resolved Intent”.
- Stats panel becomes “Signals in View”.
- Scene tiles should feel like live portals: video first, signal overlays second, diagnostics third.
- Heartbeat/running state must stay truthful; do not invent worker state.

### History & Patterns

History should feel like pattern discovery, not only chart filtering:

- Page title: “History & Patterns” or “Patterns”.
- Toolbar copy should emphasize time, scenes, signals, and evidence.
- Export module should be quieter and more utility-like.
- Bucket detail should feel like drilling through time.
- Speed, counts, and boundary events are metrics, not product identity.

### Evidence Desk

Evidence Desk is already the strongest product name. Improve the hierarchy:

- Queue on the left, evidence in the center, facts/actions on the right.
- Emphasize review state and decision state.
- Use “Review Queue” for list sections.
- Use “Evidence” for media.
- Use “Facts” for structured metadata.
- Avoid “incident facts kept in one triage workspace” style copy; it sounds internal.

### Scene Setup

The Cameras page should be reframed as scene setup:

- Page title: “Scene Setup”
- Hardware-specific labels remain where needed: RTSP URL, camera, source capability.
- Calibration copy should explain spatial understanding broadly.
- Event boundaries replace count boundaries.
- Browser delivery and native ingest should move into an advanced stream diagnostics tone.

### Operations

Operations should feel like fleet control and runtime confidence:

- Page title: “Edge Fleet & Operations” or “Operations”.
- Replace “delivery truth” with “stream diagnostics”.
- Replace “desired state” with “planned state” where user-facing.
- Preserve honest runtime semantics: if per-worker heartbeat is not reported, show `not reported`, `unknown`, `stale`, or `offline` explicitly.
- Keep copied commands prominent and copyable.

## Information Architecture

Primary navigation should communicate product scope:

- Live
- Patterns
- Evidence
- Scenes
- Sites
- Operations

If route changes are deferred, nav labels can change before URL paths. For example, `/settings` can temporarily render as Operations while a later migration updates route paths.

## Accessibility and Performance

The redesign must preserve operational accessibility:

- Text contrast must stay high.
- Live video and evidence media cannot be obscured by decorative overlays.
- Motion must respect `prefers-reduced-motion`.
- 3D rendering must not block app interaction or slow low-power clients.
- Background animation should pause or simplify on low-power devices.
- All buttons and controls remain keyboard accessible.

## Implementation Approach

Implement in phases.

### Phase 1: Product Language and Shell Tokens

- Add or refine design tokens for the Vezor visual system.
- Rename high-level page titles and user-facing copy.
- Introduce shared surfaces for page headers, panels, badges, empty states, and diagnostics.
- Keep behavior unchanged.

### Phase 2: OmniSight Field and Entry Redesign

- Build the `OmniSightField` visual primitive.
- Redesign sign-in around the bold lens.
- Add faint shell background mode.
- Add reduced-motion behavior.

### Phase 3: Dynamic Browsing

- Add route transition wrapper.
- Improve active nav motion.
- Add selected-card depth interactions where useful.
- Keep dense workflow motion subtle.

### Phase 4: Page-Specific Polish

- Live Intelligence scene tiles and “Ask Vezor”.
- Evidence Desk queue/detail hierarchy.
- History & Patterns chart and drilldown polish.
- Scene Setup calibration and event-boundary language.
- Operations runtime and stream diagnostics language.

## Testing and Verification

Use visual and behavioral verification:

- Desktop browser review of Sign-In, Live, History, Evidence Desk, Scene Setup, Operations.
- Mobile or narrow viewport review of shell and dense workflows.
- Unit tests for copy changes where current tests assert headings or labels.
- Build and lint.
- Browser interaction checks for route transitions, nav hover/focus, scene selection, evidence queue selection, wizard navigation, and command resolution.

Visual QA should check:

- Does the entry page clearly say OmniSight?
- Does the app still feel readable after adding depth?
- Are traffic/counting terms demoted?
- Does the shell feel alive but not distracting?
- Are runtime states honest and not overpromised?

## Implementation Defaults

Use these defaults for the first implementation pass:

- Do not add `/overview` in the first implementation pass.
- Use `History & Patterns` first; move to `Patterns` after users understand the scope.
- Use `Scenes` in nav immediately and `Scene Setup` as the page title; keep `/cameras` only as the route path for this pass.
- Start with CSS/Canvas for the shell field; use Three.js only for a bold entry/overview render if performance remains good.
