# Argus UI Refresh Design

- Date: 2026-04-19
- Scope: Full frontend product refresh
- Status: Approved design, ready for implementation planning after user review

## Goal

Refresh the Argus frontend so it feels current, premium, and operationally credible while remaining faithful to the Argus brand system.

The refreshed product should feel:

- more modern
- less dated
- calmer and more premium
- structurally closer to best-in-class web applications
- still unmistakably a dark-mode command workspace

This is not a cosmetic repaint. The user explicitly approved structural layout changes across the full product.

## Why This Refresh Is Needed

The current frontend works functionally, but its visual language is still too close to an early “styled dashboard shell” rather than a refined product UI.

The main problems are:

- oversized header framing
- hero-style page intros occupying too much operational space
- heavy card treatment across nearly every screen
- persistent right-side layout tax even when no inspector is needed
- strong gradients and glow doing too much of the identity work
- configuration pages feeling visually behind the more ambitious operational pages

The History calendar bug reinforced the same broader issue: the current layout system is visually assertive but not yet disciplined enough.

## User-Approved Design Decisions

This design is based on these confirmed decisions:

- the refresh scope is the whole product, not just one or two pages
- structural layout changes are allowed
- the design should follow modern best-in-class web application UX/UI patterns
- the preferred visual direction is `A`: `Matte Command Rail`
- the preferred density target is `Balanced`
- the shell architecture is `Unified Left Rail Workspace`
- the refreshed product should use the best of the two provided logo directions, with:
  - the cleaner attached logo direction used as the default in-product lockup
  - only a very subtle atmospheric glow influence from the alternate logo reserved for sign-in or rare brand moments

## Brand Alignment

The refresh must follow the existing Argus brand documentation in `docs/brand/`.

The visual system should stay aligned with:

- obsidian and charcoal foundations
- controlled cerulean and violet accent use
- luminous off-white typography
- premium matte surfaces rather than glossy or neon-heavy treatment
- a vigilant, precise, enterprise-grade tone

For product UI specifically, this design follows the `Product/UI lockup` guidance, not the heavier `Hero glow lockup` treatment.

## Chosen Product Direction

### Visual Thesis

Argus should feel like a matte, premium control workspace: less “futuristic dashboard render,” more “serious enterprise platform with refined operational presence.”

### Content Plan

Across the product:

1. Persistent workspace shell
2. Content-first page plane
3. Utility bar for filters and actions
4. Conditional inspector or detail area only when useful

### Interaction Thesis

Motion should be restrained and product-like:

- subtle shell and nav state transitions
- calm panel reveals for inspectors and dialogs
- lightweight hover/focus movement on navigation and action controls

No ornamental motion loops or decorative page theatrics.

## Information Architecture

### Primary Shell

The refreshed product uses a three-zone shell:

1. **Icon rail**
   - very slim left-most rail
   - brand mark at top
   - primary workspace icons
   - persistent but quiet

2. **Context rail**
   - textual secondary rail beside the icon rail
   - grouped navigation and workspace context
   - houses the split between operational and configuration areas

3. **Main content canvas**
   - dominant workspace plane
   - utility bar at top of each page
   - full-width content unless a secondary inspector is actually needed

This replaces the current top-led header plus permanent management aside.

### Navigation Model

Navigation should be grouped into two families:

- **Operations**
  - Dashboard
  - Live
  - History
  - Incidents

- **Configuration**
  - Sites
  - Cameras
  - Settings

The shell should make this split explicit so the product feels intentional rather than mixed.

### Right-Side Inspector Rule

There should be **no permanent right rail** anymore.

Instead:

- pages that benefit from context detail can open or reserve a secondary inspector area
- pages that do not need it get the full content width

This is a core rule of the refresh, because the current layout wastes too much space on persistent secondary framing.

## Responsive Behavior

The shell must remain responsive without becoming a separate mobile design system.

### Desktop

- icon rail + context rail + content canvas
- inspector appears only when needed

### Laptop / narrower desktop

- icon rail remains
- context rail may collapse in width but stays visible
- inspector becomes more selective and may fold below content sooner

### Tablet / narrow widths

- context rail collapses into a drawer or overlay
- top utility bar remains page-local
- content becomes single-column where needed

The responsive system should be based on actual available space, not only viewport-wide visual assumptions.

## Visual System Refresh

### Surface Model

The product should move from “many framed cards” to “fewer, stronger planes.”

Rules:

- use larger matte surfaces for major page regions
- use lighter separators and softer region boundaries
- reserve heavier framing for truly distinct modules
- reduce repeated border-plus-shadow-plus-gradient combinations

### Color

The palette remains dark-first, but should be more disciplined:

- `#0A0D12` / `#151A22` style backgrounds remain primary
- cerulean is the main active accent
- violet is supporting, not co-equal
- status colors should stay controlled and enterprise-credible

### Typography

Typography must become more product-like and less splashy:

- page labels become smaller and more structural
- page titles remain strong but tighter
- support copy becomes shorter and more operational
- page-level text should sound like product UI, not launch copy

### Logo Usage

Use the cleaner approved logo direction as the in-product lockup.

Rules:

- default product shell uses the cleaner, flatter product/UI lockup
- no strong halo in the persistent application shell
- sign-in may keep one controlled atmospheric brand moment
- avoid decorative sparkle or glow artifacts in product UI

## Cross-App Layout Rules

These rules should apply consistently across the product:

1. Large marketing-style intros are replaced by compact labels and functional titles.
2. Page actions and filters live in a utility bar near the working surface.
3. Badges and status chips become quieter and more scan-friendly.
4. Right-side detail panels are conditional, not permanent.
5. Tables and forms should feel flatter, cleaner, and easier to scan.
6. Empty states should be informative and product-like, not placeholder text.

## Page-by-Page Design

### Dashboard

The Dashboard becomes a true content-first command workspace.

Changes:

- remove the oversized hero-style messaging block
- move query controls and status into a utility bar at the top of the content plane
- keep live tiles as the primary visual center
- make counts and state feel embedded rather than banner-like
- use a conditional inspector for active query/filter detail

The emotional center of the product remains live monitoring, but the page should feel more mature and less presentation-oriented.

### Live

The Live workspace should inherit the Dashboard shell language rather than looking like a separate surface family.

Changes:

- same utility-bar-first structure
- stronger emphasis on streams and overlays
- inspectors only for selected camera or stream detail
- shared layout rhythm with Dashboard so both feel like one operational family

At the moment, `/live` still resolves to the Dashboard implementation. The refresh should therefore treat Dashboard and Live as one shared operational workspace family first, and only separate them visually if the implementation pass introduces a distinct Live surface.

### History

History should become a broader analysis canvas.

Changes:

- move filters into the utility bar where possible
- make the chart plane visually dominant
- simplify the date-range module and remove unnecessary framing pressure
- treat supplementary analytics or filters as secondary modules, not co-equal “cards”

History should feel like an investigation workspace, not a decorative reporting screen.

### Incidents

Incidents should become evidence-first.

Changes:

- make snapshot/clip media and incident detail feel like the core artifact
- improve the balance between preview media, metadata, and actions
- use cleaner list/card hybrids rather than heavily ornamented content blocks
- ensure signed evidence actions remain obvious and high-trust

### Sites

Sites should become a lighter management workspace.

Changes:

- compact action header
- cleaner table treatment
- clearer empty states
- less decorative framing

This page should feel fast and confident, not over-designed.

### Cameras

Cameras remain the richest admin page, but the framing should improve.

Changes:

- stronger action header
- cleaner table and row actions
- flatter wizard shell
- better page rhythm between list mode and edit/create mode
- camera setup should still feel substantial, but less visually heavy

### Settings

Settings should stop acting like placeholder copy inside a hero shell.

Changes:

- turn it into a proper settings workspace scaffold
- align its structure with the new configuration family
- keep it intentionally spare, but real

### Sign-in

Sign-in remains brand-forward, but should be more refined.

Changes:

- preserve a premium brand moment
- use the approved product/UI lockup with a controlled atmospheric accent
- reduce the sense of a high-glow concept render
- make the sign-in card cleaner and more product-trustworthy

## Components And Shared Systems Likely To Change

The implementation should expect updates to these shared surfaces:

- app shell
- nav components
- utility bars / section headers
- badges / pills
- tables
- dialogs and wizards
- empty states
- page spacing and container rules
- sign-in layout

The goal is not page-by-page patchwork. The refresh should establish a reusable shared system first.

## Error Handling And UX States

The refresh should also improve how state is expressed.

Rules:

- loading states should be calmer and closer to the real layout
- empty states should explain what to do next
- degraded/error states should be clear without becoming visually alarming
- destructive actions should remain obvious and safe

## Testing And Verification

Implementation should verify both behavior and visual stability.

Expected verification areas:

- existing frontend tests continue to pass
- any updated layout-sensitive tests are adjusted intentionally
- responsive behavior works on desktop and narrow widths
- History calendar and other layout-sensitive controls remain uncropped
- the sign-in flow still works unchanged functionally
- Prompt 8 and Prompt 9 flows remain usable after the refresh

If practical, add a small number of focused tests around shared shell/layout behavior rather than trying to snapshot every page.

## Non-Goals

This refresh does not include:

- backend feature changes
- new product features beyond what is needed to support the refreshed UX
- logo redesign from scratch
- a new design system package or token framework unless implementation clearly needs it
- decorative motion for its own sake

## Recommended Implementation Strategy

Even though the design scope is full-product, implementation should still be staged:

1. shared shell and visual tokens
2. sign-in and core operational pages
3. configuration family
4. final consistency pass across empty states, dialogs, and secondary surfaces

This keeps risk manageable while still honoring the full refresh scope.

## Final Design Summary

Argus should evolve from a visually ambitious but somewhat early-stage command-center UI into a more mature product workspace.

The approved direction is:

- full-product refresh
- structural changes allowed
- `Matte Command Rail`
- `Balanced` density
- `Unified Left Rail Workspace`
- cleaner in-product logo usage
- calmer matte surfaces
- content-first operational pages
- flatter, stronger configuration pages

The result should feel like a real premium enterprise platform, not a concept dashboard.
