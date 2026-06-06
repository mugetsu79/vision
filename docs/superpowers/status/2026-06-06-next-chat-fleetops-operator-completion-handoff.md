# FleetOps Operator Completion Next-Chat Handoff

Date: 2026-06-06
Current branch: `codex/sceneops-pack-registry`
Current pushed HEAD: `1e567fe8c90ded31b5a3b597648545b2dffb0ea6`

## Current State

The Maritime FleetOps runtime implementation plan from 2026-06-05 has been
executed through the original product runtime scope and pushed. FleetOps now
installs and exposes the runtime pages, but user validation on the MacBook
found the next product gap:

- there is no visible way to add a vessel from the UI
- the left rail only exposes one FleetOps icon, so the FleetOps subpages feel
  hidden
- Support and Onboarding look like the same workflow
- "Diagnostic groups" is too internal and does not explain the operational
  state
- link modeling and UI copy are too satellite-shaped; FleetOps must support
  satellite, LTE, 5G, Wi-Fi, fiber, ethernet, and other wireless/wired paths

A new spec and implementation plan have been created and pushed for this
follow-up work. The next chat should continue the same branch, start
implementation from the new plan, and keep commits focused.

Do not create a new branch unless the user explicitly asks. Do not merge to
`main` unless the user explicitly asks.

## Files To Read First

Read these in order:

1. `docs/superpowers/status/2026-06-06-next-chat-fleetops-operator-completion-handoff.md`
2. `docs/superpowers/specs/2026-06-06-fleetops-operator-completion-design.md`
3. `docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md`
4. `docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md`
5. `docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md`
6. `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
7. `docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md`
8. `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`
9. `packs/README.md`
10. `packs/maritime-fleet/pack.yaml`
11. `packs/traffic-public-space/pack.yaml`

The 2026-06-05 runtime files remain binding for `CC-*` constraints and pack
boundaries. The 2026-06-06 operator-completion files are the active
implementation target.

## What Is Already Done On This Branch

Latest pushed commits:

```text
1e567fe8 docs: plan fleetops operator completion
3129be50 fix: clear fleetops verification errors
8b6ef35f test: harden fleetops playwright smoke
be3b3af0 test: add fleetops product smoke coverage
40147a69 feat: add fleetops workspace
160e7ffa feat: add fleetops frontend hooks
```

Completed before this handoff:

- Read-only pack registry and pack API.
- Maritime FleetOps runtime implementation.
- Core link, fleet, billing, and support baselines from the original runtime
  plan.
- Maritime vessel, voyage, port-call, telemetry, evidence, billing, support,
  onboarding, and FleetOps frontend pages.
- OpenAPI generation and frontend typed hooks for the runtime baseline.
- Installer validation for macOS master, Linux master, and Jetson Orin edge
  artifacts.
- Real-stack FleetOps Playwright smoke for the existing runtime UI.
- New Product Design/UI/UX grounded spec:
  `docs/superpowers/specs/2026-06-06-fleetops-operator-completion-design.md`.
- New TDD implementation plan:
  `docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md`.

## New Implementation Scope

Use:

```text
docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md
```

Start with Gate 1, Task 1: FleetOps Rail Navigation.

Then continue task-by-task:

1. Gate 1 Task 1: FleetOps Rail Navigation.
2. Gate 1 Task 2: Vessel Create And Edit Flow.
3. Gate 2 Task 3: Core Link Connections.
4. Gate 2 Task 4: Maritime Carrier Mapping To Core Connections.
5. Gate 3 Task 5: Link, Evidence, And Billing UI Plumbing.
6. Gate 3 Task 6: Support And Onboarding Split.
7. Gate 3 Task 7: Product Completeness Sweep.
8. Gate 4 Task 8: Full Verification, Real Stack, And Installer Artifacts.

Use Superpowers, preferably `superpowers:subagent-driven-development`, and
execute the plan with TDD:

1. Write failing tests.
2. Run them red.
3. Implement the smallest product code that satisfies the behavior.
4. Run the tests green.
5. Commit focused changes.
6. Push `origin codex/sceneops-pack-registry` at implementation checkpoints.

## First Task Details

Begin with:

```text
docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md#task-1-fleetops-rail-navigation
```

Expected files:

- `frontend/src/components/layout/workspace-nav.ts`
- `frontend/src/components/layout/AppContextRail.tsx`
- `frontend/src/components/layout/AppIconRail.tsx`
- `frontend/src/components/layout/AppShell.test.tsx`

Expected first red test:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/components/layout/AppShell.test.tsx
```

Expected first commit:

```bash
git add frontend/src/components/layout/workspace-nav.ts frontend/src/components/layout/AppContextRail.tsx frontend/src/components/layout/AppIconRail.tsx frontend/src/components/layout/AppShell.test.tsx
git commit -m "feat: expose fleetops section navigation"
```

Push after Gate 1 Task 2:

```bash
git push origin codex/sceneops-pack-registry
```

## Key Product Decisions

- FleetOps gets one icon in the icon rail and nested FleetOps links in the
  expanded section rail.
- The nested links are:
  - FleetOps overview: `/fleetops`
  - Vessels: `/fleetops/vessels`
  - Evidence: `/fleetops/evidence`
  - Billing: `/fleetops/billing`
  - Support: `/fleetops/support`
  - Onboarding: `/fleetops/onboarding`
- Vessels page gets Add Vessel as the first empty-state action.
- Add Vessel defaults to creating a core site for the vessel, with an advanced
  option to bind an existing core site.
- Core link gets domain-neutral `LinkConnection` support for:
  - `satellite`
  - `lte`
  - `5g`
  - `wifi`
  - `fiber`
  - `ethernet`
  - `other`
- Maritime carrier terminal ingest maps into core link connections by site ID.
- Support and Onboarding must become distinct workflows:
  - Support diagnoses and assists an operational vessel.
  - Onboarding gets a vessel/site/link/camera/evidence/billing/support setup
    ready.
- "Diagnostic groups" should not be user-facing vocabulary. Use support
  readiness/readiness groups with checks, status, source, and next action.

## Backend Notes

Existing backend routes already available and expected to be reused:

```text
GET    /api/v1/sites
POST   /api/v1/sites
GET    /api/v1/maritime/vessels
POST   /api/v1/maritime/vessels
GET    /api/v1/maritime/vessels/{vessel_id}
PATCH  /api/v1/maritime/vessels/{vessel_id}
DELETE /api/v1/maritime/vessels/{vessel_id}
GET    /api/v1/link/sites/{site_id}/status
GET    /api/v1/link/sites/{site_id}/budget
PUT    /api/v1/link/sites/{site_id}/budget
GET    /api/v1/link/sites/{site_id}/queue
GET    /api/v1/link/sites/{site_id}/probes
POST   /api/v1/link/sites/{site_id}/probes
GET    /api/v1/link/sites/{site_id}/policies
PUT    /api/v1/link/sites/{site_id}/policies
GET    /api/v1/support/bundles
POST   /api/v1/support/bundles
POST   /api/v1/support/sessions
POST   /api/v1/support/tunnels
POST   /api/v1/support/break-glass
GET    /api/v1/support/onboarding-checks
POST   /api/v1/support/onboarding-checks/run
GET    /api/v1/billing/meters
GET    /api/v1/billing/usage
GET    /api/v1/billing/invoice-runs
GET    /api/v1/maritime/billing/usage
GET    /api/v1/maritime/billing/rollups
GET    /api/v1/maritime/support/diagnostics
GET    /api/v1/maritime/support/checklist
```

New backend routes planned for core link connections:

```text
GET    /api/v1/link/sites/{site_id}/connections
POST   /api/v1/link/sites/{site_id}/connections
PATCH  /api/v1/link/sites/{site_id}/connections/{connection_id}
DELETE /api/v1/link/sites/{site_id}/connections/{connection_id}
GET    /api/v1/link/sites/{site_id}/connections/selection
```

Current highest migration file is `0036_core_support.py`. The plan reserves:

```text
backend/src/argus/migrations/versions/0037_core_link_connections.py
```

Before writing migrations, confirm:

```bash
ls backend/src/argus/migrations/versions/*.py | sed -E 's#.*/([0-9]+).*#\1#' | sort -n | tail -1
```

If the result is no longer `0036`, choose the next free migration number and
update the task locally before writing the migration.

## Frontend Notes

Current FleetOps pages:

```text
frontend/src/pages/FleetOps.tsx
frontend/src/pages/FleetOpsVessels.tsx
frontend/src/pages/FleetOpsVesselDetail.tsx
frontend/src/pages/FleetOpsEvidence.tsx
frontend/src/pages/FleetOpsBilling.tsx
frontend/src/pages/FleetOpsSupport.tsx
frontend/src/pages/FleetOpsOnboarding.tsx
```

Current hook gaps:

- `frontend/src/hooks/use-maritime.ts` has read hooks but no vessel mutations.
- `frontend/src/hooks/use-link.ts` has read hooks but needs connection and
  queue/probe/policy/budget mutations.
- `frontend/src/hooks/use-support.ts` has read hooks but needs bundle, session,
  tunnel, break-glass, and onboarding-run mutations.
- `frontend/src/hooks/use-billing.ts` should provide typed FleetOps billing
  page list hooks if not already present in the local branch state.

Use existing surfaces:

- `frontend/src/components/ui/dialog.tsx`
- `frontend/src/components/layout/workspace-surfaces.tsx`
- `frontend/src/components/layout/command-surfaces.tsx`

Use Lucide icons for visible action buttons when icons are useful.

## Non-Negotiable Constraints

Preserve all `CC-*` constraints from:

```text
docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md
```

The important boundary for this follow-up:

- `CC-4 Link Is Core`: satellite, LTE, 5G, Wi-Fi, fiber, ethernet, and other
  are core link connection transport kinds, not maritime-only link types.
- Maritime carrier terminals remain pack-owned and map into core connections
  through `site_id`.
- Core link/fleet/billing/support must not contain `Vessel`, `Voyage`,
  `PortCall`, AIS, NMEA, `CarrierTerminal`, owner, manager, or charterer
  fields.
- Traffic/public-space remains manifest-only.
- Home/lab testing remains packless engine validation, not a pack or UI.

Stop if a task appears to require:

- relaxing any `CC-*` constraint
- moving a vertical noun into core
- implementing traffic/public-space runtime
- adding a home-lab pack, `lab_only` status, or home-lab UI
- adding proprietary carrier SDK integrations
- adding payment processor or accounting integrations
- changing runtime detector semantics outside the plan

## Validation Targets

At minimum, the implementation should end with:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link tests/maritime tests/api/test_link_routes.py tests/api/test_maritime_routes.py tests/api/test_support_routes.py tests/api/test_openapi_export.py tests/core/test_packless_empty_registry.py tests/e2e/test_maritime_fleetops_smoke.py -q
python3 -m uv run ruff check src tests
python3 -m uv run mypy src/argus

cd /Users/yann.moren/vision/frontend
corepack pnpm test --run
corepack pnpm build
corepack pnpm lint

cd /Users/yann.moren/vision/installer
python3 -m uv run pytest tests/test_macos_master_artifacts.py tests/test_linux_master_artifacts.py tests/test_edge_installer_artifacts.py -q
python3 -m uv run pytest -q
```

Then run a real-stack FleetOps Playwright smoke:

```bash
cd /Users/yann.moren/vision
CI=true corepack pnpm exec playwright test e2e/fleetops.spec.ts
```

The smoke should prove:

- FleetOps icon exposes child navigation.
- Vessels page can add a vessel.
- Created vessel detail shows connectivity.
- Evidence, Billing, Support, and Onboarding load from rail links.
- Support and Onboarding are visibly distinct.
- Link posture can represent satellite, LTE/5G, Wi-Fi, fiber, ethernet, and
  other where fixtures/API data provide those transports.

## MacBook Appliance Notes

The local appliance install uses:

```text
/opt/vezor/current -> /Users/yann.moren/vision
/etc/vezor/master.json
```

The short command:

```bash
/opt/vezor/current/bin/vezor-master up --config /etc/vezor/master.json
```

restarts existing images. To rebuild UI/backend images from this branch, rerun
the installer from `/opt/vezor/current` after pulling the branch:

```bash
cd /opt/vezor/current
git checkout codex/sceneops-pack-registry
git pull --ff-only origin codex/sceneops-pack-registry

MASTER_PUBLIC_HOST="192.168.1.166"
MASTER_PUBLIC_URL="http://${MASTER_PUBLIC_HOST}:3000"

sudo ./installer/macos/install-master.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "$MASTER_PUBLIC_URL" \
  --data-dir /var/lib/vezor
```

Do not run installer rebuilds until implementation has a checkpoint worth
testing.

## Workspace Notes

The workspace has unrelated untracked files. Do not stage them.

Known unrelated untracked files/directories include:

```text
.claude/
.codex/
.playwright-mcp/
.superpowers/brainstorm/
.vite/
Capture d'écran*.png
camera-capture.md
codex-review-findings.md
docs/brand/*.png
docs/strategy/2026-06-04-vezor-unique-proposition-blueprint.md
docs/strategy/vezor-market-positioning-report.md
docs/superpowers/plans/2026-05-16-browser-delivery-overlays-and-profile-grid.md
taste-skill/
```

Use explicit `git add` commands with concrete file paths. Do not use
`git add -A`.

## Suggested Start Commands

```bash
cd /Users/yann.moren/vision
git fetch origin
git checkout codex/sceneops-pack-registry
git pull --ff-only origin codex/sceneops-pack-registry
git rev-parse HEAD
git status --short
```

Expected HEAD is `1e567fe8c90ded31b5a3b597648545b2dffb0ea6` or newer.

## Prompt For Next Chat

```text
Follow-up from /Users/yann.moren/vision/docs/superpowers/status/2026-06-06-next-chat-fleetops-operator-completion-handoff.md

Continue branch codex/sceneops-pack-registry from origin at 1e567fe8c90ded31b5a3b597648545b2dffb0ea6 or newer. Do not create a new branch unless I explicitly ask. Do not merge to main unless I explicitly ask.

Read first:
- /Users/yann.moren/vision/docs/superpowers/status/2026-06-06-next-chat-fleetops-operator-completion-handoff.md
- /Users/yann.moren/vision/docs/superpowers/specs/2026-06-06-fleetops-operator-completion-design.md
- /Users/yann.moren/vision/docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md
- /Users/yann.moren/vision/docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md
- /Users/yann.moren/vision/docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md
- /Users/yann.moren/vision/docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md
- /Users/yann.moren/vision/docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md
- /Users/yann.moren/vision/docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md
- /Users/yann.moren/vision/packs/README.md
- /Users/yann.moren/vision/packs/maritime-fleet/pack.yaml
- /Users/yann.moren/vision/packs/traffic-public-space/pack.yaml

Use Superpowers, preferably subagent-driven-development, and begin implementation from docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md.

Start with Gate 1 Task 1: FleetOps Rail Navigation. Use TDD. Follow the plan's atomic commit policy, commit focused changes, and push origin codex/sceneops-pack-registry at implementation checkpoints.

Preserve all CC-* constraints. If a task requires relaxing a constraint, changing a cross-cutting decision, or moving a vertical noun into core, stop and surface the conflict.

Do not implement traffic/public-space runtime, home-lab packs, lab_only status, public-space demos, traffic UI, proprietary carrier SDK integrations, payment processor/accounting integrations, or runtime semantic changes outside the plan.

Do not stage unrelated scratch files or taste-skill/. Do not use git add -A.
```
