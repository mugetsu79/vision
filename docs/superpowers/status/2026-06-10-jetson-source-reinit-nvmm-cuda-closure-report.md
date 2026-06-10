# Jetson Source Reinitialization And NVMM/CUDA Frame Closure Report

Date: 2026-06-10
Branch: `codex/sceneops-pack-registry`
Status: ready for user commit approval; live smoke not run from this uncommitted tree.

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
| Live Jetson smoke | NOT RUN | Pending user approval to commit, rebuild, redeploy from the final committed branch, then run live Jetson/central smoke. |
| Full frontend lint | FAIL | `corepack pnpm --dir frontend lint` still fails on unrelated `frontend/src/hooks/use-platform-bootstrap.ts:36` unsafe `any` assignment. Targeted frontend tests passed. |

## Verification

PASS:

- `backend/.venv/bin/pytest backend/tests/vision/test_camera.py backend/tests/vision/test_jetson_nvmm_capture.py backend/tests/inference/test_engine.py backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py backend/tests/services/test_operations_service.py backend/tests/api/test_operations_endpoints.py backend/tests/supervisor/test_operations_client.py backend/tests/supervisor/test_reconciler.py -q`
  - `265 passed`
- `corepack pnpm --dir frontend test CameraWizard.test.tsx Settings.test.tsx operational-health.test.ts`
  - `51 passed`
- `backend/.venv/bin/ruff check` on touched backend source and tests
  - passed
- `git diff --check`
  - passed
- `cd backend && .venv/bin/alembic heads`
  - single head: `0048_runtime_source_profile_hash`
- `git check-ignore -v .playwright-cli/... .playwright-mcp/...`
  - both generated tool directories are ignored

FAIL:

- `corepack pnpm --dir frontend lint`
  - unrelated existing error: `frontend/src/hooks/use-platform-bootstrap.ts:36` unsafe assignment of an `any` value.

Security/secrets check:

- Scanned changed source/docs/test paths for the live local RTSP credentials and direct credentialed RTSP patterns.
- No live local raw credentials were found in this change set. Existing test placeholders and prior redacted status docs remain.

## Commit Gate

Do not run live smoke from this dirty tree. Next safe sequence:

1. User approves local commit.
2. Commit only the intended implementation/report files, excluding unrelated untracked artifacts.
3. Rebuild/redeploy from the committed branch.
4. Run live Jetson and central reference smoke with sanitized monitoring and redacted evidence.
