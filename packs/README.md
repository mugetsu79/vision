# Vezor Pack Manifests

This directory contains pack manifests for the SceneOps Engine. A manifest is a
strategy and architecture artifact first: it records which vertical concepts are
allowed to live outside core, which engine primitives they extend, and which
dependencies are forbidden.

## Current Packs

| Pack | Status | Meaning |
|---|---|---|
| `maritime-fleet` | `planned_mvp` | The first commercial pack to build for Vezor FleetOps. |
| `traffic-public-space` | `designed_not_implemented` | A future architectural target used to pressure-test engine generality. It is not a build commitment. |

## Rules

- Core owns scenes, scene contracts, signals, evidence, runtime passports, link
  passports, model catalog, cameras, tenants, generic sites, generic billing,
  and pack registry hooks.
- Packs own vertical entities, integrations, templates, default vocabulary,
  evidence fields, UI labels, and compliance defaults.
- No second pack ships until Maritime FleetOps has paying renewal proof and a
  dated decision records the scope change.
- Home/lab scenes with roads, cars, people, or other objects validate the engine
  through generic primitives. They do not create a traffic pack.
- Do not add a `home-lab` pack for local validation. Home/lab testing is
  documented in `docs/engineering/home-lab-engine-validation.md` and must stay
  packless unless a later dated decision changes the architecture.
- If a vertical noun needs to be added to a core contract, the pack boundary has
  failed and the engine design must be fixed before implementation continues.
