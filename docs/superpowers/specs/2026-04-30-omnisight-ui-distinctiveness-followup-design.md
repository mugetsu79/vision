# OmniSight UI Distinctiveness Follow-Up Design

Date: 2026-04-30
Branch: `main`
Checkpoint: `32c3f28`
Status: Approved for implementation planning

## Purpose

The current OmniSight redesign moved Vezor in the right direction, but it still reads too much like a generic dark SaaS console. The app now has better naming, the official 2D and 3D logo assets, and a reusable `OmniSightField`, but most screens still share the same composition: a rounded dark header card, a faint logo field, and stacked rounded panels.

This follow-up pass should make Vezor feel like a distinctive spatial intelligence product without weakening operator clarity.

## Source Findings

This spec addresses the current review findings:

1. The 3D OmniSight logo competes with the sign-in headline instead of acting as a deliberate hero-stage object.
2. The current motion is decorative drift, not a meaningful product animation.
3. Product pages repeat the same generic header-card pattern.
4. `/dashboard` redirects to `/live`, so there is no true OmniSight cockpit or overview.
5. Sites still feels like a placeholder table page.

It also formalizes the palette shift requested after review.

## North Star

Vezor should feel like an operator is moving through a single intelligence layer:

- **Entry** is cinematic and memorable.
- **Dashboard** is the product cockpit and overview.
- **Live** is a wall of scene portals.
- **Patterns** is a time and signal workbench.
- **Evidence** is a media-first review desk.
- **Scenes** is spatial setup and calibration.
- **Sites** is fleet geography and deployment context.
- **Operations** is infrastructure and edge-fleet control.

The product should remain premium, dark, precise, and operational. It should not become a neon sci-fi toy, a marketing landing page, or a dense table-only admin panel.

## Palette Discipline

Keep the Vezor brand palette, but use it with stricter hierarchy.

### Keep

- Obsidian and near-black canvas.
- Cool off-white primary text.
- Cerulean as the intelligence light.
- Violet as the secondary glow.

### Reduce

- Blue/violet gradients on every page header and card.
- Large translucent glass panels behind ordinary workflow copy.
- Violet as a default dashboard tint.

### Add

- Stronger neutral graphite surfaces.
- Sharper black zones for video, evidence media, and high-focus work.
- Status colors only when state matters:
  - green for healthy/live/success
  - amber for degraded/pending/attention
  - rose for failed/risk/destructive

### Target Ratios

Use these as visual ratios across authenticated product pages:

- 75% neutral dark surfaces
- 15% cerulean accents
- 5% violet accents
- 5% operational status colors

Sign-in and future marketing-style entry moments may use more violet, but workflow pages should not.

## Motion Model

Motion should communicate intelligence, navigation, and state changes. It should not exist only as background movement.

Required motion principles:

- Respect `prefers-reduced-motion`.
- Keep dense workflow screens calm.
- Use short, purposeful animation in the 180-320ms range for UI transitions.
- Use slower ambient motion only in sign-in and dashboard overview.
- Avoid animation behind dense text, tables, forms, and evidence media.

Recommended motion:

- Sign-in lens has layered motion: slow lens float, orbital ring sweep, subtle glint.
- Dashboard cards have spatial hover depth and a small active-light sweep.
- Nav active state feels like a lens focus moving between workspaces.
- Live scene selection or hover raises the portal without shifting layout.
- Evidence queue selection transitions into the evidence media plane.
- Ask Vezor results reveal quickly, then settle.

## Sign-In Design

The sign-in page should be the strongest brand moment.

### Current Problem

The 3D logo sits behind the H1 at common desktop viewport sizes. This makes the asset feel like accidental background decoration.

### Required Direction

Create a deliberate sign-in stage:

- Put the 3D OmniSight lens in its own visual zone.
- Keep the headline and body copy clear of the lens silhouette.
- Make the sign-in panel secondary but trustworthy.
- Use the official 2D lockup in the top-left.
- Use the 3D logo as a dimensional product object, not wallpaper.
- Add meaningful CSS motion around the lens and orbital rings.
- Keep the page usable at 375px, 768px, 1024px, and 1440px widths.

### Preferred Layout

Desktop:

- Top-left: 2D lockup.
- Left or lower-left: headline, product promise, three compact proof signals.
- Right/center-right: 3D lens stage with orbital rings and glints.
- Lower-right: sign-in panel, visually connected to the lens but not overlapping it.

Mobile:

- Lockup at top.
- Lens stage visible below lockup and above headline or between headline and sign-in.
- No overlap between lens, headline, and sign-in controls.

## Dashboard / Overview Design

Restore `/dashboard` as a real product cockpit.

### Current Problem

The route redirects to `/live`, so the authenticated product has no overview moment. Operators land directly in a workflow, which makes the product feel smaller.

### Required Direction

Create a Dashboard page that shows OmniSight as a connected platform:

- Live scene status summary.
- Active signals summary.
- Evidence queue summary.
- Pattern trend summary.
- Sites and edge-fleet status.
- Primary action links into Live, Patterns, Evidence, Scenes, Sites, and Operations.

The Dashboard should be dimensional but not a marketing page. It should be useful on first login and should make the rest of the product feel connected.

### Composition

Use a spatial cockpit layout:

- A strong top band with restrained 3D lens field.
- A large Live Intelligence preview panel.
- A right-side or lower instrument strip for Evidence, Patterns, and Operations.
- Site/fleet context represented as deployment nodes or summary tiles, not a plain table.

## Shared Composition System

The current page header pattern should be replaced with a small set of reusable page composition primitives.

### Required Primitives

- `WorkspaceHero`: only for sign-in and dashboard-level moments.
- `WorkspaceBand`: compact page intro band for workflow pages, mostly neutral graphite.
- `WorkspaceSurface`: neutral operational panel with limited accent usage.
- `MediaSurface`: pure or near-pure black media/evidence container.
- `InstrumentRail`: compact right-side metrics/actions rail.
- `StatusTone`: shared semantic tone mapping for healthy, attention, danger, muted, and accent.

These do not need to be over-engineered as a full design-system package, but repeated ad hoc gradient strings should be reduced.

## Page-Specific Direction

### Live Intelligence

Live should feel like scene portals first.

Required changes:

- Remove the generic header-card feeling.
- Make video tiles the visual center.
- Use a compact command strip for Ask Vezor and telemetry state.
- Move diagnostics below or inside each scene tile as secondary information.
- Keep status truthful.
- Use sharper black media zones.
- Let scene hover/focus feel like a portal raising into focus.

### History & Patterns

Patterns should feel like time exploration.

Required changes:

- Make chart and bucket detail the primary composition.
- Treat filters as a workbench toolbar, not duplicate side-panel controls.
- Reduce export prominence; it is a utility, not a feature hero.
- Use neutral surfaces with cerulean for active time, selected bucket, and chart emphasis.
- Keep speed/count details as metrics, not product identity.

### Evidence Desk

Evidence should be media-first.

Required changes:

- Keep queue left, evidence media center, facts/actions right.
- Make media black and dominant.
- Make review state clear with semantic color.
- Avoid blue-purple wash around evidence media.
- Add a stronger selected-record transition or state.

### Scene Setup

Scenes should feel like spatial setup, not camera CRUD.

Required changes:

- Keep the table for scanability, but add a scene setup summary or topology band.
- Use “Scene Setup” as the page frame.
- Emphasize source stream, model, privacy, boundaries, and calibration as a setup sequence.
- Keep RTSP/camera wording where technically needed.
- Reduce generic table-only feel.

### Sites

Sites needs the largest conceptual lift.

Required changes:

- Replace the placeholder-feeling repeated “Sites / Sites” header.
- Present sites as deployment contexts.
- Show site cards or rows with time zone, scene count, configured scenes, and edge/fleet hints when available.
- Keep a table only if it has enough operational density.
- Empty state should invite creating the first deployment location.

### Operations

Operations can remain dense, but should use clearer system hierarchy.

Required changes:

- Distinguish fleet summary, nodes, bootstrap, workers, and stream diagnostics visually.
- Use status colors semantically.
- Keep command blocks neutral and highly legible.
- Avoid presenting every section as the same rounded panel.

## Accessibility And Responsive Requirements

- All interactive elements must have visible focus states.
- Motion must respect `prefers-reduced-motion`.
- Text must not overlap decorative elements.
- Media/evidence images must keep useful alt text.
- Forms must preserve visible labels.
- No horizontal overflow at 375px.
- Verify at 375px, 768px, 1024px, and 1440px.

## Testing And Verification

Implementation should include:

- Unit tests for any new composition/tone helpers.
- Existing page tests updated for Dashboard restoration and new labels.
- Visual/browser checks for sign-in desktop/mobile.
- Browser checks for authenticated routes with seeded local dev data when available.
- CSS check that reduced-motion disables ambient animation.
- Build, lint, and frontend tests.

## Non-Goals

- No backend API changes.
- No auth flow changes.
- No new 3D rendering dependency unless separately approved.
- No full route rename migration; `/cameras`, `/history`, `/incidents`, and `/settings` may remain technical routes.
- No redesign of the official logo assets.
- No broad copy rewrite outside the UI surfaces touched by this follow-up.

## Success Criteria

The pass is successful when:

- The sign-in page shows the 3D lens as an intentional hero object with no text collision.
- `/dashboard` is a useful OmniSight overview, not a redirect.
- Each major page has a distinct workflow composition.
- Product pages use neutral graphite/black surfaces as the dominant visual language.
- Cerulean and violet accents feel intentional and scarce.
- Sites no longer feels like a placeholder table page.
- Existing workflows remain usable and testable.
