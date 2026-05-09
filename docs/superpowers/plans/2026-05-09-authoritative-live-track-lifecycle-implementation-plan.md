# Authoritative Live Track Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop live telemetry and annotated stream overlays from flapping between visible and invisible during short detector/tracker misses.

**Architecture:** Add a backend track lifecycle manager after tracker association. Use its active/coasting stable tracks for live telemetry and annotated overlays, while keeping raw associated tracks for rules, count events, privacy, and persistence.

**Tech Stack:** Python 3.12, Pydantic, OpenCV, Ultralytics BoT-SORT/ByteTrack adapter, FastAPI OpenAPI generation, TypeScript, Vitest.

**Spec source:** `/Users/yann.moren/vision/docs/superpowers/specs/2026-05-09-authoritative-live-track-lifecycle-design.md`

---

## Execution Protocol

Execute one task at a time, commit after each completed task, and push to origin
for testing. Do not stage unrelated untracked scratch files.

Keep WebGL off. Do not reopen Jetson/TensorRT/RTSP work.

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `backend/src/argus/vision/track_lifecycle.py` | Create | Stable track lifecycle, coasting, duplicate suppression, re-association |
| `backend/tests/vision/test_track_lifecycle.py` | Create | Pure lifecycle unit tests |
| `backend/src/argus/inference/publisher.py` | Modify | Add optional lifecycle fields to telemetry tracks |
| `backend/src/argus/inference/engine.py` | Modify | Use stable tracks for live telemetry and annotations |
| `backend/tests/inference/test_engine.py` | Modify | Engine coverage for stable counts, coasting metadata, raw rules |
| `frontend/src/lib/api.generated.ts` | Regenerate | Include lifecycle fields from OpenAPI |
| `frontend/src/lib/live-signal-stability.ts` | Modify | Map backend active/coasting state into display state |
| `frontend/src/lib/live-signal-stability.test.ts` | Modify | Cover backend lifecycle fields |
| `frontend/src/components/live/TelemetryCanvas.tsx` | Modify | Avoid duplicate overlay on backend-annotated streams |
| `frontend/src/components/live/TelemetryCanvas.test.tsx` | Modify | Cover no duplicate annotated overlay behavior |
| `frontend/src/pages/Live.tsx` | Modify | Count stabilized visible total as visible now |
| `frontend/src/pages/Live.test.tsx` | Modify | Integration test for no `1 -> 0 -> 1` flicker |

---

## Task 1: Backend Track Lifecycle Model

**Files:**
- Create: `backend/src/argus/vision/track_lifecycle.py`
- Create: `backend/tests/vision/test_track_lifecycle.py`

- [ ] **Step 1: Write failing lifecycle tests**

Create tests for these behaviors:

- `test_missing_track_coasts_until_ttl`
- `test_coasting_track_expires_after_ttl`
- `test_tracker_id_switch_reuses_stable_id_by_overlap`
- `test_duplicate_same_class_track_is_suppressed`
- `test_single_low_confidence_candidate_stays_tentative`

Use `Detection` instances from `argus.vision.types` and timestamps spaced by
milliseconds. The expected API:

```python
manager = TrackLifecycleManager(
    TrackLifecycleConfig(coast_ttl_ms=2500, tentative_hits=2)
)
visible = manager.update(
    detections=[Detection(class_name="person", confidence=0.91, bbox=(10, 10, 60, 120), track_id=4)],
    ts=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
    frame_shape=(720, 1280, 3),
)
```

Expected track fields:

- `stable_track_id`
- `source_track_id`
- `state`
- `last_seen_age_ms`
- `detection`

- [ ] **Step 2: Run failing tests**

```bash
python3 -m uv run pytest backend/tests/vision/test_track_lifecycle.py -q
```

Expected: fail because the module does not exist.

- [ ] **Step 3: Implement lifecycle manager**

Implement:

- `TrackLifecycleState = Literal["tentative", "active", "coasting", "lost"]`
- `TrackLifecycleConfig`
- `LifecycleTrack`
- `TrackLifecycleManager.update(...)`
- duplicate suppression helpers
- IoU and center-distance helpers
- damped bbox prediction with frame clamping

Keep the module pure: no OpenCV, no network, no engine imports.

- [ ] **Step 4: Verify lifecycle tests**

```bash
python3 -m uv run pytest backend/tests/vision/test_track_lifecycle.py -q
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add backend/src/argus/vision/track_lifecycle.py backend/tests/vision/test_track_lifecycle.py
git commit -m "feat(live): add authoritative track lifecycle"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 2: Telemetry Contract For Stable Tracks

**Files:**
- Modify: `backend/src/argus/inference/publisher.py`
- Regenerate: `frontend/src/lib/api.generated.ts`
- Modify: frontend tests that construct `TelemetryTrack` only if required by
  stricter generated types

- [ ] **Step 1: Add backend telemetry fields**

Update `TelemetryTrack` with defaulted fields:

```python
stable_track_id: int | None = None
track_state: Literal["active", "coasting"] = "active"
last_seen_age_ms: int = 0
source_track_id: int | None = None
```

Import `Literal` from `typing`.

- [ ] **Step 2: Generate frontend API types**

```bash
corepack pnpm --dir frontend generate:api
```

Expected: `frontend/src/lib/api.generated.ts` includes optional/defaulted
lifecycle fields.

- [ ] **Step 3: Run focused contract tests**

```bash
python3 -m uv run pytest backend/tests/inference/test_publisher.py backend/tests/api/test_prompt5_routes.py -q
corepack pnpm --dir frontend exec vitest run src/lib/live-signal-stability.test.ts
```

Expected: pass or only require fixture updates for the new defaulted fields.

- [ ] **Step 4: Commit and push**

```bash
git add backend/src/argus/inference/publisher.py frontend/src/lib/api.generated.ts
git commit -m "feat(live): expose telemetry track lifecycle state"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 3: Engine Integration And Stable Annotated Overlay

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write failing engine tests**

Add tests for:

- a person frame followed by an empty frame still publishes count `{"person": 1}`
- the second frame's track has `track_state == "coasting"`
- the tracking store records only raw active detections
- rule evaluation receives only raw active detections
- lifecycle resets when `CameraCommand.tracker_type` changes

Use a sequence detector and a pass-through fake tracker that preserves or assigns
source `track_id`.

- [ ] **Step 2: Run failing engine tests**

```bash
python3 -m uv run pytest backend/tests/inference/test_engine.py -q
```

Expected: new tests fail because the engine still publishes raw latest-frame
tracks/counts.

- [ ] **Step 3: Wire lifecycle into `InferenceEngine`**

Implementation points:

- instantiate `TrackLifecycleManager` in the engine constructor
- reset it when tracker type changes
- after `_apply_zones(tracked)`, compute `stable_tracks = self._track_lifecycle.update(...)`
- keep `tracked` for rules, count events, ANPR, tracking persistence, and privacy
- use `stable_tracks` for `_build_stream_frame(...)`
- use `stable_tracks` for `TelemetryFrame.counts`
- map lifecycle metadata into `TelemetryTrack`

- [ ] **Step 4: Draw lifecycle-aware annotations**

Update annotation drawing so:

- active boxes are solid
- coasting boxes are dashed/subdued
- labels do not include tracker IDs
- colors match the class family palette as closely as OpenCV BGR allows

- [ ] **Step 5: Verify backend tests**

```bash
python3 -m uv run pytest backend/tests/vision/test_track_lifecycle.py backend/tests/inference/test_engine.py backend/tests/vision/test_tracker.py -q
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/inference/engine.py backend/tests/inference/test_engine.py
git commit -m "feat(live): publish stable lifecycle telemetry"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 4: Frontend Reconciliation With Backend Lifecycle

**Files:**
- Modify: `frontend/src/lib/live-signal-stability.ts`
- Modify: `frontend/src/lib/live-signal-stability.test.ts`
- Modify: `frontend/src/components/live/TelemetryCanvas.tsx`
- Modify: `frontend/src/components/live/TelemetryCanvas.test.tsx`
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Add coverage for:

- backend `track_state: "coasting"` maps to held display state
- `annotated-whip` selects no frontend overlay tracks once backend lifecycle
  annotations are authoritative
- `visible now` uses stabilized total, so active/coasting total of `1` displays
  as `1 visible now`

- [ ] **Step 2: Run failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/live-signal-stability.test.ts src/components/live/TelemetryCanvas.test.tsx src/pages/Live.test.tsx
```

Expected: new tests fail.

- [ ] **Step 3: Implement frontend mapping**

Update `updateSignalTracks` to read backend lifecycle state:

- `track_state === "active"` -> local `state: "live"`
- `track_state === "coasting"` -> local `state: "held"`
- missing frontend frame fallback still uses the local hold window

Update `selectDrawableSignalTracks`:

- `annotated-whip` returns `[]`
- unannotated modes return stable tracks for canvas drawing

Update visible copy:

- display total active + coasting count as visible continuity
- keep existing terrain row state labels as the place where held/coasting
  uncertainty is exposed

- [ ] **Step 4: Verify frontend focused tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/live-signal-stability.test.ts src/components/live/TelemetryCanvas.test.tsx src/pages/Live.test.tsx src/hooks/use-stable-signal-frame.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/lib/live-signal-stability.ts frontend/src/lib/live-signal-stability.test.ts frontend/src/components/live/TelemetryCanvas.tsx frontend/src/components/live/TelemetryCanvas.test.tsx frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx
git commit -m "fix(live): reconcile UI with backend lifecycle tracks"
git push origin codex/omnisight-ui-spec-implementation
```

---

## Task 5: Verification And Live Smoke

**Files:**
- Modify only if verification exposes a focused bug.

- [ ] **Step 1: Run backend verification**

```bash
python3 -m uv run pytest backend/tests/vision/test_track_lifecycle.py backend/tests/vision/test_tracker.py backend/tests/inference/test_engine.py backend/tests/inference/test_publisher.py -q
```

Expected: pass.

- [ ] **Step 2: Run frontend verification**

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
```

Expected: pass. Existing React `act(...)` warnings in `VideoStream.test.tsx`
are acceptable if no assertions fail.

- [ ] **Step 3: Optional browser smoke**

If local services are running:

```bash
curl -I http://127.0.0.1:3000
curl -s http://127.0.0.1:8000/healthz
```

Open `/live` and verify:

- annotated stream has only one box for the user
- count does not flash to `0 visible now` during slow movement
- no duplicate frontend overlay appears on `annotated-whip`

- [ ] **Step 4: Commit and push any verification fix**

Only if files changed:

```bash
git add <focused files>
git commit -m "fix(live): harden lifecycle verification"
git push origin codex/omnisight-ui-spec-implementation
```

## Final Acceptance

The work is complete when the user can run the same iMac live feed and observe:

- one stable person identity while walking slowly
- no second duplicate person box for the same body
- no immediate `1 visible now -> 0 visible now -> 1 visible now` flicker
- video and telemetry recover after route navigation without duplicate overlays
