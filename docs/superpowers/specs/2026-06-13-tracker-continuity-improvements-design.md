# Tracker Continuity Improvements Design

Date: 2026-06-13
Branch: `codex/sceneops-pack-registry`

## Goal

Reduce live tracking ID churn for simple scenes, especially one-to-two person
scenes, without introducing a new tracker family or changing the canonical
telemetry contract.

This spec starts from the current branch state after commit
`75e95b8f feat: stabilize worker cadence and tracking`. That commit already
landed the Phase 0/1 prerequisites:

- processing cadence is decoupled from browser delivery cadence
- the Scene UI `fps_cap` is again the processing FPS source of truth unless an
  explicit operator CPU fallback clamp is configured
- MediaMTX path registration is idempotent and RTSP pulls are forced through TCP
  where MediaMTX supports it
- runtime reports expose processing FPS, output FPS, transport, drops,
  duplicates, and tracking diagnostics
- candidate quality already has separate display and association threshold
  fields, though the new-track semantics still need tightening

The implementation from this spec must make tracker identity continuity
measurably better on a committed replay fixture and must keep NATS, persistence,
WebSocket fanout, and telemetry schemas compatible with the current product.

## Current Evidence

Live evidence on the current branch:

- central camera: UI processing cap `25`, runtime processing cap `25`, browser
  output `5`, CPU ONNX runtime, about `18.5 FPS` at about `164%` worker CPU
- edge camera: UI processing cap `18`, runtime processing cap `18`, TensorRT
  runtime, about `16.2 FPS` at about `64%` worker CPU
- telemetry path is NATS on both central and edge, with zero publish drops and
  zero duplicate frames in the post-deploy smoke
- MediaMTX path churn is no longer observed after the idempotency fix

The unresolved product gap is tracker continuity: a max-two-person scene can
still produce more persisted stable IDs than real people. The next PR should
therefore focus on tracker configuration, lifecycle motion modeling, and
quality gating, backed by a replay benchmark with real ground-truth identity
annotations.

## Architecture Decision

Keep the tracker stack as three cooperating layers:

```text
detector outputs
  -> candidate_quality_gate     (new-track threshold vs association threshold)
  -> ultralytics tracker        (BoT-SORT, frame_rate = effective processing FPS)
  -> track_lifecycle_manager    (tentative/active/coasting/lost,
                                 center motion filter,
                                 confidence EMA,
                                 class voting)
  -> published telemetry        (unchanged contract)
```

The key timing value is **effective processing FPS**, not browser delivery FPS
and not raw camera source FPS. It is the same value used to build
`CameraSourceConfig.fps_cap` after applying the optional
`ARGUS_CPU_FALLBACK_PROCESSING_FPS_CAP` clamp:

```python
effective_processing_fps = _processing_fps_cap(
    camera.fps_cap,
    runtime_policy=runtime_policy,
    cpu_fallback_cap=settings.cpu_fallback_processing_fps_cap,
)
```

Every tracker component that interprets frame cadence uses this value:

- `TrackerConfig.frame_rate`
- `TrackLifecycleConfig.nominal_frame_interval_ms`
- coasting damping
- replay benchmark profile settings

The telemetry contract remains unchanged. Published live/persisted tracks still
carry:

- `stable_track_id`
- `source_track_id`
- `state`
- `last_seen_age_ms`
- `detection`
- `lifecycle_reason`

Runtime reports and internal benchmark summaries may include additional
diagnostic counters, but direct live telemetry frame shape must not change.

## Scope

### A1: Cadence-Aligned Tracker Configuration

#### A1.a - Source `TrackerConfig.frame_rate` from effective processing FPS

`TrackerConfig.frame_rate` currently defaults to `30` and is sourced from
`config.tracker.frame_rate`. BoT-SORT uses this value for its internal motion
model, so wrong FPS produces wrong process noise and association behavior.

Change `_tracker_config_from_resolved_profile(...)` to accept
`effective_processing_fps: int`. The value must be the same cap passed into
`CameraSourceConfig.fps_cap`.

`RuntimeInferenceEngine._build_tracker()` recomputes this value through
`self._effective_processing_fps_cap()` every time it builds a tracker. This
applies both during initial construction and when a runtime command changes the
tracker type and forces `_build_tracker()` / `_build_track_lifecycle()` to run
again.

Files:

- `backend/src/argus/inference/engine.py`
- `backend/src/argus/vision/tracker.py`

#### A1.b - Source lifecycle nominal frame interval from effective processing FPS

`TrackLifecycleConfig` gains:

```python
nominal_frame_interval_ms: float = 1000.0 / 25.0
```

`_track_lifecycle_config_from_resolved_profile(...)` accepts
`effective_processing_fps: int` and sets:

```python
nominal_frame_interval_ms = 1000.0 / max(1, effective_processing_fps)
```

`coast_ttl_ms` keeps absolute time semantics. Track expiry still depends on
`elapsed_ms(last_seen_ts, now)`, not frame count.

`RuntimeInferenceEngine._build_track_lifecycle()` recomputes the same effective
processing FPS through `self._effective_processing_fps_cap()` whenever lifecycle
state is rebuilt. No separate cached FPS value is stored in state.

Files:

- `backend/src/argus/inference/engine.py`
- `backend/src/argus/vision/track_lifecycle.py`

### A2: Runtime-Gated Tracker Profile Wiring

#### A2.a - ReID is requested by profile, enabled only when runtime allows it

`ResolvedTrackerProfile.appearance_ready` means the scene profile wants
appearance cues. It is not sufficient by itself to enable ReID.

`TrackerConfig.with_reid` becomes true only when all are true:

1. `resolved_profile.tracker.appearance_ready` is true.
2. The tracker type is BoT-SORT.
3. Runtime is not CPU fallback. Dockerized central CPU ONNX must keep ReID off.
4. The appearance model is locally available or the configured tracker backend
   can provide it without network downloads.

The implementation must not trigger implicit model downloads in live worker
startup or frame processing. If ReID is requested but unavailable, the worker
keeps `with_reid=False` and reports a tracking diagnostic reason such as
`reid_unavailable_runtime`.

Files:

- `backend/src/argus/inference/engine.py`
- `backend/src/argus/vision/profiles.py`
- `backend/src/argus/vision/tracker.py`

#### A2.b - GMC is an explicit JSON-only profile override

`ResolvedTrackerProfile` gains:

```python
gmc_method: Literal["none", "sparseOptFlow"] = "none"
```

`SceneVisionProfile.tracker_profile` becomes a typed Pydantic submodel with
`extra="allow"` so existing JSON keys still round-trip. It accepts
`gmc_method`, defaulting to `"none"`. Only `"none"` and `"sparseOptFlow"` are
in scope for this PR. This keeps fixed traffic cameras on the current low-cost
behavior while letting jitter-prone deployments opt in via JSON.

No frontend UI control is added in this PR. The operator-facing UI can follow
after live validation proves the setting is worth exposing.

Files:

- `backend/src/argus/api/contracts.py`
- `backend/src/argus/vision/profiles.py`
- `backend/src/argus/inference/engine.py`
- `backend/src/argus/vision/tracker.py`

### A3: Candidate Quality Semantics

The current gate has separate `display_min_confidence` and
`association_min_confidence`, but detections above the association threshold can
still create new tracks even when they are below the display/new-track
threshold.

Tighten the rule:

- A detection may create a new track only when confidence is at least the
  display/new-track threshold for its class.
- A detection below display/new-track threshold but at or above association
  threshold may extend an existing tentative, active, or coasting track only if
  it is spatially near that track.
- A detection below association threshold may still extend an existing track
  only through the existing continuation path when it is at least
  `continuation_min_confidence` and spatially near an existing track.

This keeps low-confidence true positives useful for continuity without letting
them spawn new stable IDs.

Files:

- `backend/src/argus/vision/candidate_quality.py`
- `backend/tests/vision/test_candidate_quality.py`

### A4: Lifecycle Motion and Output Stabilization

#### A4.a - Constrained center motion filter for coasting

Replace bbox-edge extrapolation during coasting with a constrained center
motion model:

- state: `[cx, cy, vx, vy]`
- velocities are stored as pixels per millisecond
- detection update computes velocity from the previous observed center and
  elapsed time between detections
- prediction uses `dt_ms = elapsed_ms(updated_ts, now)`
- damping uses
  `velocity_damping ** (dt_ms / nominal_frame_interval_ms)`
- width and height are frozen from the most recent detection
- predicted bbox is clamped to frame shape

`last_seen_ts` remains the timestamp of the last real detection and is used for
TTL and `last_seen_age_ms`. `updated_ts` advances on both detection updates and
coast predictions and is used only for incremental prediction.

State lives inside `_TrackMemory` as a private `_MotionFilter` dataclass. No
covariance or motion state is added to live telemetry.

Files:

- `backend/src/argus/vision/track_lifecycle.py`

#### A4.b - Per-track confidence EMA

`_TrackMemory` gains `confidence_ema: float | None`.

Each detection update applies:

```python
confidence_ema = detection.confidence if confidence_ema is None else (
    alpha * detection.confidence + (1.0 - alpha) * confidence_ema
)
```

`alpha` is added to `TrackLifecycleConfig` as:

```python
confidence_ema_alpha: float = 0.4
```

Published lifecycle detections use the EMA confidence. Raw detector/tracker
outputs before lifecycle processing remain unchanged for rules and count-event
consumers.

Files:

- `backend/src/argus/vision/track_lifecycle.py`

#### A4.c - Per-track class voting

`_TrackMemory` gains `class_votes: dict[str, int]`. Every detection update
increments the detected class. Published lifecycle detections use the most
common class, with deterministic tie-breaking by the current detection class
and then lexical class name.

Votes are deleted when the track is forgotten. Duplicate replacement must merge
or preserve votes so stable identity does not lose history when adopting a
better duplicate detection.

Files:

- `backend/src/argus/vision/track_lifecycle.py`

#### A4.d - Frozen detection attributes

`Detection.attributes` becomes a read-only mapping to avoid per-frame deep copy
work in lifecycle snapshots.

Implementation requirements:

- Type as `Mapping[str, Any]`, not `dict[str, Any]`.
- Store an immutable shallow copy using `types.MappingProxyType(dict(value))`.
- Make the freeze helper idempotent: if the supplied value is already a
  `MappingProxyType`, return it unchanged so `_copy_detection()` can share the
  frozen reference instead of allocating a new proxy/dict pair.
- `Detection.with_updates(attributes=...)` freezes the supplied mapping.
- `_copy_detection` can share the frozen attributes reference.
- Serialization paths that need a mutable dict convert with `dict(attributes)`.
- Tests cover telemetry serialization, rule/count consumers, and mutation
  attempts.

Files:

- `backend/src/argus/vision/types.py`
- `backend/src/argus/vision/track_lifecycle.py`
- relevant telemetry serialization tests

#### A4.e - `_TrackerResults.cls` uses integer dtype

Class IDs are integer values. `_TrackerResults.cls` currently uses `float32`
with a `-1` sentinel. Switch it to `int32` and keep `-1` as the invalid class
sentinel because Ultralytics class IDs are non-negative.

Files:

- `backend/src/argus/vision/tracker.py`

### A5: Replay Benchmark With Ground Truth

The current replay script does not measure true ID switches because it does not
have ground-truth identities. This PR must replace the merge gate with an
annotated replay fixture.

#### Fixture format

Create a committed fixture directory:

```text
backend/tests/scripts/fixtures/tracker_continuity_people_001/
  manifest.json
  frames/
    000001.jpg
    000002.jpg
    000003.jpg
  detections.jsonl
  ground_truth.jsonl
```

`manifest.json` contains:

```json
{
  "fixture_id": "tracker_continuity_people_001",
  "description": "Redacted two-person continuity scene",
  "fps": 15,
  "frame_count": 450,
  "classes": ["person"],
  "tracker_scene_profile": "difficult",
  "iou_match_threshold": 0.5,
  "redacted": true
}
```

`detections.jsonl` contains one record per frame:

```json
{
  "frame_id": 1,
  "image": "frames/000001.jpg",
  "detections": [
    {
      "class_name": "person",
      "class_id": 0,
      "confidence": 0.73,
      "bbox": [100.0, 120.0, 180.0, 420.0]
    }
  ]
}
```

`ground_truth.jsonl` contains one record per visible ground-truth object per
frame:

```json
{
  "frame_id": 1,
  "gt_id": "person_1",
  "class_name": "person",
  "bbox": [98.0, 119.0, 181.0, 421.0],
  "visibility": 1.0,
  "ignore": false
}
```

The fixture itself is invalid unless it contains at least two distinct
non-ignored `gt_id` values. The replay gate is invalid unless the committed
baseline has at least five total continuity defects across
`id_switches + track_fragmentation_sum`. This avoids a benchmark that cannot
prove improvement.

#### Evaluator semantics

For each frame:

1. Replay fixture detections into the tracker stack.
2. Match published lifecycle tracks to ground truth with class-compatible IoU
   >= `iou_match_threshold`.
3. Use greedy highest-IoU matching after sorting candidate pairs by IoU
   descending.
4. Ignore ground-truth rows with `ignore=true`.
5. Count an ID switch when the same `gt_id` is matched to a different
   `stable_track_id` than its previous matched frame.
6. Count fragmentation for each `gt_id` as
   `max(0, distinct_matched_stable_ids - 1)`.
7. Count duplicate active tracks when more than one published track matches the
   same `gt_id` above threshold before one-to-one matching.
8. Count coverage as matched frames divided by visible non-ignored frames.

The baseline JSON stores:

```json
{
  "fixture_id": "tracker_continuity_people_001",
  "fixture_sha256": "64-character-lowercase-sha256-digest",
  "base_commit": "75e95b8f",
  "effective_processing_fps": 15,
  "tracker_scene_profile": "difficult",
  "metrics": {
    "id_switches": 0,
    "track_fragmentation_sum": 0,
    "median_fragments_per_gt": 0.0,
    "median_track_lifetime_frames": 0.0,
    "coverage_ratio": 0.0,
    "duplicate_active_track_frames": 0
  }
}
```

The numeric values above are schema examples. The committed baseline file must
contain actual metrics from the base implementation.

#### Merge gate metrics

The A3/A4 implementation passes when all are true:

- ID switches decrease by at least 30% when baseline `id_switches >= 3`; if
  baseline ID switches are lower, they must not increase.
- `track_fragmentation_sum` decreases by at least 20% when baseline
  fragmentation is nonzero; if baseline fragmentation is zero, it must remain
  zero.
- `coverage_ratio` does not decrease by more than 2 percentage points.
- `median_track_lifetime_frames` does not decrease.
- `duplicate_active_track_frames` does not increase.
- Runtime benchmark median per-frame tracker+lifecycle time does not increase
  by more than 10% on the replay fixture.

Files:

- `scripts/tracking_replay_benchmark.py`
- `backend/tests/scripts/test_tracking_replay_benchmark.py`
- `backend/tests/scripts/fixtures/tracker_continuity_people_001/`

## Telemetry Contract

Unchanged for live and persisted tracking frames.

Allowed internal/reporting changes:

- runtime report `tracking_diagnostics` may include counters for
  `reid_requested`, `reid_enabled`, `reid_unavailable_runtime`,
  `gmc_method`, `id_switches_replay_only`, or similar diagnostic fields
- replay benchmark JSON may include any metric needed for evidence

Disallowed:

- renaming existing telemetry fields
- requiring clients to understand covariance, velocity, ReID features, or GMC
  state
- bypassing canonical NATS ingest, history persistence, or WebSocket fanout

## Acceptance Criteria

### Required Merge Gates

1. **Annotated replay benchmark passes.**
   `backend/tests/scripts/test_tracking_replay_benchmark.py` loads the committed
   fixture and baseline JSON, runs the current tracker stack, and enforces the
   metrics in A5.

2. **Effective processing FPS is wired end to end.**
   Tests prove `TrackerConfig.frame_rate` and
   `TrackLifecycleConfig.nominal_frame_interval_ms` use the same effective
   processing cap used by `CameraSourceConfig.fps_cap`, including when a CPU
   fallback clamp is explicitly set.

3. **ReID cannot silently enable on CPU fallback.**
   Tests prove `maximum_accuracy + central_gpu` on CPU ONNX keeps
   `with_reid=False` and emits an unavailable diagnostic, while an explicitly
   supported runtime can enable it.

4. **Candidate quality cannot spawn low-confidence new tracks.**
   Tests prove a person detection below display/new-track threshold but above
   association threshold is rejected without a nearby existing track and accepted
   only when it extends a nearby existing track.

5. **Telemetry contract remains compatible.**
   Existing lifecycle, NATS ingest, persistence, and WebSocket tests pass without
   relaxing field names or required values. Numeric coasted bbox assertions may
   switch to geometric properties.

6. **Full targeted verification passes.**
   Required commands:

   ```bash
   ./backend/.venv/bin/pytest \
     backend/tests/scripts/test_tracking_replay_benchmark.py \
     backend/tests/vision/test_track_lifecycle.py \
     backend/tests/vision/test_tracker.py \
     backend/tests/vision/test_candidate_quality.py \
     backend/tests/vision/test_profiles.py \
     backend/tests/inference/test_engine.py \
     backend/tests/services/test_camera_worker_config.py \
     backend/tests/streaming/test_mediamtx.py \
     -q
   ./backend/.venv/bin/ruff check \
     backend/src/argus/vision \
     backend/src/argus/inference/engine.py \
     backend/src/argus/api/contracts.py \
     scripts/tracking_replay_benchmark.py \
     backend/tests/scripts/test_tracking_replay_benchmark.py
   ```

### Recommended Evidence

1. **Jetson live A/B after merge-candidate build.**
   Run a 5-minute window before and after on the same Jetson scene and capture:

   - processed FPS
   - worker CPU/RSS
   - detector, tracker, lifecycle, publish telemetry stage averages
   - distinct persisted `stable_track_id` count per observed person
   - runtime tracking diagnostics
   - operator note on overlay smoothness

2. **Central A/B only after host-worker stability is clean.**
   Central macOS/CoreML/MPS acceleration remains future work. Do not claim
   Dockerized central GPU acceleration.

## Test Plan

### Unit Tests

- `backend/tests/vision/test_tracker.py`
  - `TrackerConfig.frame_rate` propagates to the Ultralytics backend
  - `with_reid` and `gmc_method` flow into `to_namespace()`
  - `_TrackerResults.cls` is `int32` and uses `-1` for unknown class IDs

- `backend/tests/vision/test_track_lifecycle.py`
  - coasting preserves width/height across multiple coast frames
  - coasting center moves in the last observed direction and clamps to frame
  - damping uses elapsed time and nominal frame interval
  - confidence EMA converges under repeated detections
  - class voting stabilizes detector class flicker
  - frozen attributes cannot be mutated and are not deep-copied per snapshot

- `backend/tests/vision/test_candidate_quality.py`
  - association-eligible but display-ineligible detection extends nearby track
  - the same detection is rejected when there is no nearby existing track
  - duplicate suppression still rejects duplicate fragments

- `backend/tests/vision/test_profiles.py`
  - `tracker_profile.gmc_method` override resolves to `ResolvedTrackerProfile`
  - invalid `gmc_method` is rejected by contract validation

### Integration Tests

- `backend/tests/inference/test_engine.py`
  - tracker frame rate uses effective processing cap, not stream output FPS
  - lifecycle nominal interval uses effective processing cap
  - explicit CPU fallback clamp affects tracker and lifecycle cadence together
  - ReID request is disabled on CPU fallback
  - ReID can be enabled only in a test runtime that declares local support

- `backend/tests/services/test_camera_worker_config.py`
  - worker config preserves scene UI `fps_cap`
  - browser delivery FPS remains decoupled from processing FPS

- `backend/tests/streaming/test_mediamtx.py`
  - existing idempotent path registration tests continue to pass

### Replay Benchmark Tests

- `backend/tests/scripts/test_tracking_replay_benchmark.py`
  - fixture schema validation rejects missing GT identities
  - evaluator counts ID switches against `gt_id`, not class changes
  - evaluator counts fragmentation as distinct stable IDs per `gt_id`
  - committed fixture passes the improvement/no-regression gates against the
    committed baseline

## Files Touched

| File | Change |
|---|---|
| `backend/src/argus/inference/engine.py` | effective FPS tracker/lifecycle wiring, ReID runtime gate |
| `backend/src/argus/vision/tracker.py` | ReID/GMC config fields, `int32` class IDs |
| `backend/src/argus/vision/track_lifecycle.py` | nominal frame interval, center motion filter, confidence EMA, class voting, frozen attributes |
| `backend/src/argus/vision/candidate_quality.py` | prevent association-only detections from spawning new tracks |
| `backend/src/argus/vision/profiles.py` | resolve ReID request and GMC override |
| `backend/src/argus/vision/types.py` | immutable detection attributes |
| `backend/src/argus/api/contracts.py` | additive `tracker_profile.gmc_method` JSON field |
| `scripts/tracking_replay_benchmark.py` | annotated fixture loader and ground-truth evaluator |
| `backend/tests/scripts/test_tracking_replay_benchmark.py` | replay metric gates |
| `backend/tests/scripts/fixtures/tracker_continuity_people_001/` | committed redacted fixture and baseline |
| `backend/tests/vision/test_*.py` | unit tests listed above |
| `backend/tests/inference/test_engine.py` | wiring and runtime-gate tests |

No frontend change is required in this PR.

## Out Of Scope

- New tracker families.
- ByteTrack reactivation as a selected profile.
- Cross-camera reidentification.
- DeepStream / NvDCF implementation.
- Native macOS/CoreML/MPS central acceleration.
- UI control for `gmc_method`.
- Telemetry contract changes.
- Any direct telemetry path that bypasses canonical ingest, persistence, or
  WebSocket fanout.

## Open Decisions Locked By This Spec

1. Replay evidence must use annotated ground-truth identities. A frame-only or
   detector-output-only fixture is not sufficient.
2. Effective processing FPS is the sole cadence source for tracker timing.
3. ReID is opt-in by profile but runtime-gated; CPU fallback stays off.
4. `gmc_method` is JSON-only for this PR.
5. Central live A/B is not a merge gate until central worker stability and
   native acceleration work are addressed separately.
