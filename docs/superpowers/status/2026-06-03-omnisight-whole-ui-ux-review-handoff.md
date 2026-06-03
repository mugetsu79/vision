# OmniSight Whole UI/UX Review Handoff

Date: 2026-06-03
Branch: `codex/omnisight-ui-ux-polish`
Upstream checkpoint before this review slice: `118c8f2f docs(ui): plan omnisight whole ui review`

## Intent

This pass follows the 2026-06-03 taste-led OmniSight UI/UX polish request. It
treats the April 28 redesign and April 30 distinctiveness work as product
lineage, not as the new spec.

The guiding direction was:

- dashboards as the primary product posture
- dark-luxe restraint without decorative obscurity
- swiss-system grid discipline
- attention-first Operations hierarchy
- runtime truth preserved
- 3D moving lens removed as the default brand expression
- video and evidence clarity protected over motion or ornament

## Skills And Review Method

Used local `taste-skill/` through `taste-skill/SKILL.md` with the dashboard,
dark-luxe, and swiss-system style recipes.

Used Product Design index and `ui-ux-pro-max` for UI/UX review framing and
design-system search.

Used Superpowers subagent-driven development, verification-before-completion,
requesting-code-review, and receiving-code-review. Final reviewer Jason found
two issues, both fixed before this handoff:

- Operations section navigation rendered too late in the page order.
- The Configuration `aria-controls` target was absent until first expansion.

## Commit Range

Source review commits now ahead of `origin/codex/omnisight-ui-ux-polish`:

```text
62fe2e9f test(ui): add omnisight visual hierarchy guardrails
fb792bd5 fix(ui): remove moving 3d brand default
aefc0a02 feat(ui): add command surface primitives
fc7e0bff feat(operations): make workbench attention first
18b2f9f0 feat(dashboard): replace hero with command overview
0e3b96c4 refactor(ui): tighten secondary workspace hierarchy
1bdf88c9 fix(ui): resolve final visual audit findings
```

This file is the documentation closeout for that review slice.

## What Changed

- Added UI audit guardrails that check for default 3D brand usage, excessive
  Operations surface count, and basic hierarchy expectations.
- Removed the moving 3D lens as the default Dashboard and sign-in brand
  expression. The sign-in screen now uses a compact command preview instead of
  a large animated lens object.
- Added command-surface primitives so the app can present state, routes, and
  runtime action without turning every area into a decorative card stack.
- Reworked Operations into a more attention-first workbench:
  - attention stack first
  - scene intelligence next
  - section navigation before Workers
  - Workers, Stream Diagnostics, Deployment Nodes, Configuration, and Installer
    Guidance as navigable operational sections
  - Configuration collapsed by default, with heavier content deferred until
    expansion
  - runtime status and operator controls preserved
- Replaced the Dashboard hero posture with a command overview that reads more
  like an operating console than a brand showcase.
- Tightened secondary page hierarchy across History, Deployment, Sites, Live,
  Incidents, and Cameras without changing runtime semantics.
- Widened the Incidents evidence media lane at desktop sizes.
- Moved Live video transport/profile chips away from top-left detection labels.

## Verification

Targeted post-fix tests:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/pages/SignIn.test.tsx \
  src/pages/Incidents.test.tsx \
  src/components/live/VideoStream.test.tsx
```

Result: 3 files passed, 37 tests passed. Existing React `act(...)` warnings
remain in VideoStream tests.

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx
```

Result: 1 file passed, 7 tests passed. Existing React Router future warnings
remain.

Full frontend tests:

```bash
corepack pnpm --dir frontend exec vitest run
```

Result: 80 files passed, 377 tests passed. Existing warnings: VideoStream
React `act(...)` warnings and React Router future warnings.

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

Clean-port Playwright audit:

```bash
corepack pnpm --dir frontend exec playwright test \
  /Users/yann.moren/vision/frontend/e2e/omnisight-ui-audit.spec.ts \
  --config /Users/yann.moren/vision/frontend/e2e/.tmp-omnisight-playwright.config.ts
```

Result: 2 tests passed:

- Dashboard does not render the moving 3D brand object.
- Operations default surface count stays below the overload budget.

The temporary Playwright config was removed after the run.

## Visual QA Evidence

Full mocked authenticated matrix:

```text
/tmp/omnisight-visual-qa-2026-06-03T19-25-08-785Z
```

Coverage: Sign-in, Dashboard, Live, Operations, Incidents, Cameras, Sites, and
Deployment at desktop and mobile widths. Metrics found no default
`omnisight-lens`, no `3d_logo`, no sign-in animated logo, no brand animations,
no horizontal overflow, and no unknown requests.

Focused polish rerun after final fixes:

```text
/tmp/omnisight-visual-polish-2026-06-03T19-30-22-244Z
```

Coverage: Sign-in, Live, and Incidents at 375 and 1440 widths. Results:

- Sign-in no longer shows the large 3D lens object.
- Live transport/profile chips sit top-right instead of covering detection
  labels.
- Incidents evidence media width at 1440 improved from 292px to 384px.
- No default lens, 3D logo, sign-in animated logo, brand animations,
  horizontal overflow, or unknown requests were detected.

## E2E Caveat

The stock command below was misleading on this Mac because Playwright reused an
existing server on port 3000, and port 3000 is owned by Docker here:

```bash
corepack pnpm --dir frontend test:e2e
```

That stale run showed old UI metrics and failed against the wrong app. The
clean-port audit on port 3102 passed. For a reliable local run, free port 3000
or point Playwright at a clean Vite server/config.

## MacBook Pull Steps

After the branch is pushed:

```bash
cd /path/to/vision
git fetch origin
git switch codex/omnisight-ui-ux-polish
git pull --ff-only origin codex/omnisight-ui-ux-polish
```

Then rebuild from that checked-out branch.

## Workspace Notes

- Untracked local scratch files were intentionally not staged.
- `taste-skill/` was intentionally not staged.
- Runtime semantics were not changed.
- Existing test warnings were left in place because they predate this polish
  slice and the related tests pass.
