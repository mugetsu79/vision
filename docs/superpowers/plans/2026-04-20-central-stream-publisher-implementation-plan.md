# Central Stream Publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish real processed frames from the worker into MediaMTX for `annotated` and `preview` streams, while making x86 RTSP ingest more reliable.

**Architecture:** Add a managed `ffmpeg`-backed publisher layer to `MediaMTXClient`, keyed by camera/path, and keep the existing WHEP/HLS/MJPEG browser path unchanged. Update x86 camera capture to prefer TCP transport so source ingest is stable enough to validate the new stream publisher on the iMac lab setup.

**Tech Stack:** Python 3.12, `asyncio`, `subprocess`, OpenCV, FFmpeg, MediaMTX, Pytest

---

### Task 1: Lock In Failing Stream Publisher Tests

**Files:**
- Modify: `backend/tests/streaming/test_mediamtx.py`

- [ ] **Step 1: Write the failing tests**

Add tests that:
- assert `push_frame()` starts a publisher for non-passthrough registrations
- assert a second frame reuses the same publisher
- assert a registration path change replaces the publisher
- assert `close()` shuts publishers down

- [ ] **Step 2: Run the targeted test file to verify the new tests fail**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/streaming/test_mediamtx.py -q`

Expected: FAIL because `push_frame()` is still a metadata stub and no publisher lifecycle exists.

- [ ] **Step 3: Commit the red test state only if helpful locally**

Skip commit if staying in a tight local TDD loop.

### Task 2: Implement MediaMTX Publisher Lifecycle

**Files:**
- Modify: `backend/src/argus/streaming/mediamtx.py`
- Test: `backend/tests/streaming/test_mediamtx.py`

- [ ] **Step 1: Add minimal publisher abstractions**

Introduce a small internal publisher wrapper that can:
- start with registration details
- accept frames
- report liveness
- close cleanly

- [ ] **Step 2: Implement minimal `push_frame()` behavior**

Make `push_frame()`:
- no-op for passthrough registrations
- create a publisher lazily for `annotated` / `preview`
- reuse the existing publisher while the path is unchanged
- replace the publisher when the path changes or the subprocess is dead

- [ ] **Step 3: Use MediaMTX publish JWTs**

Build authenticated publish URLs per path so MediaMTX accepts the worker as a publisher.

- [ ] **Step 4: Run the targeted test file**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/streaming/test_mediamtx.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/streaming/mediamtx.py backend/tests/streaming/test_mediamtx.py
git commit -m "feat: publish central frames through mediamtx"
```

### Task 3: Harden x86 RTSP Capture For Lab Validation

**Files:**
- Modify: `backend/src/argus/vision/camera.py`
- Modify: `backend/tests/vision/test_camera.py`

- [ ] **Step 1: Write the failing test**

Add a test that shows x86 RTSP capture uses a TCP-transport form instead of the plain RTSP URL.

- [ ] **Step 2: Run the camera tests to verify failure**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/vision/test_camera.py -q`

Expected: FAIL because x86 capture currently passes the raw RTSP URL straight to `cv2.CAP_FFMPEG`.

- [ ] **Step 3: Implement the minimal capture change**

Update x86 capture resolution so RTSP inputs prefer TCP transport while keeping the existing FFMPEG backend.

- [ ] **Step 4: Re-run the camera tests**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/vision/test_camera.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/vision/camera.py backend/tests/vision/test_camera.py
git commit -m "fix: prefer tcp for x86 rtsp capture"
```

### Task 4: Verify Engine Integration

**Files:**
- Modify if needed: `backend/tests/inference/test_engine.py`
- Modify if needed: `backend/tests/inference/test_e2e_worker.py`

- [ ] **Step 1: Extend tests only if current coverage misses the new publisher behavior**

Keep the change minimal: only add assertions if the engine contract changed in a visible way.

- [ ] **Step 2: Run focused backend verification**

Run:
- `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/streaming/test_mediamtx.py tests/vision/test_camera.py tests/inference/test_engine.py tests/inference/test_e2e_worker.py -q`

Expected: PASS

- [ ] **Step 3: Run a formatting / diff sanity check**

Run:
- `cd /Users/yann.moren/vision && git diff --check`

Expected: no output

- [ ] **Step 4: Commit the integrated result**

```bash
git add backend/src/argus/streaming/mediamtx.py backend/src/argus/vision/camera.py backend/tests/streaming/test_mediamtx.py backend/tests/vision/test_camera.py backend/tests/inference/test_engine.py backend/tests/inference/test_e2e_worker.py docs/superpowers/specs/2026-04-20-central-stream-publisher-design.md docs/superpowers/plans/2026-04-20-central-stream-publisher-implementation-plan.md
git commit -m "feat: stream central video through mediamtx"
```
