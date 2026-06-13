# Tracker Continuity Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce stable track ID churn by wiring tracker cadence to effective processing FPS, tightening low-confidence association semantics, adding runtime-gated ReID/GMC configuration, and stabilizing lifecycle coasting output with a ground-truth replay gate.

**Architecture:** Keep the detector, Ultralytics tracker, lifecycle manager, canonical NATS ingest, persistence, and WebSocket fanout boundaries intact. The tracker stack uses effective processing FPS as its single cadence source, and continuity quality is measured against annotated ground-truth identities in a committed replay fixture.

**Tech Stack:** Python 3.12 backend, Pydantic contracts, dataclass vision types, Ultralytics BoT-SORT adapter, pytest, ruff, OpenCV for fixture frame loading.

---

## File Structure

- Modify `scripts/tracking_replay_benchmark.py`: fixture schema loader, replay runner, ground-truth evaluator, baseline comparison CLI.
- Modify `backend/tests/scripts/test_tracking_replay_benchmark.py`: schema, metric, and gate tests.
- Create `backend/tests/scripts/fixtures/tracker_continuity_people_001/manifest.json`: fixture metadata.
- Create `backend/tests/scripts/fixtures/tracker_continuity_people_001/detections.jsonl`: detector output replay stream.
- Create `backend/tests/scripts/fixtures/tracker_continuity_people_001/ground_truth.jsonl`: ground-truth identity annotations.
- Create generated fixture frames under `backend/tests/scripts/fixtures/tracker_continuity_people_001/frames/`.
- Create `backend/tests/scripts/fixtures/tracking_replay_baseline.json`: baseline metrics generated from the pre-A3 implementation.
- Modify `backend/src/argus/inference/engine.py`: pass effective processing FPS into tracker and lifecycle config; runtime-gate ReID.
- Modify `backend/src/argus/vision/tracker.py`: ReID/GMC config propagation and `_TrackerResults.cls` dtype.
- Modify `backend/src/argus/vision/profiles.py`: resolve `gmc_method` and ReID request intent.
- Modify `backend/src/argus/api/contracts.py`: validate `tracker_profile.gmc_method`.
- Modify `backend/src/argus/vision/candidate_quality.py`: prevent association-only detections from spawning new tracks.
- Modify `backend/src/argus/vision/track_lifecycle.py`: center motion filter, nominal frame interval, EMA confidence, class voting, frozen attributes.
- Modify `backend/src/argus/vision/types.py`: immutable detection attributes.
- Extend tests in `backend/tests/vision/`, `backend/tests/inference/test_engine.py`, and `backend/tests/services/test_camera_worker_config.py`.

---

### Task 1: Ground-Truth Replay Benchmark

**Files:**
- Modify: `scripts/tracking_replay_benchmark.py`
- Modify: `backend/tests/scripts/test_tracking_replay_benchmark.py`
- Create: `backend/tests/scripts/fixtures/tracker_continuity_people_001/manifest.json`
- Create: `backend/tests/scripts/fixtures/tracker_continuity_people_001/detections.jsonl`
- Create: `backend/tests/scripts/fixtures/tracker_continuity_people_001/ground_truth.jsonl`
- Create: `backend/tests/scripts/fixtures/tracker_continuity_people_001/frames/000001.jpg` through `000090.jpg`
- Create: `backend/tests/scripts/fixtures/tracking_replay_baseline.json`

- [x] **Step 1: Add failing schema and evaluator tests**

Append these tests to `backend/tests/scripts/test_tracking_replay_benchmark.py`:

```python
def test_replay_fixture_requires_ground_truth_identities(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    (fixture_dir / "manifest.json").write_text(
        json.dumps(
            {
                "fixture_id": "empty",
                "fps": 15,
                "frame_count": 1,
                "classes": ["person"],
                "iou_match_threshold": 0.5,
                "redacted": True,
            }
        ),
        encoding="utf-8",
    )
    (fixture_dir / "detections.jsonl").write_text(
        json.dumps({"frame_id": 1, "image": "frames/000001.jpg", "detections": []}) + "\n",
        encoding="utf-8",
    )
    (fixture_dir / "ground_truth.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="at least two distinct"):
        MODULE.load_replay_fixture(fixture_dir)


def test_evaluator_counts_id_switches_against_ground_truth() -> None:
    frames = [
        MODULE.ReplayFrame(
            frame_id=1,
            image_path=None,
            detections=[],
            ground_truth=[
                MODULE.GroundTruthObject(
                    frame_id=1,
                    gt_id="person_1",
                    class_name="person",
                    bbox=(0.0, 0.0, 10.0, 10.0),
                    visibility=1.0,
                    ignore=False,
                )
            ],
        ),
        MODULE.ReplayFrame(
            frame_id=2,
            image_path=None,
            detections=[],
            ground_truth=[
                MODULE.GroundTruthObject(
                    frame_id=2,
                    gt_id="person_1",
                    class_name="person",
                    bbox=(1.0, 0.0, 11.0, 10.0),
                    visibility=1.0,
                    ignore=False,
                )
            ],
        ),
    ]
    outputs = {
        1: [MODULE.ReplayTrack(stable_track_id=10, class_name="person", bbox=(0.0, 0.0, 10.0, 10.0))],
        2: [MODULE.ReplayTrack(stable_track_id=11, class_name="person", bbox=(1.0, 0.0, 11.0, 10.0))],
    }

    metrics = MODULE.evaluate_tracks(
        frames,
        track_outputs_by_frame=outputs,
        iou_match_threshold=0.5,
    )

    assert metrics["id_switches"] == 1
    assert metrics["track_fragmentation_sum"] == 1
    assert metrics["coverage_ratio"] == 1.0
```

Add imports at the top:

```python
import json
import pytest
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/scripts/test_tracking_replay_benchmark.py -q
```

Expected: FAIL because `load_replay_fixture`, `ReplayFrame`, `GroundTruthObject`, `ReplayTrack`, and `evaluate_tracks` are not defined.

- [x] **Step 3: Implement fixture dataclasses and loader**

In `scripts/tracking_replay_benchmark.py`, add dataclasses after constants:

```python
from dataclasses import dataclass


BoundingBox = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class ReplayDetection:
    class_name: str
    class_id: int | None
    confidence: float
    bbox: BoundingBox


@dataclass(frozen=True, slots=True)
class GroundTruthObject:
    frame_id: int
    gt_id: str
    class_name: str
    bbox: BoundingBox
    visibility: float
    ignore: bool


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    frame_id: int
    image_path: Path | None
    detections: list[ReplayDetection]
    ground_truth: list[GroundTruthObject]


@dataclass(frozen=True, slots=True)
class ReplayTrack:
    stable_track_id: int
    class_name: str
    bbox: BoundingBox
```

Add loader helpers:

```python
def load_replay_fixture(fixture_dir: Path) -> tuple[dict[str, Any], list[ReplayFrame]]:
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    detection_rows = _read_jsonl(fixture_dir / "detections.jsonl")
    gt_rows = _read_jsonl(fixture_dir / "ground_truth.jsonl")
    gt_by_frame: dict[int, list[GroundTruthObject]] = {}
    for row in gt_rows:
        gt = GroundTruthObject(
            frame_id=int(row["frame_id"]),
            gt_id=str(row["gt_id"]),
            class_name=str(row["class_name"]),
            bbox=_bbox_tuple(row["bbox"]),
            visibility=float(row.get("visibility", 1.0)),
            ignore=bool(row.get("ignore", False)),
        )
        gt_by_frame.setdefault(gt.frame_id, []).append(gt)
    distinct_gt_ids = {
        gt.gt_id for values in gt_by_frame.values() for gt in values if not gt.ignore
    }
    if len(distinct_gt_ids) < 2:
        raise ValueError("Replay fixture must contain at least two distinct ground-truth identities.")

    frames: list[ReplayFrame] = []
    for row in detection_rows:
        frame_id = int(row["frame_id"])
        image_value = row.get("image")
        frames.append(
            ReplayFrame(
                frame_id=frame_id,
                image_path=fixture_dir / str(image_value) if image_value else None,
                detections=[
                    ReplayDetection(
                        class_name=str(det["class_name"]),
                        class_id=int(det["class_id"]) if det.get("class_id") is not None else None,
                        confidence=float(det["confidence"]),
                        bbox=_bbox_tuple(det["bbox"]),
                    )
                    for det in row.get("detections", [])
                ],
                ground_truth=gt_by_frame.get(frame_id, []),
            )
        )
    return manifest, frames


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _bbox_tuple(value: object) -> BoundingBox:
    values = list(value) if isinstance(value, Sequence) else []
    if len(values) != 4:
        raise ValueError(f"Expected bbox with four values, got {value!r}")
    return (float(values[0]), float(values[1]), float(values[2]), float(values[3]))
```

- [x] **Step 4: Implement evaluator metrics**

Add:

```python
def evaluate_tracks(
    frames: list[ReplayFrame],
    *,
    track_outputs_by_frame: dict[int, list[ReplayTrack]],
    iou_match_threshold: float,
) -> dict[str, object]:
    previous_match_by_gt: dict[str, int] = {}
    matched_ids_by_gt: dict[str, set[int]] = {}
    visible_frames_by_gt: Counter[str] = Counter()
    matched_frames_by_gt: Counter[str] = Counter()
    track_lifetime_frames: Counter[int] = Counter()
    id_switches = 0
    duplicate_active_track_frames = 0

    for frame in frames:
        gt_objects = [gt for gt in frame.ground_truth if not gt.ignore]
        tracks = track_outputs_by_frame.get(frame.frame_id, [])
        for gt in gt_objects:
            visible_frames_by_gt[gt.gt_id] += 1
        candidate_pairs: list[tuple[float, str, int]] = []
        duplicate_matches_by_gt: Counter[str] = Counter()
        for gt in gt_objects:
            for track in tracks:
                if gt.class_name != track.class_name:
                    continue
                overlap = _iou(gt.bbox, track.bbox)
                if overlap >= iou_match_threshold:
                    duplicate_matches_by_gt[gt.gt_id] += 1
                    candidate_pairs.append((overlap, gt.gt_id, track.stable_track_id))
        duplicate_active_track_frames += sum(
            1 for count in duplicate_matches_by_gt.values() if count > 1
        )
        used_gt: set[str] = set()
        used_track: set[int] = set()
        for overlap, gt_id, stable_track_id in sorted(candidate_pairs, reverse=True):
            del overlap
            if gt_id in used_gt or stable_track_id in used_track:
                continue
            used_gt.add(gt_id)
            used_track.add(stable_track_id)
            matched_frames_by_gt[gt_id] += 1
            matched_ids_by_gt.setdefault(gt_id, set()).add(stable_track_id)
            previous = previous_match_by_gt.get(gt_id)
            if previous is not None and previous != stable_track_id:
                id_switches += 1
            previous_match_by_gt[gt_id] = stable_track_id
            track_lifetime_frames[stable_track_id] += 1

    fragmentation_by_gt = {
        gt_id: max(0, len(stable_ids) - 1)
        for gt_id, stable_ids in matched_ids_by_gt.items()
    }
    visible_total = sum(visible_frames_by_gt.values())
    matched_total = sum(matched_frames_by_gt.values())
    lifetimes = sorted(track_lifetime_frames.values())
    fragments = sorted(fragmentation_by_gt.values())
    return {
        "id_switches": id_switches,
        "track_fragmentation_sum": sum(fragmentation_by_gt.values()),
        "median_fragments_per_gt": _median(fragments),
        "median_track_lifetime_frames": _median(lifetimes),
        "coverage_ratio": matched_total / visible_total if visible_total else 0.0,
        "duplicate_active_track_frames": duplicate_active_track_frames,
    }


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    midpoint = len(values) // 2
    if len(values) % 2 == 1:
        return float(values[midpoint])
    return (values[midpoint - 1] + values[midpoint]) / 2.0
```

- [x] **Step 5: Run evaluator tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/scripts/test_tracking_replay_benchmark.py -q
```

Expected: PASS for the new schema/evaluator tests and existing script tests.

- [x] **Step 6: Generate deterministic replay fixture**

Add a small fixture-generation helper inside the test module, or run this one-off Python command and commit the generated files:

```bash
./backend/.venv/bin/python - <<'PY'
from pathlib import Path
import json
import cv2
import numpy as np

root = Path("backend/tests/scripts/fixtures/tracker_continuity_people_001")
(root / "frames").mkdir(parents=True, exist_ok=True)
manifest = {
    "fixture_id": "tracker_continuity_people_001",
    "description": "Synthetic two-person continuity scene with crossing paths and detector gaps.",
    "fps": 15,
    "frame_count": 90,
    "classes": ["person"],
    "tracker_scene_profile": "difficult",
    "iou_match_threshold": 0.5,
    "redacted": True,
}
(root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
detection_lines = []
gt_lines = []
for frame_id in range(1, 91):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    p1_x = 80 + frame_id * 2
    p2_x = 460 - frame_id * 2
    gt = [
        ("person_1", [p1_x, 120, p1_x + 70, 420]),
        ("person_2", [p2_x, 118, p2_x + 70, 418]),
    ]
    detections = []
    for gt_id, bbox in gt:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), 2)
        gt_lines.append(json.dumps({
            "frame_id": frame_id,
            "gt_id": gt_id,
            "class_name": "person",
            "bbox": [float(x1), float(y1), float(x2), float(y2)],
            "visibility": 1.0,
            "ignore": False,
        }))
        if not (gt_id == "person_1" and 32 <= frame_id <= 37) and not (gt_id == "person_2" and 48 <= frame_id <= 54):
            confidence = 0.72
            if gt_id == "person_1" and 38 <= frame_id <= 42:
                confidence = 0.31
            if gt_id == "person_2" and 55 <= frame_id <= 60:
                confidence = 0.30
            detections.append({
                "class_name": "person",
                "class_id": 0,
                "confidence": confidence,
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
            })
    image = f"frames/{frame_id:06d}.jpg"
    cv2.imwrite(str(root / image), frame)
    detection_lines.append(json.dumps({
        "frame_id": frame_id,
        "image": image,
        "detections": detections,
    }))
(root / "detections.jsonl").write_text("\n".join(detection_lines) + "\n", encoding="utf-8")
(root / "ground_truth.jsonl").write_text("\n".join(gt_lines) + "\n", encoding="utf-8")
PY
```

Expected: fixture files exist and contain 90 frame rows with two ground-truth IDs.

- [x] **Step 7: Add baseline comparison logic**

In `scripts/tracking_replay_benchmark.py`, add:

```python
def compare_to_baseline(current: dict[str, object], baseline: dict[str, object]) -> list[str]:
    failures: list[str] = []
    base_metrics = baseline["metrics"]
    base_id_switches = int(base_metrics["id_switches"])
    base_fragments = int(base_metrics["track_fragmentation_sum"])
    if base_id_switches + base_fragments < 5:
        failures.append(
            "baseline continuity defects are below the required floor of 5"
        )
    current_id_switches = int(current["id_switches"])
    if base_id_switches >= 3:
        if current_id_switches > base_id_switches * 0.70:
            failures.append("id_switches did not improve by at least 30 percent")
    elif current_id_switches > base_id_switches:
        failures.append("id_switches increased")

    current_fragments = int(current["track_fragmentation_sum"])
    if base_fragments > 0:
        if current_fragments > base_fragments * 0.80:
            failures.append("track_fragmentation_sum did not improve by at least 20 percent")
    elif current_fragments > 0:
        failures.append("track_fragmentation_sum regressed from zero")

    if float(current["coverage_ratio"]) + 0.02 < float(base_metrics["coverage_ratio"]):
        failures.append("coverage_ratio regressed by more than 2 percentage points")
    if float(current["median_track_lifetime_frames"]) < float(base_metrics["median_track_lifetime_frames"]):
        failures.append("median_track_lifetime_frames decreased")
    if int(current["duplicate_active_track_frames"]) > int(base_metrics["duplicate_active_track_frames"]):
        failures.append("duplicate_active_track_frames increased")
    return failures
```

- [x] **Step 8: Add benchmark gate test**

Add a test that loads `tracking_replay_baseline.json`, runs the fixture, and asserts `compare_to_baseline(...) == []`. Mark this gate with `pytest.mark.xfail(reason="A3 continuity implementation not applied yet", strict=True)` until Task 8 removes the marker after the implementation improves the replay metrics.

Also add a unit test for the baseline floor:

```python
def test_compare_to_baseline_rejects_weak_baseline() -> None:
    failures = MODULE.compare_to_baseline(
        {
            "id_switches": 0,
            "track_fragmentation_sum": 0,
            "coverage_ratio": 1.0,
            "median_track_lifetime_frames": 10,
            "duplicate_active_track_frames": 0,
        },
        {
            "metrics": {
                "id_switches": 1,
                "track_fragmentation_sum": 1,
                "coverage_ratio": 1.0,
                "median_track_lifetime_frames": 10,
                "duplicate_active_track_frames": 0,
            }
        },
    )

    assert failures == [
        "baseline continuity defects are below the required floor of 5"
    ]
```

Run:

```bash
./backend/.venv/bin/pytest backend/tests/scripts/test_tracking_replay_benchmark.py -q
```

Expected at this step: PASS for schema tests; the gate can be marked `xfail` only until Task 5 removes the marker. The xfail reason must be exactly `A3 continuity implementation not applied yet`.

---

### Task 2: Effective Processing FPS Wiring

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/vision/track_lifecycle.py`
- Modify: `backend/tests/inference/test_engine.py`
- Modify: `backend/tests/vision/test_track_lifecycle.py`

- [x] **Step 1: Write failing tracker frame-rate tests**

In `backend/tests/inference/test_engine.py`, add construction and rebuild tests
near existing runtime-engine FPS tests:

```python
@pytest.mark.asyncio
async def test_tracker_uses_effective_processing_fps_after_cpu_fallback_clamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    captured: dict[str, TrackerConfig] = {}
    _patch_runtime_engine_build_dependencies(monkeypatch)

    class _CpuRuntime:
        @staticmethod
        def get_available_providers() -> list[str]:
            return ["CPUExecutionProvider"]

    def fake_create_tracker(config: TrackerConfig) -> _FakeTracker:
        captured["tracker_config"] = config
        return _FakeTracker()

    monkeypatch.setattr(engine_module, "import_onnxruntime", lambda: _CpuRuntime())
    monkeypatch.setattr(engine_module, "create_tracker", fake_create_tracker)
    base_config = _engine_config(camera_id)
    config = base_config.model_copy(
        update={"camera": base_config.camera.model_copy(update={"fps_cap": 25})}
    )

    engine = await engine_module.build_runtime_engine(
        config,
        settings=engine_module.Settings(
            _env_file=None,
            cpu_fallback_processing_fps_cap=12,
        ),
        events_client=_FakeEventClient(),
    )

    try:
        assert captured["tracker_config"].frame_rate == 12
        assert engine._track_lifecycle.config.nominal_frame_interval_ms == pytest.approx(1000.0 / 12.0)
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_tracker_rebuild_uses_effective_processing_fps_after_cpu_fallback_clamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    camera_id = uuid4()
    captured: list[TrackerConfig] = []
    _patch_runtime_engine_build_dependencies(monkeypatch)

    class _CpuRuntime:
        @staticmethod
        def get_available_providers() -> list[str]:
            return ["CPUExecutionProvider"]

    def fake_create_tracker(config: TrackerConfig) -> _FakeTracker:
        captured.append(config)
        return _FakeTracker(tracker_type=config.tracker_type)

    monkeypatch.setattr(engine_module, "import_onnxruntime", lambda: _CpuRuntime())
    monkeypatch.setattr(engine_module, "create_tracker", fake_create_tracker)
    base_config = _engine_config(camera_id)
    config = base_config.model_copy(
        update={"camera": base_config.camera.model_copy(update={"fps_cap": 25})}
    )

    engine = await engine_module.build_runtime_engine(
        config,
        settings=engine_module.Settings(
            _env_file=None,
            cpu_fallback_processing_fps_cap=12,
        ),
        events_client=_FakeEventClient(),
    )

    try:
        await engine.apply_command(engine_module.CameraCommand(tracker_type=TrackerType.BYTETRACK))

        assert captured[-1].tracker_type is TrackerType.BYTETRACK
        assert captured[-1].frame_rate == 12
        assert engine._track_lifecycle.config.nominal_frame_interval_ms == pytest.approx(1000.0 / 12.0)
    finally:
        await engine.close()
```

- [x] **Step 2: Run the test to verify failure**

Run:

```bash
./backend/.venv/bin/pytest \
  backend/tests/inference/test_engine.py::test_tracker_uses_effective_processing_fps_after_cpu_fallback_clamp \
  backend/tests/inference/test_engine.py::test_tracker_rebuild_uses_effective_processing_fps_after_cpu_fallback_clamp \
  -q
```

Expected: FAIL because tracker config still uses `config.tracker.frame_rate`.

- [x] **Step 3: Add lifecycle config cadence field**

In `backend/src/argus/vision/track_lifecycle.py`, update `TrackLifecycleConfig`:

```python
@dataclass(frozen=True, slots=True)
class TrackLifecycleConfig:
    coast_ttl_ms: int = DEFAULT_TRACK_COAST_TTL_MS
    tentative_hits: int = 2
    instant_activation_confidence: float = 0.75
    duplicate_iou_threshold: float = 0.60
    duplicate_replacement_confidence_delta: float = 0.25
    source_match_center_distance_ratio: float = 1.50
    reassociate_iou_threshold: float = 0.35
    reassociate_center_distance_ratio: float = 0.45
    velocity_damping: float = 0.70
    nominal_frame_interval_ms: float = 1000.0 / 25.0
    confidence_ema_alpha: float = 0.4
```

- [x] **Step 4: Thread effective FPS into tracker and lifecycle config**

In `backend/src/argus/inference/engine.py`, change signatures:

```python
def _tracker_config_from_resolved_profile(
    config: EngineConfig,
    tracker_type: TrackerType,
    resolved_profile: ResolvedSceneVisionProfile,
    *,
    effective_processing_fps: int,
) -> TrackerConfig:
    frame_rate = max(1, int(effective_processing_fps))
```

```python
def _track_lifecycle_config_from_resolved_profile(
    config: EngineConfig,
    resolved_profile: ResolvedSceneVisionProfile,
    *,
    effective_processing_fps: int,
) -> TrackLifecycleConfig:
    del config
    nominal_frame_interval_ms = 1000.0 / max(1, int(effective_processing_fps))
```

Pass `effective_processing_fps` from the same local variable used for
`CameraSourceConfig.fps_cap` in `build_runtime_engine(...)`. In
`RuntimeInferenceEngine._build_tracker()` and
`RuntimeInferenceEngine._build_track_lifecycle()`, recompute the value with
`self._effective_processing_fps_cap()` rather than storing a second copy:

```python
def _build_tracker(self, tracker_type: TrackerType) -> Tracker:
    tracker_config = _tracker_config_from_resolved_profile(
        self.config,
        tracker_type,
        self._resolved_vision_profile,
        effective_processing_fps=self._effective_processing_fps_cap(),
        runtime_policy=self._runtime_policy,
    )
    return _call_tracker_factory(self._tracker_factory, tracker_type, tracker_config)


def _build_track_lifecycle(self) -> TrackLifecycleManager:
    lifecycle_config = _track_lifecycle_config_from_resolved_profile(
        self.config,
        self._resolved_vision_profile,
        effective_processing_fps=self._effective_processing_fps_cap(),
    )
    return TrackLifecycleManager(lifecycle_config)
```

- [x] **Step 5: Run focused FPS tests**

Run:

```bash
./backend/.venv/bin/pytest \
  backend/tests/inference/test_engine.py::test_build_runtime_engine_uses_camera_fps_cap_for_capture_not_stream_profile \
  backend/tests/inference/test_engine.py::test_build_runtime_engine_caps_cpu_fallback_processing_fps \
  backend/tests/inference/test_engine.py::test_tracker_uses_effective_processing_fps_after_cpu_fallback_clamp \
  backend/tests/inference/test_engine.py::test_tracker_rebuild_uses_effective_processing_fps_after_cpu_fallback_clamp \
  -q
```

Expected: PASS.

---

### Task 3: Runtime-Gated ReID and GMC Profile Wiring

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/vision/profiles.py`
- Modify: `backend/src/argus/vision/tracker.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/tests/vision/test_profiles.py`
- Modify: `backend/tests/vision/test_tracker.py`
- Modify: `backend/tests/inference/test_engine.py`

- [x] **Step 1: Write failing profile tests**

Add to `backend/tests/vision/test_profiles.py`:

```python
def test_tracker_profile_resolves_gmc_method_override() -> None:
    resolved = resolve_scene_vision_profile(
        {
            "accuracy_mode": "balanced",
            "compute_tier": "edge_standard",
            "tracker_profile": {"gmc_method": "sparseOptFlow"},
        },
        has_homography=False,
    )

    assert resolved.tracker.gmc_method == "sparseOptFlow"


def test_tracker_profile_rejects_unknown_gmc_method() -> None:
    with pytest.raises(ValidationError):
        SceneVisionProfile.model_validate(
            {"tracker_profile": {"gmc_method": "ecc"}}
        )
```

Add imports:

```python
from pydantic import ValidationError
from argus.api.contracts import SceneVisionProfile
```

- [x] **Step 2: Implement contract and profile fields**

In `backend/src/argus/api/contracts.py`, define this model next to
`MotionMetricsSettings`:

```python
TrackerGmcMethod = Literal["none", "sparseOptFlow"]


class TrackerProfileSettings(BaseModel):
    new_track_min_hits: int | None = Field(default=None, ge=1)
    coast_seconds: float | None = Field(default=None, ge=0.5, le=8.0)
    gmc_method: TrackerGmcMethod = "none"

    model_config = ConfigDict(extra="allow")
```

Change `SceneVisionProfile.tracker_profile` from a free dict to:

```python
tracker_profile: TrackerProfileSettings = Field(default_factory=TrackerProfileSettings)
```

In `backend/src/argus/vision/profiles.py`, add to `ResolvedTrackerProfile`:

```python
gmc_method: Literal["none", "sparseOptFlow"] = "none"
```

Normalize the typed settings before reading overrides:

```python
tracker_overrides = requested.tracker_profile.model_dump(mode="python")
gmc_method = tracker_overrides["gmc_method"]
```

Set `gmc_method=gmc_method` in `ResolvedTrackerProfile(...)`.

- [x] **Step 3: Write failing ReID runtime-gate tests**

In `backend/tests/inference/test_engine.py`, add:

```python
def test_tracker_config_disables_reid_for_cpu_fallback_runtime() -> None:
    config = _engine_config(uuid4()).model_copy(
        update={
            "vision_profile": SceneVisionProfile(
                accuracy_mode="maximum_accuracy",
                compute_tier="central_gpu",
            ).model_dump(mode="python")
        }
    )
    resolved = engine_module.resolve_scene_vision_profile(
        config.vision_profile,
        has_homography=False,
    )

    tracker_config = engine_module._tracker_config_from_resolved_profile(
        config,
        TrackerType.BOTSORT,
        resolved,
        effective_processing_fps=15,
        runtime_policy=RuntimeExecutionPolicy(
            provider="CPUExecutionProvider",
            profile=ExecutionProfile.CPU_FALLBACK,
        ),
    )

    assert tracker_config.with_reid is False
```

- [x] **Step 4: Implement ReID runtime gate**

In `backend/src/argus/inference/engine.py`, add helper:

```python
def _runtime_supports_reid(runtime_policy: RuntimeExecutionPolicy | None) -> bool:
    if runtime_policy is None:
        return False
    if _runtime_policy_uses_cpu_fallback(runtime_policy):
        return False
    return runtime_policy.provider in {
        "CUDAExecutionProvider",
        "TensorrtExecutionProvider",
    }
```

Update `_tracker_config_from_resolved_profile(...)` to accept
`runtime_policy: RuntimeExecutionPolicy | None = None`, then:

```python
with_reid = (
    tracker_type is TrackerType.BOTSORT
    and resolved_profile.tracker.appearance_ready
    and _runtime_supports_reid(runtime_policy)
)
tracker_config = TrackerConfig.for_scene_profile(
    scene_profile,
    tracker_type=tracker_type,
    frame_rate=frame_rate,
)
tracker_config.with_reid = with_reid
tracker_config.gmc_method = resolved_profile.tracker.gmc_method
return tracker_config
```

If assignment fails because `TrackerConfig` is made frozen in the same branch,
use `dataclasses.replace(...)` instead of mutating the object.

- [x] **Step 5: Run profile and ReID tests**

Run:

```bash
./backend/.venv/bin/pytest \
  backend/tests/vision/test_profiles.py \
  backend/tests/vision/test_tracker.py \
  backend/tests/inference/test_engine.py::test_tracker_config_disables_reid_for_cpu_fallback_runtime \
  -q
```

Expected: PASS.

---

### Task 4: Candidate Quality Association Semantics

**Files:**
- Modify: `backend/src/argus/vision/candidate_quality.py`
- Modify: `backend/tests/vision/test_candidate_quality.py`

- [x] **Step 1: Write failing test for no new low-confidence track**

Update `test_person_can_be_association_eligible_without_display_eligibility` in
`backend/tests/vision/test_candidate_quality.py` so it expects rejection without
an existing track:

```python
assert filtered == []
assert [
    (decision.accepted, decision.display_eligible, decision.reason)
    for decision in decisions
] == [
    (False, False, "new_track_low_confidence")
]
```

Add a separate accepted association test:

```python
def test_association_eligible_person_extends_nearby_existing_track() -> None:
    gate = CandidateQualityGate(
        CandidateQualityConfig(
            association_min_confidence={"person": 0.25, "default": 0.40},
            display_min_confidence={"person": 0.45, "default": 0.40},
        )
    )
    detection = _person(confidence=0.30, bbox=(112.0, 106.0, 272.0, 526.0))

    filtered, decisions = gate.filter_detections(
        [detection],
        existing_tracks=[_stable_person_track()],
        frame_shape=FRAME_SHAPE,
    )

    assert filtered == [detection]
    assert [(decision.accepted, decision.display_eligible, decision.reason) for decision in decisions] == [
        (True, False, "existing_track_association")
    ]
```

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_candidate_quality.py -q
```

Expected: FAIL because the gate currently accepts association-threshold detections as `new_track_high_confidence`.

- [x] **Step 3: Implement semantics**

In `_decide(...)`, replace the `if detection.confidence >= association_threshold` branch with:

```python
if (
    detection.confidence >= association_threshold
    and self._is_near_existing_track(detection, same_class_tracks, frame_shape)
):
    return CandidateDecision(
        detection,
        accepted=True,
        reason="existing_track_association",
        display_eligible=display_eligible,
    )

if display_eligible:
    return CandidateDecision(
        detection,
        accepted=True,
        reason="new_track_high_confidence",
        display_eligible=True,
    )
```

Keep the continuation and duplicate-fragment logic before this branch.

- [x] **Step 4: Run candidate quality tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_candidate_quality.py -q
```

Expected: PASS.

---

### Task 5: Lifecycle Motion, Confidence, Class, and Attributes

**Files:**
- Modify: `backend/src/argus/vision/track_lifecycle.py`
- Modify: `backend/src/argus/vision/types.py`
- Modify: `backend/tests/vision/test_track_lifecycle.py`

- [x] **Step 1: Write failing lifecycle tests**

Add tests to `backend/tests/vision/test_track_lifecycle.py`:

```python
def test_coasting_preserves_bbox_size_and_moves_center_by_velocity() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(
            coast_ttl_ms=2_500,
            nominal_frame_interval_ms=100.0,
            velocity_damping=1.0,
        )
    )
    ts0 = datetime(2026, 1, 1, tzinfo=UTC)
    ts1 = ts0 + timedelta(milliseconds=100)
    ts2 = ts1 + timedelta(milliseconds=100)
    manager.update([_person(track_id=1, bbox=(100.0, 100.0, 140.0, 200.0))], ts=ts0, frame_shape=(300, 300, 3))
    manager.update([_person(track_id=1, bbox=(110.0, 100.0, 150.0, 200.0))], ts=ts1, frame_shape=(300, 300, 3))

    tracks = manager.update([], ts=ts2, frame_shape=(300, 300, 3))

    assert len(tracks) == 1
    x1, y1, x2, y2 = tracks[0].detection.bbox
    assert (x2 - x1, y2 - y1) == pytest.approx((40.0, 100.0))
    assert ((x1 + x2) / 2.0) > 130.0


def test_confidence_ema_smooths_published_detection_confidence() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(confidence_ema_alpha=0.5, tentative_hits=1)
    )
    ts0 = datetime(2026, 1, 1, tzinfo=UTC)
    manager.update([_person(track_id=1, confidence=0.9)], ts=ts0, frame_shape=(300, 300, 3))
    tracks = manager.update(
        [_person(track_id=1, confidence=0.5)],
        ts=ts0 + timedelta(milliseconds=100),
        frame_shape=(300, 300, 3),
    )

    assert tracks[0].detection.confidence == pytest.approx(0.7)


def test_class_votes_stabilize_detector_flicker() -> None:
    manager = TrackLifecycleManager(TrackLifecycleConfig(tentative_hits=1))
    ts0 = datetime(2026, 1, 1, tzinfo=UTC)
    manager.update([_person(track_id=1, class_name="person")], ts=ts0, frame_shape=(300, 300, 3))
    manager.update([_person(track_id=1, class_name="person")], ts=ts0 + timedelta(milliseconds=100), frame_shape=(300, 300, 3))
    tracks = manager.update([_person(track_id=1, class_name="pedestrian")], ts=ts0 + timedelta(milliseconds=200), frame_shape=(300, 300, 3))

    assert tracks[0].detection.class_name == "person"


def test_detection_attributes_are_immutable_and_shared() -> None:
    detection = Detection(class_name="person", confidence=0.9, bbox=(0.0, 0.0, 1.0, 1.0), attributes={"k": "v"})

    with pytest.raises(TypeError):
        detection.attributes["k"] = "changed"

    copied = _copy_detection(detection)
    assert copied.attributes is detection.attributes
```

Add imports if missing:

```python
from datetime import UTC, datetime, timedelta
```

- [x] **Step 2: Run lifecycle tests to verify failure**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_track_lifecycle.py -q
```

Expected: FAIL on bbox-size preservation, EMA, class voting, and immutable attributes.

- [x] **Step 3: Freeze detection attributes**

In `backend/src/argus/vision/types.py`, update `Detection`:

```python
from collections.abc import Mapping
from types import MappingProxyType


@dataclass(slots=True)
class Detection:
    class_name: str
    confidence: float
    bbox: BoundingBox
    class_id: int | None = None
    track_id: int | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)
    zone_id: str | None = None
    speed_kph: float | None = None
    direction_deg: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _freeze_attributes(self.attributes))

    def with_updates(self, **changes: Any) -> Detection:
        if "attributes" in changes:
            changes["attributes"] = _freeze_attributes(changes["attributes"])
        return replace(self, **changes)


def _freeze_attributes(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if isinstance(value, MappingProxyType):
        return value
    return MappingProxyType(dict(value or {}))
```

In `track_lifecycle.py`, change:

```python
def _copy_detection(detection: Detection) -> Detection:
    return detection.with_updates()
```

- [x] **Step 4: Add motion filter and output smoothing**

In `track_lifecycle.py`, add:

```python
@dataclass(slots=True)
class _MotionFilter:
    center_x: float
    center_y: float
    velocity_x_per_ms: float = 0.0
    velocity_y_per_ms: float = 0.0

    def update(self, bbox: BoundingBox, dt_ms: float) -> None:
        new_center_x, new_center_y, _, _ = _bbox_center_size(bbox)
        safe_dt = max(1.0, dt_ms)
        self.velocity_x_per_ms = (new_center_x - self.center_x) / safe_dt
        self.velocity_y_per_ms = (new_center_y - self.center_y) / safe_dt
        self.center_x = new_center_x
        self.center_y = new_center_y

    def predict(self, dt_ms: float, damping: float) -> tuple[float, float]:
        self.velocity_x_per_ms *= damping
        self.velocity_y_per_ms *= damping
        self.center_x += self.velocity_x_per_ms * dt_ms
        self.center_y += self.velocity_y_per_ms * dt_ms
        return self.center_x, self.center_y
```

Add fields to `_TrackMemory`:

```python
motion_filter: _MotionFilter | None = None
last_width: float = 0.0
last_height: float = 0.0
confidence_ema: float | None = None
class_votes: dict[str, int] = field(default_factory=dict)
```

Add helper:

```python
def _bbox_center_size(bbox: BoundingBox) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    return (x1 + width / 2.0, y1 + height / 2.0, width, height)
```

In `_apply_detection`, update motion, EMA, and votes before setting
`memory.detection`:

```python
previous_seen_ts = memory.last_seen_ts
dt_ms = max(1, _elapsed_ms(previous_seen_ts, ts))
center_x, center_y, width, height = _bbox_center_size(bbox)
if memory.motion_filter is None:
    memory.motion_filter = _MotionFilter(center_x=center_x, center_y=center_y)
else:
    memory.motion_filter.update(bbox, float(dt_ms))
memory.last_width = width
memory.last_height = height
memory.confidence_ema = (
    detection.confidence
    if memory.confidence_ema is None
    else self.config.confidence_ema_alpha * detection.confidence
    + (1.0 - self.config.confidence_ema_alpha) * memory.confidence_ema
)
memory.class_votes[detection.class_name] = memory.class_votes.get(detection.class_name, 0) + 1
published_class_name = _voted_class_name(memory.class_votes, detection.class_name)
published_detection = detection.with_updates(
    track_id=stable_id,
    bbox=bbox,
    confidence=memory.confidence_ema,
    class_name=published_class_name,
)
memory.detection = _copy_detection(published_detection)
```

Add:

```python
def _voted_class_name(votes: dict[str, int], current_class_name: str) -> str:
    best_count = max(votes.values(), default=0)
    tied = [class_name for class_name, count in votes.items() if count == best_count]
    if current_class_name in tied:
        return current_class_name
    return sorted(tied)[0] if tied else current_class_name
```

In `_coast_track`, use the motion filter:

```python
dt_ms = max(1, _elapsed_ms(memory.updated_ts, ts))
damping = self.config.velocity_damping ** (
    dt_ms / max(1.0, self.config.nominal_frame_interval_ms)
)
if memory.motion_filter is None:
    center_x, center_y, width, height = _bbox_center_size(memory.detection.bbox)
    memory.motion_filter = _MotionFilter(center_x=center_x, center_y=center_y)
    memory.last_width = width
    memory.last_height = height
predicted_center_x, predicted_center_y = memory.motion_filter.predict(float(dt_ms), damping)
width = memory.last_width
height = memory.last_height
predicted_bbox = (
    predicted_center_x - width / 2.0,
    predicted_center_y - height / 2.0,
    predicted_center_x + width / 2.0,
    predicted_center_y + height / 2.0,
)
memory.detection = _copy_detection(
    memory.detection.with_updates(
        track_id=memory.stable_track_id,
        bbox=_clamp_bbox(predicted_bbox, frame_shape),
    )
)
memory.updated_ts = ts
```

- [x] **Step 5: Run lifecycle tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_track_lifecycle.py -q
```

Expected: PASS.

---

### Task 6: Tracker Adapter Dtype and Config Propagation

**Files:**
- Modify: `backend/src/argus/vision/tracker.py`
- Modify: `backend/tests/vision/test_tracker.py`

- [x] **Step 1: Write failing dtype and namespace tests**

Add to `backend/tests/vision/test_tracker.py`:

```python
def test_tracker_results_class_ids_are_int32() -> None:
    results = tracker_module._TrackerResults(
        [
            Detection(class_name="person", class_id=0, confidence=0.9, bbox=(0.0, 0.0, 10.0, 10.0)),
            Detection(class_name="unknown", class_id=None, confidence=0.3, bbox=(10.0, 10.0, 20.0, 20.0)),
        ]
    )

    assert results.cls.dtype == np.int32
    assert results.cls.tolist() == [0, -1]


def test_tracker_config_namespace_carries_reid_and_gmc() -> None:
    namespace = TrackerConfig(
        tracker_type=TrackerType.BOTSORT,
        with_reid=True,
        gmc_method="sparseOptFlow",
    ).to_namespace()

    assert namespace.with_reid is True
    assert namespace.gmc_method == "sparseOptFlow"
```

- [x] **Step 2: Run tests to verify dtype failure**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_tracker.py -q
```

Expected: FAIL on dtype until implementation changes.

- [x] **Step 3: Change dtype**

In `_TrackerResults.__init__`, change:

```python
self.cls = np.asarray(
    [
        detection.class_id if detection.class_id is not None else -1
        for detection in detections
    ],
    dtype=np.int32,
)
```

- [x] **Step 4: Run tracker tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_tracker.py -q
```

Expected: PASS.

---

### Task 7: Wire Replay Runner to Actual Tracker Stack

**Files:**
- Modify: `scripts/tracking_replay_benchmark.py`
- Modify: `backend/tests/scripts/test_tracking_replay_benchmark.py`

- [x] **Step 1: Add replay runner test with fake tracker stack**

Add a test that passes detections through a simple runner and compares metrics:

```python
def test_run_fixture_benchmark_uses_ground_truth_metrics(tmp_path: Path) -> None:
    fixture = _write_two_frame_fixture(tmp_path)

    summary = MODULE.run_fixture_benchmark(
        fixture_dir=fixture,
        output_json=False,
        track_runner=lambda frame: [
            MODULE.ReplayTrack(
                stable_track_id=frame.frame_id,
                class_name="person",
                bbox=frame.ground_truth[0].bbox,
            )
        ],
    )

    assert summary["id_switches"] == 1
    assert summary["track_fragmentation_sum"] == 1
```

Define `_write_two_frame_fixture(...)` in the test file using the same schema from Task 1.

- [x] **Step 2: Implement `run_fixture_benchmark`**

In `scripts/tracking_replay_benchmark.py`, add:

```python
def run_fixture_benchmark(
    *,
    fixture_dir: Path,
    output_json: bool,
    track_runner: Callable[[ReplayFrame], list[ReplayTrack]] | None = None,
) -> dict[str, object]:
    manifest, frames = load_replay_fixture(fixture_dir)
    tracker_scene_profile = str(manifest.get("tracker_scene_profile", "difficult"))
    runner = track_runner or _default_track_runner(
        int(manifest["fps"]),
        tracker_scene_profile=tracker_scene_profile,
    )
    outputs = {frame.frame_id: runner(frame) for frame in frames}
    return evaluate_tracks(
        frames,
        track_outputs_by_frame=outputs,
        iou_match_threshold=float(manifest.get("iou_match_threshold", 0.5)),
    )
```

Implement `_default_track_runner(...)` by creating detections, tracker, and lifecycle manager once:

```python
def _default_track_runner(
    fps: int,
    *,
    tracker_scene_profile: str = "difficult",
) -> Callable[[ReplayFrame], list[ReplayTrack]]:
    from datetime import UTC, datetime, timedelta

    from argus.models.enums import TrackerType
    from argus.vision.track_lifecycle import TrackLifecycleConfig, TrackLifecycleManager
    from argus.vision.tracker import TrackerConfig, create_tracker
    from argus.vision.types import Detection

    if tracker_scene_profile not in {"efficient", "difficult"}:
        raise ValueError("tracker_scene_profile must be 'efficient' or 'difficult'.")
    tracker = create_tracker(
        TrackerConfig.for_scene_profile(
            tracker_scene_profile,
            tracker_type=TrackerType.BOTSORT,
            frame_rate=fps,
        )
    )
    lifecycle = TrackLifecycleManager(
        TrackLifecycleConfig(nominal_frame_interval_ms=1000.0 / max(1, fps))
    )
    start = datetime(2026, 1, 1, tzinfo=UTC)

    def run(frame: ReplayFrame) -> list[ReplayTrack]:
        detections = [
            Detection(
                class_name=detection.class_name,
                class_id=detection.class_id,
                confidence=detection.confidence,
                bbox=detection.bbox,
            )
            for detection in frame.detections
        ]
        image = cv2.imread(str(frame.image_path)) if frame.image_path is not None else None
        tracked = tracker.update(detections, frame=image)
        lifecycle_tracks = lifecycle.update(
            tracked,
            ts=start + timedelta(milliseconds=(frame.frame_id - 1) * (1000.0 / max(1, fps))),
            frame_shape=image.shape if image is not None else None,
        )
        return [
            ReplayTrack(
                stable_track_id=track.stable_track_id,
                class_name=track.detection.class_name,
                bbox=track.detection.bbox,
            )
            for track in lifecycle_tracks
        ]

    return run
```

- [x] **Step 3: Update CLI args**

Add:

```python
parser.add_argument("--fixture", type=Path, help="Directory containing replay fixture manifest and JSONL streams.")
parser.add_argument("--baseline", type=Path, help="Optional baseline JSON to compare against.")
```

In `main()`, if `args.fixture` is set, call `run_fixture_benchmark(...)`, compare baseline if supplied, print JSON if requested, and return `1` on comparison failures.

- [x] **Step 4: Run replay tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/scripts/test_tracking_replay_benchmark.py -q
```

Expected: PASS, except the intentionally marked xfail benchmark gate until Task 8.

---

### Task 8: Enable Replay Gate and Final Verification

**Files:**
- Modify: `backend/tests/scripts/test_tracking_replay_benchmark.py`
- Modify: `backend/tests/scripts/fixtures/tracking_replay_baseline.json`
- Modify: `docs/superpowers/status/2026-06-13-tracker-continuity-implementation-evidence.md`

- [x] **Step 1: Generate baseline JSON from base commit**

Use a temporary worktree at base commit `75e95b8f`:

```bash
git worktree add /tmp/vision-tracker-baseline 75e95b8f
cd /tmp/vision-tracker-baseline
./backend/.venv/bin/python scripts/tracking_replay_benchmark.py \
  --fixture backend/tests/scripts/fixtures/tracker_continuity_people_001 \
  --json > /tmp/tracking_replay_baseline_metrics.json
cd /Users/yann.moren/vision
git worktree remove /tmp/vision-tracker-baseline
```

If the fixture files do not exist in the base worktree, copy the fixture
directory from the implementation worktree into `/tmp/vision-tracker-baseline/backend/tests/scripts/fixtures/`
before running the benchmark. Copy only files under
`backend/tests/scripts/fixtures/tracker_continuity_people_001/`.
Do not regenerate fixture JSONL or images between the baseline and current
runs; both comparisons must use byte-identical fixture contents.

- [x] **Step 2: Write committed baseline file**

Create `backend/tests/scripts/fixtures/tracking_replay_baseline.json`:

```json
{
  "fixture_id": "tracker_continuity_people_001",
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

Replace the numeric metric values with the values from `/tmp/tracking_replay_baseline_metrics.json`.

- [x] **Step 3: Remove xfail from replay gate**

In `backend/tests/scripts/test_tracking_replay_benchmark.py`, remove the xfail marker from the committed fixture gate test.

- [x] **Step 4: Run full targeted verification**

Run:

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
```

Expected: PASS.

Run:

```bash
./backend/.venv/bin/ruff check \
  backend/src/argus/vision \
  backend/src/argus/inference/engine.py \
  backend/src/argus/api/contracts.py \
  scripts/tracking_replay_benchmark.py \
  backend/tests/scripts/test_tracking_replay_benchmark.py
```

Expected: `All checks passed!`

- [x] **Step 5: Write implementation evidence**

Generate the evidence file from the two benchmark JSON files:

```bash
./backend/.venv/bin/python scripts/tracking_replay_benchmark.py \
  --fixture backend/tests/scripts/fixtures/tracker_continuity_people_001 \
  --json > /tmp/tracking_replay_current_metrics.json
./backend/.venv/bin/python - <<'PY'
from pathlib import Path
import json

baseline = json.loads(Path("/tmp/tracking_replay_baseline_metrics.json").read_text(encoding="utf-8"))
current = json.loads(Path("/tmp/tracking_replay_current_metrics.json").read_text(encoding="utf-8"))
lines = [
    "# Tracker Continuity Implementation Evidence",
    "",
    "Date: 2026-06-13",
    "Branch: codex/sceneops-pack-registry",
    "",
    "## Replay Gate",
    "",
    "- Fixture: tracker_continuity_people_001",
    "- Base commit: 75e95b8f",
    "- Current commit: local implementation branch",
    f"- ID switches: {baseline['id_switches']} -> {current['id_switches']}",
    f"- Track fragmentation sum: {baseline['track_fragmentation_sum']} -> {current['track_fragmentation_sum']}",
    f"- Coverage ratio: {baseline['coverage_ratio']} -> {current['coverage_ratio']}",
    f"- Duplicate active track frames: {baseline['duplicate_active_track_frames']} -> {current['duplicate_active_track_frames']}",
    "",
    "## Verification",
    "",
    "- backend replay and vision tests: PASS",
    "- inference wiring tests: PASS",
    "- MediaMTX regression tests: PASS",
    "- ruff: PASS",
    "",
    "## Live Evidence",
    "",
    "- Jetson live A/B: NOT RUN in this implementation pass",
    "- Central live A/B: NOT RUN, blocked by central worker stability and native acceleration follow-up",
    "",
]
Path("docs/superpowers/status/2026-06-13-tracker-continuity-implementation-evidence.md").write_text(
    "\n".join(lines),
    encoding="utf-8",
)
PY
```

---

## Final Verification Before Commit

Run:

```bash
git diff --check
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

Expected:

- `git diff --check` exits 0
- pytest exits 0
- ruff prints `All checks passed!`

Commit only after the user approves:

```bash
git add \
  scripts/tracking_replay_benchmark.py \
  backend/src/argus/inference/engine.py \
  backend/src/argus/vision/tracker.py \
  backend/src/argus/vision/profiles.py \
  backend/src/argus/vision/candidate_quality.py \
  backend/src/argus/vision/track_lifecycle.py \
  backend/src/argus/vision/types.py \
  backend/src/argus/api/contracts.py \
  backend/tests/scripts/test_tracking_replay_benchmark.py \
  backend/tests/scripts/fixtures/tracker_continuity_people_001 \
  backend/tests/scripts/fixtures/tracking_replay_baseline.json \
  backend/tests/vision/test_tracker.py \
  backend/tests/vision/test_profiles.py \
  backend/tests/vision/test_candidate_quality.py \
  backend/tests/vision/test_track_lifecycle.py \
  backend/tests/inference/test_engine.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/streaming/test_mediamtx.py \
  docs/superpowers/status/2026-06-13-tracker-continuity-implementation-evidence.md
git commit -m "feat: improve tracker continuity"
```

---

## Self-Review Notes

- Spec coverage: all revised spec sections A1 through A5 map to tasks above.
- Contract safety: no live telemetry fields are renamed or required by clients.
- Runtime safety: ReID remains off on CPU fallback and cannot silently download a model.
- Evidence safety: replay benchmark uses ground-truth `gt_id`, not class changes.
