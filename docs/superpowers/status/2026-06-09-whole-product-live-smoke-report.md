# Whole-Product Live Smoke Report

Date: 2026-06-09

Branch/head during smoke: `codex/sceneops-pack-registry` at `4d6a75f8`, with smoke-blocker fixes committed afterward on this branch
Stack type: installed macOS master product stack, rebuilt from the local repo with `bin/vezor install master`
URLs: frontend `http://192.168.1.166:3000`, backend `http://192.168.1.166:8000`, Keycloak `http://192.168.1.166:8080`, MediaMTX RTSP `rtsp://192.168.1.166:8554`
Fresh first-run verified: yes, on targeted reset before live validation; first-run completed at `2026-06-09T00:38:15.448559Z`
Model file used: `/models/yolo26n.onnx`; `/models/yolo26s.onnx` also registered
RTSP/source used: real Office RTSP camera, redacted as `rtsp://[redacted]@192.168.1.165:8554/ch2`
Edge-agent mode: emulated deployment/Jetson node only; real Jetson supervisor/API was not reachable

## Summary

The installed MacBook master stack is running from the updated repo, first-run is complete, tenant auth works, YOLO26n/YOLO26s are bundled and registered, the Office RTSP source probes as `1280x720` H.264 at 20 fps, the Office scene runs under the central supervisor, and Live plays the native stream when the tile is in view.

Four confirmed smoke blockers were fixed narrowly with failing tests first:

- model catalog relative `models/...` paths did not resolve to the installed `/models` mount.
- fixed-vocab catalog entries with empty declared classes rejected embedded ONNX class metadata.
- model sync job creation set `last_sync_job_id` before the sync job row was flushed.
- installed master supervisor had no configured node credential path registered in the backend.

The current stack required a one-time credential repair because first-run had already completed before the central supervisor credential fix. New master installs now generate `central_supervisor_credential`, mirror it to `supervisor.credential`, and first-run registers only its hash.

## Pass/Fail Matrix

| Area | Status | Evidence |
|---|---|---|
| First-run/auth/tenant | PASS | Fresh reset completed first-run at `2026-06-09T00:38:15.448559Z`; bootstrap status is `first_run_required=false`, tenant `mugetsu-demo`; admin direct-grant token calls tenant APIs. |
| Deployment/support bundle | PASS | Central node `d3918de1-b816-4a53-bdcb-f5da7ae94646` reports `install_status=healthy`, `credential_status=active`, `service_status=running`; support bundle includes credential-store diagnostics, service reports, completed lifecycle request, runtime reports, hardware reports, and model-admission report. |
| Model registration | PASS | `/api/v1/models` lists YOLO26n and YOLO26s registered at `/models/yolo26n.onnx` and `/models/yolo26s.onnx`; catalog entries `yolo26n-coco-onnx` and `yolo26s-coco-onnx` are `registered` with `artifact_exists=true`. |
| Scenes/cameras | PASS | Office edge site exists; Vezor Master remains `site_kind=control_plane`; Office camera uses central processing, YOLO26n, `native` default profile, source capability `1280x720`, `fps=20`, `codec=h264`. |
| Worker lifecycle | PASS | Central supervisor authenticated with node credential, claimed lifecycle request `327215ff-a941-417b-bd91-bc0d0633a19d`, completed it, recorded model admission `supported`, and posted repeated runtime reports with `runtime_state=running`. |
| Live/history/evidence | PASS/BLOCKED | Live PASS: Office tile shows `TELEMETRY LIVE`, `WORKER RUNNING`, WebRTC first frame around `1230ms`, video `1280x720`; HLS playlist and MJPEG fallback endpoints also returned data. History route loaded in UI sweep. Evidence/Incidents BLOCKED for real evidence because no deterministic detection/evidence fixture or actual incident was generated; `/api/v1/incidents` is empty. |
| Core Link paths/targets | PASS | `/api/v1/link/sites/summary` shows Office as edge/configurable and Vezor Master as `control_plane`, `can_configure_links=false`, `can_receive_edge_probes=true`. |
| Master reflector | BLOCKED | Master reflector API exists but profile is disabled and `secret_state=missing`; no real reflector secret distribution or live UDP reflector probe was available. |
| Emulated edge-agent probes | BLOCKED | Emulated Jetson node and support bundle exist, but real supervisor/API/SSH on `192.168.1.165` were unreachable; only RTSP `8554` was reachable. |
| FleetOps | PASS/BLOCKED | Routes and `/api/v1/operations/fleet` load; overview shows `desired_workers=1`, `running_workers=1`, central healthy and emulated Jetson offline. Maritime/FleetOps real vessel/evidence/billing flows were not generated, so those remain BLOCKED/NOT RUN. |
| Helm/Compose/deployment posture | PASS | `make verify-installers` passed: `86 passed`, shell syntax, executable bits, manifest validation, product secret scan, master/edge compose render. Master compose now mounts backend secret `ARGUS_CENTRAL_SUPERVISOR_CREDENTIAL`. Helm was not separately exercised. |
| Docs consistency | PASS | Product installer guide and runbook now document generated central supervisor credential and first-run hash binding. |

## Confirmed Bugs

- `backend/src/argus/services/model_catalog.py`: installed catalog entries using `models/...` were treated as repo-relative paths instead of `/models/...`, so bundled models appeared missing.
- `backend/src/argus/services/model_lifecycle.py`: empty fixed-vocab catalog classes were passed as an explicit empty class set, causing embedded ONNX class metadata validation failure.
- `backend/src/argus/services/model_lifecycle.py`: model sync job creation updated assignment FK before the job row was flushed, causing a foreign-key violation.
- Master installer/bootstrap path did not provision a central supervisor credential for installed operation, leaving the supervisor unable to poll/apply lifecycle work without manual repair.

## Product Gaps

- Deterministic detection/evidence fixture is still missing; real Evidence/Incidents cannot be called passed without a generated event.
- Real Jetson edge supervisor was not reachable. The camera RTSP source is real, but Jetson API/SSH and real model sync/inventory were blocked.
- Real billing usage generation was not exercised; billing nodes, accounts, and usage are empty.
- Runtime artifact/TensorRT engine creation from the UI was not live-built on a Jetson.
- Master reflector secret distribution and edge-agent authenticated UDP reflector probe are not complete.

## UX Clarity Issues

- Live idles offscreen scene tiles by design. When the Office tile was below the viewport it showed `Standby preview`; after scrolling into view it negotiated WebRTC and played. The UI could make offscreen stream idling clearer.
- The camera API still carries raw default profile inventory including unsupported profiles, while the Live UI correctly filters options by source capability. This is acceptable for now but should stay documented.

## Test Gaps

- No end-to-end deterministic smoke fixture creates a known detection, incident, evidence clip, history datapoint, and billing usage record.
- No fresh destructive-reset proof was rerun after the central supervisor credential fix; behavior is covered by backend/installer tests and current-stack repair/reinstall evidence.
- No real Jetson supervisor sync/admission/inventory verification.
- No real Core Link UDP reflector probe with secret distribution.

## Deployment/Ops Gaps

- Existing installs that completed first-run before the central credential fix need one-time credential rotation plus supervisor config alignment.
- Helm/k3s deployment posture was not exercised in this smoke.
- Edge model assignment for the emulated Jetson remains `syncing` because no real edge supervisor consumed the sync job.

## Security/Tenant Risks

- No raw bootstrap token, bearer token, admin password, RTSP password, reflector secret, or supervisor credential material is recorded here.
- Support bundle diagnostics redacted credential-like fields in inspected responses.
- Master reflector remains disabled with missing secret, so no reflector traffic was accepted.

## Documentation Mismatches

None left for the changes made in this smoke. The product guide and runbook now describe central supervisor credential generation and first-run binding.

## Commands Run

Representative commands, with secrets redacted:

```bash
git status --short --branch
python3 -m uv run --project backend pytest backend/tests/services/test_deployment_nodes.py backend/tests/services/test_model_catalog.py backend/tests/services/test_model_lifecycle_imports.py backend/tests/services/test_supervisor_model_jobs.py -q
python3 -m uv run --project backend pytest backend/tests/services/test_model_lifecycle_imports.py backend/tests/services/test_deployment_model_inventory.py backend/tests/services/test_supervisor_model_jobs.py backend/tests/services/test_runtime_artifact_build_jobs.py backend/tests/services/test_edge_configuration_assignments.py backend/tests/supervisor/test_model_jobs.py backend/tests/supervisor/test_artifact_build_jobs.py backend/tests/services/test_deployment_nodes.py backend/tests/services/test_model_catalog.py -q
python3 -m uv run --project backend ruff check backend/src/argus/core/config.py backend/src/argus/services/app.py backend/src/argus/services/deployment_nodes.py backend/src/argus/services/model_catalog.py backend/src/argus/services/model_lifecycle.py backend/tests/services/test_deployment_nodes.py backend/tests/services/test_model_catalog.py backend/tests/services/test_model_lifecycle_imports.py backend/tests/services/test_supervisor_model_jobs.py
installer/.venv/bin/python -m pytest installer/tests/test_macos_master_artifacts.py installer/tests/test_linux_master_artifacts.py installer/tests/test_edge_installer_artifacts.py -q
make verify-installers
npm --prefix frontend run test -- Live.test.tsx Models.test.tsx Deployment.test.tsx Cameras.test.tsx use-model-lifecycle.test.tsx
git diff --check
sudo ./bin/vezor install master --public-url http://192.168.1.166:3000
curl -fsS http://192.168.1.166:8000/healthz
curl -fsS -H "Authorization: Bearer [redacted]" http://192.168.1.166:8000/api/v1/deployment/bootstrap/status
curl -fsS -H "Authorization: Bearer [redacted]" http://192.168.1.166:8000/api/v1/models
curl -fsS -H "Authorization: Bearer [redacted]" http://192.168.1.166:8000/api/v1/model-catalog
curl -fsS -H "Authorization: Bearer [redacted]" http://192.168.1.166:8000/api/v1/operations/fleet
curl -fsS -H "Authorization: Bearer [redacted]" "http://192.168.1.166:8000/api/v1/streams/d7dc9b0f-faea-4e6c-a947-be8b2e017eda/hls.m3u8?profile_id=native"
curl -m 6 -H "Authorization: Bearer [redacted]" "http://192.168.1.166:8000/video_feed/d7dc9b0f-faea-4e6c-a947-be8b2e017eda?profile_id=native"
```

Verification results:

- backend focused/broader suites: `47 passed`, `80 passed`
- backend Ruff: `All checks passed`
- installer artifact suite: `43 passed`
- `make verify-installers`: `86 passed`, installer validation passed
- frontend selected suites: `54 passed`
- `git diff --check`: passed
- stack health: `{"status":"ok"}`

## Screenshots/Logs Captured

- Supervisor logs after credential repair show:
  - `Supervisor service report posted supervisor_id=100`
  - `POST /api/v1/operations/runtime-reports` `201 Created`
  - `Loaded detection model YOLO26n COCO with provider CPUExecutionProvider`
  - repeated inference timing summaries for Office camera.
- Browser Live check showed:
  - Office selected, `TELEMETRY LIVE`, `WORKER RUNNING`
  - rendition options: `Native camera`, `Annotated`, `720p20/15/10/5`, `540p20/15/10/5`, `360p20/15/10/5`, `240p20/15/10/5`
  - no `1080p` or `900p` options for the `1280x720` source
  - visible tile transport `webrtc`, first frame `1230ms`, video dimensions `1280x720`.

## Recommended Next Steps

1. Add the deterministic detection/evidence/history/billing fixture and make it part of the whole-product smoke.
2. Rerun a destructive fresh-stack smoke after the central supervisor credential fix to prove the new first-run credential binding without current-stack repair.
3. Pair the real Jetson supervisor, then validate model sync inventory, TensorRT artifact build, runtime admission, and edge worker lifecycle from the UI.
4. Enable master reflector with real secret distribution and run authenticated edge-agent UDP sequence probes.
5. Generate real billing usage from a controlled event or fixture, then validate FleetOps billing and support flows.
