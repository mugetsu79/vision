# Fleet Operations Workbench Design

> **Status:** Phase 1 implemented; supervisor lifecycle controls remain follow-on work
>
> **Date:** 2026-04-28
>
> **Goal:** Replace the placeholder Settings page with an operator-grade Fleet and Operations workbench that explains worker lifecycle, camera assignment, bootstrap, and delivery diagnostics across local development and production.

---

## 1. Context

The handoff document identified Fleet / Operations as the next remaining product hardening track after boundary setup, source-aware browser delivery, native routing, and History workbench work. Phase 1 has now landed under the `/settings` route as the Fleet and operations workbench.

The current product has real worker building blocks, but their lifecycle is still developer-oriented:

- local iMac testing starts one worker per camera with `python -m argus.inference.engine --camera-id ...`
- edge development has `infra/docker-compose.edge.yml`, which runs one `inference-worker` container for one camera
- Helm has an `edge-worker` deployment with one configured camera id
- `backend/src/argus/inference/scheduler.py` can spawn per-camera workers from database camera state, but it is not exposed as a product contract
- the Settings route has been replaced by a Fleet and operations workbench
- edge registration and heartbeat exist; Phase 1 exposes assignment and node health, while true per-worker runtime reports remain follow-on supervisor work

Phase 1 makes the mental model visible, but lifecycle control is still intentionally limited. It shows who owns a worker, how to run local dev workers, what runtime state is currently reported, and where production should use a supervisor instead of backend shell execution.

The current product now also has the Evidence Desk review queue and open-vocab control-plane foundation. That makes Operations more important: detector capability and review workflows are meaningful only when workers are placed, started, restarted, and observed honestly across central and edge nodes.

---

## 2. Product Position

The Operations UI should not directly start or stop OS processes.

The product should separate:

- **desired state**: what the control plane wants to be running
- **runtime state**: what supervisors and workers report as actually running
- **operator actions**: safe requests that change desired state or ask a supervisor to act
- **developer commands**: local/manual commands used only for dev and troubleshooting

In production, a supervisor owns process lifecycle. The UI owns visibility, desired state, bootstrap, and safe lifecycle requests.

### Start/Stop Button Model

The product should eventually have Start, Stop, Restart, and Drain controls in the Operations UI, but those controls must target a supervisor contract, not a raw shell command.

The intended flow is:

```text
UI lifecycle button
  -> backend authorizes and records desired state or lifecycle request
  -> central or edge supervisor reconciles that request on the correct node
  -> worker reports heartbeat, status, metrics, and last error
  -> UI renders desired state versus actual runtime state
```

The backend API process should not directly shell out to start host workers. That would couple the product to the backend container host, bypass the node that actually owns the worker, and create a dangerous remote-command-execution surface. It also would not survive backend restarts, browser refreshes, process crashes, machine reboot, or multi-node edge placement.

Local development is different because there is not yet a local supervisor process. In dev, copyable shell commands are an honest bridge: the developer owns the terminal process and can interrupt it with `Ctrl-C`. Production should not rely on that manual path. Production should run a central or edge supervisor that owns process start/stop/restart and reports truth back to the control plane.

---

## 3. Terms

### Camera Worker

A camera worker is a process running `argus.inference.engine --camera-id <id>`. It pulls worker config from the backend, reads the camera or relay stream, runs inference, emits telemetry, and publishes live media when configured.

### Supervisor

A supervisor is the local process manager on a central or edge node. It may be:

- a Python scheduler process
- `systemd`
- Docker Compose
- Kubernetes
- a future Argus edge agent

The supervisor starts, stops, restarts, and monitors worker processes. The browser UI does not shell into hosts.

### Desired State

Desired state is the backend's answer to: "Which camera workers should exist?"

Phase 1 derives desired state from existing camera configuration:

- central cameras with no `edge_node_id` want a central worker
- hybrid cameras want a central worker unless later assigned to an edge node for local processing
- edge cameras with an `edge_node_id` want a worker on that edge node
- inactive or disabled processing states want no worker

Phase 1 does not add a `worker_assignments` table. That table can be added once the UI supports real reassignment workflows.

### Runtime State

Runtime state is the reported truth from supervisors and workers:

- node heartbeat timestamp
- node version
- reported camera count
- running worker camera ids
- failed worker camera ids
- restart counts
- last error summary

Phase 1 uses the existing `EdgeNode.last_seen_at` and heartbeat camera count, then defines contracts that can grow to per-worker detail.

---

## 4. Dev Versus Production

### Local Development

In local development:

- Docker starts platform services, not per-camera workers.
- The developer manually starts workers in terminal tabs.
- Stop means `Ctrl-C`.
- The Operations page should show copyable dev run commands for central cameras.
- The page should label this mode as **Manual dev mode**.

Example command:

```bash
TOKEN="$(
  curl -fsS \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

cd "${ARGUS_REPO_DIR:-$HOME/vision}/backend" && \
ARGUS_API_BASE_URL="http://127.0.0.1:8000" \
ARGUS_API_BEARER_TOKEN="$TOKEN" \
python3 -m uv run python -m argus.inference.engine --camera-id "replace-with-camera-id"
```

### Edge Development

In edge development:

- `infra/docker-compose.edge.yml` starts one worker container for one configured camera.
- Stop and restart happen through Docker Compose.
- The Operations page should show the equivalent compose command and required environment variables.

Example command:

```bash
TOKEN="$(
  curl -fsS \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

ARGUS_EDGE_CAMERA_ID="${ARGUS_EDGE_CAMERA_ID:-replace-with-camera-id}" \
ARGUS_API_BASE_URL="${ARGUS_API_BASE_URL:-http://host.docker.internal:8000}" \
ARGUS_API_BEARER_TOKEN="$TOKEN" \
docker compose -f infra/docker-compose.edge.yml up inference-worker
```

### Production

In production:

- a central supervisor runs on the master node for central/hybrid cameras
- an edge supervisor runs on each edge node for edge-assigned cameras
- supervisors reconcile desired state to runtime state
- workers restart automatically after crashes
- disabling or reassigning a camera changes desired state, and the supervisor stops or starts workers accordingly
- restart requests are delivered to the supervisor as lifecycle commands

The Operations UI should show this distinction directly. Operators should never have to infer whether a camera is unmanaged, manually managed, or supervisor-managed.

Production deployment shape:

```text
Operator browser
  -> HTTPS / OIDC
  -> Linux master / HQ
       frontend, API, Postgres/Timescale, Keycloak, Redis, NATS,
       MinIO, MediaMTX, observability, central supervisor
  -> Tailscale or WireGuard
  -> Jetson Orin edge node
       edge supervisor, inference worker(s), local MediaMTX,
       NATS leaf, OTEL collector
  -> site cameras
```

The iMac + Jetson setup is a lab/pilot topology for validating this shape. It should not be described as the production master deployment.

---

## 5. Phase 1 Scope

Phase 1 is a read-first Operations workbench with safe bootstrap support.

It includes:

1. Fleet overview
2. Desired worker list
3. Runtime status summary
4. Camera assignment view
5. Delivery diagnostics
6. Edge bootstrap material generation
7. Dev/manual run command hints

It does not include:

- direct process start/stop from the browser
- Kubernetes or Compose mutation from the backend
- a persistent `worker_assignments` table
- secret rotation automation
- live log streaming
- node draining
- camera reassignment mutation
- production-grade per-worker heartbeat and last-error reporting

These are intentionally deferred until the status model is trustworthy.

---

## 6. Backend Contract

Add an operations API under `/api/v1/operations`.

### GET `/api/v1/operations/fleet`

Returns one tenant-scoped overview:

```json
{
  "mode": "manual_dev",
  "generated_at": "2026-04-28T07:00:00Z",
  "summary": {
    "desired_workers": 2,
    "running_workers": 1,
    "stale_nodes": 1,
    "offline_nodes": 0,
    "native_unavailable_cameras": 1
  },
  "nodes": [],
  "camera_workers": [],
  "delivery_diagnostics": []
}
```

`mode` values:

- `manual_dev`
- `supervised`
- `mixed`

Phase 1 may derive `mode` from settings and available runtime reports. If no supervisor reports exist, use `manual_dev`.

### POST `/api/v1/operations/bootstrap`

Creates edge bootstrap material through the existing edge registration path.

The response includes:

- edge node id
- one-time API key
- NATS seed
- MediaMTX hints
- copyable edge compose command
- copyable production supervisor command or environment block

Plaintext secret material must be returned only in this response.

---

## 7. Backend Read Model

The operations service should aggregate existing data:

- `sites`
- `edge_nodes`
- `cameras`
- `camera.browser_delivery`
- `camera.source_capability`
- `camera.processing_mode`
- `camera.edge_node_id`
- `edge_nodes.last_seen_at`

Desired worker state:

- `desired`: backend expects a worker for the camera
- `not_desired`: no worker should run
- `manual`: worker is expected to be launched manually in dev mode
- `supervised`: worker is expected to be reconciled by a supervisor

Runtime status:

- `running`
- `stale`
- `offline`
- `unknown`
- `not_reported`

Phase 1 cannot know per-camera runtime truth for manually launched workers unless they report it. The UI should state that clearly.

---

## 8. Delivery Diagnostics

The Operations page should include a delivery diagnostics table so the same page answers native delivery questions.

For each camera, show:

- camera name
- processing mode
- assigned node or central
- source width/height/fps/codec when known
- browser default profile
- available profiles
- native available/unavailable
- native reason
- whether native resolves to passthrough or processed access

This reuses the source-aware fields already added to camera responses. It should not probe RTSP again.

---

## 9. UI Design

The route remains `/settings`, but the page title is **Fleet and operations** and the navigation labels the route as **Operations**.

The page should make the operational purpose clear while preserving the existing route for compatibility.

Page sections:

1. **Fleet Summary**
   - desired workers
   - running or reported workers
   - stale nodes
   - native unavailable cameras

2. **Worker Lifecycle**
   - explains current mode: manual dev, supervised, or mixed
   - shows who owns start/stop
   - shows copyable dev commands when in manual mode

3. **Nodes**
   - central node row
   - edge node rows
   - last seen
   - version
   - assigned cameras
   - status badge

4. **Camera Workers**
   - camera
   - desired location
   - desired state
   - runtime status
   - command hint or supervisor owner

5. **Delivery Diagnostics**
   - source capability and browser delivery truth
   - native unavailable reason

6. **Bootstrap Edge Node**
   - site selector
   - hostname
   - version
   - generate material
   - one-time secret warning

The page should use dense operational layout, not a marketing hero. It should favor tables, badges, command blocks, and compact explanatory copy.

---

## 10. Operator Actions

Phase 1 actions:

- generate edge bootstrap material
- copy manual central worker command with local dev token fetch
- copy edge compose command
- refresh fleet overview

Future actions:

- restart worker
- disable processing
- enable processing
- reassign camera
- drain edge node
- rotate edge bootstrap credentials

Future actions should be explicit requests to a supervisor or desired-state change. They should not execute shell commands from the API process.

---

## 11. Security

Operations endpoints require admin access.

Bootstrap responses contain one-time secret material and should:

- be omitted from logs
- not be persisted in plaintext
- show warning copy in the UI
- require deliberate operator action

Runtime diagnostic fields must not expose RTSP passwords, JWTs, API keys, or NATS seeds.

Copyable commands should use placeholders for secrets unless the command is generated immediately after bootstrap and is shown once.

Local development commands may include the seeded local-dev token fetch for `admin-dev` because those credentials are already documented for local-only use. Production commands should not embed operator passwords or long-lived secrets.

---

## 12. Testing

Backend tests:

- route registration for `/api/v1/operations/fleet`
- admin authorization
- tenant scoping
- desired worker derivation for central, hybrid, edge, and disabled cameras
- edge heartbeat status mapping
- delivery diagnostics serialization
- bootstrap wraps existing edge registration

Frontend tests:

- placeholder Settings copy is removed
- fleet summary renders
- manual dev mode explains copyable commands
- stale/offline badges render
- delivery diagnostics render native unavailable reasons
- bootstrap success shows one-time secret warning and generated command

Manual validation:

- local dev stack with no workers shows manual dev mode
- adding a central camera shows copyable central worker command
- an edge node heartbeat changes node status from offline/stale to healthy
- native-unavailable camera shows the reason already visible on Live/Cameras pages

---

## 13. Acceptance Criteria

The work is complete when:

- `/settings` no longer shows placeholder copy
- operators can see desired worker state versus runtime state
- the page explicitly explains manual dev versus supervised production lifecycle
- central and edge cameras show the correct lifecycle owner
- edge bootstrap material can be generated from the UI
- native delivery diagnostics are visible without opening each camera
- no endpoint leaks plaintext credentials outside one-time bootstrap responses
- backend and frontend tests cover the lifecycle distinction

---

## 14. Follow-On Work

After Phase 1:

1. Add supervisor heartbeat with per-worker runtime state.
2. Add lifecycle command topics for restart and drain.
3. Add explicit worker assignment persistence.
4. Add camera reassignment UI.
5. Add live logs and recent failure summaries.
6. Add edge credential rotation.
7. Add production deployment validation for Linux master plus Jetson edge, including reboot recovery and multi-day soak.
