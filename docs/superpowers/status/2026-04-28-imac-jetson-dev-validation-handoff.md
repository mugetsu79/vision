# iMac And Jetson Dev Validation Handoff

Date: 2026-04-28

Purpose: paste this document into a fresh project chat to continue from the current repo state and validate the full development stack first on the iMac, then with the iMac as temporary master and Jetson Orin Nano as edge node.

## Current Branch State

Active branch:
- `codex/source-aware-delivery-calibration-fixes`

Remote checkpoint:
- `origin/codex/source-aware-delivery-calibration-fixes` is pushed through:
  - `aee8e52 docs(deployment): clarify production topology and status`
  - `e4a7331 fix(incidents): tighten review audit and permission feedback`
  - `eb130bb test(incidents): harden evidence desk e2e assertions`

Current local repo note:
- before this handoff was created, the branch matched origin and only pre-existing untracked scratch files were present
- do not stage `.superpowers/brainstorm/*`, screenshot PNGs, or `camera-capture.md` unless explicitly requested

To update the iMac checkout:

```bash
cd "$HOME/vision"
git fetch origin
git switch codex/source-aware-delivery-calibration-fixes
git pull --rebase origin codex/source-aware-delivery-calibration-fixes
git log --oneline -5
```

Expected recent history includes:

- `aee8e52 docs(deployment): clarify production topology and status`
- `e4a7331 fix(incidents): tighten review audit and permission feedback`
- `eb130bb test(incidents): harden evidence desk e2e assertions`

## Do Not Re-Plan Completed Work

These are already implemented and documented on the branch:

- Operations phase 1 at `/settings`
- Settings relabeled as Operations in navigation
- source-aware browser delivery and native delivery diagnostics
- setup preview and normalized boundary authoring
- History follow-now, zero/gap semantics, search, speed-aware series, and exports
- open-vocab control-plane foundation:
  - detector capability metadata
  - camera runtime vocabulary state
  - vocabulary snapshot attribution
  - capability-aware query commands
  - detector factory/interface split
  - Camera/Live UI plumbing
- Evidence Desk Task 8:
  - `/incidents` queue/evidence/facts layout
  - pending/reviewed persisted review state
  - Review/Reopen actions
  - clip-only evidence handling
  - same-transaction audit logging for review changes
- long-lived docs now explain dev, iMac+Jetson pilot, and Linux-master production topology

## Product Reality To Preserve

- The iMac + Jetson flow is lab/pilot validation, not the final production master topology.
- Production should be Linux `amd64` master plus supervisor-managed central and Jetson edge workers.
- Local dev worker commands are a bridge because there is no local supervisor yet.
- Operations must show unknown runtime truth honestly as `not_reported`, `unknown`, `stale`, or `offline`; do not invent `running`.
- Evidence Desk reviews incidents already captured by the worker pipeline. It does not start a new recording or snapshot capture flow.
- Current incident evidence is primarily `clip_url`; `snapshot_url` can be null and should render as clip-only evidence.
- Open-vocab support is currently a control-plane/runtime-vocabulary foundation. A true open-vocabulary model backend still needs target-runtime validation.

## Latest Verification Already Run

Evidence Desk / Task 8 verification before push:

- `python3 -m uv run pytest tests/models/test_schema.py tests/api/test_prompt9_routes.py tests/services/test_incident_service.py tests/services/test_incident_capture.py -q`
  - `20 passed`
- backend `ruff` targeted check
  - passed
- backend `mypy` targeted check
  - passed
- `corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx`
  - `3 passed`
- `corepack pnpm --dir frontend build`
  - passed
- `corepack pnpm --dir frontend exec playwright test e2e/prompt9-history-and-incidents.spec.ts`
  - `4 passed`

Documentation sync verification:

- `git diff --check`
  - passed before commit `aee8e52`
- targeted stale-language search over active docs
  - passed

Known warnings:
- backend tests may warn about `/run/secrets`; this is expected in local dev unless the test explicitly fails
- full frontend lint had older unrelated issues in previous handoff context; do not treat those as part of iMac/Jetson validation unless the user asks to pay down lint debt

## Primary Next Goal

Validate the full development stack in two phases:

1. **Phase A: iMac-only dev validation**
   - iMac runs the control plane
   - both cameras run as `central`
   - workers are started from Operations copyable commands
2. **Phase B: iMac master + Jetson Orin edge validation**
   - iMac remains temporary master
   - camera 1 remains `central` on the iMac
   - camera 2 moves to the Jetson as `edge`
   - validate Live, History, Operations, and Evidence Desk across the split

Use the lab guide as the operational source of truth:

- `docs/imac-master-orin-lab-test-guide.md`
- `docs/operator-deployment-playbook.md`
- `docs/runbook.md`
- `docs/deployment-modes-and-matrix.md`

## Phase A: iMac-Only Dev Validation

### 1. Prepare And Start The Stack

From the iMac:

```bash
cd "$HOME/vision"
make dev-up
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend frontend
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
until curl -fsS http://127.0.0.1:8000/healthz; do
  echo "waiting for backend health..."
  sleep 2
done
corepack pnpm --dir frontend generate:api
```

Open:

- `http://127.0.0.1:3000`
- `http://127.0.0.1:3000/settings`
- `http://127.0.0.1:8000/healthz`
- `http://127.0.0.1:8080`
- `http://127.0.0.1:9001`

If browser assets look stale, hard refresh with `Cmd+Shift+R`.

### 2. Validate Operations First

At `/settings`, verify:

- navigation label says Operations
- fleet summary loads
- manual dev mode is explained
- desired camera worker cards render
- delivery diagnostics render
- copyable central worker commands include a token fetch
- copied command sets `ARGUS_API_BEARER_TOKEN="$TOKEN"`
- no bearer-token placeholder is emitted literally
- node/worker status stays truthful when no worker is running

### 3. Prepare Model And Cameras

Follow the lab guide sections for:

- placing `models/yolo12n.onnx`
- computing model SHA and size
- registering `YOLO12n COCO iMac`
- creating `Lab Site`
- creating `Lab Camera 1`
- creating `Lab Camera 2`

Recommended camera settings:

- processing mode: `central`
- active classes: `person`, `car`, `bus`, `truck`, `motorcycle`, `bicycle`
- tracker: `botsort`
- browser delivery profile: `720p10`
- calibration: 4 source points, 4 destination points, reference distance `10`

### 4. Start Two iMac Workers

Preferred path:

1. Open `/settings`.
2. Copy the worker command for `Lab Camera 1`.
3. Run it in a terminal tab.
4. Copy the worker command for `Lab Camera 2`.
5. Run it in a second terminal tab.

If host-side worker dependencies are missing, run:

```bash
cd "$HOME/vision/backend"
python3 -m uv sync --group runtime --group dev --group llm --group vision
```

Good worker signs:

- no immediate crash
- no `401` / `403`
- no missing-model-path error
- worker keeps running
- reconnect logs are transient, not endless

### 5. Validate Product Pages

Validate:

- **Live**
  - both camera tiles appear
  - telemetry eventually becomes live or explains its pending/stale state
  - video delivery profile is truthful for the camera source
- **History**
  - event data appears after workers run
  - zero/gap behavior is understandable
  - filters and exports still work
- **Incidents / Evidence Desk**
  - Queue, evidence area, and Incident facts panel render
  - if no incidents exist yet, this is not a failure until a rule/event triggers
  - when an incident exists, `Open clip` works if clip storage succeeded
  - clip-only evidence state appears when `snapshot_url` is null
  - Review moves an incident out of Pending
  - Reviewed filter shows reviewed incidents
  - Reopen returns an incident to Pending
- **Operations**
  - status changes remain truthful after workers are running
  - missing per-worker precision is shown honestly

### 6. Run Validation

Run:

```bash
cd "$HOME/vision"
make verify-all
```

Notes:

- the validation wrapper may stop the Docker frontend so Playwright can bind port `3000`
- if the frontend remains stopped after validation, restart it with:

```bash
docker compose -f infra/docker-compose.dev.yml up -d frontend
```

Phase A passes when:

- iMac stack is healthy
- both central workers stay up
- Live shows both cameras
- History receives data
- Evidence Desk behaves correctly when incident evidence exists
- Operations worker commands and runtime state are truthful
- `make verify-all` passes or any failure is understood and documented

## Phase B: iMac Master + Jetson Orin Edge Validation

### 1. Preconditions

Required:

- iMac stack from Phase A remains running
- Jetson and iMac are on the same LAN
- Jetson can reach iMac ports:
  - `8000` backend
  - `8080` Keycloak
  - `5432` Postgres
  - `7422` NATS leaf upstream
  - `9000` MinIO
- `models/yolo12n.onnx` exists on the Jetson checkout
- iMac worker for camera 2 is stopped before moving that camera to the Jetson

### 2. Prepare Jetson

On the Jetson:

```bash
sudo nvpmodel -m 2 && sudo jetson_clocks
cd "$HOME/vision"
./scripts/jetson-preflight.sh
```

Good signs:

- JetPack/CUDA/TensorRT checks pass
- Docker and `nvidia-container-toolkit` checks pass
- NVDEC is present
- NVENC is absent, which is expected on Orin Nano

### 3. Register Jetson Model Record

On the iMac, register a second model record for the Jetson container path:

- name: `YOLO12n COCO Edge`
- path: `/models/yolo12n.onnx`
- format: `onnx`
- same SHA and size as the iMac model file

Use `docs/imac-master-orin-lab-test-guide.md` section 3.3 for the full command.

### 4. Move Camera 2 To Edge

In the Vezor UI:

- edit `Lab Camera 2`
- set processing mode to `edge`
- set primary model to `YOLO12n COCO Edge`
- keep active classes and browser profile consistent with Phase A

If the UI exposes edge-node assignment, assign camera 2 to the Jetson node. If assignment is not available or per-worker status is still incomplete, use `ARGUS_EDGE_CAMERA_ID` in the Jetson edge stack and expect Operations to represent missing precision honestly.

### 5. Start Jetson Edge Stack

On the Jetson, generate a fresh token against the iMac Keycloak, export the iMac IP values, and start edge compose:

```bash
cd "$HOME/vision"
export ARGUS_API_BASE_URL="http://$IMAC_IP:8000"
export ARGUS_API_BEARER_TOKEN="$JETSON_TOKEN"
export ARGUS_DB_URL="postgresql+asyncpg://argus:argus@$IMAC_IP:5432/argus"
export ARGUS_MINIO_ENDPOINT="$IMAC_IP:9000"
export ARGUS_MINIO_ACCESS_KEY="argus"
export ARGUS_MINIO_SECRET_KEY="argus-dev-secret"
export ARGUS_EDGE_CAMERA_ID="$CAMERA_TWO_ID"
docker compose -f infra/docker-compose.edge.yml up -d --build
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

If NATS leaf config still points at `host.docker.internal`, update `infra/nats/leaf.conf` to use the iMac IP and port `7422`.

Good signs:

- no `401` / `403`
- no missing `/models/yolo12n.onnx`
- container keeps running
- worker metrics respond on `http://127.0.0.1:9108/metrics`

### 6. Validate Split Operation

On the iMac:

- **Live**
  - camera 1 remains online from iMac central worker
  - camera 2 returns online from Jetson edge worker
- **History**
  - detections from camera 2 persist after the Jetson worker runs
- **Incidents / Evidence Desk**
  - edge-generated incident evidence appears when a rule/event triggers
  - pending/reviewed state still works
- **Operations**
  - Jetson node appears when heartbeat/bootstrap path is active
  - camera 2 shows edge ownership or the current honest unknown/not-reported state
  - status does not invent per-worker truth

Phase B passes when:

- iMac control plane remains healthy
- camera 1 works in `central`
- camera 2 works from Jetson in `edge`
- Live, History, Operations, and Evidence Desk behave across the split
- Jetson worker metrics/logs are available
- any remaining per-worker status limitations are documented as product gaps, not treated as hidden success

## Troubleshooting Notes

If worker exits immediately:

- refresh token
- verify camera id
- verify model path:
  - iMac model path is the full host path under `$HOME/vision/models`
  - Jetson model path is `/models/yolo12n.onnx`
- verify RTSP URL is reachable

If model registration fails with missing table:

```bash
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
```

If frontend types change after `generate:api`:

- inspect `frontend/src/lib/api.generated.ts`
- commit only if it is an expected OpenAPI regeneration from the current backend

If Evidence Desk has no incidents:

- let workers run longer
- verify rules/events are configured
- create a scene that triggers the relevant event
- absence of incidents is not a page failure unless the worker should have captured an event

## Known Follow-Up Work After Validation

Production hardening still needs:

- supervisor-backed Start/Stop/Restart/Drain in Operations
- per-worker heartbeat/status/restart-count/last-error reporting
- persistent worker assignment and reassignment UI
- edge credential rotation
- production Linux master deployment validation
- multi-day soak for Linux master plus Jetson edge
- true open-vocabulary detector backend validation on central and Jetson runtimes
- incident still snapshot generation if still previews become required evidence

## Useful Files For The Next Chat

Docs:

- `README.md`
- `product-spec-v4.md`
- `docs/imac-master-orin-lab-test-guide.md`
- `docs/operator-deployment-playbook.md`
- `docs/deployment-modes-and-matrix.md`
- `docs/runbook.md`
- `docs/superpowers/specs/2026-04-28-fleet-operations-workbench-design.md`
- `docs/superpowers/specs/2026-04-28-evidence-desk-review-queue-design.md`
- `docs/superpowers/specs/2026-04-26-open-vocab-hybrid-detector-design.md`

Backend:

- `backend/src/argus/api/v1/operations.py`
- `backend/src/argus/api/v1/incidents.py`
- `backend/src/argus/api/v1/edge.py`
- `backend/src/argus/services/app.py`
- `backend/src/argus/services/incident_capture.py`
- `backend/src/argus/inference/engine.py`
- `backend/src/argus/vision/detector_factory.py`
- `backend/src/argus/vision/open_vocab_detector.py`
- `backend/src/argus/models/tables.py`
- `backend/src/argus/models/enums.py`
- `backend/src/argus/migrations/versions/0006_open_vocab_hybrid_detector.py`
- `backend/src/argus/migrations/versions/0007_incident_review_state.py`

Frontend:

- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/Incidents.tsx`
- `frontend/src/pages/Live.tsx`
- `frontend/src/pages/History.tsx`
- `frontend/src/hooks/use-operations.ts`
- `frontend/src/hooks/use-incidents.ts`
- `frontend/src/components/cameras/CameraWizard.tsx`
- `frontend/src/components/live/AgentInput.tsx`
- `frontend/src/lib/api.generated.ts`

Infra:

- `infra/docker-compose.dev.yml`
- `infra/docker-compose.edge.yml`
- `infra/nats/leaf.conf`
- `infra/mediamtx/mediamtx.yml`
- `scripts/jetson-preflight.sh`
