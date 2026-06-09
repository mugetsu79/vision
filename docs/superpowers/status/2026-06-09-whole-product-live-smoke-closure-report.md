# Whole-Product Live Smoke Closure Report

Date: 2026-06-09

Branch/head during final smoke: `codex/sceneops-pack-registry` at `4c8e9e3a`, pushed to `origin/codex/sceneops-pack-registry`.
Stack type: installed macOS master product stack plus real Jetson Orin edge stack rebuilt from the committed branch; targeted destructive reset completed earlier in this closure run without global Docker prune.
URLs: frontend `http://192.168.1.166:3000`, backend `http://192.168.1.166:8000`, Keycloak `http://192.168.1.166:8080`, master MediaMTX RTSP `rtsp://192.168.1.166:8554`.
Jetson: `192.168.1.203`, rebuilt after removing old Vezor stack and preserving model files under `/var/lib/vezor/models`.
RTSP sources: Office/Test camera URLs on `192.168.1.195:8554/ch1`, `192.168.1.165:8554/ch1`, and `192.168.1.165:8554/ch2`; credentials are intentionally not recorded here.
Deterministic smoke run id: `closure-20260609T110202Z`.

## Summary

The remaining installed-product smoke gaps are closed for the macOS master plus
real Jetson edge compose/systemd path, except where explicitly marked BLOCKED or
NOT RUN below. The run proved a fresh first-run credential binding after the
central supervisor credential fix, real Jetson supervisor/API sync, deterministic
detection/history/evidence fixture data, billing usage generation, TensorRT
engine build on Jetson, reflector secret distribution, a real Jetson-origin UDP
edge-agent probe, packaged edge-agent systemd operation, rebuilt central images,
and tenant-admin user management through the installed Users UI.

Late live blocker fixed in this update:

- `installer/linux/install-edge.sh` generated `/etc/vezor/edge-agent.env` with
  an unquoted label containing spaces. `vezor-edge-agent.service` failed with
  `/etc/vezor/edge-agent.env: line 7: Core: command not found`. A failing
  regression test was added, env values are now shell-quoted, the fix was
  pushed, the Jetson pulled `4c8e9e3a`, and the service now runs.

Remaining product gap:

- Platform-superadmin tenant/user management UI controls exist after a
  platform-superadmin token is available, but the installed product does not yet
  bootstrap the first platform-superadmin account or platform sign-in path from
  UI. That is documented as a follow-up spec and plan.

## Pass/Fail Matrix

| Area | Status | Evidence |
|---|---|---|
| Targeted destructive reset | PASS | Removed installed Vezor DB/config/secret state and old Jetson stack; no global Docker prune; unrelated Docker resources left alone; model files preserved. |
| Fresh first-run and central credential | PASS | First-run completed after reset; central credential files existed and matched by hash; central supervisor authenticated without manual credential repair after the credential fix. |
| Jetson destructive rebuild | PASS | Old Jetson Vezor stack deleted and rebuilt; `/var/lib/vezor/models` preserved; `vezor-edge.service` enabled/active. |
| Real Jetson supervisor/API sync and inventory | PASS | Edge node `9ca35fc9-0c88-44f7-bf70-d59e1897a72b`; YOLO26n and YOLO26s assignments reached `synced`; inventory reported both ONNX model files with expected sizes/SHA256s. |
| TensorRT engine build on Jetson | PASS | Build job `5664f4c4-3ef9-4685-ad28-7ffc3737bfa3` succeeded; artifact `abd16885-865f-408b-927a-396e63750324`, `/models/runtime-artifacts/.../yolo26n.engine`, size `8327412`, SHA256 `f34b01b38e90ce659f8148fa3d1e04e3637c53e9bc2443f94a7c276f9c78f6da`. |
| Real RTSP 1296p lane | PASS | Jetson `ffprobe` and smoke harness passed for redacted `192.168.1.195:8554/ch1`: H.264, `2304x1296`, `20/1` fps. |
| Real RTSP 720p lane | PASS | Smoke harness passed for redacted `192.168.1.165:8554/ch2`: H.264, `1280x720`, `20/1` fps. |
| Real camera assigned to Jetson edge | PASS | Camera `376520ca-29ff-425b-adda-b091e6f3b314` created for Smoke Office site with `processing_mode=edge`; fleet worker row reported edge supervisor ownership and `runtime_status=running`; delivery diagnostics exposed native/passthrough profiles. |
| Deterministic detection/history fixture | PASS | Fixture run `closure-20260609T110202Z`; history returned `person` detections for camera `376520ca-29ff-425b-adda-b091e6f3b314`; latest seeded incident present. |
| Evidence artifact content | PASS | Artifact `d8941fc5-4b2e-50e4-82ca-d50daf60db05` content route returned 200 from `/var/lib/vezor/evidence`; content included smoke run id, camera id, and `class_name=person`; SHA256 matched fixture output. |
| Billing usage and invoice | PASS | Billing usage generated for meters `evidence_pack_export` and `managed_edge_node`; invoice `3c6af742-55e2-4075-9c53-38991da8ea5d` present with two line items. |
| Master reflector profile redaction | PASS | Normal reflector profile returned `secret_state=present` and did not expose raw secret material. |
| Master reflector secret distribution | PASS | Admin and node-credential edge-agent config fetches returned 200; raw config stored only under local `/tmp`/Jetson `/tmp` with mode `0600`; report output redacted secret material. |
| Real UDP edge-agent probe from Jetson | PASS | Packaged `vezor-edge-agent.service` posted a real UDP sample from Jetson using the supervisor node credential: `reachable=true`, `packet_loss_percent=0.0`, `packets_received=20/20`, average RTT about 5.3 ms. |
| Edge-agent installed service packaging | PASS | Added `bin/vezor-edge-agent`, `infra/install/systemd/vezor-edge-agent.service`, installer wiring, node-credential bearer-token-file use, and regression tests. |
| Edge-agent systemd service live run | PASS | After reinstall from `4c8e9e3a`, both `vezor-edge.service` and `vezor-edge-agent.service` were enabled/active; Docker showed `vezor-edge-agent`, `vezor-supervisor`, `vezor-edge-nats-leaf`, and `vezor-edge-mediamtx` running. |
| Backend Docker cache-friendly layer order | PASS | Central and edge Dockerfiles copy dependency manifests before source; regression tests assert dependency install happens before `COPY src` / app source. |
| Rebuild central images from committed branch | PASS | Rebuilt `vezor/backend:portable-demo` image `73ba717a0333` and `vezor/frontend:portable-demo` image `7f3ca4b9e84e` from branch head `4c8e9e3a`; recreated backend, frontend, and central supervisor containers from those images. |
| Rebuild Jetson edge image from committed branch | PASS | Jetson pulled `4c8e9e3a`; packaged edge installer rebuilt `vezor/edge-worker:portable-demo` image `34c9c8dc2f68` using cached dependency layers and installed services. |
| Jetson GPU ONNX Runtime packaging | BLOCKED | The dev edge image build still required `--allow-cpu-onnx-runtime` because no Jetson GPU ONNX Runtime wheel URL was configured. TensorRT build itself passed; this is a packaging input gap. |
| Tenant/user/admin implementation | PASS | Added backend/API/UI for tenant-admin scoped user management and platform-superadmin tenant/user management once platform auth exists; full backend suite `1245 passed`, full frontend suite `493 passed`. |
| Tenant-admin installed Users API smoke | PASS | On rebuilt stack, refreshed smoke admin auth locally, `GET /api/v1/users` returned 200, `POST /api/v1/users` created additional admin `live-smoke-admin-1781008625@vezor.local`, reset-password returned 200, and tenant admin `GET /api/v1/tenants` correctly returned 403. |
| Tenant-admin installed Users UI smoke | PASS | Playwright rendered `http://192.168.1.166:3000/users` with a real tenant-admin OIDC session; Users nav/form/table rendered and listed the first-run admin plus the newly-created additional admin. Screenshot: `output/playwright/users-live-smoke.png`. |
| Platform superadmin Users UI controls | PASS | Automated frontend tests verify platform-superadmin mode can create tenants and tenant users from Users UI when `realm=platform-admin` and role `superadmin` are present. |
| First platform-superadmin bootstrap from UI | BLOCKED | Current installed Keycloak has only `master` and `argus-dev` realms; no `platform-admin` realm or platform sign-in authority is installed. Product UI cannot yet create/sign in the first platform superadmin. Follow-up spec/plan added. |
| Helm render posture | PASS | `helm lint` passed for central and edge values; `helm template` rendered 371 central lines and 402 edge lines, including central backend/frontend deployments, reflector env, edge worker, NATS leaf, and `nvidia.com/gpu: "1"`. |
| k3s live deployment posture | NOT RUN | No local kube context was configured, Jetson reported missing `k3s`, `kubectl`, and `helm`, and no live k3s cluster was available for apply/rollout. |

## Confirmed Bugs Fixed

- `infra/install/compose/compose.supervisor.yml`: Jetson supervisor `/models`
  mount is writable so synced artifacts and TensorRT engines can be written.
- `installer/linux/install-edge.sh`: model directory ownership is adjusted
  non-recursively, preserving model files while allowing supervisor writes.
- `backend/src/argus/supervisor/tensorrt_builder.py`: `trtexec` now uses
  equals-form flags accepted by the Jetson `trtexec` version.
- `scripts/validation/whole_product_live_smoke.py`: real RTSP checks run
  `ffprobe` and redact credentials.
- `backend/src/argus/scripts/seed_whole_product_smoke_fixture.py`: default
  evidence root follows `Settings().incident_local_storage_root`.
- `backend/src/argus/services/app.py`: supervisor site-scope auth validates the
  deployment credential's actual edge node site.
- `backend/src/argus/link/api.py`: edge-agent config fetch reconciles an
  enabled persisted master reflector profile into a live UDP listener after
  backend restart.
- `backend/src/argus/link/edge_agent.py`: supports bearer token files for
  service packaging.
- `backend/Dockerfile` and `backend/Dockerfile.edge`: dependency layers are
  cache-friendly for source-only rebuilds.
- `installer/linux/install-edge.sh`: edge-agent env values are shell-quoted so
  labels with spaces do not break the sourced env file.

## User And Admin Management

Current installed behavior after this branch:

- First-run creates the first tenant and the first tenant admin.
- Tenant admins can use Vezor `Users` to create additional tenant admins,
  operators, and viewers; no Keycloak console is needed for tenant accounts.
- Tenant admins remain tenant-scoped through token claims and cannot assign
  `superadmin`.
- Platform superadmin API/UI behavior is implemented for users authenticated
  through the `platform-admin` realm with role `superadmin`.
- Creating the first platform superadmin from UI is not implemented yet because
  there is no installed platform bootstrap or platform sign-in path.

Follow-up design/plan for that missing product path:

- Spec: `docs/superpowers/specs/2026-06-09-platform-superadmin-ui-bootstrap-design.md`
- Plan: `docs/superpowers/plans/2026-06-09-platform-superadmin-ui-bootstrap-implementation-plan.md`

## Security/Tenant Notes

- No raw admin passwords, sudo passwords, bearer tokens, RTSP credentials, node
  credentials, bootstrap tokens, or reflector secrets are committed in this
  report.
- Temporary live auth material was stored only under `/tmp` with mode `0600` and
  deleted after the Users UI Playwright smoke.
- Profile APIs return `secret_state`; only the scoped edge-agent config route
  returns reflector secret material to authorized admin/supervisor callers.
- The edge-agent service uses the Jetson supervisor node credential, not an
  admin bearer token.

## Verification

Commands run in this final closure pass:

```bash
python3 -m uv run --project installer pytest installer/tests/test_edge_installer_artifacts.py -q
# 11 passed

scripts/validate-installers.sh
# installer validation passed, 88 installer tests passed

docker build -f backend/Dockerfile -t vezor/backend:portable-demo .
docker build -f frontend/Dockerfile -t vezor/frontend:portable-demo frontend
docker compose --env-file /etc/vezor/master.env \
  -f infra/install/compose/compose.master.yml \
  up -d --force-recreate backend frontend vezor-supervisor

curl -fsS http://192.168.1.166:8000/healthz
# {"status":"ok"}

helm lint infra/helm/argus -f infra/helm/argus/values-central.yaml
helm lint infra/helm/argus -f infra/helm/argus/values-edge.yaml
helm template vezor-central infra/helm/argus -f infra/helm/argus/values-central.yaml
helm template vezor-edge infra/helm/argus -f infra/helm/argus/values-edge.yaml

python3 -m uv run --project backend pytest backend/tests -q
# 1245 passed

corepack pnpm --dir frontend test
# 493 passed

corepack pnpm --dir frontend exec tsc -b
# passed
```

Representative live commands, with secrets redacted:

```bash
ssh ai-user@192.168.1.203 \
  'cd /home/ai-user/vision && git pull --rebase origin codex/sceneops-pack-registry'

ssh ai-user@192.168.1.203 \
  'sudo installer/linux/install-edge.sh --unpaired --api-url [redacted] \
   --edge-name jetson-orin-1 --model-dir /var/lib/vezor/models \
   --public-mediamtx-rtsp-url rtsp://192.168.1.203:8554 \
   --version 4c8e9e3a --allow-cpu-onnx-runtime'

ssh ai-user@192.168.1.203 \
  'sudo systemctl restart vezor-edge-agent.service && systemctl is-active vezor-edge-agent.service'

curl -H "Authorization: Bearer [redacted]" http://192.168.1.166:8000/api/v1/users
curl -H "Authorization: Bearer [node credential redacted]" \
  http://192.168.1.166:8000/api/v1/link/control-targets/master/edge-agent-config
```

## Remaining Work

1. Implement the platform-superadmin UI bootstrap spec so the first
   platform-superadmin account and platform sign-in path are product-managed.
2. Provide or publish a Jetson GPU ONNX Runtime wheel artifact for dev packaged
   edge builds so `--allow-cpu-onnx-runtime` is not needed.
3. Exercise a true k3s live deployment on a reachable k3s cluster and record
   apply/rollout evidence.
