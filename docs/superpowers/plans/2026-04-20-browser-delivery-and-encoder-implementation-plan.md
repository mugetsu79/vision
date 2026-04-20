# Browser Delivery And Encoder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make browser-delivery presets such as `720p10` drive the actual published live stream, then add host-aware encoder selection without changing the browser-side contract.

**Architecture:** First resolve `browser_delivery` into explicit worker stream settings and apply those settings in the MediaMTX publisher pipeline for resizing and FPS throttling. After user validation, add encoder capability selection so the same publish path can use NVENC, VideoToolbox, or `libx264` depending on the machine.

**Tech Stack:** Python 3.12, FastAPI/Pydantic contracts, OpenCV, FFmpeg, MediaMTX, Pytest

---

## Phase Gate

- **Step 1 is a shippable checkpoint.**
- **Do not start Step 2 until the user validates Step 1 on the real camera.**

### Task 1: Resolve Browser Delivery In Worker Config

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Write the failing worker-config test**

Add a test that creates a camera with `browser_delivery.default_profile = "720p10"` and expects worker config to include resolved stream settings such as:

```python
assert response.stream.model_dump() == {
    "profile_id": "720p10",
    "kind": "transcode",
    "width": 1280,
    "height": 720,
    "fps": 10,
}
```

- [ ] **Step 2: Run the worker-config test to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_camera_worker_config.py -q
```

Expected: FAIL because `WorkerStreamSettings` is currently empty.

- [ ] **Step 3: Implement the minimal contract and mapping**

Update `WorkerStreamSettings` and `_camera_to_worker_config(...)` so the selected browser delivery profile is resolved into explicit stream settings.

- [ ] **Step 4: Re-run the worker-config test**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_camera_worker_config.py -q
```

Expected: PASS

### Task 2: Apply Resolution And FPS Policy In The Publisher

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/streaming/mediamtx.py`
- Test: `backend/tests/streaming/test_mediamtx.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing publisher behavior tests**

Add tests that show:
- a `720p10` stream policy results in a 1280x720 published frame shape
- frame publishing is cadence-limited to the configured browser FPS
- `native` keeps the original processed frame size

- [ ] **Step 2: Run the targeted tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/streaming/test_mediamtx.py tests/inference/test_engine.py -q
```

Expected: FAIL because the publisher currently uses worker frame shape and worker FPS only.

- [ ] **Step 3: Implement the minimal publish-policy handling**

Add stream policy application so:
- outgoing frames are resized for transcode profiles
- publish cadence follows `stream.fps`
- `native` behaves as pass-through for size/rate at the processed frame level

- [ ] **Step 4: Re-run the targeted tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/streaming/test_mediamtx.py tests/inference/test_engine.py -q
```

Expected: PASS

- [ ] **Step 5: Run the full Step 1 verification set**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_camera_worker_config.py tests/streaming/test_mediamtx.py tests/inference/test_engine.py tests/inference/test_e2e_worker.py -q
```

Expected: PASS

- [ ] **Step 6: Commit Step 1 and stop for user confirmation**

```bash
git add backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/src/argus/inference/engine.py backend/src/argus/streaming/mediamtx.py backend/tests/services/test_camera_worker_config.py backend/tests/streaming/test_mediamtx.py backend/tests/inference/test_engine.py backend/tests/inference/test_e2e_worker.py
git commit -m "feat: make browser delivery presets real"
```

**Stop here. Ask the user to validate `720p10` on the iMac before proceeding.**

### Task 3: Add Encoder Capability Selection

**Files:**
- Modify: `backend/src/argus/streaming/mediamtx.py`
- Modify: `backend/src/argus/core/config.py`
- Test: `backend/tests/streaming/test_mediamtx.py`
- Test: `backend/tests/core/test_config.py`

- [ ] **Step 1: Write the failing encoder-selection tests**

Add tests that assert:
- Linux + NVIDIA capability => `h264_nvenc`
- macOS capability => `h264_videotoolbox`
- unsupported hosts => `libx264`

- [ ] **Step 2: Run the targeted tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/streaming/test_mediamtx.py tests/core/test_config.py -q
```

Expected: FAIL because encoder choice is currently hardcoded.

- [ ] **Step 3: Implement encoder capability selection**

Add a small encoder-selection layer that:
- respects an explicit override if configured
- otherwise chooses the best available encoder by host/runtime capability
- keeps the publish contract unchanged

- [ ] **Step 4: Re-run the targeted tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/streaming/test_mediamtx.py tests/core/test_config.py -q
```

Expected: PASS

### Task 4: Final Verification And Delivery

**Files:**
- Modify if needed: `docs/imac-master-orin-lab-test-guide.md`

- [ ] **Step 1: Run the focused backend verification suite**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_camera_worker_config.py tests/streaming/test_mediamtx.py tests/inference/test_engine.py tests/inference/test_e2e_worker.py tests/core/test_config.py -q
```

Expected: PASS

- [ ] **Step 2: Run a diff sanity check**

Run:

```bash
cd /Users/yann.moren/vision
git diff --check
```

Expected: no output

- [ ] **Step 3: Commit Step 2**

```bash
git add backend/src/argus/streaming/mediamtx.py backend/src/argus/core/config.py backend/tests/streaming/test_mediamtx.py backend/tests/core/test_config.py docs/imac-master-orin-lab-test-guide.md
git commit -m "feat: add stream encoder capability selection"
```
