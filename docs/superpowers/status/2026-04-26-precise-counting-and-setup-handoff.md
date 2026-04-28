# Precise Counting And Setup Handoff

Date: 2026-04-28

Purpose: paste this document into a fresh project chat to continue from the current repo state without redoing completed setup, source-aware delivery, native routing, or History work.

## Current branch state

Active branch:
- `codex/source-aware-delivery-calibration-fixes`

Important branch note:
- `origin/codex/source-aware-delivery-calibration-fixes` is pushed through `a41f8e2`.
- Local branch also has `d9da189` with the new Fleet / Operations spec and implementation plan.
- Push the branch before testing from another machine if that machine needs the Fleet / Operations docs.

Latest relevant commits:
- `d9da189 docs(operations): spec fleet workbench lifecycle plan`
- `a41f8e2 fix(history): mark unproven empty buckets as gaps`
- `275c22c fix(history): scope default queries and expose bucket picker`
- `dcf07e3 fix(history): use raw count events for partial buckets`
- `0a88ee3 fix(history): refresh following windows and use exclusive ends`
- `c96dcf4 fix: route central native delivery through processed stream`
- `67b3711 fix: probe source profiles in camera wizard`
- `37b0614 feat: add source-aware delivery and setup fixes`
- `8a556e7 fix(setup): harden calibration still capture`

## Current baseline

These handoff items are done and should not be re-planned:

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

The old handoff branch `codex/precise-counting-occupancy` is no longer the active continuation branch for this work.

## Current product model

Important concepts to preserve:

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

## Latest verification

After the final History coverage fix on `a41f8e2`, these passed:

Backend:
- `python3 -m uv run pytest tests/services/test_history_service.py tests/api/test_history_endpoints.py tests/api/test_export_endpoints.py -q`
  - `38 passed`
- `python3 -m uv run ruff check src/argus/models/enums.py src/argus/api/contracts.py src/argus/services/app.py tests/services/test_history_service.py tests/api/test_history_endpoints.py tests/api/test_export_endpoints.py`
  - passed
- `python3 -m uv run mypy src/argus/services/app.py src/argus/api/contracts.py`
  - passed

Frontend:
- `corepack pnpm --dir frontend exec vitest run src/lib/history-url-state.test.ts src/lib/history-workbench.test.ts src/lib/history-search.test.ts src/components/history/HistoryTrendChart.test.tsx src/pages/History.test.tsx`
  - `51 passed`
- `corepack pnpm --dir frontend build`
  - passed
- `CI=1 corepack pnpm --dir frontend exec playwright test e2e/prompt9-history-and-incidents.spec.ts`
  - `3 passed`

The Fleet / Operations documents in `d9da189` are docs-only and were self-reviewed plus staged with `git diff --cached --check` before commit.

## Primary next task

Implement the Fleet / Operations workbench.

Use these docs as the source of truth:

Spec:
- `docs/superpowers/specs/2026-04-28-fleet-operations-workbench-design.md`

Plan:
- `docs/superpowers/plans/2026-04-28-fleet-operations-workbench-implementation-plan.md`

Implementation mode:
- Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`.
- Follow the implementation plan task-by-task.
- Keep the first phase read-first and safe:
  - fleet overview
  - desired worker state
  - runtime status summary from current heartbeat data
  - camera assignment visibility
  - source/native/transcode diagnostics
  - edge bootstrap material
  - manual dev run commands

Do not implement direct process start/stop from the browser in phase 1.

The intended lifecycle model:

- Dev:
  - platform services are started by Docker Compose
  - camera workers are started manually with `argus.inference.engine --camera-id ...`
  - edge dev can use `infra/docker-compose.edge.yml`
- Production:
  - a central or edge supervisor owns worker processes
  - backend stores/derives desired worker state
  - supervisors reconcile desired state to actual processes
  - UI shows and changes desired state, or sends lifecycle requests to supervisors
  - UI never shells into the host

## Secondary future task

After Fleet / Operations phase 1, continue with the open-vocab hybrid detector track.

Reference docs:
- `docs/superpowers/specs/2026-04-26-open-vocab-hybrid-detector-design.md`
- `docs/superpowers/plans/2026-04-26-open-vocab-hybrid-detector-implementation-plan.md`

Important note:
- Natural-language history/search can become richer once open-vocab hybrid detection exists.
- Do not mix open-vocab implementation into Fleet / Operations phase 1.

## Known follow-up risks

Fleet / Operations implementation risks:

- Current `EdgeHeartbeatRequest` reports only `node_id`, `version`, and camera count. Per-worker runtime state is not available yet.
- Phase 1 should represent per-camera runtime as `not_reported`, `stale`, `offline`, or `unknown` rather than inventing false precision.
- Existing scheduler is minimal and not yet a product supervisor contract.
- Bootstrap returns secret material and must show it once only; do not persist plaintext secrets.
- Delivery diagnostics must not expose RTSP credentials, JWTs, API keys, or NATS seeds.

Validation risks:

- Native central routing is code-fixed, but should still be validated on the real target camera/runtime after pulling the branch.
- Source capability migration `0005_source_capability.py` must be applied in any redeployed database before the camera list endpoint reads `cameras.source_capability`.

## Useful files for the next chat

Backend:
- `backend/src/argus/api/contracts.py`
- `backend/src/argus/api/v1/edge.py`
- `backend/src/argus/api/v1/__init__.py`
- `backend/src/argus/services/app.py`
- `backend/src/argus/inference/engine.py`
- `backend/src/argus/inference/scheduler.py`
- `backend/src/argus/models/tables.py`
- `backend/src/argus/migrations/versions/0005_source_capability.py`

Frontend:
- `frontend/src/pages/Settings.tsx`
- `frontend/src/components/layout/TopNav.tsx`
- `frontend/src/components/layout/AppShell.test.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/api.generated.ts`

Infra:
- `infra/docker-compose.dev.yml`
- `infra/docker-compose.edge.yml`
- `infra/helm/argus/values.yaml`
- `infra/helm/argus/templates/deployment-edge-worker.yaml`

Docs:
- `docs/superpowers/specs/2026-04-28-fleet-operations-workbench-design.md`
- `docs/superpowers/plans/2026-04-28-fleet-operations-workbench-implementation-plan.md`
- `docs/imac-master-orin-lab-test-guide.md`
