# Home-Lab Engine Validation

Date: 2026-06-05
Status: engineering guidance, not a product pack

## Short Answer

You can test with cars at home today using the current core engine primitives:

- COCO fixed-vocabulary classes such as `person`, `bicycle`, `car`,
  `motorcycle`, `bus`, and `truck`
- line crossings
- detection regions
- include/exclude polygons
- count events
- scene contracts
- runtime passports

No home-lab pack is required. Do not create `packs/home-lab/pack.yaml` for this
phase.

## Purpose

Home/lab testing is the positive proof that the SceneOps Engine is not
maritime-shaped. A road, driveway, yard, water edge, or other local scene should
produce useful signals through generic primitives without adding traffic,
public-space, maritime, or lab-specific entities.

This is an architectural validation loop, not a product surface.

## Setup

Use any current local camera source:

- RTSP IP camera
- USB webcam
- existing analytics still
- existing live stream path

Use core scene configuration:

- draw a line across a driveway or road lane for count events
- draw an include region around the observable operating area
- draw exclusion regions for noise such as reflections, walls, sky, or private
  areas outside the test scene
- select fixed-vocabulary classes from the existing COCO model
- save the scene contract

Suggested class presets:

| Scenario | Classes |
|---|---|
| Street count | `person`, `bicycle`, `car`, `motorcycle`, `bus`, `truck` |
| Driveway presence | `person`, `car`, `truck` |
| Generic object-flow smoke test | one or two classes that are visible and stable in the scene |

Open vocabulary may be used for discovery only. Keep the term list small and do
not promote discovered terms into a pack without a separate product decision.

## Rules

1. No home-lab pack.
2. No traffic-specific entities such as `Intersection`, `Approach`,
   `Movement`, `Crosswalk`, `CurbZone`, or `SignalPhase`.
3. No maritime-specific entities such as `Vessel`, `Voyage`, or `PortCall`.
4. No home-lab UI panel, dashboard, pricing meter, or customer-facing demo.
5. No home-lab database migration.
6. Outputs should be logs, existing count events, existing scene contract
   artifacts, existing runtime passport state, and optional Prometheus metrics.
7. If the home test requires a non-maritime concept in core, treat it as a
   generality bug in the engine, not as a reason to start a traffic pack.

## Manual Acceptance Criteria

A home/lab car test is successful when:

- the scene runs with no pack registered for home/lab, traffic, or public space
- the configured COCO class is detected in the live or still scene
- count events or occupancy signals are emitted through existing core tables and
  services
- the scene contract stores class filters, regions, boundaries, and runtime
  vocabulary state as generic configuration
- runtime passport state remains accurate
- no vertical entity or pack-owned schema is needed

## Future Automated Harness

After the read-only pack registry ships, add a small engine-validation harness
in a separate implementation slice.

Recommended future test:

- path: `backend/tests/engine_validation/test_engine_handles_generic_scenes.py`
- fixture: canned frames or a tiny synthetic video with stable object boxes
- behavior: run the generic scene/signal/event pipeline with classes such as
  `car` and `person`
- assertion: the engine produces count events through core primitives with no
  registered pack and no vertical entities

The harness should complement the pack-boundary tests. Boundary tests prove
what the engine does not depend on; this harness proves what the engine can do.

## Trap To Avoid

Do not let the lab setup become interesting product UI. If a useful result
appears, record it as an engine improvement or a later strategy input. Do not
create a dashboard, panel, study export, or traffic demo from it.
