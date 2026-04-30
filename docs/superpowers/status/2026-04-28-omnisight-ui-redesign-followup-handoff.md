# OmniSight UI Redesign And Test Process Handoff

Date: 2026-04-28
Updated: 2026-04-30

Purpose: paste this document into a fresh project chat to continue from the current repo state, understand what changed in the OmniSight UI redesign, and move into the next test process without re-opening completed design work.

## Current Branch State

Active branch:

- `codex/source-aware-delivery-calibration-fixes`

Remote checkpoint:

- `origin/codex/source-aware-delivery-calibration-fixes` is pushed through:
  - `01567ee fix(e2e): align verify suite with redesigned workspace`

To update another iMac checkout:

```bash
cd "$HOME/vision"
git fetch origin
git switch codex/source-aware-delivery-calibration-fixes
git pull --ff-only
git log --oneline -5
```

Expected recent history includes:

- `01567ee fix(e2e): align verify suite with redesigned workspace`
- `64489b8 fix(frontend): harden vitest browser globals`
- `bf26e79 fix(camera): satisfy opencv fallback typing`
- `047e04a Implement Approach C app-wide redesign`

Working tree note after the push:

- tracked redesign files were committed and pushed
- untracked scratch files still exist locally and were intentionally not committed:
  - `.superpowers/brainstorm/*`
  - screenshot PNGs
  - `camera-capture.md`
  - unused logo variants such as `docs/brand/2d_logo.png`, `docs/brand/3d_logo.png`, and `docs/brand/animated_logo.mp4`
- do not stage those unrelated untracked files unless the user explicitly asks

## Important Context

The original handoff said the logo work was provisional and that the official logo asset still needed to arrive. That is now resolved.

The user-provided logo files that must be treated as canonical for this UI pass are:

- `docs/brand/2d_logo_no_ring.png`
- `docs/brand/3d_logo_no_bg.png`

Runtime copies were added at:

- `frontend/public/brand/2d_logo_no_ring.png`
- `frontend/public/brand/3d_logo_no_bg.png`

Tests assert that the runtime copies match the source files in `docs/brand`.

## What Was Implemented

Approach C app-wide redesign is implemented and pushed.

Major UI changes:

- centralized OmniSight product copy in `frontend/src/copy/omnisight.ts`
- changed visible navigation groups to `Intelligence` and `Control`
- changed visible navigation from `Cameras` to `Scenes` while keeping `/cameras` as the internal route
- reframed Live as `Live Intelligence`
- reframed History as `History & Patterns` and visible nav as `Patterns`
- reframed Incidents as `Evidence Desk`
- reframed camera setup as `Scene Setup`
- expanded `Sites` into the same spatial workspace language
- expanded `Settings` into `Operations`
- added official 2D logo usage for lockups and rails
- added official 3D logo usage in `OmniSightField`
- replaced the earlier generic sign-in sphere with a logo-derived spatial field
- fixed mobile logo/ring overflow found during Playwright visual verification
- tightened shared input/select radius and panel treatment to better match the UI spec

Primary files to inspect for the redesign:

- `frontend/src/brand/product.ts`
- `frontend/src/components/brand/OmniSightField.tsx`
- `frontend/src/components/layout/ProductLockup.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/copy/omnisight.ts`
- `frontend/src/index.css`
- `frontend/src/pages/SignIn.tsx`
- `frontend/src/pages/Live.tsx`
- `frontend/src/pages/History.tsx`
- `frontend/src/pages/Incidents.tsx`
- `frontend/src/pages/Cameras.tsx`
- `frontend/src/pages/Sites.tsx`
- `frontend/src/pages/Settings.tsx`

## Verification Already Run

Full iMac verification after the redesign and validation fixes, 2026-04-30:

```bash
make verify-all
```

Result:

- backend migrations, `ruff`, `mypy`, and tests passed
- frontend API generation, lint, tests, and build passed
- Playwright E2E passed: 8 tests
- Helm template rendering passed after Helm was installed on the iMac
- runtime health returned healthy

The final E2E repair aligned the suite with the current UI labels:

- `Live`, `Patterns`, and `Evidence` under `Intelligence`
- `Sites`, `Scenes`, and `Operations` under `Control`
- `Ask Vezor` / `Apply` instead of the legacy query affordance
- `Telemetry live` instead of the previous `online` label
- Prompt 7 now waits for the camera-create response before reloading

After implementing and before pushing `047e04a`, these checks passed:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/copy/omnisight.test.ts \
  src/components/layout/AppShell.test.tsx \
  src/components/history/HistorySearchBox.test.tsx \
  src/pages/History.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Cameras.test.tsx \
  src/pages/Settings.test.tsx \
  src/pages/Sites.test.tsx
```

Result:

- 8 files passed
- 46 tests passed

Full frontend verification:

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec eslint .
git diff --check
```

Results:

- frontend tests passed: 38 files, 146 tests
- production build passed
- ESLint returned 0 errors and 12 existing warnings
- `git diff --check` passed

Browser visual verification:

- temporary Playwright harness covered:
  - `/signin`
  - `/live`
  - `/history`
  - `/incidents`
  - `/cameras`
  - `/sites`
  - `/settings`
  - mobile `/signin`
  - mobile `/live`
- verified:
  - 2D logo loads
  - 3D logo loads
  - no old camera-first copy appears on redesigned app routes
  - no page errors
  - no horizontal overflow after the mobile spatial-field fix
- temporary harness/screenshots were removed
- temporary Vite dev servers started for this check were stopped

Known warnings that are not new to the redesign:

- `VideoStream` tests emit React `act(...)` warnings
- React Router future-flag warnings appear in a transition test
- ESLint warnings remain in:
  - `frontend/src/components/history/HistoryTrendChart.tsx`
  - `frontend/src/components/layout/TopNav.tsx`
  - `frontend/src/components/live/VideoStream.tsx`
  - `frontend/src/pages/Incidents.tsx`

## Next Direction: Test Process

The next chat should move from UI implementation into validation. Do not start by redesigning again.

Use this order.

### 1. Pull And Sanity Check The iMac Checkout

```bash
cd "$HOME/vision"
git fetch origin
git switch codex/source-aware-delivery-calibration-fixes
git pull --ff-only
git status -sb
```

Expected:

- branch is `codex/source-aware-delivery-calibration-fixes`
- commit includes `01567ee`
- no tracked local changes unless the user has edited files locally

### 2. Refresh Tooling And Dependencies

```bash
node --version
python3 --version
docker --version
docker compose version
uv --version
corepack enable
corepack prepare pnpm@10.11.0 --activate
cd "$HOME/vision/backend"
python3 -m uv sync
cd "$HOME/vision"
corepack pnpm --dir frontend install
```

### 3. Run The Fast Frontend Confidence Pass

This verifies the pushed redesign before bringing up the whole stack:

```bash
cd "$HOME/vision"
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec eslint .
git diff --check
```

Expected:

- tests pass
- build passes
- lint has 0 errors, with the known warnings listed above
- diff whitespace check passes

### 4. Bring Up The Local Dev Stack

```bash
cd "$HOME/vision"
make dev-up
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
until curl -fsS http://127.0.0.1:8000/healthz; do
  echo "waiting for backend health..."
  sleep 2
done
corepack pnpm --dir frontend generate:api
```

Open:

- `http://127.0.0.1:3000`
- `http://127.0.0.1:3000/settings`
- `http://127.0.0.1:8000/healthz`
- `http://127.0.0.1:8080`
- `http://127.0.0.1:9001`

Local login:

- username: `admin-dev`
- password: `argus-admin-pass`

### 5. Manual UI Smoke Test

Check these pages in the browser:

- `/signin`
  - 2D lockup is correct
  - 3D logo field is centered and not clipped awkwardly
  - sign-in page has no weird rectangular artifacts
- `/live`
  - visible title is `Live Intelligence`
  - nav groups are `Intelligence` and `Control`
  - visible nav item is `Patterns`, not `History`
  - visible nav item is `Scenes`, not `Cameras`
- `/history`
  - page reads as `History & Patterns`
  - filters say `Scene filters`
  - search says `Search patterns`
- `/incidents`
  - page reads as `Evidence Desk`
  - queue/evidence/facts layout renders
  - filters say `Scene filter` and `Event type`
- `/cameras`
  - page reads as `Scene Setup`
  - primary action is `Add scene`
- `/sites`
  - page reads as `Sites`
  - copy is scene/site/operations-oriented
- `/settings`
  - page reads as `Operations`
  - worker language says `Scene workers`
  - runtime state remains truthful and does not invent running workers

Use narrow/mobile widths too, especially sign-in and live shell.

### 6. Run Whole-Suite Validation

The best single command for the repo-level test process is:

```bash
cd "$HOME/vision"
make verify-all
```

This wraps `scripts/run-full-validation.sh` and runs:

- Docker Compose backend/infrastructure startup
- backend migrations
- frontend API type generation
- backend `ruff`
- backend `mypy`
- backend tests
- frontend lint
- frontend tests
- frontend build
- Playwright e2e suite
- Helm template rendering
- runtime health checks

Expected success shape:

- backend checks pass
- backend tests pass
- frontend checks pass
- Playwright passes
- Helm renders cleanly
- Compose services are up
- `/healthz` returns healthy

### 7. Move Into Lab Validation

After `make verify-all` is clean, use:

- `docs/imac-master-orin-lab-test-guide.md`
- `docs/superpowers/status/2026-04-28-imac-jetson-dev-validation-handoff.md`
- `docs/operator-deployment-playbook.md`
- `docs/runbook.md`

Recommended lab order:

1. **iMac-only functional validation**
   - iMac runs control plane
   - two RTSP cameras use `central`
   - workers are started from Operations copyable commands
   - validate Live, Patterns, Evidence Desk, Scene Setup, Sites, and Operations
2. **iMac master + Jetson Orin edge validation**
   - iMac remains temporary master
   - camera 1 stays `central`
   - camera 2 moves to Jetson as `edge`
   - validate telemetry, history, evidence, delivery diagnostics, and Operations truthfulness across the split

## Do Not Re-Plan Completed Work

These areas were already implemented and documented. Do not re-plan them by default:

- Operations phase 1
- source-aware browser delivery
- setup preview and normalized boundary authoring
- History / Patterns
- open-vocab control-plane foundation
- Evidence Desk review queue
- deployment docs
- iMac / Jetson lab guide
- tracker/calibration fixes from prior review findings
- Approach C app-wide UI redesign
- official 2D/3D logo asset wiring

If validation finds a real bug in those areas, debug and fix it systematically, but do not restart their design plans unless the user explicitly asks.

## Suggested First Prompt For The Next Chat

Paste this:

```text
We are on branch codex/source-aware-delivery-calibration-fixes, pushed through 01567ee fix(e2e): align verify suite with redesigned workspace. Read docs/superpowers/status/2026-04-28-omnisight-ui-redesign-followup-handoff.md and docs/superpowers/status/2026-04-28-imac-jetson-dev-validation-handoff.md. Phase A iMac-only validation and make verify-all are green. Help me continue with Phase B iMac master plus Jetson Orin edge validation. Do not re-open the redesign unless validation shows a concrete issue.
```
