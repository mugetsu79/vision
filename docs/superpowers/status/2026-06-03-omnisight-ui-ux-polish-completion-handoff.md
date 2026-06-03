# OmniSight UI/UX Polish Completion Handoff

Date: 2026-06-03
Branch: `codex/omnisight-ui-ux-polish`
Base: `d88f904e docs: seed taste-led ui polish`

## Implementation Range

Code/docs implementation commits currently on the branch:

- `9cb0fd22 docs(ui): audit taste-led polish scope`
- `b53029a7 fix(ui): refine omnisight logo treatment`
- `c899dd6c feat(operations): organize attention-first workbench`

The implementation range from main is `d88f904e..c899dd6c`. This handoff file
is docs-only and may be committed after that range.

## What Changed

- App chrome now uses the stable 2D identity anchor while workflow pages use a
  quiet static shell watermark instead of the ambient 3D mark stack.
- Reduced-motion coverage was extended for the lens tilt hook so CSS variable
  writes stop when the user prefers reduced motion.
- Operations now opens with an attention stack, followed by scene readiness,
  section navigation, operational memory, Workers, Stream Diagnostics,
  Deployment Nodes, Configuration, and Installer Guidance.
- Worker cards keep lifecycle controls visible while lower-level runtime
  passport, hardware admission, rule runtime, and detail text live behind a
  native `Runtime diagnostics` disclosure.
- Runtime labels and semantics remain unchanged: stale, unknown, not reported,
  direct stream unavailable, manual dev, and supervisor ownership states are
  still shown directly from the current data model.

## Visual QA

Screenshots were captured under `/tmp/omnisight-polish-qa` for:

- Sign-in: 375, 768, 1024, 1440
- Dashboard: 375, 768, 1024, 1440
- Live: 375, 768, 1024, 1440
- Operations: 375, 768, 1024, 1440
- Scenes: 375, 768, 1024, 1440
- Deployment: 375, 768, 1024, 1440

Metrics:

- `/tmp/omnisight-polish-qa/metrics.json`
- `/tmp/omnisight-polish-qa/signin-metrics.json`

Results:

- No severe console errors in the mocked authenticated capture run.
- Sign-in has no overflow at the checked widths.
- Dashboard, Live, and Operations have no horizontal overflow at the checked
  widths.
- Shell captures report `hasShellMarkStack: false` and `hasShellWatermark:
  true`.
- Scenes and Deployment still report wide table content inside existing
  horizontal table regions; these were not introduced by this polish slice and
  were left alone to avoid broad page churn.

## Verification

Focused Operations:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/pages/Settings.test.tsx \
  src/components/operations/SceneIntelligenceMatrix.test.tsx \
  src/lib/operational-health.test.ts
```

Result: 3 files passed, 18 tests passed.

Regression slice:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/components/brand/OmniSightField.test.tsx \
  src/components/brand/OmniSightLens.test.tsx \
  src/components/brand/use-lens-tilt.test.ts \
  src/components/layout/AppShell.test.tsx \
  src/pages/Dashboard.test.tsx \
  src/pages/Live.test.tsx \
  src/pages/Settings.test.tsx \
  src/pages/Cameras.test.tsx \
  src/pages/Deployment.test.tsx \
  src/lib/operational-health.test.ts
```

Result: 10 files passed, 62 tests passed.

Production build:

```bash
corepack pnpm --dir frontend build
```

Result: passed.

Whitespace:

```bash
git diff --check
```

Result: passed.

## Workspace Notes

- Do not stage `taste-skill/`.
- Do not use `git add -A`; there are many unrelated untracked scratch files in
  the workspace.
- A Vite dev server was running at `http://localhost:3001/` during QA.
- The authenticated visual QA used Playwright with mocked auth/API responses and
  a fake telemetry WebSocket; it did not change source or runtime semantics.
