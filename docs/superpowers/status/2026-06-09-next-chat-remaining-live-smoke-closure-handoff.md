# Remaining Whole-Product Live Smoke Closure Handoff

Date: 2026-06-09
Current branch: `codex/sceneops-pack-registry`
Current pushed head: `79112d02`

## Purpose

The next chat should close the remaining whole-product live smoke gaps from the
2026-06-09 MacBook installed-stack validation. This is a validation-plus-fix
handoff: start by proving the current behavior on a fresh stack and real Jetson,
then implement narrow fixes only where a confirmed blocker prevents the smoke
from continuing.

The required outcome is a new whole-product smoke report that distinguishes
`PASS`, `FAIL`, `BLOCKED`, and `NOT RUN`. Do not call missing Jetson access,
missing model files, missing RTSP, missing reflector secret access, missing
billing usage, missing deterministic evidence, or missing fresh-stack proof a
pass.

## Read First

Read these before touching the stack:

1. `docs/superpowers/specs/2026-06-09-remaining-live-smoke-closure-design.md`
2. `docs/superpowers/plans/2026-06-09-remaining-live-smoke-closure-implementation-plan.md`
3. `docs/superpowers/status/2026-06-09-whole-product-live-smoke-report.md`
4. `docs/superpowers/status/2026-06-08-next-chat-whole-product-live-smoke-handoff.md`
5. `docs/superpowers/status/2026-06-07-next-chat-core-link-reflector-completion-handoff.md`
6. `docs/superpowers/plans/2026-06-08-central-model-edge-artifact-management-plan.md`
7. `docs/superpowers/specs/2026-06-08-central-model-edge-artifact-management-spec.md`
8. `docs/superpowers/plans/2026-06-08-protected-control-plane-and-model-ui-plan.md`
9. `docs/model-loading-and-configuration-guide.md`
10. `docs/core-link-performance-guide.md`
11. `docs/product-installer-and-first-run-guide.md`
12. `docs/operator-deployment-playbook.md`
13. `docs/runbook.md`
14. `README.md`

If code changes are needed, use Superpowers:

- `superpowers:systematic-debugging` for any unexpected live behavior.
- `superpowers:test-driven-development` before fixing blockers.
- `superpowers:verification-before-completion` before claiming pass, committing,
  or pushing.
- `superpowers:requesting-code-review` before finalizing a substantial fix set.

## Branch And Worktree State

Start here:

```bash
cd /Users/yann.moren/vision
git fetch origin codex/sceneops-pack-registry
git status --short --branch
git rev-parse --short HEAD
git rev-list --left-right --count origin/codex/sceneops-pack-registry...HEAD
```

Expected: branch `codex/sceneops-pack-registry` at or after `79112d02`, with
`0 0` ahead/behind unless a newer commit has landed. Pull/rebase before work if
the branch is behind.

This workspace has unrelated untracked local files and folders such as
`.claude/`, `.codex/`, `.playwright-*`, `.superpowers/brainstorm/...`,
screenshots, strategy drafts, `output/`, and `taste-skill/`. Do not stage them.
Use explicit `git add -- path ...` if a fix is committed. Do not use
`git add -A`.

## Secrets And Safety

Do not write raw admin passwords, sudo passwords, bearer tokens, bootstrap
tokens, RTSP credentials, node credentials, or reflector secrets into docs,
reports, git commits, terminal transcripts, screenshots, or shell history.

Use local environment variables or temporary files outside git for secrets:

```bash
export VEZOR_API_URL="http://MASTER_LAN_IP:8000"
export VEZOR_FRONTEND_URL="http://MASTER_LAN_IP:3000"
export VEZOR_ADMIN_EMAIL="..."
export VEZOR_ADMIN_PASSWORD="..."
export VEZOR_RTSP_720P_URL="rtsp://...@192.168.1.165:8554/ch2"
export VEZOR_RTSP_1296P_URL="rtsp://...@192.168.1.165:8554/ch1"
export ARGUS_LINK_REFLECTOR_SECRET="..."
```

If a required secret is unavailable, record `BLOCKED` with the missing secret
class, not the secret value.

Known lab addresses from the last smoke:

- MacBook master LAN IP used last time: `192.168.1.166`
- Jetson/camera host IP: `192.168.1.165`
- Office RTSP 720p lane: redacted as `rtsp://[redacted]@192.168.1.165:8554/ch2`
- Office RTSP 1296p lane: redacted as `rtsp://[redacted]@192.168.1.165:8554/ch1`

Ask the user for fresh credentials if needed. Do not copy credentials from chat
history into committed files.

## Current Known State

Commit `79112d02` fixed the smoke blockers found during the previous run:

- installed model catalog paths such as `models/yolo26n.onnx` now resolve to the
  installed `/models` mount.
- fixed-vocab catalog entries with empty declared classes can use embedded ONNX
  class metadata.
- model sync job creation flushes before assignment FK updates.
- master installers generate `/etc/vezor/secrets/central_supervisor_credential`,
  mirror it into `/var/lib/vezor/credentials/supervisor.credential`, and
  first-run registers only the hash.

The previous live smoke was strong but not complete:

- Fresh first-run was validated before the central credential fix.
- The current stack then needed a one-time credential repair.
- Office RTSP live native and annotated playback passed on the central
  supervisor.
- Real Jetson supervisor/API sync and inventory were blocked.
- Deterministic incident/evidence/history generation was missing.
- Real billing usage generation was not exercised.
- TensorRT engine build from the UI was not live-built on Jetson.
- Master reflector existed but had `secret_state=missing`; no real UDP
  edge-agent probe ran.

The next run must prove these remaining points on a fresh post-fix stack.

## Targeted Fresh Destructive Reset

The purpose of this reset is to prove that the central supervisor credential fix
works from scratch. Preserve model files, but remove installed DB/config/secret
state so the installer and first-run regenerate it. Do not run global Docker
prune. Do not delete unrelated Docker resources. Do not delete
`/var/lib/vezor/models`.

Inventory first:

```bash
cd /Users/yann.moren/vision
docker compose ls
docker ps -a --format 'table {{.Names}}\t{{.Label "com.docker.compose.project"}}\t{{.Status}}\t{{.Ports}}' \
  | grep -E 'vezor|argus|validation|infra|backend|frontend|keycloak' || true
docker volume ls --format 'table {{.Name}}\t{{.Label "com.docker.compose.project"}}' \
  | grep -E 'vezor|argus|validation|infra' || true
sudo find /var/lib/vezor/models -maxdepth 1 -type f -name 'yolo26*.onnx' -ls 2>/dev/null || true
```

Stop service wrappers and known Compose projects:

```bash
sudo launchctl bootout system/com.vezor.master 2>/dev/null || true
sudo systemctl stop vezor-master.service 2>/dev/null || true
docker compose -f infra/docker-compose.dev.yml down -v --remove-orphans || true
docker compose -p vezor-live-validation \
  -f infra/install/compose/compose.master.yml \
  down -v --remove-orphans || true
docker compose -p vezor-master \
  -f infra/install/compose/compose.master.yml \
  down -v --remove-orphans || true
```

Remove leftover Vezor validation containers and volumes by exact project labels
and Vezor naming patterns:

```bash
for project in infra vezor-live-validation vezor-master; do
  for container_id in $(docker ps -aq --filter "label=com.docker.compose.project=$project"); do
    docker rm -f "$container_id"
  done
  for volume_name in $(docker volume ls -q --filter "label=com.docker.compose.project=$project"); do
    docker volume rm "$volume_name"
  done
done

docker ps -a --format '{{.ID}} {{.Names}}' | grep -E 'vezor|argus|validation' || true
for container_id in $(
  docker ps -a --format '{{.ID}} {{.Names}}' | awk '/vezor|argus|validation/ {print $1}'
); do
  docker rm -f "$container_id"
done

docker volume ls --format '{{.Name}}' | grep -E 'vezor|argus|validation|^infra_' || true
for volume_name in $(
  docker volume ls --format '{{.Name}}' | awk '/vezor|argus|validation|^infra_/ {print $1}'
); do
  docker volume rm "$volume_name"
done
```

Remove installed master state except bundled models:

```bash
sudo rm -rf /etc/vezor
sudo find /var/lib/vezor -mindepth 1 -maxdepth 1 \
  ! -name models \
  -exec rm -rf {} +
sudo install -d -m 0755 /var/lib/vezor/models
sudo find /var/lib/vezor/models -maxdepth 1 -type f -name 'yolo26*.onnx' -ls
```

Verify reset before reinstall:

```bash
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' \
  | grep -E 'vezor|argus|validation|infra|backend|frontend|keycloak' || true
docker volume ls --format 'table {{.Name}}\t{{.Label "com.docker.compose.project"}}' \
  | grep -E 'vezor|argus|validation|infra' || true
sudo test -f /etc/vezor/secrets/central_supervisor_credential && echo "unexpected old central credential" || true
sudo find /var/lib/vezor/models -maxdepth 1 -type f -name 'yolo26*.onnx' -ls
```

Expected: no Vezor validation containers/volumes remain, no old
`/etc/vezor/secrets/central_supervisor_credential` remains, and the YOLO26 model
files are still present.

## Fresh Install And First-Run Proof

Install master using the MacBook LAN IP, not localhost:

```bash
MASTER_IP="$(ipconfig getifaddr en0 || ipconfig getifaddr en1)"
sudo ./bin/vezor install master --public-url "http://${MASTER_IP}:3000"
curl -fsS "http://${MASTER_IP}:8000/healthz"
```

Generate first-run bootstrap token from the master host only:

```bash
./bin/vezor ctl bootstrap-master \
  --api-url "http://${MASTER_IP}:8000" \
  --rotate-local-token \
  --json
```

Complete first-run in the UI and then validate:

```bash
sudo test -s /etc/vezor/secrets/central_supervisor_credential
sudo test -s /var/lib/vezor/credentials/supervisor.credential
sudo cmp -s /etc/vezor/secrets/central_supervisor_credential \
  /var/lib/vezor/credentials/supervisor.credential
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
sudo docker logs --tail 200 vezor-master-supervisor 2>/dev/null || true
```

Acceptance:

- first-run completes without manual credential repair.
- bootstrap status returns `first_run_required=false`.
- central deployment node has `credential_status=active`.
- central supervisor posts service reports and runtime reports using the
  generated credential.
- `GET /api/v1/models` and `GET /api/v1/model-catalog` show bundled YOLO26n and
  YOLO26s as registered/available with real artifacts.

If the central supervisor cannot authenticate after a fresh reset, record the
evidence, write a failing backend/installer regression test, fix narrowly, and
verify before continuing.

## Real Jetson Supervisor/API Sync And Inventory

This must use the real Jetson, not an emulated node.

1. Confirm the Jetson is reachable:

```bash
ping -c 3 192.168.1.165
nc -vz 192.168.1.165 8554
```

2. If SSH or the edge installer requires credentials, ask the user. Do not
   store them in docs.
3. In the master UI or API, create a deployment pairing session for the Jetson.
4. Run the edge installer on the Jetson with the master API URL, session id, and
   pairing code:

```bash
sudo ./bin/vezor install edge \
  --api-url "http://MASTER_LAN_IP:8000" \
  --session-id "SESSION_ID" \
  --pairing-code "PAIRING_CODE"
```

5. Validate supervisor/API:

```bash
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/deployment/nodes"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/deployment/nodes/${JETSON_NODE_ID}/support-bundle"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/deployment/nodes/${JETSON_NODE_ID}/model-inventory"
```

6. Assign YOLO26n and YOLO26s to the Jetson and start model sync:

```bash
curl -fsS -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d '{"model_id":"YOLO26N_MODEL_ID","target_path":"/var/lib/vezor/models/yolo26n.onnx"}' \
  "${VEZOR_API_URL}/api/v1/deployment/nodes/${JETSON_NODE_ID}/model-assignments"
curl -fsS -X POST -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/deployment/nodes/${JETSON_NODE_ID}/model-sync-jobs"
```

Primary APIs to inspect:

- `GET /api/v1/deployment/nodes`
- `GET /api/v1/deployment/nodes/{node_id}/support-bundle`
- `GET /api/v1/deployment/nodes/{node_id}/model-assignments`
- `POST /api/v1/deployment/nodes/{node_id}/model-sync-jobs`
- `GET /api/v1/deployment/nodes/{node_id}/model-inventory`
- supervisor routes:
  - `POST /api/v1/deployment/supervisors/{supervisor_id}/model-jobs/poll`
  - `POST /api/v1/deployment/supervisors/{supervisor_id}/model-jobs/{job_id}/events`
  - `POST /api/v1/deployment/supervisors/{supervisor_id}/model-jobs/{job_id}/complete`
  - `POST /api/v1/deployment/supervisors/{supervisor_id}/model-inventory`

Acceptance:

- real Jetson node is paired with an active credential.
- Jetson supervisor service reports are current.
- model sync jobs are claimed and completed by the Jetson supervisor.
- `model-inventory` contains the synced YOLO26n and YOLO26s with matching
  SHA-256/size/path.
- support bundle includes Jetson hardware/runtime reports and model inventory.

## TensorRT Engine Build On Jetson

Use the central UI/API job path first. Only use manual `trtexec` commands when
debugging the Jetson runtime or when the UI/API path is blocked.

Preflight on the Jetson:

```bash
nvidia-smi 2>/dev/null || true
tegrastats --interval 1000 --count 1 2>/dev/null || true
which trtexec || true
trtexec --version || true
ls -lh /var/lib/vezor/models/yolo26n.onnx /var/lib/vezor/models/yolo26s.onnx
```

Create the build job from Models -> Runtime artifacts, or via:

```bash
curl -fsS -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d '{
    "deployment_node_id":"JETSON_NODE_ID",
    "build_format":"tensorrt_engine",
    "target_profile":"linux-aarch64-nvidia-jetson",
    "precision":"fp16",
    "input_shape":{"batch":1,"channels":3,"height":640,"width":640}
  }' \
  "${VEZOR_API_URL}/api/v1/models/${YOLO26N_MODEL_ID}/runtime-artifact-build-jobs"
```

Primary files and tests if blocked:

- `backend/src/argus/supervisor/model_jobs.py`
- `backend/src/argus/supervisor/operations_client.py`
- `backend/src/argus/vision/runtime_artifact_builder.py`
- `backend/tests/supervisor/test_artifact_build_jobs.py`
- `backend/tests/services/test_runtime_artifact_build_jobs.py`

Acceptance:

- Jetson supervisor claims an `artifact_build` job.
- TensorRT build runs on the Jetson, not the MacBook.
- `GET /api/v1/models/{model_id}/runtime-artifacts` shows a valid
  `tensorrt_engine` artifact with target profile
  `linux-aarch64-nvidia-jetson`.
- support bundle/runtime admission reports show TensorRT artifact readiness.
- camera runtime selection prefers the TensorRT artifact when assigned to the
  Jetson and falls back honestly when unavailable.

## Office Scene And Real RTSP

Use a physical/operator site such as `Office`; keep `Vezor Master` protected as
the control-plane target.

Acceptance:

- Office scene is attached to an edge/operator site, not to the control-plane
  `Vezor Master` site.
- Office camera uses the redacted real RTSP source.
- 720p lane probes as `1280x720` and only exposes compatible Live renditions.
- Native mode is available and plays.
- Annotated mode plays when the worker is running.
- Live, History, Incidents/Evidence, Deployment support bundle, FleetOps, and
  Links all show the same site/camera/node relationships.

## Deterministic Detection/Evidence/History Fixture

The previous run could not pass Evidence/Incidents because no deterministic
event was generated. Build or use a fixture that creates a known event on the
fresh stack.

First inspect:

- `scripts/validation/whole_product_live_smoke.py`
- `backend/tests/scripts/test_whole_product_live_smoke.py`
- `backend/src/argus/models/tables.py` for `TrackingEvent`, `Incident`, and
  `EvidenceArtifact`
- `backend/src/argus/services/incident_capture.py`
- `backend/src/argus/services/app.py` `HistoryService` and `IncidentService`
- `backend/tests/services/test_incident_capture.py`
- `backend/tests/services/test_incident_service.py`
- `backend/tests/services/test_history_service.py`

The current smoke script is only a skeleton. If no live fixture exists, add one
behind an explicit command or flag, with tests first. It should create all of:

- one deterministic `tracking_events` row for the Office camera and a known
  class such as `person`.
- one deterministic incident tied to the camera/site/tenant.
- one evidence artifact or intentionally small local fixture clip/snapshot whose
  content endpoint works.
- scene-contract, privacy-manifest, runtime-passport, and ledger rows when the
  product expects them for incident review.
- one History datapoint visible through `/api/v1/history` and
  `/api/v1/history/series`.

Acceptance:

- `GET /api/v1/history` and `/api/v1/history/series` are non-empty for the
  Office camera.
- `GET /api/v1/incidents` returns the deterministic incident.
- incident detail endpoints work:
  - `/api/v1/incidents/{incident_id}/scene-contract`
  - `/api/v1/incidents/{incident_id}/privacy-manifest`
  - `/api/v1/incidents/{incident_id}/runtime-passport`
  - `/api/v1/incidents/{incident_id}/ledger`
  - `/api/v1/incidents/{incident_id}/artifacts/{artifact_id}/content`
- Evidence/Incidents UI loads and can review the incident.

## Real Billing Usage Generation

The previous stack had empty billing nodes/accounts/usage. The next run must
generate real product usage, not just mock UI data.

Use the existing billing APIs:

- `POST /api/v1/billing/nodes`
- `POST /api/v1/billing/accounts`
- `POST /api/v1/billing/entitlements`
- `POST /api/v1/billing/price-books`
- `POST /api/v1/billing/usage`
- `POST /api/v1/billing/invoice-runs`
- `GET /api/v1/billing/usage`
- `GET /api/v1/billing/invoice-runs`
- FleetOps views: `/fleetops`, `/fleetops/evidence`, `/fleetops/billing`

Recommended smoke usage records:

- `evidence_pack_export`, quantity `1`, source object id = deterministic
  incident or evidence export id.
- `managed_edge_node`, quantity `1`, source object id = Jetson deployment node.
- `managed_link_gb`, quantity based on a small controlled probe value if Core
  Link sample metadata records bytes; otherwise record a clearly labeled
  deterministic fixture usage with source object id = link probe id.

Acceptance:

- billing node, account, entitlement, price book, usage, and invoice run are
  tenant-scoped and retrievable.
- FleetOps billing page shows non-empty current usage and invoice run.
- final report distinguishes real product-generated usage from any temporary
  deterministic fixture usage.

## Master Reflector Secret Distribution And Real UDP Edge-Agent Probe

The previous smoke stopped at `secret_state=missing`. The next run must prove a
real authenticated UDP sequence probe from an edge source to the master
reflector.

Important: this may require a product fix. Existing docs say paired edge-agent
secret distribution is still an open hardening gap. If it is not implemented,
write the failing regression test first, implement the smallest safe
distribution path, and verify.

Relevant files:

- `backend/src/argus/link/api.py`
- `backend/src/argus/link/edge_agent.py`
- `backend/src/argus/link/reflector.py`
- `backend/src/argus/link/reflector_profiles.py`
- `backend/src/argus/link/udp_sequence.py`
- `backend/tests/link/test_reflector.py`
- `backend/tests/link/test_edge_agent.py`
- `docs/core-link-performance-guide.md`
- `docs/runbook.md`

Relevant APIs:

- `GET /api/v1/link/reflectors/master`
- `POST /api/v1/link/reflectors/master/rotate-key`
- `POST /api/v1/link/reflectors/master/enable`
- `POST /api/v1/link/sites/{site_id}/control-targets/master`
- `POST /api/v1/link/sites/{site_id}/probe-targets/{target_id}/edge-samples`
- `GET /api/v1/link/sites/{site_id}/probes`
- `GET /api/v1/link/sites/summary`

Basic manual shape, with secrets supplied only through env:

```bash
curl -fsS -X POST -H "Authorization: Bearer ${TOKEN}" \
  "${VEZOR_API_URL}/api/v1/link/reflectors/master/rotate-key"

curl -fsS -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d '{"public_address":"MASTER_LAN_IP","bind_address":"0.0.0.0","udp_port":8622,"allowed_source_cidrs":["192.168.1.0/24"],"rate_limit_pps_per_source":100}' \
  "${VEZOR_API_URL}/api/v1/link/reflectors/master/enable"

curl -fsS -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d '{"mode":"udp_reflector","address":"MASTER_LAN_IP","packet_count":20,"packet_spacing_ms":100,"loss_timeout_ms":1000}' \
  "${VEZOR_API_URL}/api/v1/link/sites/${OFFICE_SITE_ID}/control-targets/master"

python3 -m argus.link.edge_agent \
  --api-base-url "${VEZOR_API_URL}" \
  --bearer-token "${TOKEN}" \
  --site-id "${OFFICE_SITE_ID}" \
  --target-id "${MASTER_UDP_TARGET_ID}" \
  --target "MASTER_LAN_IP" \
  --method udp_sequence \
  --reflector "MASTER_LAN_IP" \
  --reflector-port 8622 \
  --reflector-key-id "${ARGUS_LINK_REFLECTOR_KEY_ID}" \
  --reflector-secret "${ARGUS_LINK_REFLECTOR_SECRET}" \
  --packet-count 20 \
  --once
```

Acceptance:

- master reflector profile has `enabled=true` and `secret_state=present`.
- backend binds UDP port `8622` and logs no reflector startup error.
- edge-agent UDP sequence run posts an edge sample with
  `method=udp_sequence`.
- Link Performance shows source-side packet counts, loss, RTT metadata, and
  target site linkage.
- Vezor Master remains target-only: it can receive probes but cannot be edited
  like a normal edge site.

## Validation Commands

Run focused tests for any code changed, then at minimum:

```bash
python3 -m uv run --project backend pytest \
  backend/tests/services/test_deployment_nodes.py \
  backend/tests/services/test_model_catalog.py \
  backend/tests/services/test_model_lifecycle_imports.py \
  backend/tests/services/test_supervisor_model_jobs.py \
  backend/tests/services/test_deployment_model_inventory.py \
  backend/tests/services/test_runtime_artifact_build_jobs.py \
  backend/tests/services/test_edge_configuration_assignments.py \
  backend/tests/supervisor/test_model_jobs.py \
  backend/tests/supervisor/test_artifact_build_jobs.py \
  backend/tests/link/test_reflector.py \
  backend/tests/link/test_edge_agent.py \
  backend/tests/scripts/test_whole_product_live_smoke.py \
  backend/tests/api/test_billing_routes.py \
  backend/tests/e2e/test_maritime_fleetops_smoke.py \
  -q

python3 -m uv run --project backend ruff check backend/src backend/tests scripts/validation
installer/.venv/bin/python -m pytest installer/tests/test_macos_master_artifacts.py installer/tests/test_linux_master_artifacts.py installer/tests/test_edge_installer_artifacts.py -q
npm --prefix frontend run test -- Live.test.tsx Models.test.tsx Deployment.test.tsx Cameras.test.tsx Links.test.tsx FleetOps.test.tsx FleetOpsBilling.test.tsx Incidents.test.tsx
git diff --check
```

Also run product validation when installer/deployment files changed:

```bash
make verify-installers
```

## Final Smoke Report Template

Write the final report to:

```text
docs/superpowers/status/YYYY-MM-DD-whole-product-live-smoke-closure-report.md
```

Use this structure:

```markdown
# Whole-Product Live Smoke Closure Report

Date:
Branch/head:
Stack type:
Master URL:
Jetson:
RTSP/source used: redacted
Fresh destructive reset proof:

## Summary

## Pass/Fail Matrix

| Area | Status | Evidence |
|---|---|---|
| Fresh destructive reset after central credential fix | PASS/FAIL/BLOCKED/NOT RUN | |
| First-run/auth/tenant claims | PASS/FAIL/BLOCKED/NOT RUN | |
| Central supervisor credential binding | PASS/FAIL/BLOCKED/NOT RUN | |
| Real Jetson supervisor/API | PASS/FAIL/BLOCKED/NOT RUN | |
| Jetson model sync and inventory | PASS/FAIL/BLOCKED/NOT RUN | |
| TensorRT engine build on Jetson | PASS/FAIL/BLOCKED/NOT RUN | |
| Office real RTSP native and annotated live | PASS/FAIL/BLOCKED/NOT RUN | |
| Worker lifecycle/runtime reports | PASS/FAIL/BLOCKED/NOT RUN | |
| Deterministic detection/history | PASS/FAIL/BLOCKED/NOT RUN | |
| Evidence/Incidents/artifact content | PASS/FAIL/BLOCKED/NOT RUN | |
| Real billing usage/invoice/FleetOps billing | PASS/FAIL/BLOCKED/NOT RUN | |
| Master reflector secret distribution | PASS/FAIL/BLOCKED/NOT RUN | |
| Real UDP edge-agent probe | PASS/FAIL/BLOCKED/NOT RUN | |
| Core Link master target-only behavior | PASS/FAIL/BLOCKED/NOT RUN | |
| FleetOps overview/vessels/evidence/support | PASS/FAIL/BLOCKED/NOT RUN | |
| Compose/Helm/deployment posture | PASS/FAIL/BLOCKED/NOT RUN | |
| Docs consistency | PASS/FAIL/BLOCKED/NOT RUN | |

## Confirmed Bugs

## Fixes Implemented

## Remaining Gaps

## Security/Secret Handling

## Commands Run

## Screenshots/Logs Captured

## Recommended Next Steps
```

## Commit And Push Rules

If code changes are needed:

1. document the live evidence for the blocker first.
2. write a failing regression test.
3. fix narrowly.
4. rerun focused tests and smoke validation.
5. ask before committing/pushing unless the user explicitly requests it.

When staging, use explicit paths only. Keep raw credentials and local scratch
files out of git.
