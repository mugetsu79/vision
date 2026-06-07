# Operator Focus Consistency Design

Date: 2026-06-07
Status: implemented
Related plan: `docs/superpowers/plans/2026-06-07-operator-focus-consistency.md`
Related FleetOps plan: `docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md`

## Product Design Playback

The operator workspace should not silently choose a site, scene, vessel, queue,
or diagnostic context. Every page that can show scoped operational detail must
start from an explicit operator focus. The page may show searchable selectors,
counts, and empty guidance, but it must not render the first matching row,
card, chart, support workflow, or FleetOps site workflow by default.

The visual source remains the current Vezor dark command workspace. Use the
existing app shell, `WorkspaceBand`, `WorkspaceSurface`, form controls, and
scene focus patterns. Interactivity is full: search, selection, clearing,
pagination, edit dialogs, and scoped mutations must work.

## Goals

1. Make empty selection mean empty detail across scene-heavy pages.
2. Use searchable selectors instead of raw long multi-selects or long default
   lists.
3. Keep History/Patterns stable while filters refetch; no full-page blink when
   a scene filter changes.
4. Add searchable, paginated Sites inventory with 10, 25, or 50 visible entries
   per page.
5. Add edit-site behavior using the existing core site update API.
6. Keep FleetOps Evidence, Support, and Onboarding from binding to the first
   vessel/site until the operator chooses one.

## Non-Goals

- Do not change runtime detector semantics.
- Do not add traffic/public-space runtime, demos, UI, or migrations.
- Do not add home-lab pack UI or `lab_only` status.
- Do not add proprietary carrier SDKs, payment processors, or accounting
  integrations.
- Do not move maritime nouns into core.
- Do not add backend History site filters unless existing camera-derived
  frontend filtering is insufficient.

## Operator Focus Rule

For any page that contains scoped detail:

- Empty selection and empty search show a neutral empty state, not the first
  item.
- Search text is an explicit focus and may show matching rows/cards.
- Checkbox/radio selection is an explicit focus and should override the search
  result set for the detail area.
- Clearing selection returns the detail area to empty guidance.
- Side-effect buttons remain disabled until an explicit site/vessel scope
  exists.

## Page Requirements

### Live

The scene browser remains organized by site, with search and checkboxes. The
active scene grid is empty until search, explicit selection, or an applied
Vezor intent creates scope.

### Patterns / History

The raw scene multi-select is replaced with a searchable scene selector. With no
selected scene, History does not load series/classes and shows a choose-scene
empty state. When a selected scene changes, the workbench keeps its prior chart
surface visible while the new query refetches and uses inline pending copy
instead of replacing the page with `Loading patterns...`.

### Scenes

Scene inventory uses the searchable scene selector. With no search or selected
scene, the inventory table shows an empty prompt instead of the first scene.

### Operations

Scene readiness, Workers, Observed Patterns, and Delivery Truth use the same
explicit focus rule. With no selected or searched scene, each scoped section
shows the same neutral empty guidance.

### FleetOps Evidence / Support / Onboarding

These pages use a searchable vessel/site selector and do not bind to the first
vessel site. Link queue, support bundle/session/break-glass, and onboarding-run
actions remain disabled until a vessel/site is selected.

### Sites

Sites inventory provides search, page size selection limited to 10, 25, and 50,
pagination controls, and edit/delete actions. Add and edit share the same
dialog pattern. Search does not auto-select a site; it only filters the visible
page.

## Scope Safety

This addendum preserves the existing `CC-*` constraints. The work is a frontend
operator consistency pass plus a frontend hook for the existing core site
`PATCH /api/v1/sites/{site_id}` route.
