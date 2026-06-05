# SceneOps Pack Boundary Implementation Handoff

Date: 2026-06-05
Closeout branch: `codex/omnisight-ui-ux-polish`
Next development branch: `codex/sceneops-pack-registry`

## Current State

This handoff closes the strategy/spec/planning slice that followed the OmniSight
UI/UX polish work. The next chat should start a new development branch from
`main` and implement the pack-registry plan.

The spec and plan were tightened after review to automate the no-runtime-pack
directory check, validate `extends` against declared core extension points,
document how `forbidden_dependencies` are enforced, and clarify that
`pack_registry` in `required_capabilities` is an intentional bootstrap
capability.

The strategic decision is now:

- Sell one focused product first: Vezor FleetOps for satellite-connected fleet
  operations.
- Build a domain-neutral SceneOps Engine underneath.
- Treat `maritime-fleet` as the first pack authorized for implementation.
- Treat `traffic-public-space` as `designed_not_implemented`, a manifest-only
  architectural target and not a year-one product, demo, pricing path, or sales
  motion.
- Keep home/lab road/car/person/object testing as engine validation, not as a
  second pack.

## Files To Read First

Read these in order:

1. `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`
2. `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
3. `docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md`
4. `packs/README.md`
5. `packs/maritime-fleet/pack.yaml`
6. `packs/traffic-public-space/pack.yaml`

Older strategy drafts can be used as lineage, but the 2026-06-05 blueprint is
the canonical document for this work.

## What Was Added In This Closeout

- Canonical one-pack SceneOps/FleetOps blueprint.
- Full pack-boundary design spec.
- Detailed implementation plan for a read-only pack registry and API.
- Actual repo-native pack manifests:
  - `maritime-fleet`, status `planned_mvp`
  - `traffic-public-space`, status `designed_not_implemented`
- Pack README explaining the engine/pack boundary and focus rules.

## Verification Completed

The YAML manifests were parsed with Ruby's standard YAML parser:

```text
packs/maritime-fleet/pack.yaml maritime-fleet planned_mvp true
packs/traffic-public-space/pack.yaml traffic-public-space designed_not_implemented false
```

A marker scan found no unresolved planning markers in the new
strategy/spec/plan/manifest documents.

Backend `uv` verification was not run in this closeout because `uv` was not on
the shell PATH and system Python did not have PyYAML installed. The
implementation plan explicitly adds `PyYAML` and `types-PyYAML` as direct
backend dependencies before implementing the registry.

## Implementation Scope For Next Chat

Implement only the plan in:

```text
docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md
```

The plan builds:

- `backend/src/argus/services/pack_registry.py`
- `backend/src/argus/api/v1/packs.py`
- API response contracts in `backend/src/argus/api/contracts.py`
- route registration in `backend/src/argus/api/v1/__init__.py`
- `AppServices.packs` wiring in `backend/src/argus/services/app.py`
- tests for registry, routes, and core noun-boundary governance
- automated assertion that Phase 1 does not create
  `backend/src/argus/maritime` or `backend/src/argus/traffic_public_space`

## Explicit Non-Goals

Do not implement:

- `argus.maritime` runtime entities
- `argus.traffic_public_space` runtime entities
- AIS, NMEA, carrier telemetry, ATSPM, CDS, GTFS, V2X, or GIS adapters
- traffic/public-space UI, demos, pricing, or sales surfaces
- new billing migrations or entity database migrations
- changes to detection, streaming, evidence, scene execution, or runtime
  semantics beyond the read-only pack registry/API

## Workspace Notes

- Do not stage unrelated scratch files.
- Do not stage `taste-skill/`.
- Do not use `git add -A`; the workspace contains unrelated untracked files.
- The next implementation should use a new development branch from `main`.
- Prefer Superpowers `subagent-driven-development` for the implementation plan.
- Keep commits small and task-oriented.

## Prompt For Next Chat

```text
Follow-up from /Users/yann.moren/vision/docs/superpowers/status/2026-06-05-next-chat-sceneops-pack-boundary-implementation-handoff.md

Start from main at the commit containing that handoff or newer, then create branch codex/sceneops-pack-registry.

Read first:
- /Users/yann.moren/vision/docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md
- /Users/yann.moren/vision/docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md
- /Users/yann.moren/vision/docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md
- /Users/yann.moren/vision/packs/README.md
- /Users/yann.moren/vision/packs/maritime-fleet/pack.yaml
- /Users/yann.moren/vision/packs/traffic-public-space/pack.yaml

Use Superpowers, preferably subagent-driven-development, and implement the plan task by task with TDD. Build only the read-only SceneOps pack registry and pack API described in the plan.

Do not implement maritime runtime entities, traffic/public-space runtime entities, new vertical integrations, billing migrations, traffic UI, public-space demos, or runtime semantic changes. Keep Traffic/Public-Space manifest-only with status designed_not_implemented.

Do not stage unrelated scratch files or taste-skill/. Commit focused changes and push the development branch when complete.
```
