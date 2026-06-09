# Whole-Product Live Smoke Closure Report

Date: 2026-06-09

Branch: `codex/sceneops-pack-registry`, pushed to `origin/codex/sceneops-pack-registry`.

Smoke execution head: `5fc19c1f`. The report itself is committed after that smoke execution on the same branch.

Stack type: installed macOS master product stack plus real Jetson Orin edge stack; master compose services and Jetson systemd services rebuilt/restarted from committed branch artifacts. No global Docker prune was run.

Master URL: frontend `http://192.168.1.166:3000`, backend `http://192.168.1.166:8000`, Keycloak `http://192.168.1.166:8080`.

Jetson: Orin at `192.168.1.203`, checkout fast-forwarded to `5fc19c1f`; packaged edge image rebuilt at `ac380eb` for the latest edge production change, and the final `5fc19c1f` commit is frontend-test-only.

RTSP/source used: credentials redacted; central `192.168.1.195:8554/ch1`, edge `192.168.1.165:8554/ch1`, edge 720p lane `192.168.1.165:8554/ch2`.

Fresh destructive reset proof: targeted master reset was run after the central supervisor credential fix; Jetson old Vezor stack was deleted and rebuilt; `/var/lib/vezor/models` was preserved; no unrelated Docker resources were deleted.

## Summary

The remaining whole-product live smoke gaps are closed except for the explicitly scoped-out live k3s/Helm deployment posture, external registry publishing, final-pass annotated-browser rendering, and the central camera worker runtime row still reporting `not_reported`. The fresh stack now has a product-created superadmin identity, tenant `CENTRAL`, control-plane site `Vezor Master`, edge site/node `EDGE`, central person scene, edge vehicle scene, Jetson TensorRT runtime artifact, real UDP Core Link samples with throughput, deterministic history/evidence/billing fixture data, and active systemd-managed edge services.

Two late live blockers were fixed with regressions:

- Evidence artifact metadata existed but `/api/v1/incidents/{incident}/artifacts/{artifact}/content` returned 404 when the fixture wrote under `/var/lib/vezor/evidence/smoke`. Fixed by storing fixture object keys relative to the configured evidence root when the evidence directory is a subdirectory.
- `vezor-edge-agent.service` entered an auto-restart loop because a stale `vezor-edge-agent` Docker container already owned the name. Fixed by making the wrapper remove a stale container before the foreground `docker run`.

## Pass/Fail Matrix

| Area | Status | Evidence |
|---|---|---|
| Fresh destructive reset after central credential fix | PASS | Targeted reset removed Vezor master state and old Jetson stack while preserving `/var/lib/vezor/models`; no global prune. |
| First-run/auth/tenant claims | PASS | First-run created tenant `CENTRAL`; tenant-admin token can list users and is forbidden from tenant administration; platform token can list tenants/users. |
| Central supervisor credential binding | PASS | Master node `f518f016-3215-4ba2-85d5-d22904a1421e` reports `install_status=healthy`, `credential_status=active`, `service_status=running`; credential file hash recorded without exposing secret. |
| Real Jetson supervisor/API | PASS | Edge deployment node `80d5a1aa-e2d4-4f7c-b302-0e79c6c46fc6` reports `supervisor_id=EDGE`, `service_manager=systemd`, `service_status=running`, `host_profile=linux-aarch64-nvidia-jetson`. |
| Jetson model sync and inventory | PASS | Sync job `b3220ea9-f615-48b7-925c-4a083070c551` moved YOLO26n assignment to `synced`; Jetson files preserved with ONNX SHA256s `44def...d3d` and `4ffdd...ab6`; runtime artifact inventory reports TensorRT engine SHA256 `d413...c9b`. |
| TensorRT engine build on Jetson | PASS | Build job `2617d5cb-28c9-456f-a2fc-e18a19c317c3` succeeded on supervisor `EDGE`; artifact `4e849c27-f03e-4ec6-b575-9ba525a8763f`, size `8219692`, SHA256 `d4130e898ae0937e81aa9e28f2c7ab83e305720c1e0537bb131ac55cb2453c9b`, validation `valid`. |
| Jetson GPU ONNX Runtime packaging | PASS | Packaged Jetson install resolved the GPU ORT wheel from manifest automatically; no manual wheel URL was supplied; build asserted GPU providers during cached dependency layer. |
| CENTRAL scene configuration | PASS | Site `CENTRAL`; camera `CENTRAL persons RTSP`; processing `central`; active classes `["person"]`; RTSP probe from master backend saw H.264 `2304x1296` at `20/1` fps. |
| EDGE scene configuration | PASS | Site/node `EDGE`; camera `EDGE vehicles RTSP`; processing `edge`; active classes `["car","truck","bus","motorcycle"]`; RTSP probe from Jetson saw H.264 `2304x1296` at `20/1` fps. |
| Office real RTSP 720p lane | PASS | Jetson ffprobe on redacted `192.168.1.165:8554/ch2` returned H.264 `1280x720` at `20/1` fps. |
| Worker lifecycle/runtime reports | FAIL | Fleet API reports central supervisor healthy and EDGE healthy; EDGE camera worker `runtime_status=running`, selected backend `tensorrt_engine`, artifact `4e849c27-f03e-4ec6-b575-9ba525a8763f`. Central camera is owned by central supervisor but still reports `runtime_status=not_reported`, so the full worker-runtime row is not a PASS. |
| Annotated live browser rendering | NOT RUN | Final pass used real RTSP ffprobe plus API worker/runtime evidence. No final browser screenshot/canvas validation of annotated live output was captured. |
| Deterministic detection/history | PASS | Fresh fixture `closure-20260609182441`; `/api/v1/history` returned one `person` occupancy point at `2026-06-09T18:24:00Z`; history classes returned `person` count `1`. |
| Evidence/Incidents/artifact content | PASS | Incident `3dceaff7-a493-5bd0-b132-b299b9be810e` has one artifact and one ledger entry; scene/privacy/runtime snapshot routes returned 200; artifact content route returned 200, 136 bytes, SHA256 `7dcc3aa9440c77dd485015a2f9a4365fbf918f118a3151fcb9b3e922799592e8`. |
| Real billing usage/invoice/FleetOps billing | PASS | Billing usage contains both `evidence_pack_export` and `managed_edge_node` records for `closure-20260609182441`; invoice run `df371d24-f22c-40cd-bce0-63d3f96b54af` has two line items totaling `5.00` and `25.00`. |
| Master reflector secret distribution | PASS | Edge-agent config fetch used node credential and reflector profile exposed `secret_state` only in normal profile views; raw secret material not printed or committed. |
| Real UDP edge-agent probe | PASS | Packaged install one-shot and service run posted real Jetson-origin samples; latest API sample at `2026-06-09T18:32:54Z` was `20/20`, `0%` loss, `4 ms`, `646.963 Mbps`, payload SHA256 `31dc9ecb7f6bd764a0b00289ce006ac393c46b18b67cb374db9043b80c14ac23`. |
| Core Link master target-only behavior | PASS | Link summary shows `EDGE` and `Vezor Master` healthy using the master reflector target; active connection remains target-only/fallback sample, not a fake active link. |
| Edge-agent installed service packaging | PASS | `/etc/systemd/system/vezor-edge-agent.service` enabled and active; `systemctl is-active vezor-edge.service vezor-edge-agent.service` returned `active`, `active`; service runs wrapper under Docker with node credential file. |
| Backend Docker cache-friendly layer order | PASS | Jetson and master rebuilds reused dependency layers; only source layers rebuilt for source-only changes. |
| Rebuild images from committed branch | PASS | Master backend image `sha256:439b18fd...7185d3`, frontend image `sha256:22df2957...983c9`, Jetson edge image `sha256:491f4e1f...59ee0`; frontend was rebuilt/recreated after final head `5fc19c1f`. |
| Tenant/user/admin management | PASS | API and UI tests verify tenant-admin user management and platform-superadmin tenant/user management; installed API checks confirmed tenant admin users 200, tenant admin tenants 403, platform tenants/users 200. |
| Platform-superadmin bootstrap/sign-in UI | PASS | Frontend `PlatformBootstrap.test.tsx` and full suite verify platform bootstrap form and platform sign-in entry point; installed platform token for `yann.moren@mugetsu.tech` can list tenants and users. |
| FleetOps overview/vessels/evidence/support | PASS | Existing full frontend suite and API smoke cover FleetOps pages, billing, evidence, support, and link views; no new live blocker found in those surfaces. |
| Compose/Helm/deployment posture | NOT RUN | User explicitly excluded the separate Helm/k3s smoke in this pass. Compose posture was exercised by master/edge reinstall; live k3s apply/rollout was not run. |
| External registry publish | NOT RUN | No registry target/credentials were provided. Local master and edge images were rebuilt from committed branch artifacts. |
| Docs consistency | PASS | Closure report updated; no raw secrets, RTSP credentials, bearer tokens, bootstrap tokens, node credentials, sudo passwords, or reflector secrets committed. |

## Confirmed Bugs

- TensorRT artifact completion initially rejected camera-context jobs that produced model-scoped artifacts.
- Python 3.10 edge-agent UDP timeout handling crashed on `asyncio.TimeoutError`.
- Smoke fixture evidence content route returned 404 when evidence was seeded under a subdirectory root.
- Edge-agent systemd restart conflicted with an already-running `vezor-edge-agent` Docker container.
- Frontend App test assumed a single sign-in button after platform sign-in was intentionally added.

## Fixes Implemented

- `backend/src/argus/services/model_lifecycle.py` accepts model-scoped runtime artifacts produced from camera-context TensorRT build jobs.
- `backend/src/argus/link/edge_agent.py` catches Python 3.10 timeout exceptions and keeps probes running.
- `backend/src/argus/scripts/seed_whole_product_smoke_fixture.py` stores reviewable object keys when the evidence root is a configured-storage subdirectory.
- `bin/vezor-edge-agent` removes stale `vezor-edge-agent` containers before systemd restarts the foreground Docker process.
- `frontend/src/App.test.tsx` now expects both tenant sign-in and platform sign-in entry points.

## Remaining Gaps

- Live k3s deployment posture is NOT RUN by user instruction.
- External image publish is NOT RUN because no registry target was supplied.
- Central camera worker runtime report remains `not_reported` while central supervisor/node health is healthy; the EDGE worker runtime path is the one verified with TensorRT.

## Security/Secret Handling

- Raw passwords, sudo passwords, RTSP credentials, bearer tokens, bootstrap tokens, node credentials, and reflector secrets were not committed or recorded in this report.
- Local token files were kept under `/tmp` with mode `0600`.
- RTSP sources are recorded by host/path only, with credentials redacted.

## Commands Run

Representative verification commands:

```bash
backend/.venv/bin/python -m pytest backend/tests/scripts/test_seed_whole_product_smoke_fixture.py -q
installer/.venv/bin/python -m pytest installer/tests/test_edge_installer_artifacts.py -q
corepack pnpm --dir frontend test
git diff --check
docker build -f backend/Dockerfile -t vezor/backend:portable-demo .
docker build -f frontend/Dockerfile -t vezor/frontend:portable-demo frontend
docker compose --env-file /etc/vezor/master.env -f infra/install/compose/compose.master.yml up -d --force-recreate backend vezor-supervisor frontend
ssh ai-user@192.168.1.203 'cd /home/ai-user/vision && git pull --rebase origin codex/sceneops-pack-registry'
ssh ai-user@192.168.1.203 'systemctl is-active vezor-edge.service vezor-edge-agent.service'
```

Live probes and API checks:

```bash
ffprobe redacted CENTRAL 1296p RTSP
ffprobe redacted EDGE 1296p RTSP
ffprobe redacted EDGE 720p RTSP
POST /api/v1/deployment/nodes/{EDGE}/model-sync-jobs
GET /api/v1/deployment/nodes/{EDGE}/model-assignments
GET /api/v1/link/sites/summary
GET /api/v1/operations/fleet
GET /api/v1/history
GET /api/v1/incidents/{incident}/ledger
GET /api/v1/incidents/{incident}/artifacts/{artifact}/content
GET /api/v1/billing/usage
GET /api/v1/billing/invoice-runs/{invoice_run_id}
```

## Screenshots/Logs Captured

- Systemd evidence: `vezor-edge-agent.service` active/running after stale-container fix; Docker process shown in service cgroup.
- Core Link evidence: `20/20` packets, `0%` loss, `646.963 Mbps` throughput at `2026-06-09T18:32:54Z`.
- TensorRT evidence: API runtime artifact and Jetson file SHA256 both `d4130e898ae0937e81aa9e28f2c7ab83e305720c1e0537bb131ac55cb2453c9b`.

## Recommended Next Steps

1. Run the separate Helm/k3s smoke on a reachable k3s cluster.
2. Provide registry target/credentials and publish the rebuilt master/edge images.
3. Decide whether central-supervisor-owned cameras should emit explicit `runtime_status=running`; today central health is healthy but the central camera worker row remains `not_reported`.
