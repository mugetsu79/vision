# Maritime FleetOps Runtime Implementation Handoff

Date: 2026-06-05
Current branch: `codex/sceneops-pack-registry`
Current pushed HEAD: `a277e3f2acc4e4ac48884440b1b2263456f03ba8`

## Current State

The read-only SceneOps pack registry work is implemented on
`codex/sceneops-pack-registry`. The branch now also contains the canonical
Maritime FleetOps runtime spec and hardened implementation plan for building the
full working product.

The next chat should continue this same branch, start implementation from the
hardened plan, commit focused changes as tasks progress, and push to
`origin/codex/sceneops-pack-registry`.

Do not create a new branch unless the user explicitly asks. This branch is the
development branch for the FleetOps runtime implementation.

## Files To Read First

Read these in order:

1. `docs/superpowers/status/2026-06-05-next-chat-maritime-fleetops-runtime-implementation-handoff.md`
2. `docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md`
3. `docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md`
4. `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`
5. `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
6. `docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md`
7. `packs/README.md`
8. `packs/maritime-fleet/pack.yaml`
9. `packs/traffic-public-space/pack.yaml`

## What Is Already Done On This Branch

- Read-only pack registry and pack API are implemented and pushed.
- Installer/backend build-context alignment is fixed and pushed.
- Maritime FleetOps runtime spec is expanded to full-product scope.
- Cross-cutting constraints appendix exists in the spec with stable `CC-*` IDs.
- Implementation plan exists and has been hardened after review:
  - atomic commit policy for large tasks
  - hard stop if any task would relax a cross-cutting constraint
  - dynamic migration numbering
  - empty-pack-registry API tests for core domains
  - file-based OpenAPI export
  - backend/supervisor split for support tunnel tests
  - real docker-compose Playwright product smoke
  - final packless verification and constraint traceability

Latest pushed commits:

```text
a277e3f2 docs: harden fleetops implementation plan
cabc127d docs: plan maritime fleetops runtime implementation
d7b74d2e docs: integrate fleetops spec review feedback
1ad7fa92 docs: expand fleetops spec to full product
35e69087 docs: add fleet baseline to fleetops spec
150e4f04 docs: add argus link baseline to fleetops spec
e5788676 docs: specify maritime fleetops runtime pack
53476b3c fix: align installer backend build context
```

## Implementation Scope For Next Chat

Use:

```text
docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md
```

Start with Gate 1, Task 1: Core Link Baseline.

Use Superpowers, preferably `superpowers:subagent-driven-development`, and
execute the plan task-by-task with TDD:

1. Write failing tests.
2. Run them red.
3. Implement minimal product code.
4. Run them green.
5. Commit focused changes.
6. Push `codex/sceneops-pack-registry` to origin at sensible checkpoints.

For large tasks, follow the plan's atomic commit policy rather than making one
large commit per task.

## Non-Negotiable Constraints

Preserve the spec's cross-cutting constraints:

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

If a task appears to require relaxing a `CC-*` constraint, changing a
cross-cutting decision, or moving a vertical noun into core to make a test pass,
stop and surface the conflict. Do not silently work around the constraint.

## Explicit Non-Goals

Do not implement or add:

- traffic/public-space runtime code, routes, migrations, UI, demos, or product
  surfaces
- `backend/src/argus/traffic_public_space`
- a home-lab pack, home-lab dashboard, or `lab_only` status
- public-space demos or traffic UI
- payment processor or accounting-system integrations
- proprietary carrier SDK integrations
- runtime semantic changes that bypass current scene contracts, camera
  configuration, evidence, or runtime passport behavior

Traffic/Public-Space remains manifest-only with status
`designed_not_implemented`. Home-lab car/person/road testing remains packless
engine validation.

## Workspace Notes

- Continue from `origin/codex/sceneops-pack-registry` at `a277e3f2` or newer.
- Do not stage unrelated scratch files.
- Do not stage `taste-skill/`.
- Do not use `git add -A`; the workspace has unrelated untracked files.
- Keep commits focused and push the branch when implementation checkpoints are
  complete.
- Prefer `rg` for search and `apply_patch` for manual edits.

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

## Suggested Start Commands

```bash
cd /Users/yann.moren/vision
git fetch origin
git checkout codex/sceneops-pack-registry
git pull --ff-only origin codex/sceneops-pack-registry
git rev-parse HEAD
git status --short
```

Expected HEAD is `a277e3f2acc4e4ac48884440b1b2263456f03ba8` or newer.

Before writing migrations in Task 1, reserve migration numbers:

```bash
ls backend/src/argus/migrations/versions/*.py | sed -E 's#.*/([0-9]+).*#\1#' | sort -n | tail -1
```

Expected today: `0029`.

## Prompt For Next Chat

```text
Follow-up from /Users/yann.moren/vision/docs/superpowers/status/2026-06-05-next-chat-maritime-fleetops-runtime-implementation-handoff.md

Continue branch codex/sceneops-pack-registry from origin at a277e3f2 or newer. Do not create a new branch unless I explicitly ask.

Read first:
- /Users/yann.moren/vision/docs/superpowers/status/2026-06-05-next-chat-maritime-fleetops-runtime-implementation-handoff.md
- /Users/yann.moren/vision/docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md
- /Users/yann.moren/vision/docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md
- /Users/yann.moren/vision/docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md
- /Users/yann.moren/vision/docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md
- /Users/yann.moren/vision/docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md
- /Users/yann.moren/vision/packs/README.md
- /Users/yann.moren/vision/packs/maritime-fleet/pack.yaml
- /Users/yann.moren/vision/packs/traffic-public-space/pack.yaml

Use Superpowers, preferably subagent-driven-development, and begin implementation from docs/superpowers/plans/2026-06-05-maritime-fleetops-runtime-pack.md.

Start with Gate 1 Task 1: Core Link Baseline. Use TDD. Follow the plan's atomic commit policy, commit focused changes, and push origin codex/sceneops-pack-registry at implementation checkpoints.

Preserve all CC-* constraints. If a task requires relaxing a constraint, changing a cross-cutting decision, or moving a vertical noun into core, stop and surface the conflict.

Do not implement traffic/public-space runtime, home-lab packs, lab_only status, public-space demos, traffic UI, proprietary carrier SDK integrations, payment processor/accounting integrations, or runtime semantic changes outside the plan.

Do not stage unrelated scratch files or taste-skill/. Do not use git add -A.
```
