# OmniSight Whole UI/UX Review Design

Date: 2026-06-03
Status: Proposed
Branch context: `codex/omnisight-ui-ux-polish` at `eb1acaf2`

## Purpose

This spec turns the June 3 taste-led polish pass into a stronger product-wide UI/UX reset. The previous implementation improved pieces of Operations, but it did not create enough visible change: the Dashboard still leads with a moving 3D logo object, and Operations still feels like one continuous dense control slab.

The next implementation should preserve runtime truth and operator density, but change the default scan path, surface hierarchy, brand behavior, and route composition enough that the product feels materially different when rebuilt on a MacBook.

## Inputs Used

- Local `taste-skill/`, routed through `taste-skill/SKILL.md`
- Taste direction: `dashboards` primary, with `dark-luxe` restraint and `swiss-system` grid discipline
- Product Design plugin route: audit plus context playback, grounded in local screenshots
- `ui-ux-pro-max` design-system search for dark operator dashboards, motion accessibility, and realtime evidence timelines
- `docs/superpowers/specs/2026-06-03-taste-led-omnisight-ui-ux-polish-design.md`
- `docs/superpowers/plans/2026-06-03-taste-led-omnisight-ui-ux-polish.md`
- `docs/brand/omnisight-ui-spec-sheet.md`
- `docs/superpowers/specs/2026-04-30-omnisight-ui-distinctiveness-followup-design.md`

## Evidence

Local screenshot evidence was captured under:

- `/tmp/omnisight-whole-ui-ux-review`
- `/tmp/omnisight-polish-audit-2`

The capture used mocked auth and seeded API fixtures so the review could inspect authenticated UI structure without depending on live backend state. The first Operations and Deployment fixture pass exposed missing fixture fields; the corrected pass rendered those pages cleanly and is recorded in `/tmp/omnisight-whole-ui-ux-review/operations-deployment-fixed-audit.json`.

### Quantitative Snapshot

Desktop route metrics from the visual audit:

| Route | Panel-like surfaces | Visible interactive controls | Lens present |
| --- | ---: | ---: | --- |
| Sign-in | 10 | 1 | Yes |
| Dashboard | 55 | 28 | Yes |
| Live | 86 | 45 | No |
| Patterns | 48 | 35 | No |
| Evidence | 61 | 27 | No |
| Sites | 29 | 21 | No |
| Scenes | 57 | 31 | No |
| Operations | 211 | 102 | No |
| Deployment | 62 | 29 | No |

The key read: Operations is not merely dense. It is structurally overloaded. It has more than three times the surface count of Evidence and over three times the interaction count, while all sections use very similar dark rounded chrome.

## High-Confidence Findings

### 1. The 3D Brand Object Is Still Wrong For Default App Use

Dashboard and Sign-in still render `OmniSightLens` with `/brand/3d_logo_no_bg.png`. The mark has perpetual ambient animation and pointer-driven hover tilt. It reads as a decorative product object, not as stable app identity.

Recommendation:

- Remove the moving 3D sphere from all default workflow and entry experiences.
- Use a flat 2D mark or lockup as the normal app identity.
- If the dimensional asset remains anywhere, make it an opt-in static brand/marketing artifact, not a pointer-reactive app control.
- Delete or disable `lens-breathe` and `useLensTilt` for the app experience.

### 2. Dashboard Still Opens Like A Product Hero

The first Dashboard viewport is visually anchored by the 3D lens and card metrics. It does show real operational state, but the composition still says "overview hero" before it says "command surface."

Recommendation:

- Replace the hero/lens stage with a command overview band.
- First viewport should answer: what needs attention, what is live, what changed, and where should the operator go next.
- Use one horizontal attention ledger plus one primary status board, not a hero plus detached cards.

### 3. Operations Has Runtime Truth But No Scan Discipline

The Operations page contains useful material: attention stack, scene readiness, worker state, stream diagnostics, deployment nodes, configuration, model runtimes, installer guidance. The problem is default exposure and equal visual weight.

Recommendation:

- Split Operations into explicit chapters with stronger section dividers and a sticky section index.
- Default view should contain only attention, scene readiness summary, and worker board.
- Move configuration, installer guidance, and deep diagnostics into lower-priority tabs, drawers, or route-adjacent panels.
- Keep all hashes, runtime reports, config winners, admission state, and command copy available, but not all visible at once.

### 4. Evidence And Live Show The Direction To Preserve

Evidence works better because it separates queue, selected evidence media, and facts. Live works better when video/telemetry slabs remain visually primary. Both routes still have panel repetition, but their primary surfaces are clear.

Recommendation:

- Preserve black media/evidence slabs.
- Do not add decorative motion or brand overlays to video/evidence areas.
- Use Evidence as the pattern for Operations: queue/status rail, selected workboard, facts/detail rail.

### 5. Shared Surface Language Needs Harder Rules

Repeated rounded cards, pill badges, and `WorkspaceBand` page headers make multiple routes feel like variants of the same kit. This is especially visible on Dashboard, Operations, Live, and Deployment.

Recommendation:

- Establish a surface hierarchy:
  - command bands for page-level status
  - ledgers for attention and next actions
  - media slabs for video/evidence
  - row boards for workers, nodes, and scenes
  - drawers/disclosures for hashes and diagnostics
  - compact cards only for repeated entities where enclosure helps
- Cap default cards inside cards.
- Reduce pill use to semantic state only.

## Product Direction

The desired product should feel like a quiet operator workstation: dark, precise, dense, and sober. Premium quality should come from grid, contrast, typography, and useful surfaces rather than glows, 3D motion, or many rounded containers.

Taste settings for the next implementation:

- Dashboard style: primary
- Dark luxe: only for controlled material and light restraint
- Swiss system: grid, alignment, section rhythm, typographic labels
- Motion intensity: low, state-driven, never perpetual branding
- Visual density: high, but grouped more calmly

## Route-Level Recommendations

### Sign-in

- Remove `OmniSightLens`.
- Use static 2D lockup and a still brand field.
- Keep sign-in concise; no pointer-reactive logo.
- Replace purple/violet radial glow emphasis with a restrained dark material stage.

### Dashboard

- Remove the 3D hero object.
- Rename first composition mentally from "hero" to "command overview."
- Show attention, live scenes, evidence queue, fleet health, and recent pattern change as one instrument band.
- Replace the six route cards with a compact workspace switchboard or command list.

### Live

- Preserve video-first clarity.
- Reduce secondary panel chrome around tile controls and signal trend.
- Keep overlays readable and never obscured by decorative motion.
- Right rail can become a tighter "signals in view / resolved intent / selected scene" inspector.

### Patterns

- Fix heading hierarchy: avoid multiple `h1` equivalents in the workbench.
- Treat the chart as the primary surface, with filters as a compact toolbar.
- Move export and advanced filters into a side rail or drawer.

### Evidence

- Keep the queue / selected media / facts structure.
- Increase media slab dominance relative to surrounding panels.
- Keep accountability disclosures, but reduce nested border repetition.

### Sites

- Sites currently has the lowest overload, but it is too card-list based.
- Add deployment relationship density: scene count, node assignment, unresolved setup issues.
- Use a table or row group on desktop, cards only on mobile.

### Scenes

- Scene setup needs stronger sectioning and more than one heading.
- Desktop should feel like inventory plus setup workflow, not one compressed table.
- Preserve camera setup breadth, but group source/model/privacy/boundaries/calibration into clear setup phases.

### Operations

- Highest priority page.
- Use this default order:
  1. Attention command strip
  2. Scene readiness summary
  3. Worker board
  4. Stream diagnostics
  5. Deployment nodes
  6. Configuration
  7. Installer guidance
- Make only items 1-3 expanded by default.
- Configuration should not dominate the default viewport.
- Installer guidance should feel like help/reference, not active operations.

### Deployment

- Separate install packages from live node health.
- Put deployment nodes before installer package reference when a tenant already has nodes.
- Keep pairing flows visible, but reduce package card prominence.

## Accessibility And Motion Requirements

- No perpetual decorative logo animation.
- No pointer-reactive 3D logo hover in default product UI.
- `prefers-reduced-motion` should not be a degraded fallback; it should be the baseline quality.
- Heading hierarchy must be sequential and route-specific.
- Focus states remain visible on all command controls.
- Visual QA must cover 375, 768, 1024, and 1440 px widths.

## Success Criteria

- Rebuilding the branch on the MacBook shows obvious visual differences on Sign-in, Dashboard, and Operations.
- No default route renders a moving 3D brand sphere.
- Dashboard first viewport reads as an operational command surface.
- Operations default desktop surface count is materially reduced from the audited 211 panel-like surfaces.
- Operations default visible controls are materially reduced from the audited 102 controls.
- Operators can identify the next action on Operations in under 10 seconds.
- Video and evidence surfaces remain clean, dark, and unobscured.
- Existing runtime labels for stale, unknown, awaiting telemetry, and not reported are preserved.
- Focused Vitest coverage and Playwright visual/audit coverage pass.
