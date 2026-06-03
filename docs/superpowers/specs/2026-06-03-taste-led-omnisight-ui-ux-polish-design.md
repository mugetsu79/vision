# Taste-Led OmniSight UI/UX Polish Design

Date: 2026-06-03
Status: Proposed for next chat branch `codex/omnisight-ui-ux-polish`

## Product Goal

Run a taste-led 2026 polish pass over the current OmniSight product without
losing what makes it useful in the field: operator density, runtime honesty,
fast diagnosis, and clear action paths.

This is not the first OmniSight redesign. It is a follow-on pass over the
product as it exists after:

- `047e04a Implement Approach C app-wide redesign`
- `29224d27 test(e2e): expect restored dashboard overview`
- `d5282c60 docs: refresh markdown cleanup and handoff`
- `b6771f24 feat(dashboard): add deployment posture and attention stack`
- the 2026-06-03 configuration guidance and pre-polish correction merge

## Design Lineage To Respect

The next chat should read these as historical context, not as fresh marching
orders:

- `docs/superpowers/status/2026-04-28-omnisight-ui-redesign-followup-handoff.md`
- `docs/superpowers/specs/2026-04-28-vezor-omnisight-ui-redesign-design.md`
- `docs/superpowers/specs/2026-04-30-omnisight-ui-distinctiveness-followup-design.md`
- `docs/brand/omnisight-ui-spec-sheet.md`

The April 28 redesign created the current product language. The April 30
distinctiveness and UI spec-sheet work then pushed the product away from generic
dark SaaS toward a spatial intelligence cockpit. This polish pass should audit
where that work still falls short in the running product.

## Taste Direction

Use local `taste-skill/` as design input if it exists in the workspace. Route
through `taste-skill/SKILL.md` first, then bias toward:

- `dashboards` as the primary style: operator-first hierarchy, actionable
  density, calm monitoring surfaces, and status that answers "what needs
  attention now?"
- `dark-luxe` as material restraint: darker premium surfaces, controlled light,
  fewer generic glowing panels, no decorative neon drift.
- `swiss-system` as grid discipline: clearer typography, stricter alignment,
  better section rhythm, and fewer same-looking cards.

The output should feel premium and current, but not like a marketing page, not
like a luxury mood board, and not like an ornamental sci-fi console.

## Primary Problems

### Operations Is Overloaded

Operations currently asks the operator to parse too much at once: deployment
nodes, scene readiness, worker lifecycle, stream diagnostics, control-plane
configuration, effective runtime state, and installer guidance all compete in
one long workbench.

The redesign should make Operations attention-first:

- urgent fleet and scene issues first
- navigable sections for Workers, Stream Diagnostics, Deployment Nodes,
  Configuration, and Installer Guidance
- diagnostic details available on demand, not dominant by default
- clear separation between "needs action", "configured", and "reported by
  runtime"

### Logo And Lens Treatment Feels Off

The current moving 3D sphere/lens treatment is not the best representation of
the brand. The next chat should revise how the logo appears before adding more
motion.

Preferred direction:

- Use the 2D lockup as the stable identity anchor in app chrome.
- Treat the dimensional mark as a deliberate product object only where it earns
  attention, such as sign-in or a dashboard overview.
- Avoid a constantly moving decorative sphere in workflow screens.
- Replace ambient logo motion with quieter, purposeful responses: route focus,
  hover, loading, or status transitions.
- Support a static or near-static hero mark that still feels premium when
  `prefers-reduced-motion` is enabled.

### Repeated Panel Language

Many workflows still rely on similar rounded dark panels, border treatments,
and pill badges. The polish pass should introduce a stronger hierarchy of
surfaces:

- instrument bands for summary state
- black media slabs for video/evidence
- compact tables or row groups for worker and runtime state
- drawers/disclosures for low-level diagnostics
- calmer cards only where enclosure genuinely helps

## Scope

In scope:

- Operations information architecture and visual hierarchy.
- App shell, nav, logo, and lens treatment review.
- Dashboard, Live, Scenes, Evidence, Sites, and Deployment visual consistency
  audit, with focused changes where they support the system language.
- Shared UI primitives and CSS tokens only when they reduce repeated chrome.
- Motion review with reduced-motion coverage.
- Browser visual QA across desktop and mobile widths.

Out of scope:

- Backend/runtime semantic changes.
- Route rename migrations.
- New streaming, telemetry, or worker behavior.
- WebGL or heavy 3D dependencies unless separately approved.
- Marketing site design.

## Runtime Truth Rules

The polish pass must not make the product look healthier than the data says.

- If a worker heartbeat is not reported, say so.
- If telemetry is stale, awaiting, or absent, keep that state explicit.
- If a config profile is desired but not runtime-reported, keep that distinction.
- If a stream rendition is selected but not live, do not imply success.
- Decorative polish must never obscure video, evidence media, or actionable
  error states.

## Success Criteria

- Operations can be scanned in under 10 seconds for "what needs action now?"
- The logo feels stable, intentional, and premium; the moving 3D sphere is no
  longer the default workflow-page brand behavior.
- Dashboard and Operations feel like dense operator tools, not landing pages.
- Live video and evidence media remain visually first-class.
- The interface uses fewer repeated card shells and clearer surface hierarchy.
- Existing focused frontend tests and production build pass.
- Visual QA covers 375, 768, 1024, and 1440 px widths.
