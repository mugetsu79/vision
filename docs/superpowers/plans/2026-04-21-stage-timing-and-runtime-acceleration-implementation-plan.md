# Worker Stage Timing And Runtime Acceleration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add worker stage timing and a cross-platform execution-provider policy so we can explain inference CPU cost and choose the best available runtime per host.

**Architecture:** First instrument [InferenceEngine.run_once(...)](/Users/yann.moren/vision/backend/src/argus/inference/engine.py:293) with per-stage timing metrics and periodic summaries while keeping current telemetry contracts stable. Then introduce an explicit runtime-policy layer that resolves provider choice for detector and attribute sessions based on host capability, optional overrides, and supported provider matrices.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, OpenTelemetry/Prometheus metrics, ONNX Runtime, OpenCV, Pytest

---

## Phase Gate

- **Phase 1 is shippable on its own.**
- **Do not start Phase 2 until timing data is visible on at least one real worker run.**

### Task 1: Add Stage Timing Data Structures

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/core/metrics.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing timing aggregation test**

Add a focused engine test that exercises `run_once()` with fakes and expects stage timing output to include named stages such as `detect`, `attributes`, `publish_stream`, and `total`.

- [ ] **Step 2: Run the targeted test to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q -k timing
```

Expected: FAIL because no stage timing structure exists yet.

- [ ] **Step 3: Implement a minimal internal timing model**

Add a small helper in `engine.py` that can:

- start/stop named stage timers
- expose per-stage milliseconds
- compute total frame duration from the same timing source

- [ ] **Step 4: Re-run the timing test**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q -k timing
```

Expected: PASS

### Task 2: Expose Stage Timing Through Worker Metrics

**Files:**
- Modify: `backend/src/argus/core/metrics.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing metrics test**

Add a test that expects a per-stage histogram family such as `argus_inference_stage_duration_seconds` with labels:

- `camera_id`
- `stage`

- [ ] **Step 2: Run the targeted metrics test to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q -k stage_duration
```

Expected: FAIL because only total frame duration exists today.

- [ ] **Step 3: Implement per-stage histograms**

Keep [INFERENCE_FRAME_DURATION_SECONDS](/Users/yann.moren/vision/backend/src/argus/core/metrics.py:29) intact and add a new histogram for stage timings. Record each stage from `run_once()` after the stage completes.

- [ ] **Step 4: Re-run the targeted metrics test**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q -k stage_duration
```

Expected: PASS

### Task 3: Add Periodic Timing Summary Logs

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing logging test**

Add a test that drives several frames through the engine and expects one rolled-up timing summary log instead of one log per frame.

- [ ] **Step 2: Run the targeted logging test to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q -k timing_summary
```

Expected: FAIL because no timing summaries are logged today.

- [ ] **Step 3: Implement periodic summaries**

Add a lightweight rolling summary in `engine.py` that logs stage averages and a high-water marker every configurable interval, keeping frame-by-frame hot-path overhead low.

- [ ] **Step 4: Re-run the targeted logging test**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q -k timing_summary
```

Expected: PASS

- [ ] **Step 5: Commit Phase 1**

```bash
git add backend/src/argus/core/metrics.py backend/src/argus/inference/engine.py backend/tests/inference/test_engine.py
git commit -m "feat: add worker stage timing instrumentation"
```

### Task 4: Introduce Runtime Capability Modeling

**Files:**
- Modify: `backend/src/argus/vision/runtime.py`
- Modify: `backend/src/argus/core/config.py`
- Test: `backend/tests/vision/test_runtime.py`
- Test: `backend/tests/core/test_config.py`

- [ ] **Step 1: Write the failing runtime-policy tests**

Add tests that model these cases:

- Linux x86_64 + `TensorrtExecutionProvider` => NVIDIA path
- macOS arm64 + `CoreMLExecutionProvider` => Apple path
- Linux x86_64 Intel + `OpenVINOExecutionProvider` => Intel-optimized path
- Linux x86_64 AMD + `OpenVINOExecutionProvider` present but host vendor AMD => CPU fallback in first pass
- explicit override => override wins

- [ ] **Step 2: Run the runtime-policy tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_runtime.py tests/core/test_config.py -q
```

Expected: FAIL because runtime policy and overrides do not exist yet.

- [ ] **Step 3: Implement host and provider policy types**

Add:

- a host classification model
- an execution policy/result model
- config overrides for provider and optional thread/session tuning

Keep the API small and deterministic so tests can fully exercise it.

- [ ] **Step 4: Re-run the runtime-policy tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_runtime.py tests/core/test_config.py -q
```

Expected: PASS

### Task 5: Wire Provider Policy Into Detector And Attribute Sessions

**Files:**
- Modify: `backend/src/argus/vision/detector.py`
- Modify: `backend/src/argus/vision/attributes.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/vision/test_detector.py`
- Test: `backend/tests/vision/test_attributes.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing detector and attribute-session tests**

Add tests that assert both session constructors receive the resolved provider instead of selecting one internally.

- [ ] **Step 2: Run the targeted session tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_detector.py tests/vision/test_attributes.py tests/inference/test_engine.py -q -k provider
```

Expected: FAIL because provider selection is currently internal to each class.

- [ ] **Step 3: Implement explicit session wiring**

Refactor session creation so:

- `engine.py` resolves the execution policy once
- `detector.py` and `attributes.py` receive that resolved policy
- startup logs emit the final provider and whether an override was used

- [ ] **Step 4: Re-run the targeted session tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_detector.py tests/vision/test_attributes.py tests/inference/test_engine.py -q -k provider
```

Expected: PASS

### Task 6: Verify Cross-Platform Fallback Behavior

**Files:**
- Modify if needed: `backend/tests/vision/test_runtime.py`
- Modify if needed: `docs/operator-deployment-playbook.md`

- [ ] **Step 1: Add explicit fallback coverage**

Ensure tests cover:

- missing accelerated provider => CPU fallback
- invalid override => clean startup failure or validation error
- attribute classifier and detector staying aligned on the same resolved policy unless explicitly split later

- [ ] **Step 2: Run the focused runtime verification set**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_runtime.py tests/vision/test_detector.py tests/vision/test_attributes.py tests/inference/test_engine.py tests/core/test_config.py -q
```

Expected: PASS

- [ ] **Step 3: Run lint on touched files**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run ruff check src/argus/vision/runtime.py src/argus/vision/detector.py src/argus/vision/attributes.py src/argus/inference/engine.py src/argus/core/config.py tests/vision/test_runtime.py tests/vision/test_detector.py tests/vision/test_attributes.py tests/inference/test_engine.py tests/core/test_config.py
```

Expected: `All checks passed!`

- [ ] **Step 4: Commit Phase 2**

```bash
git add backend/src/argus/vision/runtime.py backend/src/argus/vision/detector.py backend/src/argus/vision/attributes.py backend/src/argus/inference/engine.py backend/src/argus/core/config.py backend/tests/vision/test_runtime.py backend/tests/vision/test_detector.py backend/tests/vision/test_attributes.py backend/tests/inference/test_engine.py backend/tests/core/test_config.py docs/operator-deployment-playbook.md
git commit -m "feat: add cross-platform inference runtime policy"
```

### Task 7: Final End-To-End Verification

**Files:**
- No new files required unless fixes are needed

- [ ] **Step 1: Run the combined backend verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py tests/vision/test_runtime.py tests/vision/test_detector.py tests/vision/test_attributes.py tests/core/test_config.py tests/streaming/test_mediamtx.py -q
```

Expected: PASS

- [ ] **Step 2: Run a diff sanity check**

Run:

```bash
cd /Users/yann.moren/vision
git diff --check
```

Expected: no output

- [ ] **Step 3: Record manual benchmark notes**

Capture stage timing summaries and resolved provider logs for at least:

- Apple Silicon macOS
- Linux x86_64 with NVIDIA
- Linux x86_64 Intel
- CPU fallback host

Record the results in the task summary or a follow-up doc before rollout.
