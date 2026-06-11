# Jetson Live Overlay Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize Jetson Live overlays and processed annotations across low-resolution renditions and make vision modes affect tracking behavior.

**Architecture:** Add worker-reported telemetry source geometry, use it in the Live overlay, add short coasting visual hysteresis, remove the default center trail dot, and wire resolved vision-profile tracker/lifecycle settings into the worker. Keep the changes local to the Live overlay and inference worker paths.

**Tech Stack:** FastAPI/Pydantic contracts, Python inference engine, Vitest/React Testing Library, pytest.

---

## File Structure

- Modify `backend/src/argus/inference/publisher.py`: add optional telemetry `source_size`.
- Modify `backend/src/argus/inference/engine.py`: populate `source_size`, add annotation coasting grace, and build tracker/lifecycle from resolved profile.
- Modify `backend/src/argus/vision/track_lifecycle.py`: expose the default coast constant for profile mapping.
- Modify `backend/tests/inference/test_engine.py`: backend regression coverage.
- Modify `frontend/src/lib/live-signal-stability.ts`: short coasting grace.
- Modify `frontend/src/lib/live-signal-stability.test.ts`: frontend stability regression.
- Modify `frontend/src/components/live/TelemetryCanvas.tsx`: use frame source size and remove center endpoint dot.
- Modify `frontend/src/components/live/TelemetryCanvas.test.tsx`: geometry and drawing regression.
- Modify `frontend/src/pages/Live.tsx`: pass frame-aware source size into media geometry and canvas.

## Task 1: Frontend Overlay Stability And Geometry

**Files:**
- Modify: `frontend/src/lib/live-signal-stability.ts`
- Modify: `frontend/src/lib/live-signal-stability.test.ts`
- Modify: `frontend/src/components/live/TelemetryCanvas.tsx`
- Modify: `frontend/src/components/live/TelemetryCanvas.test.tsx`
- Modify: `frontend/src/pages/Live.tsx`

- [x] **Step 1: Add failing coasting grace test**

Add a test in `frontend/src/lib/live-signal-stability.test.ts` that sends a coasting person with `last_seen_age_ms: 300` and expects `state: "live"`, then sends one with `last_seen_age_ms: 900` and expects `state: "held"`.

- [x] **Step 2: Add failing source-size test**

Add a test in `frontend/src/components/live/TelemetryCanvas.test.tsx` that renders a frame with `source_size: { width: 1280, height: 720 }`, passes a conflicting `sourceSize={{ width: 2304, height: 1296 }}`, and expects the box projection to use the frame source size.

- [x] **Step 3: Add failing no-center-dot test**

In `TelemetryCanvas.test.tsx`, assert the overlay does not call `arc` for the track center endpoint during normal drawing.

- [x] **Step 4: Verify frontend tests fail**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/lib/live-signal-stability.test.ts src/components/live/TelemetryCanvas.test.tsx
```

Expected: the new tests fail before implementation.

- [x] **Step 5: Implement frontend stability and geometry**

Update `live-signal-stability.ts`:

- add `DEFAULT_SIGNAL_COAST_GRACE_MS`;
- treat coasting tracks with age below that grace as `live`;
- keep longer coasts as `held`.
- suppress browser-drawn boxes for both worker-rendered stream modes: `annotated-whip` and `filtered-preview`.

Update `TelemetryCanvas.tsx`:

- read optional `frame.source_size`;
- prefer frame source size over camera source size;
- remove the center endpoint `arc` draw from the default overlay.

Update `Live.tsx`:

- derive an effective overlay source size from the latest frame first and camera source capability second.

- [x] **Step 6: Verify frontend tests pass**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/lib/live-signal-stability.test.ts src/hooks/use-stable-signal-frame.test.tsx src/components/live/TelemetryCanvas.test.tsx
```

Expected: all selected frontend tests pass.

## Task 2: Backend Telemetry Geometry And Mode Wiring

**Files:**
- Modify: `backend/src/argus/inference/publisher.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/vision/track_lifecycle.py`
- Modify: `backend/tests/inference/test_engine.py`
- Modify: `backend/tests/vision/test_profiles.py` if profile expectations need explicit assertions.

- [x] **Step 1: Add failing telemetry source-size test**

Add a test in `backend/tests/inference/test_engine.py` that runs `InferenceEngine.run_once()` with a known `720x1280` frame and asserts the returned `TelemetryFrame.source_size == {"width": 1280, "height": 720}`.

- [x] **Step 2: Add failing mode-wiring test**

Add a test in `backend/tests/inference/test_engine.py` that constructs an engine with `vision_profile={"accuracy_mode": "maximum_accuracy", "compute_tier": "edge_advanced_jetson"}` and asserts the lifecycle config uses `tentative_hits == 3` and a non-trivial coast TTL derived from profile memory/FPS.

- [x] **Step 3: Verify backend tests fail**

Run:

```bash
cd /Users/yann.moren/vision
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "source_size or vision_profile" -q
```

Expected: the new tests fail before implementation.

- [x] **Step 4: Implement backend telemetry geometry**

Update `TelemetryFrame` in `publisher.py` with:

```python
source_size: dict[str, int] | None = None
```

Populate it in `InferenceEngine.run_once()` from the processed frame shape used for tracking:

```python
source_size={"width": int(processed.shape[1]), "height": int(processed.shape[0])}
```

- [x] **Step 5: Implement mode wiring**

Update `InferenceEngine` so tracker and lifecycle construction use the resolved profile:

- maximum accuracy on advanced Jetson or central GPU uses a difficult tracker scene profile when compatible;
- lifecycle tentative hits comes from `resolved.tracker.new_track_min_hits`;
- lifecycle coast TTL comes from `resolved.candidate_quality.memory_frames`, scaled against the existing default TTL baseline with bounded defaults;
- runtime vision-profile changes rebuild tracker, candidate gate, lifecycle manager, and reset track state.

- [x] **Step 6: Add processed stream annotation grace**

In `engine.py`, keep coasting tracks with `last_seen_age_ms` below the frontend grace window visually active: solid box and class label. Longer coasts keep dashed held styling.

- [x] **Step 7: Verify backend tests pass**

Run:

```bash
cd /Users/yann.moren/vision
backend/.venv/bin/pytest backend/tests/inference/test_engine.py backend/tests/vision/test_profiles.py backend/tests/vision/test_track_lifecycle.py backend/tests/vision/test_tracker.py -q
```

Expected: all selected backend tests pass.

## Task 3: Integration Verification And Live Smoke

**Files:**
- No new code files unless Task 1 or Task 2 reveals a regression.

- [x] **Step 1: Run combined targeted tests**

Run:

```bash
cd /Users/yann.moren/vision
backend/.venv/bin/pytest backend/tests/inference/test_engine.py backend/tests/vision/test_profiles.py backend/tests/vision/test_track_lifecycle.py backend/tests/vision/test_tracker.py backend/tests/services/test_operations_service.py -q
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/lib/live-signal-stability.test.ts src/hooks/use-stable-signal-frame.test.tsx src/components/live/TelemetryCanvas.test.tsx
```

- [ ] **Step 2: Build/redeploy only after user approval**

Do not commit, push, or redeploy without explicit user approval.

- [ ] **Step 3: Live Jetson smoke after deployment**

After approval and deployment, verify:

- runtime report fresh;
- selected provider still `tensorrt_engine`;
- media pipeline still `jetson_gstreamer_native`;
- selected browser rendition can be `240p`;
- browser overlay aligns with the person at 240p;
- active/held label does not flap during a short stationary sample;
- worker processed FPS remains near pre-change baseline.
