# Scene Vision Profiles And Candidate Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add selectable scene vision profiles, explicit speed enablement, detection include/exclusion regions, and a candidate quality gate so live tracking can reject obvious false positives and avoid duplicate fragments without sacrificing low-score association for existing tracks.

**Architecture:** Store operator-facing profile settings on the camera, resolve them into worker runtime settings, run detection regions and candidate quality gating before the tracker, keep authoritative lifecycle state after the tracker, and compute speed only when motion metrics are enabled. Event zones remain separate from detection regions.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, SQLAlchemy/Alembic, Shapely, OpenCV, Ultralytics BoT-SORT/ByteTrack adapter, React 19, TypeScript 5.7, Vite 6, Tailwind v4, Vitest, React Testing Library.

**Spec source:** `/Users/yann.moren/vision/docs/superpowers/specs/2026-05-10-scene-vision-profiles-and-candidate-quality-design.md`

---

## Execution Protocol

Execute one task at a time. Commit after each completed task and push to origin
for testing. Do not stage unrelated untracked scratch files.

Keep WebGL off. Do not reopen Jetson/TensorRT/RTSP runtime work in this plan.
Jetson Orin Nano Super is represented as an advanced edge compute tier, but this
plan does not implement a DeepStream or TensorRT path.

## Pre-Flight

```bash
cd /Users/yann.moren/vision
git status --short --branch
git rev-parse --abbrev-ref HEAD
```

Expected:

- branch is `codex/omnisight-ui-spec-implementation`
- unrelated scratch files remain untracked
- no unrelated files are staged

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `backend/src/argus/api/contracts.py` | Modify | profile, motion metrics, detection region contracts |
| `backend/src/argus/models/tables.py` | Modify | camera JSONB fields |
| `backend/src/argus/migrations/versions/*_scene_vision_profiles.py` | Create | add camera columns |
| `backend/src/argus/services/app.py` | Modify | normalize/profile validation, worker config mapping |
| `backend/src/argus/vision/profiles.py` | Create | pure profile defaults and resolver |
| `backend/src/argus/vision/detection_regions.py` | Create | include/exclusion region matching |
| `backend/src/argus/vision/candidate_quality.py` | Create | candidate gate config and filtering decisions |
| `backend/src/argus/vision/track_lifecycle.py` | Modify | expose current stable tracks for candidate gate context |
| `backend/src/argus/inference/engine.py` | Modify | wire regions, gate, speed toggle, profile settings |
| `backend/src/argus/core/metrics.py` | Modify | candidate/region/motion counters |
| `backend/tests/services/test_camera_service.py` | Modify | API validation and normalization coverage |
| `backend/tests/services/test_camera_worker_config.py` | Modify | worker config profile mapping |
| `backend/tests/vision/test_profiles.py` | Create | profile resolver tests |
| `backend/tests/vision/test_detection_regions.py` | Create | region policy tests |
| `backend/tests/vision/test_candidate_quality.py` | Create | false positive and duplicate-fragment tests |
| `backend/tests/inference/test_engine.py` | Modify | integration coverage |
| `frontend/src/lib/api.generated.ts` | Regenerate | frontend API contract |
| `frontend/src/components/cameras/CameraWizard.tsx` | Modify | profile, speed toggle, detection regions UI |
| `frontend/src/components/cameras/CameraWizard.test.tsx` | Modify | wizard coverage |
| `frontend/src/pages/Cameras.tsx` | Modify | optional profile/status display |

---

## Task 1: Backend Contracts And Migration

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/*_scene_vision_profiles.py`
- Modify: `backend/tests/services/test_camera_service.py`
- Modify: `backend/tests/models/test_schema.py`

- [ ] **Step 1: Write failing contract tests**

Add tests to `backend/tests/services/test_camera_service.py`:

- `test_create_camera_allows_detection_only_scene_without_homography`
- `test_create_camera_requires_homography_when_speed_enabled`
- `test_update_camera_normalizes_detection_region_coordinates`
- `test_update_camera_rejects_detection_region_coordinates_outside_frame`

Use `CameraCreate`/`CameraUpdate` payloads with:

```python
vision_profile={
    "accuracy_mode": "balanced",
    "compute_tier": "edge_standard",
    "scene_difficulty": "cluttered",
    "object_domain": "people",
    "motion_metrics": {"speed_enabled": False},
}
detection_regions=[
    {
        "id": "lab-floor",
        "mode": "include",
        "polygon": [[100, 100], [1100, 100], [1100, 700], [100, 700]],
        "class_names": ["person"],
        "frame_size": {"width": 1280, "height": 720},
    }
]
```

Add a schema test to `backend/tests/models/test_schema.py` asserting the camera
table includes `vision_profile` and `detection_regions`.

- [ ] **Step 2: Run failing tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_camera_service.py::test_create_camera_allows_detection_only_scene_without_homography backend/tests/services/test_camera_service.py::test_create_camera_requires_homography_when_speed_enabled backend/tests/services/test_camera_service.py::test_update_camera_normalizes_detection_region_coordinates backend/tests/services/test_camera_service.py::test_update_camera_rejects_detection_region_coordinates_outside_frame backend/tests/models/test_schema.py -q
```

Expected: fail because contracts and columns do not exist or homography is still
required.

- [ ] **Step 3: Add API models**

In `backend/src/argus/api/contracts.py`, add:

```python
class MotionMetricsSettings(BaseModel):
    speed_enabled: bool = False


class SceneVisionProfile(BaseModel):
    compute_tier: Literal[
        "cpu_low",
        "edge_standard",
        "edge_advanced_jetson",
        "central_gpu",
    ] = "edge_standard"
    accuracy_mode: Literal[
        "fast",
        "balanced",
        "maximum_accuracy",
        "open_vocabulary",
    ] = "balanced"
    scene_difficulty: Literal[
        "open",
        "cluttered",
        "occluded",
        "crowded",
        "traffic",
        "custom",
    ] = "cluttered"
    object_domain: Literal["people", "vehicles", "mixed", "open_vocab"] = "mixed"
    motion_metrics: MotionMetricsSettings = Field(default_factory=MotionMetricsSettings)
    candidate_quality: dict[str, Any] = Field(default_factory=dict)
    tracker_profile: dict[str, Any] = Field(default_factory=dict)
    verifier_profile: dict[str, Any] = Field(default_factory=dict)


class DetectionRegion(BaseModel):
    id: str
    mode: Literal["include", "exclude"]
    polygon: list[Coordinate]
    class_names: list[str] = Field(default_factory=list)
    frame_size: FrameSize | None = None
    points_normalized: list[Coordinate] | None = None

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: list[Coordinate]) -> list[Coordinate]:
        if len(value) < 3:
            raise ValueError("Detection regions must contain at least three vertices.")
        for point in value:
            if len(point) != 2:
                raise ValueError("Each detection region point must contain exactly two coordinates.")
        return value
```

Update camera models:

```python
class CameraCreate(BaseModel):
    ...
    vision_profile: SceneVisionProfile = Field(default_factory=SceneVisionProfile)
    detection_regions: list[DetectionRegion] = Field(default_factory=list)
    homography: HomographyPayload | None = None


class CameraUpdate(BaseModel):
    ...
    vision_profile: SceneVisionProfile | None = None
    detection_regions: list[DetectionRegion] | None = None
    homography: HomographyPayload | None = None


class CameraResponse(BaseModel):
    ...
    vision_profile: SceneVisionProfile = Field(default_factory=SceneVisionProfile)
    detection_regions: list[DetectionRegion] = Field(default_factory=list)
    homography: HomographyPayload | None = None
```

Add a model validator to `CameraCreate` and `CameraUpdate` so
`motion_metrics.speed_enabled=True` requires homography when a complete create
payload is submitted. In update, reject an update that explicitly enables speed
while setting `homography=None`; service-level validation in Task 2 handles the
existing camera state.

- [ ] **Step 4: Add database fields**

In `backend/src/argus/models/tables.py`, add to `Camera`:

```python
vision_profile: Mapped[dict[str, object]] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
)
detection_regions: Mapped[list[dict[str, object]]] = mapped_column(
    JSONB,
    nullable=False,
    default=list,
)
```

Create an Alembic migration adding:

```python
op.add_column(
    "cameras",
    sa.Column("vision_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
)
op.add_column(
    "cameras",
    sa.Column("detection_regions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
)
```

Drop both columns in downgrade.

- [ ] **Step 5: Verify contract tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_camera_service.py::test_create_camera_allows_detection_only_scene_without_homography backend/tests/services/test_camera_service.py::test_create_camera_requires_homography_when_speed_enabled backend/tests/services/test_camera_service.py::test_update_camera_normalizes_detection_region_coordinates backend/tests/services/test_camera_service.py::test_update_camera_rejects_detection_region_coordinates_outside_frame backend/tests/models/test_schema.py -q
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/api/contracts.py backend/src/argus/models/tables.py backend/src/argus/migrations/versions/*_scene_vision_profiles.py backend/tests/services/test_camera_service.py backend/tests/models/test_schema.py
git commit -m "feat(scene): add vision profile camera contracts"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 2: Profile Resolver And Worker Config

**Files:**
- Create: `backend/src/argus/vision/profiles.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`
- Create: `backend/tests/vision/test_profiles.py`

- [ ] **Step 1: Write failing resolver tests**

Create `backend/tests/vision/test_profiles.py` with tests:

- `test_balanced_profile_resolves_botsort_without_reid`
- `test_cpu_low_fast_profile_disables_verifier_and_speed_by_default`
- `test_jetson_advanced_profile_allows_maximum_accuracy_without_deepstream_runtime`
- `test_speed_enabled_requires_homography`

Expected resolved profile fields:

```python
resolved.compute_tier == "edge_advanced_jetson"
resolved.tracker.tracker_type == TrackerType.BOTSORT
resolved.tracker.with_reid is False
resolved.candidate_quality.new_track_min_confidence["person"] >= 0.45
resolved.verifier.mode in {"none", "suspicious_only"}
```

- [ ] **Step 2: Run failing tests**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_profiles.py -q
```

Expected: fail because the resolver does not exist.

- [ ] **Step 3: Implement profile resolver**

Create `backend/src/argus/vision/profiles.py` with:

- `ResolvedMotionMetrics`
- `ResolvedCandidateQuality`
- `ResolvedTrackerProfile`
- `ResolvedVerifierProfile`
- `ResolvedSceneVisionProfile`
- `resolve_scene_vision_profile(profile: Mapping[str, object], *, has_homography: bool) -> ResolvedSceneVisionProfile`

Default behavior:

- `fast + cpu_low`: no verifier, speed off, no ReID, short candidate memory
- `balanced + edge_standard`: BoT-SORT, no ReID, duplicate suppression on
- `maximum_accuracy + edge_advanced_jetson`: BoT-SORT, appearance-ready but
  ReID off until runtime support is explicit, stricter new-track thresholds
- `maximum_accuracy + central_gpu`: BoT-SORT, verifier profile may be
  `suspicious_only`
- `open_vocabulary`: stricter new-track confidence, speed off by default

Do not instantiate models or runtime backends in this resolver.

- [ ] **Step 4: Extend worker contracts**

Add `WorkerVisionSettings` and `WorkerDetectionRegion` aliases or reuse the API
models in `WorkerConfigResponse`:

```python
vision_profile: SceneVisionProfile = Field(default_factory=SceneVisionProfile)
detection_regions: list[DetectionRegion] = Field(default_factory=list)
```

Add matching fields to `EngineConfig`.

- [ ] **Step 5: Map camera profile into worker config**

In `backend/src/argus/services/app.py`:

- load `camera.vision_profile or {}`
- validate with `SceneVisionProfile`
- normalize `camera.detection_regions`
- include both in `WorkerConfigResponse`
- when speed is enabled, verify `camera.homography is not None`

Add worker-config tests asserting:

- detection regions are returned with denormalized points
- speed-enabled profile includes homography
- speed-disabled profile can return `homography=None`
- Jetson tier survives round-trip in worker config

- [ ] **Step 6: Verify profile and worker tests**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_profiles.py backend/tests/services/test_camera_worker_config.py -q
```

Expected: pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/src/argus/vision/profiles.py backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/src/argus/inference/engine.py backend/tests/vision/test_profiles.py backend/tests/services/test_camera_worker_config.py
git commit -m "feat(scene): resolve vision profiles for workers"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 3: Detection Include And Exclusion Regions

**Files:**
- Create: `backend/src/argus/vision/detection_regions.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/tests/vision/test_detection_regions.py`
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write failing region tests**

Create `backend/tests/vision/test_detection_regions.py` with tests:

- `test_no_regions_allows_detection`
- `test_include_region_allows_candidate_inside`
- `test_include_region_rejects_candidate_outside`
- `test_exclusion_region_overrides_include`
- `test_class_scoped_region_only_applies_to_matching_class`
- `test_person_uses_bottom_center_anchor`
- `test_general_object_uses_center_anchor`

Use `Detection` from `argus.vision.types`.

- [ ] **Step 2: Run failing tests**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_detection_regions.py -q
```

Expected: fail because the module does not exist.

- [ ] **Step 3: Implement detection region policy**

Create `backend/src/argus/vision/detection_regions.py`:

- `DetectionRegionPolicy`
- `DetectionRegionDecision`
- `filter_detections(detections: list[Detection]) -> tuple[list[Detection], list[DetectionRegionDecision]]`

Rules:

- empty matching include regions means full-frame include
- include regions require the anchor inside at least one include region
- exclusion regions reject the candidate when the anchor is inside
- class-scoped regions only apply to matching classes
- `person`, `car`, `truck`, `bus`, `motorcycle`, `bicycle`, `forklift` use
  bottom-center
- other classes use bbox center

- [ ] **Step 4: Wire into engine**

In `InferenceEngine.__init__`, build a region policy from
`config.detection_regions`.

In `run_once`, after `_filter_visible_detections` and before tracker update:

```python
region_filtered, region_decisions = self._detection_region_policy.filter_detections(filtered)
```

Feed `region_filtered` forward. Record metrics for rejected decisions in Task 6;
for this task, keep decisions local or logged at debug level.

Add an engine test showing a detection outside an include region never reaches
the tracker/telemetry.

- [ ] **Step 5: Verify region tests**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_detection_regions.py backend/tests/inference/test_engine.py -q
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/vision/detection_regions.py backend/src/argus/inference/engine.py backend/tests/vision/test_detection_regions.py backend/tests/inference/test_engine.py
git commit -m "feat(scene): gate detections by scene regions"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 4: Candidate Quality Gate

**Files:**
- Create: `backend/src/argus/vision/candidate_quality.py`
- Modify: `backend/src/argus/vision/track_lifecycle.py`
- Modify: `backend/src/argus/inference/engine.py`
- Create: `backend/tests/vision/test_candidate_quality.py`
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write failing candidate gate tests**

Create `backend/tests/vision/test_candidate_quality.py` with tests:

- `test_high_confidence_new_person_candidate_passes`
- `test_low_confidence_new_person_candidate_is_rejected`
- `test_low_confidence_detection_near_existing_track_passes_for_association`
- `test_nested_person_fragment_near_existing_track_is_rejected`
- `test_duplicate_vehicle_fragment_uses_class_specific_thresholds`
- `test_unknown_class_uses_default_threshold`

Use a fake existing stable track:

```python
LifecycleTrack(
    stable_track_id=1,
    source_track_id=10,
    state="active",
    detection=Detection(class_name="person", confidence=0.91, bbox=(100, 100, 260, 520), track_id=10),
    last_seen_age_ms=0,
)
```

- [ ] **Step 2: Run failing tests**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_candidate_quality.py -q
```

Expected: fail because the gate does not exist or lifecycle does not expose
current tracks.

- [ ] **Step 3: Expose lifecycle snapshot**

In `backend/src/argus/vision/track_lifecycle.py`, add a read-only method:

```python
def visible_tracks(self) -> list[LifecycleTrack]:
    return [
        track
        for track in self._tracks.values()
        if track.state in {"active", "coasting"}
    ]
```

Use the existing internal storage names from the implemented lifecycle module.
Return copies or immutable dataclasses if needed to prevent mutation.

- [ ] **Step 4: Implement candidate quality gate**

Create `backend/src/argus/vision/candidate_quality.py` with:

- `CandidateQualityConfig`
- `CandidateDecision`
- `CandidateQualityGate`

Default thresholds:

```python
new_track_min_confidence = {
    "person": 0.45,
    "car": 0.35,
    "truck": 0.35,
    "bus": 0.35,
    "forklift": 0.35,
}
continuation_min_confidence = 0.10
near_track_iou_threshold = 0.10
near_track_center_distance_ratio = 0.65
fragment_iou_or_ios_threshold = 0.55
```

Gate behavior:

- pass high-confidence new candidates
- pass low-confidence candidates near an existing same-class active/coasting
  track so the tracker can associate them
- reject low-confidence candidates far from existing tracks
- reject same-class fragments mostly contained in an existing stable track
- attach a reason string: `new_track_high_confidence`,
  `existing_track_continuation`, `new_track_low_confidence`,
  `duplicate_fragment`

- [ ] **Step 5: Wire into engine**

In `InferenceEngine.__init__`, create the gate from the resolved profile.

In `run_once`, after detection regions and before `_tracker.update`:

```python
quality_filtered, candidate_decisions = self._candidate_quality_gate.filter_detections(
    region_filtered,
    existing_tracks=self._track_lifecycle.visible_tracks(),
    frame_shape=processed.shape,
)
tracked = self._tracker.update(quality_filtered, frame=processed)
```

Add engine tests:

- pillow-like low-confidence new `person` is not published
- low-confidence same-class detection near an active track is still sent to the
  tracker
- split-body fragment near an existing person does not create a second visible
  track

- [ ] **Step 6: Verify candidate tests**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_candidate_quality.py backend/tests/vision/test_track_lifecycle.py backend/tests/inference/test_engine.py -q
```

Expected: pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/src/argus/vision/candidate_quality.py backend/src/argus/vision/track_lifecycle.py backend/src/argus/inference/engine.py backend/tests/vision/test_candidate_quality.py backend/tests/inference/test_engine.py
git commit -m "feat(scene): add candidate quality gate"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 5: Explicit Speed Metrics

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/inference/test_engine.py`
- Modify: `backend/tests/services/test_camera_service.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Write failing speed tests**

Add tests:

- worker config rejects or refuses speed-enabled profile without homography
- speed-disabled profile with homography publishes `speed_kph=None`
- speed-enabled profile with homography publishes non-null `speed_kph` after two
  tracked points
- history and count-event persistence still accept nullable speed

- [ ] **Step 2: Run failing tests**

```bash
python3 -m uv run --project backend pytest backend/tests/inference/test_engine.py backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py -q
```

Expected: new tests fail because `_apply_speed` runs whenever homography exists.

- [ ] **Step 3: Make speed conditional**

Add `motion_metrics` to `EngineConfig` via the worker profile. In
`InferenceEngine.run_once`, call `_apply_speed` only when:

```python
self._resolved_profile.motion_metrics.speed_enabled and self.homography is not None
```

If disabled, record the stage as skipped or run a no-op path that leaves
`speed_kph` unchanged.

Ensure `CameraService` validates speed-enabled profiles against existing or
incoming homography during create and update.

- [ ] **Step 4: Verify speed tests**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_homography.py backend/tests/inference/test_engine.py backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py -q
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add backend/src/argus/inference/engine.py backend/src/argus/services/app.py backend/tests/inference/test_engine.py backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py
git commit -m "feat(scene): make speed metrics explicit"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 6: Metrics And Observability

**Files:**
- Modify: `backend/src/argus/core/metrics.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write failing metrics tests**

Add engine tests or metrics unit coverage asserting these counters increment:

- candidate rejected with reason `new_track_low_confidence`
- candidate rejected with reason `duplicate_fragment`
- detection region filtered with mode `exclude`
- speed disabled counter or skipped stage is observable

- [ ] **Step 2: Add metrics**

In `backend/src/argus/core/metrics.py`, define counters:

```python
CANDIDATE_REJECTED_TOTAL = Counter(...)
CANDIDATE_PASSED_TOTAL = Counter(...)
DETECTION_REGION_FILTERED_TOTAL = Counter(...)
MOTION_SPEED_SAMPLES_TOTAL = Counter(...)
MOTION_SPEED_DISABLED_TOTAL = Counter(...)
```

Use labels with bounded cardinality:

- `camera_id`
- `class_name`
- `reason`
- `mode`

Do not label with arbitrary region IDs if region names are user-entered and
could explode cardinality. Log region IDs at debug level instead.

- [ ] **Step 3: Wire metrics**

In the engine:

- record candidate decisions after candidate gate filtering
- record region decisions after region filtering
- record speed samples only when non-null speed is computed
- record speed disabled once per frame or use a skipped stage metric if a counter
  per frame is too noisy

- [ ] **Step 4: Verify metrics tests**

```bash
python3 -m uv run --project backend pytest backend/tests/inference/test_engine.py -q
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add backend/src/argus/core/metrics.py backend/src/argus/inference/engine.py backend/tests/inference/test_engine.py
git commit -m "feat(scene): add candidate quality metrics"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 7: Frontend API Types

**Files:**
- Regenerate: `frontend/src/lib/api.generated.ts`
- Modify: frontend fixtures/tests as needed

- [ ] **Step 1: Regenerate API types**

```bash
corepack pnpm --dir frontend generate:api
```

Expected: generated types include `SceneVisionProfile`, `MotionMetricsSettings`,
and `DetectionRegion`.

- [ ] **Step 2: Run generated-type smoke tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx
```

Expected: fail only where camera fixtures need new nullable/optional fields.

- [ ] **Step 3: Update fixtures**

Update frontend tests to include or tolerate:

```ts
vision_profile: {
  compute_tier: "edge_standard",
  accuracy_mode: "balanced",
  scene_difficulty: "cluttered",
  object_domain: "mixed",
  motion_metrics: { speed_enabled: false },
  candidate_quality: {},
  tracker_profile: {},
  verifier_profile: {},
},
detection_regions: [],
homography: null,
```

- [ ] **Step 4: Verify frontend smoke tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/lib/api.generated.ts frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/pages/Cameras.test.tsx
git commit -m "chore(frontend): refresh scene vision API types"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 8: Camera Wizard Profile And Region Authoring

**Files:**
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Modify: `frontend/src/components/cameras/BoundaryAuthoringCanvas.tsx` only if needed

- [ ] **Step 1: Write failing wizard tests**

Add tests:

- default create payload sends balanced profile, speed disabled, and no
  homography when calibration is untouched
- enabling speed requires four source points, four destination points, and
  reference distance
- selecting `Maximum Accuracy` and `Advanced Edge` submits
  `compute_tier: "edge_advanced_jetson"`
- adding an include detection region submits `detection_regions[0].mode="include"`
- adding an exclusion detection region submits `detection_regions[0].mode="exclude"`
- event boundaries still submit to `zones`, not `detection_regions`

- [ ] **Step 2: Run failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: fail because the UI does not expose profile/speed/detection regions.

- [ ] **Step 3: Add wizard state**

Extend `CameraWizardData` with:

```ts
visionProfile: {
  computeTier: "cpu_low" | "edge_standard" | "edge_advanced_jetson" | "central_gpu";
  accuracyMode: "fast" | "balanced" | "maximum_accuracy" | "open_vocabulary";
  sceneDifficulty: "open" | "cluttered" | "occluded" | "crowded" | "traffic" | "custom";
  objectDomain: "people" | "vehicles" | "mixed" | "open_vocab";
  speedEnabled: boolean;
};
detectionRegions: DetectionRegionDraft[];
```

Use current camera values when editing.

- [ ] **Step 4: Add profile controls**

In the setup flow, add a compact section before calibration:

- profile segmented control: Fast, Balanced, Maximum Accuracy, Open Vocabulary
- compute target select: Low CPU, Standard Edge, Advanced Edge, Central GPU
- speed metrics toggle

Use restrained operational copy. Do not add a landing-page style panel.

- [ ] **Step 5: Split detection regions from event boundaries**

In Calibration:

- keep existing `Event boundaries` section for line crossings and zone enter/exit
- add `Detection regions` section for include/exclusion polygons
- reuse `BoundaryAuthoringCanvas` in polygon mode
- add buttons:
  - `Add include region`
  - `Add exclusion region`

Serialize detection regions separately from `zones`.

- [ ] **Step 6: Make calibration conditional**

Validation should require homography only when `visionProfile.speedEnabled` is
true. If speed is disabled and homography is incomplete, submit `homography:
null`.

- [ ] **Step 7: Verify wizard tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: pass.

- [ ] **Step 8: Commit and push**

```bash
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/components/cameras/BoundaryAuthoringCanvas.tsx
git commit -m "feat(scene): add vision profile setup controls"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 9: Scene List Visibility

**Files:**
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Cameras.test.tsx`

- [ ] **Step 1: Add tests**

Add tests asserting the camera list shows the selected accuracy mode and speed
state without overwhelming the table.

- [ ] **Step 2: Implement list display**

Show concise text such as:

- `Balanced`
- `Max accuracy`
- `Advanced edge`
- `Speed off`
- `Speed on`

Keep current table density.

- [ ] **Step 3: Verify tests**

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Cameras.test.tsx
```

Expected: pass.

- [ ] **Step 4: Commit and push**

```bash
git add frontend/src/pages/Cameras.tsx frontend/src/pages/Cameras.test.tsx
git commit -m "feat(scene): show vision profile in cameras"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 10: Full Verification

**Files:**
- Modify only if verification finds issues.

- [ ] **Step 1: Backend verification**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_profiles.py backend/tests/vision/test_detection_regions.py backend/tests/vision/test_candidate_quality.py backend/tests/vision/test_track_lifecycle.py backend/tests/vision/test_homography.py backend/tests/vision/test_zones.py backend/tests/services/test_camera_worker_config.py backend/tests/services/test_camera_service.py backend/tests/inference/test_engine.py -q
```

Expected: pass.

- [ ] **Step 2: Frontend verification**

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx src/pages/Live.test.tsx src/lib/live-signal-stability.test.ts
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Expected: pass.

- [ ] **Step 3: OpenAPI consistency**

```bash
corepack pnpm --dir frontend generate:api
git diff --exit-code frontend/src/lib/api.generated.ts
```

Expected: no generated API drift.

- [ ] **Step 4: Commit fixes if needed**

If verification required changes:

```bash
git add <changed-files>
git commit -m "fix(scene): complete vision profile verification"
git push origin codex/omnisight-ui-spec-implementation
```

If no fixes were needed, do not create an empty commit.

## Acceptance Criteria

- Cameras can be created without homography when speed is disabled.
- Speed is computed only when `motion_metrics.speed_enabled=true`.
- Existing homography and event-zone tests still pass.
- Detection include/exclusion regions gate tracker input.
- Existing event zones continue to produce line and zone events.
- Low-confidence new `person` candidates do not immediately become visible
  tracks.
- Low-confidence candidates near an existing active/coasting track can still
  update the tracker.
- Duplicate body fragments near an existing person are suppressed or held
  tentative.
- Jetson Orin Nano Super is represented as `edge_advanced_jetson`.
- No WebGL is introduced.
- No unrelated scratch files are staged.
