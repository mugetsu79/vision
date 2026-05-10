# Vezor Runbook

See also:

- [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md)
- [operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md)

## Worker Lifecycle And Operations

The Operations workbench currently lives at `/settings` in the frontend. It is the operator-facing view for fleet state, camera worker ownership, delivery diagnostics, edge bootstrap material, and copyable local-dev worker commands.

Local development can still start workers from a shell because there is no local supervisor process yet. Use the Operations copy button or the lab guide commands so the token fetch, API URL, database URL, NATS URL, and MinIO settings stay in sync with the current dev stack.

Production start, stop, restart, and drain actions must be supervisor-backed. The intended path is: UI action -> backend desired-state or lifecycle request -> central or edge supervisor reconciles the worker process on the correct node -> worker heartbeat/runtime reports truth back to Operations. The API must not become a generic remote shell.

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

- supervisor-backed Start/Stop/Restart/Drain for central and edge workers
- per-worker heartbeat with camera id, status, freshness, restart count, and last error
- persistent assignment/reassignment model or an equivalent supervised placement source
- backup and restore for Postgres/TimescaleDB and incident object storage
- TLS termination and stable DNS
- scoped edge credentials with a rotation path
- log and metric collection from both master and edge nodes
- soak testing for the first site before adding more cameras

The current Operations page should render unknown runtime precision honestly as `not_reported`, `unknown`, `stale`, or `offline`. Do not treat missing heartbeat detail as proof that a worker is running.

## Incident Evidence And Review

The Evidence Desk at `/incidents` reviews incidents that the worker pipeline already captured. It does not create new recordings or run a separate matching engine.

Current behavior:

- incident clips are captured by `IncidentClipCaptureService`
- `clip_url` is the primary evidence artifact today
- `snapshot_url` is supported by API/UI but may be null
- review state is persisted as `pending` or `reviewed`
- operator review/reopen actions write audit entries

If a still preview is required for a deployment, add snapshot generation as a separate feature rather than assuming every incident row has one.

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

`/Users/yann.moren/vision/models/` is only where local model files live; it does not define semantic class scope by itself. In local Docker development, the backend bind-mounts this checkout's `models/` path so registration-time ONNX validation can read the same absolute host path that host-side workers use later. When an ONNX model exposes embedded class metadata, treat that as the source of truth for registration and runtime inventory. Use `Camera.active_classes` only to narrow the operational scope. Custom reduced-class models remain an advanced optional path.

### Model Catalog And Open-Vocab Runtime

`/api/v1/model-catalog` lists recommended local model presets. It does not download model files and does not replace registered `Model` rows. A camera can only select models that are registered in `/api/v1/models`. Use `backend/scripts/register_model_preset.py` when an operator has a catalog artifact on disk and wants to create the matching `Model` row without hand-writing JSON.

Fixed-vocab ONNX models use ONNX Runtime. Provider selection can choose TensorRT, CUDA, OpenVINO, CoreML, or CPU depending on host support.

Open-vocab models use the Ultralytics adapter and are marked experimental until validated on the target central GPU and Jetson runtime. The supported first-pass formats are `.pt` model files for YOLOE and YOLO-World. Dynamic `.pt` open vocab remains the discovery and fallback mode for changing vocabularies.

Raw TensorRT `.engine` files are cataloged as planned only and must not be registered as primary camera models. The current continuation plan is `docs/superpowers/plans/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-implementation-plan.md`: keep ONNX as the canonical fixed-vocab model row, attach target-specific validated TensorRT engines as runtime artifacts, and add scene-scoped compiled open-vocab artifacts that are selected only when the saved vocabulary hash matches.

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

### Scene Vision Profiles

Cameras now carry a persisted `vision_profile` and optional `detection_regions`. These fields control profile posture, compute tier, explicit speed metric enablement, and detection include/exclusion gating before tracking. If an existing dev database errors with `column cameras.vision_profile does not exist` or `column cameras.detection_regions does not exist`, run:

```bash
docker compose -f /Users/yann.moren/vision/infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
```

See `docs/scene-vision-profile-configuration-guide.md` for operator guidance.

## Authentication Alternative

Keycloak is the default IdP. If an operator standardizes on Authentik instead, keep the same OIDC contract at the SPA and API layers, update the issuer and JWKS configuration, and record the deployment-specific divergence in a new ADR before rollout.
