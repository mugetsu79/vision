# OmniSight UI/UX Polish Audit

Date: 2026-06-03
Branch: `codex/omnisight-ui-ux-polish`
Baseline: `main` at `d88f904e`

## Source Inputs

- `docs/superpowers/specs/2026-06-03-taste-led-omnisight-ui-ux-polish-design.md`
- `docs/superpowers/plans/2026-06-03-taste-led-omnisight-ui-ux-polish.md`
- `docs/brand/omnisight-ui-spec-sheet.md`
- `docs/superpowers/specs/2026-04-30-omnisight-ui-distinctiveness-followup-design.md`
- local `taste-skill/` routed through `taste-skill/SKILL.md`

Taste direction is locked to `dashboards` first, with `dark-luxe` restraint and
`swiss-system` grid discipline as supporting inputs.

## Screenshot Evidence

Browser check:

- `http://localhost:3001/signin`
- `/tmp/omnisight-polish-audit-before/signin-1440.png`
- `/tmp/omnisight-polish-audit-before/signin-375.png`

The sign-in surface loads without console errors in the in-app Browser. Authenticated
route screenshots require mocked auth/API data for meaningful state and will be
captured in the final visual QA pass after the implementation slice lands.

## Top Operator-Impact Issues

1. Operations still reads as one long workbench. Scene readiness, setup links,
   operational memory, configuration, fleet metrics, model runtimes, nodes,
   workers, and stream diagnostics compete in a single vertical stack.
2. Attention is present but not yet the page frame. The first actionable summary
   should answer what needs action now, then route to Workers, Stream Diagnostics,
   Deployment Nodes, Configuration, and Installer Guidance sections.
3. Low-level runtime metadata is too visually dominant. Hashes, model artifacts,
   source details, lifecycle detail, and direct-stream reasons must remain true,
   but should be progressively disclosed or grouped under quieter diagnostic
   rows.
4. The stable 2D lockup is visible in the app rail, but the shell still renders
   an ambient 3D field by default. Workflow pages should treat the 3D mark as
   background atmosphere at most, not as the product identity anchor.
5. Dashboard, Operations, Live, Scenes, and Deployment share too many similar
   rounded dark shells. The next slice should strengthen instrument bands, black
   media slabs, row groups, command plates, and section navigation.

## Logo And Lens Recommendation

- Keep the 2D lockup as the stable product identity in app chrome.
- Keep the dimensional lens on sign-in and dashboard only, where it has a clear
  product-stage role.
- Change the workflow shell field to a quiet static watermark treatment: lower
  opacity, no orbital nodes, and no perpetual mark drift in normal route chrome.
- Preserve `prefers-reduced-motion` behavior and make any remaining movement
  event/state-driven rather than ambient.

## Operations IA Recommendation

- Add an attention-first operations overview directly below the page band.
- Add section navigation/anchors for Workers, Stream Diagnostics, Deployment
  Nodes, Configuration, and Installer Guidance.
- Move deployment setup guidance and node-pairing links into the section system
  so operators can navigate instead of scrolling through unrelated blocks.
- Convert repeated panel internals to denser rows and disclosure blocks while
  preserving unknown, stale, offline, not-reported, desired, and runtime-reported
  distinctions.

## First-Slice Page Scope

Touch now:

- App shell and logo/lens treatment.
- Operations page and operations row components.
- Focused surface hierarchy in Dashboard, Live, Scenes setup header, and
  Deployment installer guidance if the Operations change remains contained.

Do not touch now:

- Backend/runtime contracts.
- Auth semantics.
- Streaming or telemetry semantics.
- Evidence review flow unless visual QA reveals a direct media clarity issue.
- Sites table/card IA unless it becomes necessary for consistency in this slice.

## Baseline Verification

Focused baseline command:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/components/brand/OmniSightField.test.tsx \
  src/components/brand/OmniSightLens.test.tsx \
  src/components/layout/AppShell.test.tsx \
  src/pages/Settings.test.tsx \
  src/components/operations/SceneIntelligenceMatrix.test.tsx \
  src/lib/operational-health.test.ts
```

Result: 29 tests passed. Existing React Router future-flag warnings remain.
