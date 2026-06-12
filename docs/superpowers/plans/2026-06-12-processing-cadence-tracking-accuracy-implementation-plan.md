# Processing Cadence And Tracking Accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple worker processing FPS from browser delivery FPS, then add
diagnostics, replay benchmarking, tracker tuning, and live A/B validation for
central and edge tracking accuracy.

**Architecture:** `Camera.fps_cap` remains the worker processing cap used for
capture throttle and tracker frame rate. `WorkerStreamSettings.fps` remains the
preview/output stream FPS used for MediaMTX registration and browser delivery.
Tracking changes are gated by metrics and replay/live evidence before heavier
runtime features are considered.

**Tech Stack:** Python/FastAPI, SQLAlchemy models/contracts, worker engine,
MediaMTX stream registration, Prometheus metrics, pytest, frontend generated
API tests, optional offline replay script.

---

## File Map

- Modify `backend/src/argus/inference/engine.py`: stop passing stream FPS into
  capture throttling, report processing/output FPS separately, expose tracker
  diagnostics.
- Modify `backend/src/argus/vision/camera.py`: keep
  `CameraSourceConfig.fps_cap` as processing-only and test throttle behavior.
- Modify `backend/src/argus/services/app.py`: keep worker config stream FPS for
  preview while camera FPS caps processing; add runtime health fields if needed.
- Modify `backend/src/argus/api/contracts.py`: add explicit runtime/report
  fields for processing FPS, output FPS, and tracking diagnostics.
- Modify `backend/src/argus/models/tables.py`: add optional tracking diagnostic
  fields only if runtime-report payloads need persistence.
- Add migration only if runtime-report columns are added.
- Modify `backend/src/argus/vision/track_lifecycle.py`: add diagnostic counters and time-normalized lifecycle config.
- Modify `backend/src/argus/vision/candidate_quality.py`: support
  tracker-association confidence separate from display confidence.
- Modify `backend/src/argus/vision/profiles.py`: derive central-person and edge-mixed tracker defaults.
- Add `scripts/tracking_replay_benchmark.py`: offline replay benchmark for central and edge clips/frame directories.
- Add tests:
  - `backend/tests/inference/test_engine.py`
  - `backend/tests/vision/test_camera.py`
  - `backend/tests/services/test_camera_worker_config.py`
  - `backend/tests/vision/test_track_lifecycle.py`
  - `backend/tests/vision/test_candidate_quality.py`
  - `backend/tests/vision/test_profiles.py`
  - `backend/tests/scripts/test_tracking_replay_benchmark.py`
  - affected frontend runtime-health tests if API output changes

## Phase 0: Decouple Processing FPS From Preview FPS

### Task 0.1: Red Test For Worker Capture FPS

**Files:**
- Test: `backend/tests/inference/test_engine.py`
- Modify: `backend/src/argus/inference/engine.py`

- [ ] **Step 1: Add a failing test**

Add a test beside the runtime engine construction tests:

```python
async def test_run_engine_uses_camera_fps_cap_for_capture_not_stream_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeSource:
        def __init__(self, config: object) -> None:
            captured["source_config"] = config

        def next_frame(self) -> object:
            raise KeyboardInterrupt

        def close(self) -> None:
            return None

    def fake_create_camera_source(config: object) -> _FakeSource:
        return _FakeSource(config)

    monkeypatch.setattr(engine_module, "create_camera_source", fake_create_camera_source)

    config = _engine_config(
        camera_fps_cap=15,
        stream_fps=5,
        stream_profile_id="360p5",
        mode=ProcessingMode.CENTRAL,
    )

    with pytest.raises(KeyboardInterrupt):
        await engine_module.run_engine(config=config, settings=_settings())

    source_config = captured["source_config"]
    assert source_config.fps_cap == 15
```

- [ ] **Step 2: Run red test**

Run:

```bash
./backend/.venv/bin/pytest \
  backend/tests/inference/test_engine.py::test_run_engine_uses_camera_fps_cap_for_capture_not_stream_profile -q
```

Expected before implementation: `source_config.fps_cap == 5`.

- [ ] **Step 3: Implement minimal fix**

In `backend/src/argus/inference/engine.py`, replace capture source FPS cap
calculation:

```python
fps_cap=_capture_fps_cap(config.camera.fps_cap, registration.target_fps),
```

with:

```python
fps_cap=max(1, int(config.camera.fps_cap)),
```

Update `_reconfigure_frame_source_for_stream()` the same way:

```python
fps_cap=max(1, int(self.config.camera.fps_cap)),
```

Keep `target_fps=config.stream.fps` in `register_stream()` calls. That is output
stream FPS, not processing FPS.

- [ ] **Step 4: Run green test**

Run:

```bash
./backend/.venv/bin/pytest \
  backend/tests/inference/test_engine.py::test_run_engine_uses_camera_fps_cap_for_capture_not_stream_profile -q
```

Expected: pass.

### Task 0.2: Worker Config Contract Test

**Files:**
- Test: `backend/tests/services/test_camera_worker_config.py`
- Modify: `backend/src/argus/services/app.py`

- [ ] **Step 1: Add a failing worker-config test**

Add a test that creates a central camera with `fps_cap=15` and
`browser_delivery.default_profile="360p5"`, then fetches worker config:

```python
async def test_worker_config_keeps_processing_fps_separate_from_preview_fps(
    camera_service: CameraService,
    camera: Camera,
) -> None:
    camera.fps_cap = 15
    camera.browser_delivery = BrowserDeliverySettings(
        default_profile="360p5"
    ).model_dump(mode="json")

    config = await camera_service.worker_config(camera.id)

    assert config.camera.fps_cap == 15
    assert config.stream.profile_id == "360p5"
    assert config.stream.fps == 5
    assert config.tracker.frame_rate == 15
```

- [ ] **Step 2: Run red test**

Run:

```bash
TEST_FILE=backend/tests/services/test_camera_worker_config.py
TEST_NAME=test_worker_config_keeps_processing_fps_separate_from_preview_fps
./backend/.venv/bin/pytest "${TEST_FILE}::${TEST_NAME}" -q
```

Expected before implementation: tracker frame rate or source capture behavior
is coupled to stream FPS.

- [ ] **Step 3: Ensure tracker frame rate uses camera FPS cap**

In worker config construction, keep:

```python
tracker=WorkerTrackerSettings(
    tracker_type=camera.tracker_type,
    frame_rate=camera.fps_cap,
)
```

If a path derives tracker frame rate from `worker_stream.fps`, change it to
`camera.fps_cap`.

- [ ] **Step 4: Run green test**

Run the same test and expect pass.

### Task 0.3: Runtime Health Fields

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/models/tables.py` if persisted
- Test: `backend/tests/inference/test_engine.py`
- Test: `backend/tests/api/test_prompt5_routes.py`

- [ ] **Step 1: Add failing assertions for processing/output FPS**

Extend runtime report tests to expect:

```python
assert report.processing_fps_cap == 15
assert report.output_fps == 5
assert report.stream_profile_id == "360p5"
```

- [ ] **Step 2: Add contract fields**

Add optional fields to `SupervisorRuntimeReportCreate` and response contracts:

```python
processing_fps_cap: float | None = None
output_fps: float | None = None
stream_profile_id: str | None = None
```

- [ ] **Step 3: Populate from worker engine**

When building runtime report payloads:

```python
processing_fps_cap=float(self.config.camera.fps_cap)
output_fps=float(self.config.stream.fps)
stream_profile_id=self.config.stream.profile_id
```

- [ ] **Step 4: Persist only if the operations UI needs history**

If persisted, add nullable columns to `worker_runtime_reports` and a migration.
If UI only needs the latest report payload path, keep this in response mapping
without adding DB columns.

- [ ] **Step 5: Run tests and regenerate API**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/inference/test_engine.py backend/tests/api/test_prompt5_routes.py -q
./backend/.venv/bin/python scripts/generate_openapi.py
corepack pnpm --dir frontend exec openapi-typescript src/lib/openapi.json -o src/lib/api.generated.ts
```

Expected: tests pass and generated API changes are deterministic.

## Phase 1: Tracking Diagnostics

### Task 1.1: Lifecycle Diagnostic Counters

**Files:**
- Modify: `backend/src/argus/vision/track_lifecycle.py`
- Test: `backend/tests/vision/test_track_lifecycle.py`

- [ ] **Step 1: Write failing diagnostic test**

Add:

```python
def test_lifecycle_reports_decision_counts_for_reassociation_and_loss() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(coast_ttl_ms=1000, reassociate_iou_threshold=0.2)
    )
    first = Detection(class_name="person", confidence=0.8, bbox=(0, 0, 20, 40), track_id=1)
    second = Detection(class_name="person", confidence=0.8, bbox=(2, 0, 22, 40), track_id=9)

    manager.update(detections=[first], ts=_ts(0), frame_shape=(100, 100, 3))
    manager.update(detections=[second], ts=_ts(100), frame_shape=(100, 100, 3))
    manager.update(detections=[], ts=_ts(1200), frame_shape=(100, 100, 3))

    summary = manager.last_diagnostic_summary()

    assert summary["new_track"] == 1
    assert summary["spatial_reassociation"] == 1
    assert summary["forgotten"] == 1
```

- [ ] **Step 2: Run red test**

Run:

```bash
./backend/.venv/bin/pytest \
  backend/tests/vision/test_track_lifecycle.py::test_lifecycle_reports_decision_counts_for_reassociation_and_loss -q
```

Expected: `last_diagnostic_summary` is missing.

- [ ] **Step 3: Implement summary method**

Add to `TrackLifecycleManager`:

```python
def last_diagnostic_summary(self) -> dict[str, int]:
    summary: dict[str, int] = {}
    for decision in self._last_diagnostics:
        summary[decision.reason] = summary.get(decision.reason, 0) + 1
    return summary
```

- [ ] **Step 4: Run green test**

Run the same test and expect pass.

### Task 1.2: Worker Runtime Tracking Diagnostics

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Add failing report test**

Extend runtime report test:

```python
assert report.tracking_diagnostics["new_track"] >= 0
assert "active_tracks" in report.tracking_diagnostics
assert "coasting_tracks" in report.tracking_diagnostics
```

- [ ] **Step 2: Add contract field**

Add:

```python
tracking_diagnostics: dict[str, int | float | str] = Field(default_factory=dict)
```

- [ ] **Step 3: Populate from engine state**

When reporting:

```python
diagnostics = dict(self._track_lifecycle.last_diagnostic_summary())
diagnostics["active_tracks"] = sum(
    1 for track in self._track_lifecycle.visible_tracks() if track.state == "active"
)
diagnostics["coasting_tracks"] = sum(
    1 for track in self._track_lifecycle.visible_tracks() if track.state == "coasting"
)
```

- [ ] **Step 4: Run tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/inference/test_engine.py -q
```

Expected: pass.

## Phase 2: Replay Benchmark Harness

### Task 2.1: Script Skeleton And JSON Output

**Files:**
- Create: `scripts/tracking_replay_benchmark.py`
- Test: `backend/tests/scripts/test_tracking_replay_benchmark.py`

- [ ] **Step 1: Write failing script test**

Add:

```python
def test_tracking_replay_benchmark_outputs_summary(tmp_path: Path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    write_test_frame(frames_dir / "000001.jpg")

    result = run_benchmark(
        frames_path=frames_dir,
        classes=["person"],
        output_json=True,
        detector=FakeDetector(
            [[Detection(class_name="person", confidence=0.9, bbox=(0, 0, 20, 40), track_id=1)]]
        ),
    )

    assert result["frames_processed"] == 1
    assert result["stable_tracks"] == 1
    assert result["id_switches"] == 0
```

- [ ] **Step 2: Run red test**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/scripts/test_tracking_replay_benchmark.py -q
```

Expected: module missing.

- [ ] **Step 3: Implement reusable benchmark function**

Create:

```python
def run_benchmark(
    *,
    frames_path: Path,
    classes: list[str],
    output_json: bool,
    detector: Detector | None = None,
    tracker_type: TrackerType = TrackerType.BOTSORT,
    lifecycle_config: TrackLifecycleConfig | None = None,
) -> dict[str, object]:
    frames = load_ordered_frames(frames_path)
    detector = detector or build_detector_for_profile(profile_name=None, classes=classes)
    tracker = build_tracker(tracker_type=tracker_type)
    lifecycle = TrackLifecycle(lifecycle_config or TrackLifecycleConfig())

    frame_summaries: list[dict[str, object]] = []
    for index, frame in enumerate(frames, start=1):
        detections = detector.detect(frame, classes=classes)
        tracked = tracker.update(detections)
        lifecycle_events = lifecycle.update(tracked, frame_index=index)
        frame_summaries.append(
            summarize_frame(index, detections, tracked, lifecycle_events)
        )

    return summarize_replay(frame_summaries, output_json=output_json)
```

Use existing detector/tracker/lifecycle APIs. Keep CLI parsing separate from
the pure function so tests can call it directly.

- [ ] **Step 4: Implement CLI**

Arguments:

```text
--frames PATH
--classes person,car,truck
--tracker botsort|bytetrack
--profile central-person|edge-mixed
--json
--markdown PATH
```

- [ ] **Step 5: Run green test**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/scripts/test_tracking_replay_benchmark.py -q
```

Expected: pass.

## Phase 3: Tracker And Detection Tuning

### Task 3.1: Separate Display And Association Confidence

**Files:**
- Modify: `backend/src/argus/vision/candidate_quality.py`
- Modify: `backend/src/argus/vision/profiles.py`
- Test: `backend/tests/vision/test_candidate_quality.py`
- Test: `backend/tests/vision/test_profiles.py`

- [ ] **Step 1: Add failing candidate-quality test**

Add:

```python
def test_candidate_quality_accepts_lower_person_confidence_for_association() -> None:
    gate = CandidateQualityGate(
        CandidateQualityConfig(
            display_min_confidence={"person": 0.45},
            association_min_confidence={"person": 0.25},
        )
    )
    detection = Detection(class_name="person", confidence=0.30, bbox=(0, 0, 20, 40), track_id=1)

    decision = gate.evaluate(detection, existing_tracks=[], frame_shape=(100, 100, 3))

    assert decision.accepted is True
    assert decision.display_eligible is False
```

- [ ] **Step 2: Run red test**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_candidate_quality.py -q
```

Expected: config fields or `display_eligible` missing.

- [ ] **Step 3: Implement config split**

Extend `CandidateQualityConfig`:

```python
display_min_confidence: dict[str, float] = field(default_factory=lambda: {"person": 0.45})
association_min_confidence: dict[str, float] = field(default_factory=lambda: {"person": 0.25})
```

Extend `CandidateDecision`:

```python
display_eligible: bool = True
```

Use association confidence to allow tracker candidates and display confidence
to decide whether the detection is rendered as a new visible track.

- [ ] **Step 4: Add profile tests**

Assert central-person profile resolves to lower person association confidence
than display confidence. Assert edge-mixed keeps class-specific vehicle values.

- [ ] **Step 5: Run tests**

Run:

```bash
./backend/.venv/bin/pytest \
  backend/tests/vision/test_candidate_quality.py \
  backend/tests/vision/test_profiles.py -q
```

Expected: pass.

### Task 3.2: Time-Normalized Lifecycle Memory

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/vision/profiles.py`
- Test: `backend/tests/inference/test_engine.py`
- Test: `backend/tests/vision/test_profiles.py`

- [ ] **Step 1: Add failing test**

Add:

```python
def test_lifecycle_coast_ttl_uses_seconds_not_frame_count() -> None:
    profile = resolve_scene_vision_profile(
        SceneVisionProfile(
            accuracy_mode="maximum_accuracy",
            tracker_profile={"coast_seconds": 3.0},
        )
    )

    config = _tracker_config_from_resolved_profile(
        _engine_config(tracker_frame_rate=15),
        TrackerType.BOTSORT,
        profile,
    )

    assert config.coast_ttl_ms == 3000
```

- [ ] **Step 2: Run red test**

Run:

```bash
./backend/.venv/bin/pytest \
  backend/tests/inference/test_engine.py::test_lifecycle_coast_ttl_uses_seconds_not_frame_count \
  -q
```

Expected: missing override or frame-count-derived value.

- [ ] **Step 3: Implement profile override**

In `profiles.py`, resolve `tracker_profile["coast_seconds"]` to a float bounded
between 0.5 and 8.0 seconds. In engine tracker config conversion, prefer this
explicit value for `TrackLifecycleConfig.coast_ttl_ms`.

- [ ] **Step 4: Run tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/inference/test_engine.py backend/tests/vision/test_profiles.py -q
```

Expected: pass.

## Phase 4: Live A/B Smoke

### Task 4.1: Add A/B Smoke Script

**Files:**
- Create: `scripts/tracking_live_ab_smoke.py`
- Test: `backend/tests/scripts/test_tracking_live_ab_smoke.py`

- [ ] **Step 1: Write failing smoke script test**

Add:

```python
def test_live_ab_smoke_redacts_sources_and_reports_required_fields() -> None:
    result = format_smoke_summary(
        camera_name="CENTRAL persons RTSP",
        source_url="rtsp://***:***@192.168.1.195:8554/ch2",
        before={"fps": 5.0, "id_switches": 4},
        after={"fps": 12.0, "id_switches": 1},
    )

    assert "rtsp://***:***@192.168.1.195:8554/ch2" in result
    assert "id_switches" in result
    assert "fps" in result
```

- [ ] **Step 2: Run red test**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/scripts/test_tracking_live_ab_smoke.py -q
```

Expected: module missing.

- [ ] **Step 3: Implement formatter and command runner**

The script collects:

```text
processed FPS
stage avg and p95
process CPU percent
RSS
tracking diagnostic counters
persisted frames
broadcasted frames
JetStream consumer pending/ack-pending
MediaMTX replace count
capture wait spike count
```

The script must never print raw source URLs or command args containing secrets.

- [ ] **Step 4: Run test**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/scripts/test_tracking_live_ab_smoke.py -q
```

Expected: pass.

### Task 4.2: Manual Live A/B Procedure

**Files:**
- Modify: `docs/runbook.md`
- Modify: `docs/operator-deployment-playbook.md`

- [ ] **Step 1: Add runbook section**

Document:

```text
1. Capture baseline 5-minute central and edge windows.
2. Apply candidate processing/tracker config.
3. Restart only affected worker assignments.
4. Capture candidate 5-minute windows.
5. Compare FPS, CPU, persistence, stream stability, ID switches, fragmentation.
6. Roll back if CPU rises above agreed budget or tracking gets worse.
```

- [ ] **Step 2: Add acceptance thresholds**

Use these initial gates:

```text
central processed FPS: >= 10
edge processed FPS: >= 15
JetStream pending: 0 after sample window
MediaMTX repeated replace count: 0 after startup
capture wait spikes: 0 after startup stabilization window
fallback active: false
tracking ID switches: lower than baseline on central two-person scene
```

- [ ] **Step 3: Run docs check**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

## Final Verification Suite

Run before declaring completion:

```bash
./backend/.venv/bin/pytest \
  backend/tests/inference/test_engine.py \
  backend/tests/vision/test_camera.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/vision/test_track_lifecycle.py \
  backend/tests/vision/test_candidate_quality.py \
  backend/tests/vision/test_profiles.py \
  backend/tests/scripts/test_tracking_replay_benchmark.py \
  backend/tests/scripts/test_tracking_live_ab_smoke.py -q

./backend/.venv/bin/ruff check \
  backend/src/argus/inference/engine.py \
  backend/src/argus/vision/camera.py \
  backend/src/argus/vision/track_lifecycle.py \
  backend/src/argus/vision/candidate_quality.py \
  backend/src/argus/vision/profiles.py \
  scripts/tracking_replay_benchmark.py \
  scripts/tracking_live_ab_smoke.py

corepack pnpm --dir frontend build
```

Live verification must include sanitized central and edge evidence for:

- processed FPS and stage timings
- CPU/RSS
- canonical persisted frames and broadcast markers
- NATS consumer pending/ack-pending
- MediaMTX path replace count
- capture wait spike count
- tracking diagnostic deltas

Do not include raw RTSP credentials, sudo passwords, bearer tokens, node
credentials, registry credentials, or process args containing secrets.
