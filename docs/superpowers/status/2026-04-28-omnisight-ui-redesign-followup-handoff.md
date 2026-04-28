# OmniSight UI Redesign Follow-Up Handoff

Date: 2026-04-28

Purpose: paste this document into a fresh project chat to continue the OmniSight UI/UX redesign without losing the current repo state, user feedback, and known caveats.

## Critical User Feedback

The user is not confident the implementation matches:

- `docs/superpowers/plans/2026-04-28-vezor-omnisight-ui-redesign-implementation-plan.md`

The user specifically said:

- "The logo is completely off."
- They will provide the logo asset to use.
- The earlier sign-in background sphere was not acceptable because the plan was for a 3D version of the logo, not a generic sphere.

Important next-chat instruction:

- Do not keep iterating on the current handmade/generated logo as if it is canonical.
- Wait for the user-provided logo and replace the current symbol/lockup treatment from that source.
- Treat the latest logo cleanup commit as provisional, not approved visual direction.

## Current Branch State

Active branch:

- `codex/source-aware-delivery-calibration-fixes`

Remote checkpoint:

- `origin/codex/source-aware-delivery-calibration-fixes` currently points to:
  - `8c32e06 fix: preserve tracking across stream gaps`

Local commits after origin are UI/UX redesign work and are not pushed unless the user does so later.

Recent local UI commits before this handoff:

- `477ca4a fix: clean omnisight logo field`
- `1b06ff8 fix: polish omnisight responsive ui`
- `ec457a6 fix: clarify stream accessibility labels`
- `ff096ca fix: preserve live media labels`
- `e1fb778 style: add omnisight workflow depth`
- `36cb8aa fix: remove stale evidence desk labels`
- `1c1b303 fix: rename camera summary boundaries`
- `3cf517a feat: update omnisight workspace language`
- `b799dca fix: use scene language in live workspace`
- `eae9412 feat: reframe live as intelligence`
- `e5acc7c feat: add omnisight shell motion`
- `dc471bd feat: redesign omnisight sign-in`
- `349a295 fix: support omnisight overview field`
- `b565c8e feat: add omnisight field component`
- `b2f2972 style: add omnisight visual tokens`
- `d5d2d0e feat: centralize omnisight product copy`
- `29db420 docs: add omnisight ui redesign plan`
- `67ee984 docs: add omnisight ui redesign spec`

Working tree before creating this handoff:

- tracked files were clean
- untracked scratch files existed, including `.superpowers/brainstorm/*`, screenshot PNGs, and `camera-capture.md`
- do not stage unrelated untracked scratch files unless the user explicitly asks

## Existing Design And Plan Files

Read these first in the next chat:

- `docs/superpowers/specs/2026-04-28-vezor-omnisight-ui-redesign-design.md`
- `docs/superpowers/plans/2026-04-28-vezor-omnisight-ui-redesign-implementation-plan.md`

User preferences captured in those docs and this thread:

- Product is about OmniSight / broad spatial intelligence, not car counting.
- Do not keep `Cameras` in the visible nav; use `Scenes`.
- Keep `/cameras` as internal route plumbing for now.
- Entry and overview can be bold.
- Dense operational workflows should only have a faint living background hint.
- Operations runtime state must stay truthful; do not invent running worker state.

## What Was Implemented

The UI redesign pass made broad changes:

- centralized product copy in `frontend/src/copy/omnisight.ts`
- relabeled nav groups to Intelligence / Control
- changed visible nav item from Cameras to Scenes
- reframed Live as Live Intelligence
- reframed History as History & Patterns
- reframed Incidents as Evidence Desk
- reframed camera setup copy as Scene Setup
- added `OmniSightField`
- added shell/background motion and shared visual tokens in `frontend/src/index.css`
- restyled sign-in, app shell, page headers, shared panels, badges, and buttons
- adjusted Live, History, Evidence Desk, Scene Setup, and Operations wording

The latest logo-specific work in `477ca4a` changed:

- `docs/brand/assets/source/vezor-symbol-product-ui.svg`
- `frontend/public/brand/product-symbol-ui.svg`
- `frontend/public/brand/argus-symbol-ui.svg`
- `frontend/src/components/layout/ProductLockup.tsx`
- `frontend/src/components/brand/OmniSightField.tsx`
- `frontend/src/index.css`

That commit removed the previous circular medallion/aura around the symbol and replaced the sign-in sphere with layered logo-mark imagery.

But the user still says the logo is completely off, so do not treat this as final.

## Known Logo / Asset Caveats

Current state is provisional:

- `ProductLockup` no longer uses `productBrand.runtimeAssets.lockup`; it renders a code-native lockup from the symbol plus text.
- `frontend/public/brand/product-lockup-ui.svg` and `frontend/public/brand/argus-lockup-ui.svg` still exist, but the main component is not using them.
- `productBrand.runtimeAssets.lockup` still points to `/brand/product-lockup-ui.svg`, so either restore proper lockup asset usage or update the brand model after the official logo arrives.
- The current symbol SVG is handmade and should be replaced with the user-provided logo source.
- The current `OmniSightField` uses the current symbol as a layered pseudo-3D field. After the official logo arrives, re-evaluate whether it should use:
  - the official mark directly,
  - a derived transparent depth asset,
  - or a code-native 3D treatment based on the official mark.

Recommended next step for the logo:

1. Accept the user-provided logo asset.
2. Inspect its format, intrinsic dimensions, transparency, and intended clearspace.
3. Replace source/runtime assets from that file, not from the current handmade mark.
4. Revisit `ProductLockup` to avoid duplicated or distorted wordmark text.
5. Revisit `OmniSightField` so the entry visual is a 3D/logo-derived treatment, not a generic sphere and not an inaccurate hand-drawn logo.
6. Browser-check rail, sign-in, desktop app shell, and narrow/mobile views.

## Verification Already Run

After `477ca4a`, the following passed:

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec eslint .
git diff --check
```

Notes:

- Full frontend test result: `38 passed`, `146 tests passed`.
- Build passed.
- ESLint returned 0 errors and 12 existing warnings.
- Browser verification was run for sign-in and a narrow authenticated Live rail screenshot.
- Temporary Playwright screenshots/logs were removed.
- Temporary Vite dev server was stopped; a Docker listener may still own port `3000`.

Known frontend warnings are pre-existing:

- Fast-refresh warnings in `HistoryTrendChart.tsx`, `TopNav.tsx`, and `Incidents.tsx`.
- React hook dependency warnings in `VideoStream.tsx`.

## Suggested Next-Chat Workflow

Do this before writing more UI code:

1. Read this handoff.
2. Read the UI redesign spec and implementation plan.
3. Ask for or receive the official logo asset.
4. Audit current implementation against the plan:
   - identify what is complete,
   - what is incomplete,
   - what deviates from the plan,
   - and what should be reverted versus corrected.
5. Replace the logo assets using the official logo.
6. Re-run focused tests first:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/brand/product-assets.test.ts \
  src/components/layout/ProductLockup.test.tsx \
  src/components/brand/OmniSightField.test.tsx \
  src/pages/SignIn.test.tsx \
  src/App.test.tsx
```

7. Run browser visual checks:
   - `/signin`
   - authenticated shell rail at a narrow viewport
   - `/live`
   - `/history`
   - `/incidents`
   - `/cameras`
   - `/settings`
8. Then run full verification:

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec eslint .
git diff --check
```

9. Commit only after the user approves the visual direction or after the logo replacement is clearly correct.
10. Do not push unless the user explicitly asks.

## Do Not Re-Plan Completed Non-UI Work

These areas were already updated before the UI redesign thread and should not be re-planned:

- Operations phase 1
- source-aware delivery
- History
- open-vocab control-plane foundation
- Evidence Desk review queue
- deployment docs
- iMac / Jetson lab guide
- tracker/calibration fixes from the review findings

If validation finds a real bug in those areas, debug and fix it systematically, but do not re-open their design plans by default.

