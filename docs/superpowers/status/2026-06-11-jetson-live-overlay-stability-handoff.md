# Jetson Live Overlay Stability Handoff

Date: 2026-06-11
Branch: `codex/sceneops-pack-registry`

## Purpose

This handoff records the Jetson Live overlay/tracking stability work completed
after the no-DeepStream Jetson runtime optimization pass. It preserves
DeepStream as a later optional runtime-family track and keeps this closure in
the current Python worker path.

## Implemented In This Branch

- `TelemetryFrame` now has optional `source_size` so browser overlays can use
  the worker's actual detection/tracking coordinate space.
- The Live page and `TelemetryCanvas` prefer frame `source_size` before camera
  source capability.
- Browser overlays no longer draw the default center endpoint dot.
- Short backend coasting is rendered as visually live in the browser; longer
  coasting is shown as held.
- Processed stream annotation mirrors that behavior: short coasts keep the
  active label/box, longer coasts use held styling.
- Resolved scene vision profile now affects the runtime tracker/lifecycle:
  maximum-accuracy advanced Jetson uses the difficult tracker profile, profile
  memory drives coast TTL, and profile new-track hits drive lifecycle
  activation.
- Runtime vision profile changes rebuild tracker/lifecycle state so mode
  changes take effect without waiting for a process replacement.
- Removed-assignment worker rows no longer appear as `STARTING` merely because
  an old or mismatched runtime report exists.

## Live Comparison Before Deploy

The running stack was still on the previous deployment when this handoff was
written.

Central scene:

- camera: `CENTRAL persons RTSP`
- stream profile: `720p20`
- runtime report: `running`
- selected provider: `onnxruntime`
- media path: `ffmpeg_software`
- telemetry stream mode: `annotated-whip`
- latest sampled person track: active, confidence around 0.92

Jetson edge scene:

- camera: `EDGE vehicles RTSP`
- stream profile: `720p20`
- runtime report: `running`
- selected provider: `tensorrt_engine`
- media path: `jetson_gstreamer_native`
- telemetry stream mode: `filtered-preview`
- latest sampled person track: active, confidence around 0.935

Both scenes have native/direct stream unavailable because privacy filtering is
required. Both current video tiles are worker-rendered processed streams, not
native browser-overlay-only streams.

## Important Follow-Up For Later

Do not change this in the current deploy: the backend/API currently exposes
central processed privacy-safe video as `annotated-whip` and Jetson edge
processed privacy-safe video as `filtered-preview`.

Later work should normalize or clarify this contract because `filtered-preview`
is misleading: it is a worker-published processed stream, not a browser-only
preview overlay. A future cleanup can rename modes, add a clearer
`server_rendered_overlay`/`browser_overlay_allowed` capability, or otherwise
make the UI contract explicit.

Until that cleanup happens, frontend behavior must treat both `annotated-whip`
and `filtered-preview` as worker-rendered streams where the browser overlay
toggle must not draw tracking boxes. Browser-drawn boxes are only for native
`passthrough` streams.

## Verification Completed

```bash
backend/.venv/bin/ruff check \
  backend/src/argus/inference/engine.py \
  backend/src/argus/inference/publisher.py \
  backend/src/argus/vision/track_lifecycle.py \
  backend/tests/inference/test_engine.py \
  backend/tests/services/test_operations_service.py

backend/.venv/bin/pytest \
  backend/tests/api/test_openapi_export.py \
  backend/tests/inference/test_engine.py \
  backend/tests/vision/test_profiles.py \
  backend/tests/vision/test_track_lifecycle.py \
  backend/tests/vision/test_tracker.py \
  backend/tests/services/test_operations_service.py -q

corepack pnpm --dir frontend exec vitest run \
  src/lib/live-signal-stability.test.ts \
  src/hooks/use-stable-signal-frame.test.tsx \
  src/components/live/TelemetryCanvas.test.tsx

corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
git diff --check
```

Observed results:

- backend ruff: passed
- backend targeted suite: 137 passed
- frontend targeted suite: 27 passed
- frontend lint: passed
- frontend production build: passed
- diff whitespace check: passed

## Deploy Notes

After this branch is committed and pushed, rebuild/redeploy the master and
Jetson edge stacks from the committed branch, not live patches.

Expected post-deploy smoke:

- frontend bundle shows no browser box/dot on edge `filtered-preview`
- browser overlay still works for native `passthrough`
- central remains `annotated-whip`
- Jetson may remain `filtered-preview` until the later naming/contract cleanup
- Jetson runtime report remains fresh with `selected_provider=tensorrt_engine`
  and `media_pipeline_mode=jetson_gstreamer_native`
- telemetry frames include `source_size`
- active/held flapping is reduced for short coasts

