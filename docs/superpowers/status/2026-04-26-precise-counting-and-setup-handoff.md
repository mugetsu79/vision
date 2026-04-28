# Precise Counting And Setup Handoff

Date: 2026-04-28

Purpose: paste this document into a fresh project chat to continue from the current repo state without redoing completed setup, source-aware delivery, native routing, History work, Fleet / Operations phase 1, logo cleanup, or worker lifecycle reasoning.

## Current Branch State

Active branch:
- `codex/source-aware-delivery-calibration-fixes`

Remote state:
- `origin/codex/source-aware-delivery-calibration-fixes` contains all implementation work through `24b7935` plus follow-up docs and brand cleanup commits.
- The branch may also contain handoff-only commits after `24b7935`; treat `24b7935` as the verified implementation checkpoint for worker command UX, not necessarily the branch tip.
- The old handoff branch `codex/precise-counting-occupancy` is not the active continuation branch for this work.

Latest relevant commits:
- `docs(operations): sync long-lived deployment docs`
- `24b7935 fix(operations): make dev worker command copy pasteable`
- `fa94d88 docs(handoff): refresh operations and logo status`
- `1d2ee26 fix(brand): remove logo background tile`
- `f7ca875 fix(brand): use uploaded argus icon logo`
- `f00499f fix(operations): satisfy generated type checks`
- `921f04a feat(operations-ui): label settings route as operations`
- `baf29e9 feat(operations-ui): replace settings with fleet workbench`
- `4933860 feat(operations-ui): add fleet operations hooks`
- `bed9ec0 feat(operations): expose edge bootstrap material`
- `cf54f3f feat(operations): derive fleet worker lifecycle overview`
- `874d3bd feat(operations): add fleet operations API contracts`
- `bfce5dc docs(handoff): refresh next chat context`
- `d9da189 docs(operations): spec fleet workbench lifecycle plan`
- `a41f8e2 fix(history): mark unproven empty buckets as gaps`

To update another dev machine:

```bash
cd ~/vision
git fetch origin
git switch codex/source-aware-delivery-calibration-fixes
git pull --rebase origin codex/source-aware-delivery-calibration-fixes
git log --oneline -5
```

Expected result:
- the recent history includes `24b7935 fix(operations): make dev worker command copy pasteable`
- the recent history includes `docs(operations): sync long-lived deployment docs`
- the recent history includes `docs(handoff): refresh operations and logo status`
- the recent history includes `1d2ee26 fix(brand): remove logo background tile`

## Current Baseline

These items are complete and should not be re-planned:

- camera PATCH command publishing regression is fixed by `CameraCommandPayload`
- destination world-plane point ordering is fixed with y-up destination coordinate handling
- setup preview still capture works from the UI
- Calibration uses a still-backed analytics/source frame concept
- boundary authoring supports visual line and polygon workflows with normalized zone storage
- source capability persistence and probing are in place
- invalid browser profiles such as `1080p15` are suppressed for 720p sources
- camera wizard/table/live UI expose source capability and native-unavailable reasons
- central native browser delivery routes through processed stream access instead of fragile passthrough relay startup
- History follow-now, zero/no-telemetry semantics, unified search, bucket review, exports, and accessibility fixes are implemented
- Fleet / Operations phase 1 is implemented under `/settings`
- Settings is relabeled as Operations in app navigation
- the product logo now uses `argus-icon-from-upload.svg`, with the dark background tile removed so the sidebar mark renders on transparent canvas
- Operations dev worker commands are copy/paste-safe and fetch a local dev bearer token instead of emitting a literal bearer-token placeholder.
- Root README, active design docs, product spec, runbook, operator deployment playbook, and iMac/Orin lab guide have been refreshed to describe the Operations workbench, dev worker command bridge, and production supervisor lifecycle model.

## Fleet / Operations Phase 1

Implemented behavior:

- Backend exposes `GET /api/v1/operations/fleet`.
- Backend exposes `POST /api/v1/operations/bootstrap`.
- Fleet overview derives:
  - central and edge node summaries
  - desired worker count
  - running/stale/offline/unknown node summaries
  - per-camera lifecycle owner
  - runtime state from currently available heartbeat data
  - camera assignment visibility
  - native delivery diagnostics
- Edge bootstrap wraps edge registration and returns one-time bootstrap material plus a dev compose command.
- Frontend adds `use-operations` hooks.
- `frontend/src/pages/Settings.tsx` is now the Fleet and operations workbench.
- The UI supports:
  - summary tiles
  - manual dev mode / supervised / mixed mode context
  - node list
  - bootstrap edge node form
  - desired camera worker cards
  - delivery diagnostics
- Phase 1 intentionally does not start, stop, or restart host processes from the browser.

Important constraint:
- Current edge heartbeats still do not report true per-worker process state. The UI/service must continue to represent missing precision as `not_reported`, `stale`, `offline`, or `unknown` rather than inventing a running state.

Lifecycle control note:
- The product should eventually expose Start, Stop, Restart, and Drain buttons in Operations.
- Those buttons should not make the backend shell out directly.
- The intended production path is UI action -> backend desired-state or lifecycle request -> central or edge supervisor reconciles the process on the correct node -> worker reports runtime truth.
- Dev uses copyable shell commands because there is not yet a local dev supervisor process. That is a temporary bridge, not the production control model.
- The Fleet / Operations design doc records this under `Start/Stop Button Model`; the root README, umbrella operator-hardening design, product spec, runbook, operator deployment playbook, and iMac/Orin lab guide now carry the same model.

## Product Model To Preserve

Important concepts:

- Analytics/calibration frame and browser delivery profile are separate concepts.
- Boundaries and homography should be defined against the analytics frame, not the browser rendition.
- Browser delivery options should be source-aware and truthful.
- Native availability should be represented as an explicit status and reason, not implied from hardcoded profile options.
- History must distinguish:
  - populated buckets
  - valid zero-detection buckets
  - no telemetry / unproven gaps
- Worker lifecycle must distinguish:
  - desired state: what the backend wants running
  - runtime state: what supervisors/workers report
  - dev/manual mode: terminal or compose commands
  - production/supervised mode: a supervisor owns process start/stop/restart
- UI lifecycle controls should change desired state or send a constrained supervisor request. They should never become generic remote shell execution.
- Bootstrap material can contain secrets. Show it once, do not persist plaintext API keys, and do not leak it into logs, docs, screenshots, or chat summaries.

## Latest Verification

Fresh verification after the Operations and logo work:

Backend:
- `python3 -m uv run pytest tests/services/test_operations_service.py tests/api/test_operations_endpoints.py -q`
  - `5 passed`
- `python3 -m uv run ruff check src/argus/services/app.py tests/services/test_operations_service.py`
  - passed

Frontend:
- `corepack pnpm --dir frontend exec vitest run src/hooks/use-operations.test.ts src/pages/Settings.test.tsx src/components/layout/AppShell.test.tsx src/brand/product-assets.test.ts`
  - `11 passed`
- `corepack pnpm --dir frontend exec eslint src/brand/product-assets.test.ts`
  - passed
- `corepack pnpm --dir frontend build`
  - passed after the final logo cleanup

Browser smoke:
- Reloaded `http://localhost:3000/settings`.
- Confirmed the Operations page renders.
- Confirmed the sidebar logo uses `/brand/product-symbol-ui.svg` and no longer shows the dark boxed background.

Known non-blocking validation issue:
- Full `corepack pnpm --dir frontend lint` still fails on pre-existing unrelated files outside the logo/operations patch. Do not treat those lint failures as part of the logo cleanup unless the next task is specifically to pay down lint debt.

Docs verification:
- `git diff --check`
  - passed for the README, design doc, handoff, product spec, runbook, operator deployment playbook, and iMac/Orin lab guide updates
- targeted stale-doc search checked for the deprecated container-venv Alembic path, unsafe bearer-token placeholders, and stale Settings-page language

Earlier History verification on this branch:
- `python3 -m uv run pytest tests/services/test_history_service.py tests/api/test_history_endpoints.py tests/api/test_export_endpoints.py -q`
  - `38 passed`
- targeted backend `ruff` and `mypy` checks for the History contract passed
- targeted History frontend tests passed
- History Playwright prompt 9 spec passed

## Immediate Next Step

Recommended next-chat starting point:

1. Pull `codex/source-aware-delivery-calibration-fixes` on the iMac and confirm recent history includes `24b7935 fix(operations): make dev worker command copy pasteable`.
2. Recreate backend and frontend containers so the new API and UI assets are active:

```bash
make dev-up
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend frontend
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
corepack pnpm --dir frontend generate:api
```

3. Open `http://127.0.0.1:3000/settings`.
4. Validate:
   - the nav says Operations
   - the Operations page loads
   - the transparent uploaded Argus logo renders cleanly
   - node and worker state is truthful for the current dev setup
   - copied central worker commands include token fetch and `ARGUS_API_BEARER_TOKEN="$TOKEN"`
   - bootstrap material can be generated without exposing secrets beyond the one-time UI result
5. If browser assets look stale, hard refresh with `Cmd+Shift+R`.

## Secondary Future Task

After iMac validation of Fleet / Operations phase 1, continue with the open-vocab hybrid detector track.

Reference docs:
- `docs/superpowers/specs/2026-04-26-open-vocab-hybrid-detector-design.md`
- `docs/superpowers/plans/2026-04-26-open-vocab-hybrid-detector-implementation-plan.md`

Important note:
- Natural-language history/search can become richer once open-vocab hybrid detection exists.
- Do not mix open-vocab implementation into Fleet / Operations validation or follow-up bug fixes.

## Known Follow-Up Risks

Operations risks:

- `EdgeHeartbeatRequest` reports only `node_id`, `version`, and camera count. Per-worker runtime state is not available yet.
- Existing scheduler is minimal and not yet a production supervisor contract.
- Bootstrap returns secret material and must show it once only; do not persist plaintext secrets.
- Delivery diagnostics must not expose RTSP credentials, JWTs, API keys, or NATS seeds.

Validation risks:

- Native central routing is code-fixed, but should still be validated on the real target camera/runtime after pulling the branch.
- Source capability migration `0005_source_capability.py` must be applied in any redeployed database before the camera list endpoint reads `cameras.source_capability`.
- If `frontend/src/lib/api.generated.ts` changes during iMac setup, inspect and commit that change only if it is an expected OpenAPI regeneration from the current backend.

## Useful Files For The Next Chat

Backend:
- `backend/src/argus/api/contracts.py`
- `backend/src/argus/api/v1/operations.py`
- `backend/src/argus/api/v1/edge.py`
- `backend/src/argus/api/v1/__init__.py`
- `backend/src/argus/services/app.py`
- `backend/tests/services/test_operations_service.py`
- `backend/tests/api/test_operations_endpoints.py`
- `backend/src/argus/inference/engine.py`
- `backend/src/argus/inference/scheduler.py`
- `backend/src/argus/models/tables.py`
- `backend/src/argus/migrations/versions/0005_source_capability.py`

Frontend:
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/Settings.test.tsx`
- `frontend/src/hooks/use-operations.ts`
- `frontend/src/hooks/use-operations.test.ts`
- `frontend/src/components/layout/TopNav.tsx`
- `frontend/src/components/layout/AppShell.test.tsx`
- `frontend/src/components/layout/ProductLockup.tsx`
- `frontend/src/components/layout/ProductLockup.test.tsx`
- `frontend/src/brand/product-assets.test.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.generated.ts`
- `frontend/public/brand/product-symbol-ui.svg`
- `frontend/public/brand/product-lockup-ui.svg`

Brand assets:
- `argus-icon-from-upload.svg`
- `docs/brand/assets/source/argus-icon-from-upload.svg`
- `docs/brand/assets/source/vezor-symbol-product-ui.svg`
- `docs/brand/assets/source/vezor-lockup-product-ui.svg`

Infra:
- `infra/docker-compose.dev.yml`
- `infra/docker-compose.edge.yml`
- `infra/helm/argus/values.yaml`
- `infra/helm/argus/templates/deployment-edge-worker.yaml`

Docs:
- `README.md`
- `product-spec-v4.md`
- `docs/runbook.md`
- `docs/operator-deployment-playbook.md`
- `docs/superpowers/specs/2026-04-26-operator-setup-history-delivery-hardening-design.md`
- `docs/superpowers/specs/2026-04-28-fleet-operations-workbench-design.md`
- `docs/superpowers/plans/2026-04-28-fleet-operations-workbench-implementation-plan.md`
- `docs/imac-master-orin-lab-test-guide.md`
