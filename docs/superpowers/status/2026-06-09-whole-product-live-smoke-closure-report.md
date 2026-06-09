# Whole-Product Live Smoke Closure Report

Date: 2026-06-09

Branch/head during final smoke: `codex/sceneops-pack-registry` at `a5186b9a`, `0 0` ahead/behind `origin/codex/sceneops-pack-registry` before this uncommitted report/update set.
Stack type: installed macOS master product stack plus real Jetson Orin edge stack rebuilt from the branch; targeted destructive reset completed without global Docker prune.
URLs: frontend `http://192.168.1.166:3000`, backend `http://192.168.1.166:8000`, Keycloak `http://192.168.1.166:8080`, MediaMTX RTSP `rtsp://192.168.1.166:8554`.
Jetson: `192.168.1.203`, rebuilt after removing old Vezor stack and preserving model files.
RTSP sources: redacted Office/Test camera URLs on `192.168.1.195:8554/ch1`, `192.168.1.165:8554/ch1`, and `192.168.1.165:8554/ch2`.
Deterministic smoke run id: `closure-20260609T110202Z`.

## Summary

The remaining whole-product smoke gaps are now closed for the installed macOS
master plus real Jetson edge path. The fresh stack preserved bundled YOLO26
model files, completed first-run with central supervisor credential binding,
rebuilt the Jetson edge stack, synchronized real model assignments to the
Jetson, generated a TensorRT engine on the Jetson, validated real RTSP lanes,
created deterministic history/evidence/incident/billing records, distributed
the master reflector secret through the authorized edge-agent config route, and
posted a real Jetson-origin UDP edge-agent probe using the node credential.

Two late live blockers were fixed with regression tests:

- a valid Jetson node credential was rejected when the site had an older stale
  edge-node row before the active deployment node;
- after backend restart, the persisted master reflector profile still said
  `listening` while the in-process UDP listener was absent.

Both are fixed in code and were hot-patched into the running backend for live
verification.

## Pass/Fail Matrix

| Area | Status | Evidence |
|---|---|---|
| Targeted destructive reset | PASS | Removed Vezor installed DB/config/secret state and old Jetson stack; no global Docker prune; unrelated Docker resources left alone; `/var/lib/vezor/models/yolo26n.onnx` and `yolo26s.onnx` preserved. |
| Fresh first-run and central credential | PASS | First-run completed after reset; central credential files existed and matched by hash; central supervisor authenticated without manual credential repair. |
| Jetson destructive rebuild | PASS | Old Jetson Vezor stack deleted and rebuilt; `vezor-edge.service` active; `vezor-supervisor`, `vezor-edge-nats-leaf`, and `vezor-edge-mediamtx` up/healthy; preserved model files on Jetson. |
| Real Jetson supervisor/API sync and inventory | PASS | Edge node `9ca35fc9-0c88-44f7-bf70-d59e1897a72b`; assignments for YOLO26n and YOLO26s reached `synced`; inventory reported both ONNX files with expected sizes and SHA256s. |
| TensorRT engine build on Jetson | PASS | Build job `5664f4c4-3ef9-4685-ad28-7ffc3737bfa3` succeeded after `trtexec` arg fix; artifact `abd16885-865f-408b-927a-396e63750324`, `/models/runtime-artifacts/.../yolo26n.engine`, size `8327412`, SHA256 `f34b01b38e90ce659f8148fa3d1e04e3637c53e9bc2443f94a7c276f9c78f6da`. |
| Real RTSP 1296p lane | PASS | Jetson `ffprobe` and smoke harness passed for redacted `192.168.1.195:8554/ch1`: H.264, `2304x1296`, `20/1` fps. |
| Real RTSP 720p lane | PASS | Smoke harness passed for redacted `192.168.1.165:8554/ch2`: H.264, `1280x720`, `20/1` fps. |
| Real camera assigned to Jetson edge | PASS | Camera `376520ca-29ff-425b-adda-b091e6f3b314` created for Smoke Office site with `processing_mode=edge`; fleet worker row reported edge supervisor ownership and `runtime_status=running`; delivery diagnostics exposed native/passthrough profiles. |
| Deterministic detection/history fixture | PASS | Fixture run `closure-20260609T110202Z`; history returned `person` detections for camera `376520ca-29ff-425b-adda-b091e6f3b314`; latest seeded incident present. |
| Evidence artifact content | PASS | Artifact `d8941fc5-4b2e-50e4-82ca-d50daf60db05` content route returned 200 from `/var/lib/vezor/evidence`; content included smoke run id, camera id, and `class_name=person`; SHA256 matched fixture output. |
| Billing usage and invoice | PASS | Billing usage generated for meters `evidence_pack_export` and `managed_edge_node`; invoice `3c6af742-55e2-4075-9c53-38991da8ea5d` present with two line items. |
| Master reflector profile redaction | PASS | `GET /api/v1/link/reflectors/master` returned `enabled=true`, `secret_state=present`, `last_status=listening`, and no raw secret in the normal profile response. |
| Master reflector secret distribution | PASS | Admin and node-credential `edge-agent-config` fetches returned 200; raw config stored only in `/tmp` mode `0600`; report output redacted `reflector_secret`. |
| Real UDP edge-agent probe from Jetson | PASS | One-shot edge-agent run on Jetson used the supervisor node credential and scoped config URL; probe `e34ce935-b98c-49bc-9c51-49be88206c4a` posted `reachable=true`, `packet_loss_percent=0.0`, `packets_received=20/20`, `rtt_avg_ms=5.311`. |
| Backend Docker cache-friendly layer order | PASS | Central and edge Dockerfiles now copy dependency manifests before source; regression tests assert dependency install happens before `COPY src` / app source. |
| Edge-agent installed service packaging | PASS | Added `bin/vezor-edge-agent`, `infra/install/systemd/vezor-edge-agent.service`, installer wiring, and tests. |
| Edge-agent systemd service live run | NOT RUN | The real live UDP proof used the current Jetson container module plus node credential; the newly packaged systemd service artifact was not installed and exercised as a service on the Jetson in this run. |
| Tenant/user/admin product management implementation | PASS | Added backend/API/UI for platform superadmin tenant creation and tenant-user management plus tenant-admin scoped user management; full backend suite `1245 passed`, full frontend suite `493 passed`. |
| Tenant/user/admin installed live smoke | NOT RUN | Implementation is automated-test verified only; installed-stack UI/API smoke against real Keycloak is pending the final rebuild/publish and redeploy. |
| Helm/k3s deployment posture | NOT RUN | This closure focused on the installed macOS master plus Jetson compose/service path. |

## Confirmed Bugs Fixed

- `infra/install/compose/compose.supervisor.yml`: Jetson supervisor `/models`
  mount is writable so synced artifacts and TensorRT engines can be written.
- `installer/linux/install-edge.sh`: model directory ownership is adjusted
  non-recursively, preserving model files while allowing supervisor writes.
- `backend/src/argus/supervisor/tensorrt_builder.py`: `trtexec` now uses
  equals-form flags (`--onnx=...`, `--saveEngine=...`) accepted by the Jetson
  `trtexec` version.
- `scripts/validation/whole_product_live_smoke.py`: real RTSP checks now run
  `ffprobe` and redact credentials.
- `backend/src/argus/scripts/seed_whole_product_smoke_fixture.py`: default
  evidence root follows `Settings().incident_local_storage_root`.
- `backend/src/argus/services/app.py`: supervisor site-scope auth validates the
  deployment credential's actual edge node site instead of an arbitrary first
  edge node for the site.
- `backend/src/argus/link/api.py`: edge-agent config fetch reconciles an
  enabled persisted master reflector profile into a live UDP listener after
  backend restart.
- `backend/src/argus/link/edge_agent.py`: supports bearer token files for
  service packaging.
- `backend/Dockerfile` and `backend/Dockerfile.edge`: dependency layers are
  cache-friendly for source-only rebuilds.
- `backend/src/argus/api/v1/models.py` and `runtime_artifacts.py`: FastAPI 422
  status alias works across current versions.

## User And Admin Management Answer

Current installed behavior:

- First-run creates the first Vezor `Tenant`, the first local `User` row, and
  the first Keycloak tenant admin.
- That first admin is tenant-scoped through token claims `tenant` and
  `tenant_id`.
- Runtime roles are `viewer`, `operator`, `admin`, and `superadmin`; `admin`
  inherits lower-role access by rank.
- `superadmin` is only treated as platform-wide when the token role is
  `superadmin` and the issuer realm is the configured platform realm.

Today, adding another admin with rights equivalent to the first-run user is a
Keycloak administration task: create the user in the tenant realm, set
attributes `tenant=<tenant slug>` and `tenant_id=<tenant UUID>`, assign the
realm role `admin`, set/reset the password, and confirm the `argus-frontend`
and `argus-cli` clients still map `tenant` and `tenant_id` into tokens.

Product implementation documented:

- Spec: `docs/superpowers/specs/2026-06-09-tenant-user-admin-management-design.md`
- Plan: `docs/superpowers/plans/2026-06-09-tenant-user-admin-management-implementation-plan.md`

Follow-up implementation now adds:

- `GET/POST /api/v1/tenants` for platform superadmins.
- `GET/POST/PATCH /api/v1/users` and `POST /api/v1/users/{user_id}/reset-password`.
- Vezor Users UI for tenant creation, tenant selection, user creation, role
  changes, enable/disable, and temporary password reset.
- Last-enabled-tenant-admin protection and rejection of `superadmin` assignment
  to tenant users.

## Security/Tenant Notes

- No raw admin passwords, sudo passwords, bearer tokens, RTSP credentials, node
  credentials, bootstrap tokens, or reflector secrets are committed in this
  report.
- Raw live API responses containing credential material were stored only under
  `/tmp/vezor-live-smoke` or Jetson `/tmp` with mode `0600`.
- Profile APIs return `secret_state`; only the scoped edge-agent config route
  returns reflector secret material to authorized admin/supervisor callers.
- Node credential route was verified with the real Jetson supervisor credential,
  not an admin bearer token.

## Verification

Live evidence highlights:

- Jetson model sync final raw evidence:
  `/tmp/vezor-live-smoke/jetson-model-sync-final.raw.json`
- TensorRT job/artifact raw evidence:
  `/tmp/vezor-live-smoke/tensorrt-build-jobs-2.raw.json`,
  `/tmp/vezor-live-smoke/tensorrt-artifacts.raw.json`
- Deterministic fixture/content/billing raw evidence:
  `/tmp/vezor-live-smoke/seed-fixture-content-ok.raw.json`,
  `/tmp/vezor-live-smoke/history-after-fixture.raw.json`,
  `/tmp/vezor-live-smoke/incidents-after-fixture.raw.json`,
  `/tmp/vezor-live-smoke/billing-usage-after-fixture.raw.json`
- Reflector and edge-agent raw evidence:
  `/tmp/vezor-live-smoke/master-reflector.raw.json`,
  `/tmp/vezor-live-smoke/link-probes-after-edge-agent.raw.json`,
  Jetson `/tmp/vezor-edge-agent-probe-success.raw.json`

Commands run:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/services/test_operations_service.py::test_supervisor_edge_site_scope_allows_credential_for_any_edge_node_on_site \
  backend/tests/services/test_operations_service.py::test_supervisor_edge_site_scope_blocks_other_sites \
  backend/tests/api/test_link_routes.py::test_supervisor_can_fetch_master_reflector_edge_agent_config \
  backend/tests/api/test_link_routes.py::test_supervisor_can_fetch_derived_master_reflector_edge_agent_config \
  backend/tests/api/test_link_routes.py::test_edge_agent_config_reconciles_missing_reflector_runtime \
  backend/tests/link/test_edge_agent.py \
  backend/tests/link/test_reflector.py \
  backend/tests/test_app_lifecycle.py \
  backend/tests/core/test_central_dockerfile.py \
  backend/tests/core/test_edge_dockerfile.py \
  backend/tests/supervisor/test_tensorrt_builder.py \
  backend/tests/scripts/test_whole_product_live_smoke.py \
  backend/tests/scripts/test_seed_whole_product_smoke_fixture.py \
  -q
# 67 passed

python3 -m uv run --project installer pytest \
  installer/tests/test_edge_installer_artifacts.py \
  installer/tests/test_linux_master_artifacts.py \
  -q
# 30 passed

python3 -m uv run --project backend ruff check [touched backend files]
# All checks passed

python3 -m uv run --project backend pytest \
  backend/tests/services/test_operations_service.py::test_supervisor_edge_site_scope_allows_credential_for_any_edge_node_on_site \
  backend/tests/services/test_operations_service.py::test_supervisor_edge_site_scope_blocks_other_sites \
  backend/tests/api/test_link_routes.py::test_edge_agent_config_reconciles_missing_reflector_runtime \
  backend/tests/core/test_central_dockerfile.py \
  backend/tests/core/test_edge_dockerfile.py \
  -q
# 17 passed

python3 -m uv run --project backend pytest backend/tests -q
# 1245 passed

corepack pnpm --dir frontend test
# 493 passed

corepack pnpm --dir frontend exec tsc -b
# passed
```

Representative live commands, with secrets redacted:

```bash
ssh ai-user@192.168.1.203 docker ps
ssh ai-user@192.168.1.203 docker exec vezor-supervisor ffprobe [redacted RTSP URL]
curl -H "Authorization: Bearer [redacted]" http://192.168.1.166:8000/api/v1/models
curl -H "Authorization: Bearer [redacted]" http://192.168.1.166:8000/api/v1/runtime-artifacts/build-jobs
curl -H "Authorization: Bearer [node credential redacted]" \
  http://192.168.1.166:8000/api/v1/link/sites/[site-id]/control-targets/master/edge-agent-config
ssh ai-user@192.168.1.203 docker exec vezor-supervisor \
  /app/.venv/bin/python -m argus.link.edge_agent --once
```

## Remaining Work

1. Install and run the new `vezor-edge-agent.service` on the Jetson after the
   next packaged/rebuilt edge install, then record service-manager evidence.
2. Rebuild/redeploy the installed stack and live-smoke the new Users UI/API
   against real Keycloak.
3. Exercise Helm/k3s deployment posture in a separate smoke.
4. Rebuild/publish images from the final committed branch rather than relying
   on the live backend hot-patches used to close this session.
