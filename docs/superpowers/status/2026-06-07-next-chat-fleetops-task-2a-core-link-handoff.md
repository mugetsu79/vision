# FleetOps Task 2A And Core Link Workspace Next-Chat Handoff

> Superseded by
> `docs/superpowers/status/2026-06-07-next-chat-core-link-reflector-completion-handoff.md`.
> This file is retained as the historical handoff from before FleetOps Task 2A,
> the Core Link workspace, edge-agent probes, and master reflector work were
> implemented.

Date: 2026-06-07
Current branch: `codex/sceneops-pack-registry`
Implementation base before this handoff doc: `87872f70`

## Intent For The Next Chat

Continue the same branch and implement in this order:

1. `docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md`
   - Start at `Task 2A: Vessel List Search Filters And Pagination`.
2. `docs/superpowers/plans/2026-06-07-core-link-performance-workspace.md`
   - After Task 2A is implemented, verified, committed, and pushed, begin
     `Gate 1: Backend Summary`.

Use Superpowers. Prefer `superpowers:subagent-driven-development` for the
implementation work and `superpowers:test-driven-development` for each task.
Follow each plan task-by-task with red/green tests, focused commits, and pushes
to `origin codex/sceneops-pack-registry` at implementation checkpoints.

Do not create a new branch unless the user explicitly asks. Do not merge to
`main` unless the user explicitly asks.

## Read First

Read these in order:

1. `docs/superpowers/status/2026-06-07-next-chat-fleetops-task-2a-core-link-handoff.md`
2. `docs/superpowers/specs/2026-06-06-fleetops-operator-completion-design.md`
3. `docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md`
4. `docs/superpowers/specs/2026-06-07-core-link-performance-workspace-design.md`
5. `docs/superpowers/plans/2026-06-07-core-link-performance-workspace.md`
6. `docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md`
7. `docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md`
8. `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
9. `docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md`
10. `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`
11. `packs/README.md`
12. `packs/maritime-fleet/pack.yaml`
13. `packs/traffic-public-space/pack.yaml`

The 2026-06-05 docs remain binding for pack boundaries and all `CC-*`
constraints. The 2026-06-06 FleetOps operator plan and the 2026-06-07 Core Link
workspace plan are the active implementation targets.

## Current State

Latest pushed commits before this handoff:

```text
87872f70 docs: plan fleetops vessel list controls
7c840d79 docs: plan core link performance workspace
1e4a20fb fix: paginate operator list surfaces
38e7af96 fix: align operator focus selectors
0dc36660 feat: focus scene-heavy operator views
```

At the time of this historical handoff, Task 2A was still pending. It is now
implemented on `codex/sceneops-pack-registry` through commits including
`8aa3ea50` and `0cbc39ab`.

At the time of this historical handoff, the Core Link Performance Workspace had
not landed yet. It is now implemented through commit `fca544f1` and extended by
the edge-agent/master-reflector work.

The working tree currently has unrelated untracked files and directories,
including `.claude/`, `.codex/`, `.playwright-mcp/`, `.superpowers/`, `.vite/`,
screenshots, `docs/brand/`, old strategy docs, and `taste-skill/`. Do not stage
them. Do not use `git add -A`.

## Hard Constraints

Preserve all cross-cutting constraints from the active specs and plans:

- `CC-1 Packless Core Compatibility`
- `CC-2 Pack Boundary`
- `CC-3 Traffic Boundary`
- `CC-4 Link Is Core`
- `CC-5 Fleet Is Core`
- `CC-6 Billing Positioning`
- `CC-7 Support Tunnel`
- `CC-8 Evidence Integrity`
- `CC-9 Frontend Reuse`
- `CC-10 Full Product Scope`

Stop and surface a conflict if a task requires:

- relaxing any `CC-*` constraint
- moving vessel, voyage, port-call, AIS, NMEA, carrier terminal, owner,
  manager, or charterer nouns into core
- changing evidence hash semantics
- changing detector/runtime semantics outside the plan
- implementing traffic/public-space runtime, public-space demos, traffic UI, or
  home-lab packs/status/UI
- integrating proprietary carrier SDKs
- integrating payment processors or accounting systems

Core Link must stay domain-neutral. FleetOps may deep-link into core link by
site ID, but core pages, contracts, services, and tests must not become
maritime-specific.

## First Implementation Target: FleetOps Task 2A

Plan section:

```text
docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md#task-2a-vessel-list-search-filters-and-pagination
```

Goal:

- add searchable FleetOps vessels
- add link-state filtering
- add active/inactive status filtering
- add 10/25/50 pagination, defaulting to 10
- keep true empty fleet state separate from filtered zero-result state
- keep controls URL-backed with `q`, `link`, `status`, `page`, and `pageSize`
- do not auto-open or auto-focus a vessel detail

Expected files:

```text
frontend/src/pages/FleetOpsVessels.tsx
frontend/src/components/fleetops/VesselSummaryTable.tsx
frontend/src/pages/FleetOpsVessels.test.tsx
```

Current product facts:

- `FleetOpsVessels.tsx` already loads vessels through `useMaritimeVessels`.
- `VesselSummaryTable.tsx` already renders vessel name, site ID, link state,
  export status, and active/inactive status.
- `metadata.link_state` is already available for link filtering.
- `active === false` means inactive; any other value is treated as active.
- No backend change is needed for Task 2A.

Task 2A TDD sequence:

1. Add failing tests in `frontend/src/pages/FleetOpsVessels.test.tsx`.
2. Run:

   ```bash
   cd /Users/yann.moren/vision/frontend
   corepack pnpm test --run src/pages/FleetOpsVessels.test.tsx
   ```

   Expected first result: FAIL because the controls do not exist yet.

3. Implement URL-backed list state in `FleetOpsVessels.tsx`.
4. Implement the control surface, filtered empty state, and pagination controls
   in `VesselSummaryTable.tsx`.
5. Run:

   ```bash
   cd /Users/yann.moren/vision/frontend
   corepack pnpm test --run src/pages/FleetOpsVessels.test.tsx
   corepack pnpm build
   ```

   Expected final result: PASS.

6. Commit and push:

   ```bash
   cd /Users/yann.moren/vision
   git add frontend/src/pages/FleetOpsVessels.tsx frontend/src/components/fleetops/VesselSummaryTable.tsx frontend/src/pages/FleetOpsVessels.test.tsx
   git commit -m "feat: add fleetops vessel list controls"
   git push origin codex/sceneops-pack-registry
   ```

After implementation, consider one browser smoke of `/fleetops/vessels` to make
sure the control row is visually usable at desktop and narrow widths.

## Product Expectations For Task 2A

The Vessels page is an inventory/triage page. It may show a paginated table on
load, but it must not implicitly select, open, or focus a vessel detail.

Search must match:

- vessel name
- IMO number
- MMSI
- call sign
- site ID
- embedded site name when available
- link state
- active/inactive status

Filters:

- `Link state`: derived from loaded rows, plus `All link states`
- `Status`: `All statuses`, `Active`, `Inactive`
- `Rows per page`: `10`, `25`, `50`

Changing search, link state, status, or rows per page resets page to `1`.
Invalid query values are normalized in UI behavior.

## Second Implementation Target: Core Link Performance Workspace

Plan:

```text
docs/superpowers/plans/2026-06-07-core-link-performance-workspace.md
```

Spec:

```text
docs/superpowers/specs/2026-06-07-core-link-performance-workspace-design.md
```

Goal:

Add a domain-neutral Core Link Performance workspace outside FleetOps, available
at `/links`, so operators can inspect and operate generic site link health,
connections, budgets, probes, policies, queues, and passports.

Start only after FleetOps Task 2A is committed and pushed.

Implementation checkpoints:

1. Backend link summary route.
2. Link workspace navigation and selected-site shell.
3. Link detail controls and FleetOps deep links.
4. Full verification.

Suggested commit messages from the plan:

```text
feat: add core link summary route
feat: add link performance workspace
feat: wire link workspace controls
test: validate core link workspace
```

## Core Link Gate 1: Backend Summary

Start here:

```text
docs/superpowers/plans/2026-06-07-core-link-performance-workspace.md#gate-1-backend-summary
```

Expected files:

```text
backend/src/argus/link/contracts.py
backend/src/argus/link/__init__.py
backend/src/argus/link/service.py
backend/src/argus/link/api.py
backend/tests/link/test_link_service.py
backend/tests/api/test_link_routes.py
backend/tests/core/test_packless_empty_registry.py
```

Expected route:

```text
GET /api/v1/link/sites/summary
```

Important route detail:

Define `/sites/summary` before `/sites/{site_id}/status` in
`backend/src/argus/link/api.py` so the literal `summary` segment is not captured
as a UUID.

Expected response model:

```text
LinkSiteSummaryResponse
```

Use a named Pydantic response model so OpenAPI generation creates a stable
frontend schema.

Backend verification after Gate 1:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py -q
python3 -m uv run ruff check src/argus/link tests/link tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py
python3 -m uv run mypy src/argus/link
```

Commit and push:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/contracts.py backend/src/argus/link/__init__.py backend/src/argus/link/service.py backend/src/argus/link/api.py backend/tests/link/test_link_service.py backend/tests/api/test_link_routes.py backend/tests/core/test_packless_empty_registry.py
git commit -m "feat: add core link summary route"
git push origin codex/sceneops-pack-registry
```

## Core Link Gate 2: Route And Shell

After the backend summary route is committed:

1. Export OpenAPI.
2. Regenerate frontend API types.
3. Add `useLinkSiteSummaries`.
4. Add `/links` route and `Links` Control nav entry.
5. Add explicit site selector with search and 10/25/50 pagination.
6. Keep detail panels empty until the user explicitly selects a site.

Expected files:

```text
frontend/src/lib/openapi.json
frontend/src/lib/api.generated.ts
frontend/src/hooks/use-link.ts
frontend/src/hooks/use-link.test.ts
frontend/src/app/router.tsx
frontend/src/components/layout/workspace-nav.ts
frontend/src/components/layout/AppShell.test.tsx
frontend/src/pages/Links.tsx
frontend/src/pages/Links.test.tsx
frontend/src/components/link/LinkSiteSelector.tsx
frontend/src/components/link/types.ts
```

Core product rule:

No default site. `/links` shows the search/list shell only. `/links?site=<id>`
shows selected-site detail only for that explicit ID.

Frontend verification:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/hooks/use-link.test.ts src/pages/Links.test.tsx src/components/layout/AppShell.test.tsx
corepack pnpm build
```

Commit and push:

```bash
cd /Users/yann.moren/vision
git add frontend/src/lib/openapi.json frontend/src/lib/api.generated.ts frontend/src/hooks/use-link.ts frontend/src/hooks/use-link.test.ts frontend/src/app/router.tsx frontend/src/components/layout/workspace-nav.ts frontend/src/components/layout/AppShell.test.tsx frontend/src/pages/Links.tsx frontend/src/pages/Links.test.tsx frontend/src/components/link/LinkSiteSelector.tsx frontend/src/components/link/types.ts
git commit -m "feat: add link performance workspace"
git push origin codex/sceneops-pack-registry
```

## Core Link Gate 3: Detail Panels And FleetOps Deep Links

After the `/links` shell works:

Expected link components:

```text
frontend/src/components/link/LinkPosturePanel.tsx
frontend/src/components/link/LinkConnectionsPanel.tsx
frontend/src/components/link/LinkBudgetPolicyPanel.tsx
frontend/src/components/link/LinkProbePanel.tsx
frontend/src/components/link/LinkQueuePanel.tsx
frontend/src/components/link/LinkActionDialogs.tsx
```

Expected FleetOps deep-link files:

```text
frontend/src/pages/FleetOpsVesselDetail.tsx
frontend/src/pages/FleetOpsEvidence.tsx
frontend/src/pages/FleetOpsSupport.tsx
frontend/src/pages/FleetOpsOnboarding.tsx
frontend/src/pages/FleetOps*.test.tsx
```

Only add FleetOps deep links when a specific site or vessel scope exists.
Deep links go to:

```text
/links?site=<site_id>
```

Do not make `/links` maritime-branded. The page title is `Link Performance`,
the route is `/links`, and the nav label is `Links`.

## Final Verification For Core Link Workspace

Run the targeted backend and frontend checks from the plan, then run broader
verification:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link tests/api/test_link_routes.py tests/core/test_packless_empty_registry.py -q
python3 -m uv run pytest tests/api/test_openapi_export.py -q
```

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/hooks/use-link.test.ts src/pages/Links.test.tsx src/components/layout/AppShell.test.tsx
corepack pnpm build
corepack pnpm lint
```

Run the boundary scans:

```bash
cd /Users/yann.moren/vision
rg -n "traffic-public-space|home-lab|lab_only|Intersection|CurbZone|SignalPhase" backend/src frontend/src packs docs/superpowers/specs/2026-06-07-core-link-performance-workspace-design.md docs/superpowers/plans/2026-06-07-core-link-performance-workspace.md
rg -n "Vessel|Voyage|PortCall|AIS|NMEA|CarrierTerminal|owner|charterer" backend/src/argus/link backend/src/argus/fleet backend/src/argus/billing backend/src/argus/support
```

Expected:

- no new traffic/public-space runtime or home-lab product references
- no maritime nouns in core link/fleet/billing/support contracts or services
- docs may mention forbidden words only as constraints or examples

Use the Browser plugin or Playwright to smoke `/links` and `/fleetops/vessels`
after frontend implementation. Confirm:

- `/fleetops/vessels` search, link-state filter, status filter, and 10/25/50
  pagination work
- `/links` has no default site selected
- `/links?site=<site_id>` shows selected-site detail
- search and pagination do not cause page blink or full-page error states
- mobile/narrow layouts do not overlap controls or table content

## Git Rules For The Next Chat

- Stay on `codex/sceneops-pack-registry`.
- Pull/rebase when `origin/codex/sceneops-pack-registry` has advanced; do not
  merge `main`.
- Do not create a new branch unless explicitly asked.
- Do not use `git add -A`.
- Stage only files related to the current checkpoint.
- Do not stage unrelated scratch files or `taste-skill/`.
- Commit after Task 2A.
- Push after Task 2A.
- Commit and push after each Core Link checkpoint.

Suggested first status check:

```bash
cd /Users/yann.moren/vision
git status --short --branch
git rev-parse --short HEAD
git log --oneline -5
```

## Stop Conditions

Stop and ask the user before proceeding if:

- a planned implementation step requires backend server-side vessel pagination
  for Task 2A
- Core Link summary requires moving a FleetOps or maritime noun into
  `argus.link`
- Core Link needs traffic/public-space runtime, public-space demos, traffic UI,
  or home-lab status to satisfy the page
- a test failure points to a cross-cutting decision not covered by the active
  plans
- a proprietary carrier SDK, payment processor, or accounting integration seems
  necessary

## One-Line Next-Chat Starter

Continue branch `codex/sceneops-pack-registry` from this handoff or newer. Use
Superpowers and TDD. Implement
`docs/superpowers/plans/2026-06-06-fleetops-operator-completion.md` Task 2A
first, commit and push, then implement
`docs/superpowers/plans/2026-06-07-core-link-performance-workspace.md` starting
at Gate 1. Preserve all `CC-*` constraints and do not stage unrelated files.
