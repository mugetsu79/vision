# Vezor Runbook

See also:

- [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md)
- [operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md)

## Worker Lifecycle, Deployment, And Operations

The Operations workbench currently lives at `/settings` in the frontend. It is
the operator-facing view for fleet state, camera worker ownership, delivery
diagnostics, hardware/model admission, and lifecycle requests.

The first-run deployment workbench lives at `/deployment` in the frontend. It
owns install health, central/edge node rows, service-manager reports, one-time
pairing sessions, credential status, and redacted support bundles.

The final-product deployment path is specified as Band 7.5 in
`docs/superpowers/specs/2026-05-13-installable-supervisor-and-first-run-productization-design.md`
and
`docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md`.
That band establishes the dedicated Control -> Deployment surface, UI-created
node pairing sessions, platform credential storage, and macOS/Linux service
wrappers so normal operation after installation does not require foreground
terminal commands or copied bearer tokens.

The first service-wrapper templates live in `infra/install/`:

- `infra/install/systemd/vezor-supervisor.service` for Linux central and edge
  nodes. It runs as the `vezor` user, restarts on failure, declares state/log
  directories, and references credential material instead of embedding it.
- `infra/install/launchd/com.vezor.supervisor.plist` for macOS pilot nodes and
  future packaged helper registration. It runs the supervisor daemon at load
  and points at a local config file.
- `infra/install/compose/compose.supervisor.yml` for production container or
  appliance-style deployments. It uses a restart policy, a healthcheck, mounted
  config, and mounted credentials.

The backend may render or validate these artifacts, but it must not install,
start, or shell into a node. Installation is a bootstrap responsibility; daily
operation is UI intent plus node-local supervisor reconciliation.

### Node Pairing And Credentials

Normal installed operation uses a node credential store, not a copied bearer
token. Create a pairing session from Control -> Deployment for either a central
supervisor or a specific edge node. The returned pairing code is short-lived and
one-time use. The backend persists only its hash and emits credential material
only in the successful claim response.

The supervisor product config should contain stable identity and local storage
paths, for example:

```json
{
  "supervisor_id": "central-imac-1",
  "role": "central",
  "api_base_url": "https://vezor.example.com",
  "credential_store_path": "/var/lib/vezor/supervisor/credential.json",
  "worker_metrics_url": "http://127.0.0.1:9108/metrics"
}
```

The pairing claim writes the credential to that local store with owner-only
permissions. Service units, launch daemons, and production Compose services
reference the config and credential location; they do not embed access tokens.
Revoking node credentials marks all active credentials for that node as revoked,
records a credential event, and blocks future supervisor
authentication with the old material.

Local development can still start workers from a shell, or run the pilot
supervisor when you want Operations lifecycle buttons to reconcile a direct
child worker process. Use lab guide commands or a break-glass supervisor command
so the token fetch, API URL, database URL, NATS URL, and MinIO settings stay in
sync with the current dev stack. Do not treat those commands as the production
setup path.

Production start, stop, restart, and drain actions must be supervisor-backed. The intended path is: UI action -> backend desired-state or lifecycle request -> central or edge supervisor reconciles the worker process on the correct node -> worker heartbeat/runtime reports truth back to Operations. The API must not become a generic remote shell.

Start and restart also pass through hardware admission. A supervisor reports its
host profile, accelerator/provider availability, and recent p95/p99 performance
samples. The backend records a model-admission decision for the worker. The UI
is an early explanation layer, and the supervisor is the final enforcement gate.
Manual iMac workers are labeled as a production-admission bypass because the
operator starts those processes directly from a shell.

### Deployment Diagnostics And Reboot Checks

Use Control -> Deployment before declaring a node healthy:

1. confirm the central and edge node rows show the expected service manager
   (`systemd`, `launchd`, or production Compose), version, heartbeat, install
   status, and credential status
2. open the node support bundle and confirm it includes service reports,
   lifecycle/runtime summaries, hardware/model-admission summaries, config
   references, selected log excerpts, and diagnostics
3. confirm the bundle redacts bearer tokens, passwords, secrets, pairing codes,
   and credential material
4. reboot the host or restart Docker, then verify the Deployment row receives a
   fresh service report without starting a foreground terminal supervisor

For Linux this validates the enabled `systemd` unit. For macOS this validates
the `launchd` daemon. For production Compose/appliance deployments this
validates the restart policy, healthcheck, mounted config, and mounted
credential directory.

## Production Topology

The supported production shape is not the local Docker Compose dev stack.

Run production as:

- Linux `amd64` master / HQ node
  - frontend
  - FastAPI backend
  - PostgreSQL/TimescaleDB
  - Keycloak
  - Redis
  - NATS JetStream
  - MinIO
  - MediaMTX
  - observability stack
  - central supervisor for central/hybrid workers
- Jetson Orin Nano Super 8 GB edge node where local inference is required
  - edge supervisor
  - inference worker service/container
  - local MediaMTX
  - NATS leaf
  - OTEL collector
- Tailscale or WireGuard between HQ and sites

An iMac can be used as a lab or pilot master, especially with a Jetson edge node, but production should move the master role to Linux with backups, TLS, real OIDC configuration, and supervisor-owned workers.

## Current Production Gaps

Before calling a deployment production-ready, verify that the following are implemented or supplied by the deployment platform:

- durable service wrappers around the Vezor supervisor for central and edge
  workers, such as systemd, launchd, or a production container profile
- UI-managed first-run setup and node pairing through short-lived one-time
  material for every production node
- node-bound supervisor credentials with rotation, revocation, and no long-lived
  bearer tokens embedded in service definitions
- per-worker heartbeat with camera id, status, freshness, restart count, and last error
- regular hardware capability/performance reports from each supervisor
- model-admission checks before production Start or Restart
- persistent assignment/reassignment model or an equivalent supervised placement source
- backup and restore for Postgres/TimescaleDB and incident object storage
- TLS termination and stable DNS
- scoped edge and central supervisor credentials with a rotation path
- log and metric collection from both master and edge nodes
- soak testing for the first site before adding more cameras

The current Operations page should render unknown runtime precision honestly as
`not_reported`, `unknown`, `stale`, or `offline`. Deployment node status should
come from supervisor service reports, not from inference-worker runtime
inference. Do not treat missing heartbeat detail as proof that a worker is
running.

## Supervisor Hardware Admission

The hardware-admission MVP stores two operational facts:

- `edge_node_hardware_reports`: supervisor host profile, memory, CPU,
  accelerator/provider capability, thermal state, and observed model p95/p99
  samples
- `worker_model_admission_reports`: the latest decision for a camera worker,
  including status, rationale, selected backend, and safer recommendation fields

Central supervisors should report with a stable `supervisor_id` and no
`edge_node_id`. Edge supervisors should report with both `supervisor_id` and
the assigned `edge_node_id`. The pilot runner is:

```bash
python3 -m uv run python -m argus.supervisor.runner \
  --supervisor-id central-imac \
  --role central \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN" \
  --worker-metrics-url http://127.0.0.1:9108/metrics
```

For the installed product path, prefer a config file and credential store:

```bash
python3 -m uv run python -m argus.supervisor.runner \
  --config /etc/vezor/supervisor.json
```

For Jetson edge Compose, export `ARGUS_SUPERVISOR_ID`, `ARGUS_EDGE_NODE_ID`,
`ARGUS_API_BASE_URL`, and `ARGUS_API_BEARER_TOKEN`, then start the named
supervisor service:

```bash
docker compose -f infra/docker-compose.edge.yml --profile supervisor \
  up -d --no-build mediamtx nats-leaf otel-collector supervisor
```

Use `--once` on the Python command for deterministic smoke checks. A first
hardware-only report can produce `supported`; after worker metrics include
p95/p99 samples, a matching model should become `recommended` or `degraded`.
Stop the pilot supervisor with `Ctrl-C` for the direct Python command or
`docker compose -f infra/docker-compose.edge.yml stop supervisor` for Jetson.
This MVP owns direct child worker processes only; systemd, Kubernetes, and
external Docker daemon lifecycle adapters are still future production work.
The password grant and static bearer arguments are development or break-glass
authentication modes only; they should not appear in installed service
definitions.

Admission statuses:

| Status | Meaning | Start/Restart |
|---|---|---|
| `recommended` | matching backend is available and recent p95 fits the frame budget | allowed |
| `supported` | matching backend is available but no matching performance sample exists yet | allowed |
| `degraded` | fallback can run but recent p95 exceeds the frame budget | allowed with warning |
| `unsupported` | required backend/artifact/target profile is missing or unsafe | blocked |
| `unknown` | no fresh hardware report exists for the target node/supervisor | blocked |

Model examples:

- macOS CoreML with a fixed-vocab YOLO26n model should be
  `recommended` or `supported` once CoreML is reported.
- Jetson TensorRT should be preferred when a validated artifact matches the
  node profile, and should become `recommended` after p95 fits the stream
  budget.
- CPU/ONNX fallback is acceptable for small fixed-vocab scenes only when p95
  stays inside the budget; otherwise it becomes `degraded`.
- open-world YOLOE on CPU-only hardware at 720p10 or higher should be
  `unsupported`, with a recommendation for a smaller fixed-vocab model or a
  hardware-backed runtime.

## Incident Evidence And Review

The Evidence Desk at `/incidents` reviews incidents that the worker pipeline already captured. It does not create new recordings or run a separate matching engine.

Current behavior:

- incident clips are captured by `IncidentClipCaptureService`
- short event clips are governed by each camera's `recording_policy`
- `clip_url` is retained for compatibility, and artifact rows are now the reviewable evidence record
- `snapshot_url` is supported by API/UI but may be null
- scene contract, privacy manifest, artifact, and ledger context is available from the incident detail view when the worker captured it
- rule-generated incidents include the trigger rule summary when a worker fired
  an enabled per-scene incident rule
- evidence storage, stream delivery, runtime selection, privacy policy, and LLM provider settings are UI-managed configuration profiles after bootstrap
- local, edge-local, MinIO/S3-compatible, cloud, and local-first evidence storage profiles are selectable through Settings and consumed by runtime capture paths
- local-first clips remain reviewable locally while upload sync records pending, available, or failed upload state
- review state is persisted as `pending` or `reviewed`
- operator review/reopen actions write audit entries

If a still preview is required for a deployment, add snapshot generation as a separate feature rather than assuming every incident row has one.

## Incident Rule Authoring And Provenance

Per-worker incident rules define what counts as an incident for one scene
worker. Author and edit them from Control -> Scenes on the scene's Rules
surface. Do not treat Control -> Operations or Intelligence -> Evidence as rule
authoring locations: Operations reports whether workers have loaded the desired
rules, and Evidence reports which rule fired after an incident exists.

The normal operator flow is:

1. Configure the camera source, model, privacy posture, boundaries, calibration,
   recording policy, and storage profile for the scene.
2. In Control -> Scenes, create enabled incident rules with a stable incident
   type, severity, predicate, action, cooldown, and validation sample.
3. Prefer `record_clip` for reviewable evidence. The rule action says the event
   should create reviewable evidence; the camera recording policy and bound
   storage profile still decide which clip/snapshot artifacts are captured and
   whether they live on edge local disk, central MinIO/S3-compatible storage,
   cloud S3-compatible storage, or local-first storage.
4. Use Control -> Operations to confirm active rule count, effective rule hash,
   last rule event, and rule-load status for the worker.
5. Review triggered incidents in Intelligence -> Evidence. Rule-generated
   incidents should show rule name, incident type, severity, action, cooldown,
   rule hash, scene contract hash, and detection context.

Edge and local-first deployments remain reviewable when recording is enabled.
For `edge_local` and `local_first` storage, the central record should still
include the incident, scene/privacy context, artifact metadata, ledger entries,
and trigger rule summary even when clip bytes are retained on the edge node or
waiting for upload.

Prompt-To-Policy may later propose incident rule changes, but those proposals
must remain drafts. Operators must explicitly review and apply rule changes
through the UI/API; prompt workflows must not auto-apply production incident
rules.

## Accountable Scene Evidence And Recording

Accountable evidence starts at camera setup. A production camera should have a
clear source, a saved scene configuration, a privacy posture, and a short event
clip policy before it is treated as operational.

### Edge USB/UVC Camera Sources

Use an edge USB/UVC source when the camera is physically attached to the edge
node or when the site should avoid pulling a raw camera stream back to the
master. Configure the camera source as `usb` with a URI such as
`usb:///dev/video0`, assign the edge node, and keep processing mode on `edge`.
USB/UVC sources are not central-mode sources; the worker that opens the device
must run on the node where the device exists.

For pilots, `/dev/video0` is acceptable when only one capture device is attached.
For production, prefer a stable device reference from `/dev/v4l/by-id/` or
`/dev/v4l/by-path/` and record the mapping in the site deployment notes. Recheck
the mapping after kernel, JetPack, cable, hub, or camera changes.

### Scene Contracts, Privacy Manifests, And Ledger

When a camera configuration is saved, the scene setup can be compiled into an
accountability contract. Incidents can then carry:

- the scene contract snapshot that explains the active source, model scope,
  boundaries, detection regions, speed posture, and recording policy
- the privacy manifest snapshot that explains blur policy and delivery posture
- evidence artifacts such as event clips
- ledger entries for trigger, artifact creation, review, reopen, and operator
  decisions

Treat the ledger as append-only operational evidence. Do not edit historical
ledger rows to "fix" an incident; write a new entry or reopen/review the incident
through the API/UI.

### Evidence Storage Options

Vezor supports three production storage postures for event clips:

| Storage posture | Use when | Operator implication |
|---|---|---|
| Local filesystem | lab, single-node, or edge-local retention | simplest, but backup is the node's responsibility |
| Central MinIO | normal HQ/master deployment | review is central and backups can follow the master object-store policy |
| Remote/cloud S3-compatible | multi-site, managed retention, or off-site backup | configure credentials, bucket policy, lifecycle, and network egress deliberately |

Edge-mode local clips remain reviewable when recording is enabled. If the clip is
`local_only`, the Evidence Desk should show the artifact and ledger context even
when the bytes must be fetched from the edge node or retained there until upload.
Do not mark local-only evidence as missing solely because it is not in central
MinIO.

### Short Event Clip Policy

The default evidence policy is short event clips, not continuous recording:

- recording enabled
- mode `event_clip`
- 4 seconds before the event
- 8 seconds after the event
- 10 FPS evidence capture
- 15 second maximum duration
- central storage unless the camera selects `edge_local`, `cloud`, or
  `local_first`

Increase pre/post windows only when operators need the surrounding context and
the storage budget supports it. For privacy-sensitive edge sites, use
`edge_local` or `local_first` deliberately and document retention, backup, and
review access before go-live.

### LLM Provider Configuration

LLM provider selection is UI-managed after bootstrap. Configure provider,
model, optional base URL, and the `api_key` secret in Settings -> Configuration
under `LLM provider`; do not rely on command-line environment overrides for
operator-facing prompt workflows once profiles are present.

Browser configuration responses expose only secret presence, never plaintext
API keys. Prompt workflows resolve the selected tenant/site/edge/camera profile
inside the backend service path and fail closed before sending a request when a
profile requires an API key that has not been stored.

### Development Migration Notes

The accountable evidence, configuration, runtime passport, per-worker incident
rule runway, supervisor hardware admission runway, and installable supervisor
data contract now migrate through Alembic head. The installable-supervisor
tables include deployment nodes, supervisor service reports, pairing sessions,
node credentials, credential audit events, and pairing hostname support.

After pulling the current development branch, refresh the dev database with:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run alembic upgrade head
```

If the Docker dev stack is running and the host environment cannot connect to
Postgres directly, run the same upgrade inside the backend container:

```bash
cd /Users/yann.moren/vision
docker compose -f infra/docker-compose.dev.yml exec backend \
  uv run alembic upgrade head
```

## Secrets With SOPS And Age

Vezor stores operational secrets under `/Users/yann.moren/vision/infra/secrets/` as encrypted `*.enc.yaml`, `*.enc.json`, or `*.enc.env` files. The repository is configured for SOPS + age through `/Users/yann.moren/vision/.sops.yaml`.

Before the first production deployment:

1. Generate an age keypair on an operator workstation: `age-keygen -o ~/.config/sops/age/keys.txt`.
2. Replace the bootstrap recipient in `/Users/yann.moren/vision/.sops.yaml` with the real team recipient or recipients.
3. Export `SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt`.
4. Create encrypted secret material with `sops infra/secrets/<name>.enc.yaml`.

Recommended secret sets:

- central platform secrets: database password, MinIO credentials, RTSP encryption key, MediaMTX JWT key
- auth secrets: Keycloak admin bootstrap secret and confidential client secrets
- edge secrets: edge node API keys, NATS credentials, remote bootstrap tokens

## Secret Rotation Procedure

Use this sequence when rotating any production secret set:

1. Generate a fresh age recipient and update `/Users/yann.moren/vision/.sops.yaml`.
2. Re-encrypt every tracked secret file with `sops updatekeys infra/secrets/*.enc.yaml`.
3. Rotate the live runtime secret in the backing service first:
   - Postgres user password
   - MinIO root credentials
   - Keycloak client secrets
   - `ARGUS_RTSP_ENCRYPTION_KEY`
   - MediaMTX JWT signing key
   - edge API keys or NATS credentials
4. Roll the central workloads, verify `/healthz`, `/metrics`, login, and stream authorization.
5. Roll edge workers after central verification succeeds.
6. Revoke the previous secret material and remove the old age private key from operator workstations.

## Jetson Orin Nano Super 8 GB Bootstrap

Before starting the edge stack on Jetson Orin Nano Super 8 GB, enable the 25 W Super mode:

```bash
sudo nvpmodel -m 2 && sudo jetson_clocks
```

Then run the local preflight:

```bash
/Users/yann.moren/vision/scripts/jetson-preflight.sh
```

The preflight checks JetPack/L4T compatibility, CUDA 12.6, TensorRT 10.x, NVDEC availability, the expected lack of NVENC on Orin Nano, Docker, Docker Compose v2, NVIDIA Container Toolkit, FFmpeg/FFprobe, and the GStreamer RTSP/H264 elements used by the host diagnostics and worker fallback path.

### Edge Image Runtime

The current edge Compose path is Jetson-specific:

- `infra/docker-compose.edge.yml` builds `backend/Dockerfile.edge`
- that image uses the Jetson base image's system Python 3.10 virtualenv
- the Python 3.10 runtime is intentional because the accelerated Jetson ONNX Runtime wheels available for this lab are `cp310`
- `JETSON_ORT_WHEEL_URL` is passed as a build argument and should point to the Jetson accelerated `onnxruntime-gpu` wheel when testing CUDA/TensorRT providers
- if `JETSON_ORT_WHEEL_URL` is unset, the image falls back to CPU ONNX Runtime and `CPUExecutionProvider` remains expected
- processed annotated/reduced profiles publish through FFmpeg/libx264 on Orin Nano because the device has NVDEC but no NVENC

For the current JetPack 6 / Python 3.10 lab path:

```bash
export JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"
```

The central/backend image remains Python 3.12. There is no separate generic
non-Jetson edge image still using Python 3.12 in the current Compose stack. For
non-Jetson edge hardware, treat the product role as portable but the packaging
as not yet hardened: run a host worker from the central/backend Python 3.12
environment for lab experiments, or create a hardware-specific edge image before
production use.

## Edge Bring-Up

For a single-node edge deployment:

1. Place the edge model weights under `/Users/yann.moren/vision/models/`.
2. Export the required HQ bootstrap values:
   - `ARGUS_API_BASE_URL`
   - `ARGUS_API_BEARER_TOKEN` or supervisor-provisioned edge credential
   - `ARGUS_DB_URL`
   - `ARGUS_NATS_URL`
   - `ARGUS_MINIO_ENDPOINT`
   - `ARGUS_EDGE_CAMERA_ID`
3. If validating Jetson acceleration, export `JETSON_ORT_WHEEL_URL` before building the image:
   `export JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"`
4. From the same shell, run `docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml config` to verify Compose can see the required variables.
5. Start the stack with `docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml up -d --build`.
6. Confirm MediaMTX, OTEL Collector, the worker metrics endpoint, and the Operations workbench state are reachable.

Docker Compose interpolates the full service definition even for build-only
commands such as `docker compose ... build inference-worker`. If you are doing a
long first image build with a short-lived dev token, export all stable runtime
values plus a temporary build-only token first:

```bash
export ARGUS_API_BASE_URL="http://<master-ip>:8000"
export ARGUS_API_BEARER_TOKEN="build-only-token"
export ARGUS_DB_URL="postgresql+asyncpg://argus:argus@<master-ip>:5432/argus"
export ARGUS_NATS_URL="nats://<master-ip>:4222"
export ARGUS_MINIO_ENDPOINT="<master-ip>:9000"
export ARGUS_EDGE_CAMERA_ID="<camera-id>"
```

After the build finishes, replace `ARGUS_API_BEARER_TOKEN` with a fresh real
token before running `docker compose ... config`, `up`, or the worker itself.

Before starting processed-stream tests, verify the edge image has the expected
runtime pieces:

```bash
docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint /app/.venv/bin/python inference-worker \
  -c "import sys, onnxruntime as ort; print(sys.version); print(ort.__version__); print(ort.get_available_providers())"

docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint /bin/sh inference-worker \
  -lc 'ffmpeg -hide_banner -encoders | grep -q libx264'
```

Python should report `3.10.x`. CPU-only ONNX Runtime providers mean the image
was built without `JETSON_ORT_WHEEL_URL`. The FFmpeg encoder check should exit
successfully; if it fails, the edge image cannot publish processed annotated or
reduced streams.

This Compose path is appropriate for lab and pilot bring-up. In the current iMac + Jetson lab, set `ARGUS_NATS_URL` directly to the master NATS listener, for example `nats://192.168.1.20:4222`. In production, the same edge responsibilities should be run under a supervisor so they restart after reboot, report per-worker status, and can receive constrained lifecycle requests from the control plane. The NATS leaf topology remains the intended hardened production shape once bootstrap and credentials are supervisor-managed.

## Model Metadata And Scope

For a step-by-step checklist that covers every supported catalog model, primary
model registration, scene configuration, and runtime artifact loading, see
`docs/model-loading-and-configuration-guide.md`.

`/Users/yann.moren/vision/models/` is only where local model files live; it does not define semantic class scope by itself. In local Docker development, the backend bind-mounts this checkout's `models/` path so registration-time ONNX validation can read the same absolute host path that host-side workers use later. When an ONNX model exposes embedded class metadata, treat that as the source of truth for registration and runtime inventory. Use `Camera.active_classes` only to narrow the operational scope. Custom reduced-class models remain an advanced optional path.

### Model Catalog And Open-Vocab Runtime

`/api/v1/model-catalog` lists recommended local model presets. It does not download model files and does not replace registered `Model` rows. A camera can only select models that are registered in `/api/v1/models`. Use `backend/scripts/register_model_preset.py` when an operator has a catalog artifact on disk and wants to create the matching `Model` row without hand-writing JSON.

Fixed-vocab ONNX models use ONNX Runtime. Provider selection can choose TensorRT, CUDA, OpenVINO, CoreML, or CPU depending on host support.

Open-vocab models use the Ultralytics adapter and are marked experimental until validated on the target central GPU and Jetson runtime. The supported first-pass formats are `.pt` model files for YOLOE and YOLO-World. Dynamic `.pt` open vocab remains the discovery and fallback mode for changing vocabularies.

Raw TensorRT `.engine` files must not be registered as primary camera models. Keep ONNX as the canonical fixed-vocab model row, attach target-specific validated TensorRT engines as runtime artifacts, and use scene-scoped compiled open-vocab artifacts only when the saved vocabulary hash matches. The runtime artifact lane is implemented; the next active implementation stage is accountable scene intelligence and evidence recording.

### Fixed-Vocab Runtime Artifact Registration

Keep the registered fixed-vocab model row pointed at the canonical ONNX file. When a Jetson TensorRT engine has already been built and copied into place, register it as a runtime artifact instead of registering the `.engine` as a model:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.build_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN" \
  --model-id "$MODEL_ID" \
  --source-model /Users/yann.moren/vision/models/yolo26n.onnx \
  --prebuilt-engine /Users/yann.moren/vision/models/yolo26n.jetson.fp16.engine \
  --target-profile linux-aarch64-nvidia-jetson \
  --class person --class car --class bus --class truck \
  --input-width 640 --input-height 640
```

Validate the artifact on the target host before expecting workers to select it:

```bash
python3 -m uv run python -m argus.scripts.validate_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN" \
  --model-id "$MODEL_ID" \
  --artifact-id "$ARTIFACT_ID" \
  --artifact-path /Users/yann.moren/vision/models/yolo26n.jetson.fp16.engine \
  --expected-sha256 "$ARTIFACT_SHA256" \
  --target-profile linux-aarch64-nvidia-jetson \
  --host-profile linux-aarch64-nvidia-jetson
```

The first-pass builder intentionally supports prebuilt engines only. Do not let the control plane guess TensorRT builder flags silently; record the artifact after the target-specific build is already produced.

### Open-Vocab Scene Runtime Artifact Compilation

Dynamic `.pt` open-vocab remains the exploration path while operators tune a
camera vocabulary. Once the scene vocabulary is saved for a production scene,
compile scene-scoped YOLOE artifacts from the canonical `.pt` model and register
the exported files against the camera. Compilation is a background/operator
operation, not something the request path should block on. Real build time is
captured per artifact in `build_duration_seconds`.

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.build_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN" \
  --model-id "$OPEN_VOCAB_MODEL_ID" \
  --camera-id "$CAMERA_ID" \
  --open-vocab-source-pt /Users/yann.moren/vision/models/yoloe-26n-seg.pt \
  --runtime-vocabulary person,chair,backpack \
  --vocabulary-version "$RUNTIME_VOCAB_VERSION" \
  --export-format onnx \
  --export-format engine \
  --target-profile linux-aarch64-nvidia-jetson \
  --input-width 640 --input-height 640
```

The script normalizes the comma-separated vocabulary, calls
`YOLOE.set_classes(...)` before export, records the resulting vocabulary hash on
both scene artifacts, and records per-export build duration. Validate each
exported artifact on the host that will run it before expecting worker runtime
selection to choose it. If the camera runtime vocabulary changes, workers must
fall back to the dynamic `.pt` model until a new scene artifact with the new
vocabulary hash is built and validated.

When the worker starts, verify the runtime selection log before comparing
performance:

- `selected_backend=tensorrt_engine` and `fallback=False` means the validated
  engine was selected.
- `fallback=True` means the worker continued with the canonical model runtime.
  Common reasons are `no_runtime_artifacts`, `artifact_target_mismatch`, and
  `artifact_vocabulary_mismatch`.
- A stale artifact should not be treated as valid after the source ONNX model
  changes; rebuild or re-register the artifact from the new source model.

For fixed-vocab Jetson comparisons, collect the same metrics window before and
after artifact selection:

```bash
curl -s http://127.0.0.1:9108/metrics |
  grep -E 'argus_inference_frame_duration_seconds|argus_inference_stage_duration_seconds|argus_inference_frames_processed_total'
```

Compare steady-state frame duration, stage duration, and sustained processed
frames with the same camera, scene, `fps_cap`, and delivery profile.

### A/B Runtime Artifact Validation Checklist

Use the same camera, scene, `fps_cap`, browser delivery profile, and metrics
window for every row:

| Lane | Expected selection evidence |
|---|---|
| Fixed-vocab ONNX baseline | canonical `onnxruntime` selection, no valid artifact |
| Fixed-vocab TensorRT artifact | `selected_backend=tensorrt_engine`, `fallback=False` |
| Open-vocab dynamic `.pt` | canonical `ultralytics_yoloe` selection |
| Open-vocab compiled ONNX | `selected_backend=onnxruntime`, artifact id present |
| Open-vocab compiled TensorRT | `selected_backend=tensorrt_engine`, artifact id present |
| Vocabulary change fallback | `fallback_reason=vocabulary_changed`, dynamic `.pt` continues |

Operations shows model runtime artifact counts and the best valid target. The
Cameras setup flow shows whether the selected model has a compiled artifact,
whether it is stale for the current vocabulary, or whether the worker will use
the dynamic/fallback runtime.

### Scene Vision Profiles

Cameras now carry a persisted `vision_profile` and optional `detection_regions`. These fields control profile posture, compute tier, explicit speed metric enablement, and detection include/exclusion gating before tracking. If an existing dev database errors with `column cameras.vision_profile does not exist` or `column cameras.detection_regions does not exist`, run:

```bash
docker compose -f /Users/yann.moren/vision/infra/docker-compose.dev.yml exec backend \
  uv run alembic upgrade head
```

See `docs/scene-vision-profile-configuration-guide.md` for operator guidance.

## Authentication Alternative

Keycloak is the default IdP. If an operator standardizes on Authentik instead, keep the same OIDC contract at the SPA and API layers, update the issuer and JWKS configuration, and record the deployment-specific divergence in a new ADR before rollout.
