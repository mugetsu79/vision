# Live Wall Rendition And Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Live page source-aware, explain native stream availability correctly, remove false setup warnings for running scenes, and add operator-selectable live wall array layouts.

**Architecture:** Keep stream safety decisions server-authored, but make the Live page defensive against stale camera rows by filtering rendition options against `source_capability` and `unsupported_profiles`. Keep the current focus overlay and per-tile mosaic sizing available, while adding explicit array presets that control columns and page capacity. Readiness should distinguish missing foundational setup from optional scene intelligence policy.

**Tech Stack:** React, TypeScript, Tailwind, Vitest, Python service tests.

---

### Task 1: Source-Safe Live Renditions

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`
- Modify: `backend/tests/services/test_camera_service.py`
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`

- [x] **Step 1: Add failing backend tests**

Assert that `derive_browser_profiles(SourceCapability(width=1280, height=720, fps=20))` excludes `1080p*`, `900p*`, and `720p25`; unsupported profiles above source FPS use reason `source_fps_too_high`.

- [x] **Step 2: Add failing Live page test**

Render a camera whose stale `browser_delivery.profiles` still contains `1080p15`, `900p10`, and `720p25` while `source_capability` is `1280x720@20`. The Live rendition select must not contain those options.

- [x] **Step 3: Implement backend filtering**

In `derive_browser_profiles`, reject transcode profiles when target dimensions exceed source dimensions or when target FPS exceeds known source FPS.

- [x] **Step 4: Implement frontend defensive filtering**

In `getAvailableRenditionOptions`, filter by native availability, unsupported profile ids, source dimensions, and source FPS before building options.

### Task 2: Readiness Copy

**Files:**
- Modify: `frontend/src/lib/operational-health.ts`
- Modify: `frontend/src/lib/operational-health.test.ts`

- [x] **Step 1: Add failing readiness test**

Create a central camera with source capability, delivery profile, running worker, no zones/rules, and empty `active_classes`. The readiness label must not be `Needs setup`; it may still be `Needs attention` when delivery honestly reports native unavailable because privacy filtering requires a processed stream.

- [x] **Step 2: Implement readiness tightening**

Remove optional zones/rules and active-class filters from foundational missing setup checks. Keep source capability, processing mode, unknown privacy posture, and missing delivery profile as setup blockers.

### Task 3: Live Wall Layout Presets

**Files:**
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`

- [x] **Step 1: Add failing layout test**

Select four scenes, switch the Live wall layout to `2x2`, assert the grid uses two columns and four visible tiles; switch to `Single`, assert only one scene is visible and page navigation advances through selected scenes.

- [x] **Step 2: Implement layout preset state**

Add presets: `mosaic`, `single`, `two`, `2x2`, `3x4`, `4x4`. Each preset supplies a label, page capacity, grid classes, and whether per-tile spans are locked.

- [x] **Step 3: Render controls**

Add a compact select labeled `Live wall layout` next to the active scene count. Use previous/next controls for preset-sized pages.

- [x] **Step 4: Preserve existing focus behavior**

Keep the focus overlay button on every tile. Preserve compact/standard/large tile buttons only in `mosaic`, where per-tile spans still apply.

### Verification

- [x] Run `cd frontend && ./node_modules/.bin/vitest run src/pages/Live.test.tsx src/lib/operational-health.test.ts`.
- [x] Run focused backend tests for camera profile derivation and camera service source delivery.
- [x] Run frontend lint and type/build plus backend ruff.
- [ ] Manually smoke the installed Office camera after rebuilding/restarting the affected frontend/backend containers.
