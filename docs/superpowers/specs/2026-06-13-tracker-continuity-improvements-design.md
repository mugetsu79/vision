# Tracker Continuity Improvements Design

Date: 2026-06-13
Branch: `codex/sceneops-pack-registry`

## Goal

Close the documented ID-churn gap in the live tracking pipeline without
introducing a new tracker family or breaking the canonical telemetry
contract. This spec packages the structural fixes that surface *because of*
the in-flight Phase 0 cadence decoupling (commit `982849cc feat: decouple
processing cadence and track diagnostics`) into a single, evidence-gated PR.

This is the "A3 tier" of the review work. Phase 0 (cadence + diagnostics)
and Phase 1 (counters) are already in flight in
`2026-06-12-processing-cadence-tracking-accuracy-design.md` and
`2026-06-12-edge-telemetry-tracking-optimization-design.md`; this spec does
not redo them. It assumes they are merged or running alongside.

## Current Evidence

The processing-cadence design already documents the root failure mode:

- a max-two-person scene produces many distinct persisted person stable
  track IDs across 5-minute windows on both central and edge workers
- central total stage time ~190 ms/frame (paced by browser delivery, not
  compute); `detect` ~27-32 ms; `track` < 1 ms
- edge worker total ~15-16 FPS on Jetson Orin Nano Super; TensorRT detector
  is the main cost

What that evidence does *not* yet exercise is whether the lifecycle layer
and the candidate-quality gate are correctly parameterised once cadence is
decoupled. This spec assumes the cadence fix lands and then closes four
remaining structural gaps.

## Architecture Decision

Treat the tracker stack as three cooperating layers with explicit
responsibilities and a single immutable telemetry contract:

```text
detector
  -> candidate_quality_gate     (display threshold vs association threshold)
  -> ultralytics tracker        (BoT-SORT, frame_rate aligned to processed FPS)
  -> track_lifecycle_manager    (tentative/active/coasting/lost,
                                 cx/cy Kalman coasting,
                                 confidence EMA, class voting)
  -> published telemetry        (stable_track_id, source_track_id,
                                 track_state, last_seen_age_ms)
```

The telemetry contract is preserved exactly as defined in
`2026-05-09-authoritative-live-track-lifecycle-design.md`. No new fields,
no rename, no covariance plumbed out.

The lifecycle layer keeps damped constant velocity as the default motion
*intuition* but switches the coasted bbox model from "extrapolate all four
edges linearly" to "constant-velocity Kalman on bbox center; freeze width
and height". This is the smallest correct shape model for coasted
predictions and matches what users perceive as "the box should follow the
object, not grow as it disappears".

`with_reid` and `gmc_method` stop being hard-coded constants in
`TrackerConfig` and start being driven by `ResolvedTrackerProfile`, so the
three-tier scene model from
`2026-05-10-scene-vision-profiles-and-candidate-quality-design.md`
actually activates ReID on `maximum_accuracy + edge_advanced_jetson` and
`maximum_accuracy + central_gpu`, and exposes GMC for jitter-prone or PTZ
deployments.

## Scope (A3 tier)

### A1: Cadence-aligned correctness

**A1.a — `TrackerConfig.frame_rate` sourced from processed FPS**

`TrackerConfig.frame_rate` currently defaults to 30 and is set from
`config.tracker.frame_rate`. BoT-SORT's internal Kalman uses `frame_rate`
to scale its motion model; a wrong value produces wrong process noise and
drifts association.

Source `TrackerConfig.frame_rate` from the same `camera.fps_cap` (or
measured processed FPS, whichever Phase 0 standardises on) that the frame
source uses for `CameraSourceConfig.fps_cap`. The Ultralytics adapter
forwards it via `_build_ultralytics_backend`, which already accepts a
`frame_rate` keyword.

Files: `backend/src/argus/vision/tracker.py`,
`backend/src/argus/inference/engine.py` (`_tracker_config_from_resolved_profile`).

**A1.b — Time-normalized coast TTL and damping**

`TrackLifecycleConfig.coast_ttl_ms` and `velocity_damping` currently work
against `missing_updates` (a frame count). Once processing FPS varies, the
same `coast_ttl_ms` translates to different coasting horizons on different
cadences.

`_coast_track` applies damping against `elapsed_ms` (measured from
`memory.last_seen_ts` to current `ts`) rather than against
`missing_updates`. The damping formula becomes
`damping = velocity_damping ** (elapsed_ms / nominal_frame_interval_ms)`
where `nominal_frame_interval_ms = 1000 / camera.fps_cap`. `coast_ttl_ms`
keeps its absolute-time semantics.

Files: `backend/src/argus/vision/track_lifecycle.py`.

**A1.c — Skip identical MediaMTX `/replace` calls**

Documented stability source in
`docs/superpowers/status/2026-06-11-jetson-live-overlay-stability-handoff.md`.
The publisher should hash the registration payload and skip the `/replace`
API call when the hash is identical to the last successful registration.

Files: `backend/src/argus/streaming/mediamtx.py`.

### A2: Profile wiring

**A2.a — `appearance_ready` drives `with_reid`**

`ResolvedTrackerProfile.appearance_ready` is set to `True` for
`maximum_accuracy + edge_advanced_jetson` and `maximum_accuracy +
central_gpu` in `profiles.py`. `_tracker_config_from_resolved_profile`
should map `appearance_ready` to `TrackerConfig.with_reid` rather than
hard-coding `with_reid=False`. The `model="auto"` default already lets the
Ultralytics tracker resolve a default appearance encoder.

Files: `backend/src/argus/vision/profiles.py`,
`backend/src/argus/inference/engine.py` (`_tracker_config_from_resolved_profile`),
`backend/src/argus/vision/tracker.py`.

**A2.b — `gmc_method` exposed on the profile**

`ResolvedTrackerProfile` gains an optional `gmc_method: str = "none"`
field. The resolver picks the value based on the camera/scene profile (a
new operator-facing knob on the scene-vision-profile contract, or a
deployment-level config in `argus.core.config` for now). Default remains
`"none"` so fixed traffic cameras keep current behaviour. PTZ or
vibration-prone deployments can opt in to `"sparseOptFlow"` (the
Ultralytics default) without code change.

Files: `backend/src/argus/vision/profiles.py`,
`backend/src/argus/vision/tracker.py`, contract definition in
`backend/src/argus/api/contracts.py` if exposed via profile JSON; a
`tracker_profile.gmc_method` override field is added to the existing
`SceneVisionProfile` contract.

**A2.c — Candidate quality: display vs association confidence**

`ResolvedCandidateQuality` already exposes
`display_min_confidence` and `association_min_confidence` as separate
dicts. The consumer in `candidate_quality.py` should apply
`association_min_confidence` when judging whether a low-confidence
detection can extend an existing active or coasting track, and
`display_min_confidence` (which is typically higher) when judging whether
to create a new track.

Files: `backend/src/argus/vision/candidate_quality.py`.

### A3: Lifecycle polish

**A3.a — Constrained Kalman coasting**

Replace the linear bbox-edge extrapolation in `_coast_track` with a
constant-velocity Kalman filter on `(cx, cy)` with frozen `(w, h)`.

- state: `[cx, cy, vx, vy]`
- observation: `[cx, cy]` from the matched detection
- process model: `cx_t = cx_{t-1} + vx * dt`, `cy_t = cy_{t-1} + vy * dt`,
  velocities damped by `velocity_damping ** (dt / nominal_frame_interval_ms)`
- measurement model: identity on `(cx, cy)`
- process noise: fixed; tuned against the replay benchmark
- measurement noise: fixed; tuned against the replay benchmark
- bbox at any time = `(cx - w/2, cy - h/2, cx + w/2, cy + h/2)` clamped to
  frame shape

State lives on `_TrackMemory` as a new `_MotionFilter` dataclass; no
covariance is plumbed to the telemetry contract. The filter is created
when a track first becomes `active`, re-seeded from the matched detection
on every `_apply_detection`, and used to predict during `_coast_track`.

Files: `backend/src/argus/vision/track_lifecycle.py`.

**A3.b — Per-track confidence EMA**

`_TrackMemory` gains `confidence_ema: float | None`. Each `_apply_detection`
updates it via `alpha * detection.confidence + (1 - alpha) * confidence_ema`
with `alpha = 0.4` (tuned against the replay benchmark). The published
`Detection.confidence` on the lifecycle output uses the EMA rather than
the instantaneous detection confidence. Raw detection confidence remains
available to upstream consumers (count_events, rule_engine) that read from
the pre-lifecycle `tracked` list.

Files: `backend/src/argus/vision/track_lifecycle.py`.

**A3.c — Per-track class voting**

`_TrackMemory` gains `class_votes: dict[str, int]`. Each `_apply_detection`
increments `class_votes[detection.class_name]`. The published class on
lifecycle output is the argmax class. Vote dict resets when a track
transitions through `lost`. This eliminates the visible class flicker
when a detector flips between e.g. `person` and `pedestrian` across
frames.

Files: `backend/src/argus/vision/track_lifecycle.py`.

**A3.d — Frozen attributes mapping**

`_copy_detection` currently does `deepcopy(detection.attributes)` on every
snapshot. With ANPR/attribute payloads this is non-trivial per frame per
track.

Switch to `types.MappingProxyType` over a frozen dict on the
`Detection.attributes` payload. `Detection.with_updates(attributes=…)`
wraps the new attributes in a `MappingProxyType` once, and
`_copy_detection` shares the reference. Downstream consumers already treat
`attributes` as read-only.

Files: `backend/src/argus/vision/types.py`,
`backend/src/argus/vision/track_lifecycle.py`.

**A3.e — `_TrackerResults.cls` as `int32`**

Class IDs are integers conceptually; the `float32` with `-1` sentinel in
`_TrackerResults.cls` is lossy and slower for the Ultralytics adapter's
internal comparisons. Switch to `int32`, use a separate `valid_cls` mask
or sentinel that does not collide with real class IDs (Ultralytics expects
non-negative IDs; use `-1` as int sentinel).

Files: `backend/src/argus/vision/tracker.py`.

## Telemetry Contract

Unchanged. The published `LifecycleTrack` continues to carry exactly:

- `stable_track_id: int`
- `source_track_id: int | None`
- `state: "active" | "coasting"`
- `last_seen_age_ms: int`
- `detection: Detection` (now with smoothed `confidence` and voted
  `class_name`)
- `lifecycle_reason: TrackLifecycleReason | None`

`stable_track_id` continuity semantics are preserved. The Kalman coasting
change affects the *bbox values* during `state="coasting"` but does not
introduce new states, new fields, or new lifecycle reasons.

## Acceptance Criteria

### Required (merge gate)

1. **Replay benchmark gate.** Extend
   `backend/tests/scripts/test_tracking_replay_benchmark.py` to load a
   committed person-only fixture clip (NATS replay or detection-stream
   replay; format defined by the existing harness) and assert:
   - **≥ 30% fewer ID switches** vs. the pre-A3 baseline run on the same
     fixture
   - **≥ 20% lower track fragmentation** (median count of distinct
     `stable_track_id` values per unique ground-truth track) vs. baseline
   - **no regression on track lifetime** (median active-frames-per-track
     does not decrease)

   The baseline metrics are captured by running the harness against the
   parent commit of this branch (Phase 0 + diagnostics applied, A3 not
   applied) and committed to
   `backend/tests/scripts/fixtures/tracking_replay_baseline.json`.

2. **Mypy + ruff + `make test` green.** No new mypy errors, no new ruff
   findings, full `make test` passes including the new fixture-driven
   replay test.

3. **No telemetry contract regressions.** The existing
   `tests/vision/test_track_lifecycle.py` continues to pass without
   relaxing any field shape or value assertion. The Kalman-coasted bbox
   may shift the *exact numeric value* of coasted bbox coordinates; the
   tests should assert geometric properties (bbox stays inside frame,
   center motion follows last velocity direction) rather than exact pixel
   values during coast.

4. **No detector-association regression for rules and count_events.**
   `tests/vision/test_count_events.py`, `tests/vision/test_rules.py`
   continue to pass; rule_engine and count_event_processor see the raw
   pre-lifecycle `tracked` list, not the smoothed-confidence post-lifecycle
   output.

### Recommended evidence (not merge gate)

5. **Jetson-only live A/B.** Run a 5-minute before/after window on a
   fixed Jetson camera, before deploying A3 and after. Capture:
   - distinct persisted stable_track_ids per ground-truth track
   - average per-frame tracker output count
   - average ID-switch rate
   - subjective overlay smoothness (operator note)

   Drop results into
   `docs/superpowers/status/YYYY-MM-DD-tracker-continuity-jetson-evidence.md`.

   **Skip the macOS central A/B** until the host-worker stability bug
   (open in `CLAUDE.md`) is independently resolved. Running A/B through a
   pipeline known to drop frames mid-run pollutes the evidence with
   non-tracker signal.

## Test Plan

### Unit tests (new or extended)

- `tests/vision/test_track_lifecycle.py`
  - new test: Kalman coast prediction respects frame shape clamp
  - new test: coast bbox shape (w, h) does not drift over N coast frames
  - new test: confidence EMA converges within K frames at given alpha
  - new test: class voting stabilises on argmax under detector flicker
- `tests/vision/test_tracker.py`
  - new test: `TrackerConfig.frame_rate` propagates to the underlying
    `BOTSORT` constructor
  - new test: `with_reid` is set when `appearance_ready=True` in the
    resolved profile
  - new test: `gmc_method` is set when the profile carries an override
- `tests/vision/test_candidate_quality.py`
  - new test: low-confidence detection above `association_min_confidence`
    but below `display_min_confidence` is accepted for association with an
    existing active track, rejected for new track creation
- `tests/vision/test_profiles.py`
  - new test: `gmc_method` override flows from `SceneVisionProfile` JSON
    through to `ResolvedTrackerProfile`
- `tests/streaming/test_mediamtx.py`
  - new test: identical registration payload does not trigger a
    `/replace` API call

### Integration tests (extended)

- `tests/inference/test_engine.py`
  - new test: when the resolved profile has `appearance_ready=True`, the
    tracker built by `_build_tracker` has `with_reid=True`
  - new test: when `camera.fps_cap` changes mid-run, the rebuilt tracker
    receives the new `frame_rate`

### Replay benchmark

- `tests/scripts/test_tracking_replay_benchmark.py`
  - asserts the four gate metrics above against the committed baseline
  - emits a JSON summary that the live A/B doc can reference

## Files Touched (summary)

| File | Change |
|---|---|
| `backend/src/argus/vision/tracker.py` | A1.a, A2.a, A2.b, A3.e |
| `backend/src/argus/vision/track_lifecycle.py` | A1.b, A3.a, A3.b, A3.c, A3.d |
| `backend/src/argus/vision/profiles.py` | A2.a, A2.b |
| `backend/src/argus/vision/candidate_quality.py` | A2.c |
| `backend/src/argus/vision/types.py` | A3.d |
| `backend/src/argus/streaming/mediamtx.py` | A1.c |
| `backend/src/argus/inference/engine.py` | wiring only (`_tracker_config_from_resolved_profile`, `_build_tracker`) |
| `backend/src/argus/api/contracts.py` | A2.b (new `tracker_profile.gmc_method` override) |
| `backend/tests/scripts/test_tracking_replay_benchmark.py` | new gate logic |
| `backend/tests/scripts/fixtures/tracking_replay_baseline.json` | new baseline file |
| `backend/tests/vision/test_*.py` | new and extended tests as above |
| `backend/tests/inference/test_engine.py` | new wiring tests |
| `backend/tests/streaming/test_mediamtx.py` | new replace-skip test |

No frontend changes. No API contract changes other than the additive
`tracker_profile.gmc_method` override field, which defaults to `"none"`.

## Out Of Scope

- Extracting the tracking pipeline out of `engine.py` (the 3057-LOC god
  module). Documented as item A4 in the parent review; deferred to a
  follow-up spec to avoid merge churn with the in-flight cadence work.
- ByteTrack reactivation. The Ultralytics adapter keeps the code path
  callable but no profile selects it.
- Cross-camera reidentification. Documented as out of V3 scope at the
  scene/profile design level.
- Full appearance-aware Kalman tracker on top of BoT-SORT. The
  constrained `(cx, cy, vx, vy)` filter in A3.a is intentionally the
  minimum motion model needed for correct coasted-bbox shape.
- macOS central A/B. Blocked on independent host-worker stability work
  (see `CLAUDE.md` handoff).
- DeepStream / NvDCF visual tracking on Jetson. Explicit follow-up in the
  three-tier scene model.

## Open Questions

1. **Replay fixture provenance.** Where does the committed person-only
   fixture come from? The harness format exists, but no committed clip
   does. Proposed: capture a 30-second fixture from the live Jetson rig
   the first time A3 is exercised, redact PII via the privacy pipeline
   before committing, and store the redacted payload under
   `backend/tests/scripts/fixtures/`. Approval needed before merge.
2. **`gmc_method` UI surfacing.** The `tracker_profile.gmc_method`
   override is reachable via JSON for now. Does it need a UI control in
   `CameraWizard.tsx` in this spec, or in a follow-up? Default proposal:
   JSON-only for this spec; UI control follows once the constrained
   Kalman + ReID wiring is validated.
