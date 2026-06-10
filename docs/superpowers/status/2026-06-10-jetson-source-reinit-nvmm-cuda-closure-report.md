# Jetson Source Reinitialization And NVMM/CUDA Frame Closure Report

Date: 2026-06-10
Branch: `codex/sceneops-pack-registry`
Status: locally committed and live-smoked on Jetson from committed branch state.

Local commits:

- `4bce3ead` - `feat: add Jetson source reinit and NVMM frame lane`
- `ce0f34a8` - `test: align runtime presentation fixtures`
- `683bc19a` - `fix: scope runtime artifact reports to selected provider`

## Scope

Implemented the non-DeepStream lane for dynamic Jetson source/profile changes and captured-frame envelopes:

- Dynamic worker source/profile reinitialization on camera source or browser stream profile change.
- Atomic rollback for capture reinitialization and stream registration failures.
- Runtime source profile hash propagation through worker config, supervisor runtime reports, fleet API, and UI presentation.
- Captured-frame envelope support so future CUDA/NVMM frames can reach detector fast paths before BGR materialization.
- Optional native Jetson NVMM capture wrapper and explicit `ARGUS_JETSON_CAPTURE_BACKEND=nvmm` selector.
- Setup-preview stale still protection when the camera source profile changes.
- Central supervised cameras now remain `not_reported` / awaiting first heartbeat until a fresh per-camera runtime report exists.
- Mismatched source-profile heartbeats now present as `starting` / awaiting profile heartbeat regardless of the stale report's old runtime state.

DeepStream was not implemented or claimed. It remains the later optional runtime-family track. Central macOS acceleration remains a future native CoreML/M4 lane; this change does not claim Dockerized central GPU acceleration.

## Results

| Area | Status | Evidence |
| --- | --- | --- |
| Dynamic source/profile reinit | PASS | `InferenceEngine.apply_command()` reconfigures source URI/profile and stream dimensions; tests cover source hash changes, profile changes, and rollback. |
| MediaMTX registration atomicity | PASS | Command-time capture reinit now happens before replacement stream registration; failed reinit avoids a second registration; failed registration rolls capture back. |
| Runtime report fields | PASS | Runtime reports include selected provider, runtime artifact id, media pipeline mode, encoder mode, scene contract hash, source profile hash, and heartbeat. |
| Fleet/API/UI heartbeat presentation | PASS | Missing central per-camera report shows awaiting first heartbeat; source-profile mismatch shows awaiting profile heartbeat. |
| Captured-frame envelope | PASS | `CapturedFrame` protocol supports `cpu_bgr`, `nvmm`, and `cuda`; detector fast path can consume captured frames before `as_bgr_numpy()`. |
| Native NVMM selector | PASS | `ARGUS_JETSON_CAPTURE_BACKEND=nvmm` is explicit opt-in and fail-closed; `auto` does not try NVMM. |
| Setup preview stale protection | PASS | Source-point editing is disabled when the still belongs to a stale source profile; destination editing remains available. |
| Playwright generated logs | PASS | `.playwright-cli/` and `.playwright-mcp/` are ignored to reduce risk of generated JWT-bearing logs being staged. |
| Registry publishing | BLOCKED | Registry target, repository names, credentials/auth method, and tag policy are still not provided. No fake publish was performed. |
| Full frontend lint | PASS | `corepack pnpm --dir frontend lint` passed after clearing the `use-platform-bootstrap` unsafe `any` lint issue. |
| Frontend build | PASS | `corepack pnpm --dir frontend build` passed. |
| Live Jetson smoke | PASS | Redeployed committed code `683bc19a`; Jetson image `sha256:8aa6a7294c59...`; fresh edge runtime report age 1.85 s with provider `tensorrt_engine`, pipeline `jetson_gstreamer_native`, capture backend `gstreamer_appsink`, encoder `software`, scene/source hashes present. |
| Live Jetson 720p source profile | PASS | Control-plane source capability for the edge camera is H.264 `1280x720` at 20 FPS with `fps_cap=20`; sanitized stdin-only source probe also reported `width=1280`, `height=720`, `avg_frame_rate=20/1`. |
| Live Jetson FPS/stage sample | PASS | 20.03 s sample: 360 frames, 17.97 FPS, 50.00 ms average total frame time, capture 18.53 ms, detect 23.17 ms, publish stream 5.18 ms. |
| Live Jetson resource sample | PASS | Sanitized `docker stats`: supervisor 147.31% CPU, 1.449 GiB memory; `tegrastats`: RAM about 2465-2469/7607 MB, GR3D 0-73% across the 5-second sample. |
| Central fresh per-camera smoke | FAIL | The latest central runtime report was stale after redeploy (age 1128.96 s) and still reflected an old persisted row. Per requirement, this was not accepted as `running`; central needs a fresh per-camera heartbeat before it can pass. |
| Central runtime artifact scoping | PASS (unit), NOT RUN (live fresh central) | Regression test now proves an ONNX fallback omits a stale Jetson TensorRT artifact id, but the live central worker did not emit a fresh report after redeploy, so no live central scoping pass is claimed. |

## Verification

PASS:

- `backend/.venv/bin/pytest backend/tests/vision/test_camera.py backend/tests/vision/test_jetson_nvmm_capture.py backend/tests/inference/test_engine.py backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py backend/tests/services/test_operations_service.py backend/tests/api/test_operations_endpoints.py backend/tests/supervisor/test_operations_client.py backend/tests/supervisor/test_reconciler.py -q`
  - `266 passed`
- `backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "omits_runtime_artifact_when_selected_provider_falls_back or reports_runtime_report_media_capture_backend_and_encoder_modes" -q`
  - `2 passed`
- `backend/.venv/bin/pytest backend/tests/inference/test_engine.py -q`
  - `84 passed`
- `backend/.venv/bin/ruff check backend/src/argus/inference/engine.py backend/tests/inference/test_engine.py`
  - passed
- `corepack pnpm --dir frontend lint`
  - passed
- `corepack pnpm --dir frontend test CameraWizard.test.tsx Settings.test.tsx operational-health.test.ts PlatformBootstrap.test.tsx Dashboard.test.tsx HardwareAdmissionPanel.test.tsx SupervisorLifecycleControls.test.tsx`
  - `67 passed`
- `corepack pnpm --dir frontend build`
  - passed
- `git diff --check`
  - passed
- `docker exec vezor-master-backend-1 /app/.venv/bin/alembic current`
  - `0048_runtime_source_profile_hash (head)`
- `git check-ignore -v .playwright-cli/... .playwright-mcp/...`
  - both generated tool directories are ignored

FAIL:

- Central reference smoke did not produce a fresh per-camera runtime report after redeploy. The old central row was treated as stale evidence, not a pass.

BLOCKED:

- Registry publishing remains blocked until registry target, repository names, credentials/auth method, and tag policy are provided.

Security/secrets check:

- Scanned changed source/docs/test paths for the live local RTSP credentials and direct credentialed RTSP patterns.
- No live local raw credentials were found in this change set. Existing test placeholders and prior redacted status docs remain.

## Live Smoke Notes

- Master backend was rebuilt as `vezor/backend:portable-demo` and redeployed with the master compose stack; backend and supervisor were healthy, frontend remained up.
- Jetson `/opt/vezor/current` pointed to `/home/ai-user/vision-683bc19a`; edge image `vezor/edge-worker:portable-demo` was rebuilt on-device and `vezor-edge.service` restarted.
- Jetson container health was green for supervisor and NATS before metrics collection.
- Jetson GStreamer probe: `gst-inspect-1.0 version 1.20.3`, `nvv4l2decoder=available`, `nvvidconv=available`.
- Sanitized process inspection used command names only; raw RTSP URLs and credentials were not printed.
