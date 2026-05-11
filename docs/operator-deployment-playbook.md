# Vezor Operator Deployment Playbook

This is the operator-ready deployment guide for Vezor.

Use it when you want to decide what to deploy, where to deploy it, and in what order to validate it.

For the shorter decision guide, use [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md).

## Current Implementation Snapshot

The current product includes the operator workflows needed for a serious pilot:

- Live wall with source-aware browser delivery
- metric-aware History with exports
- Fleet and Operations workbench at `/settings`
- Evidence Desk incident review queue at `/incidents`
- central and edge worker configuration paths
- model catalog presets and registration helper
- fixed-vocab and open-vocab detector capability contracts
- experimental Ultralytics-backed open-vocab `.pt` runtime path
- stabilized Live track lifecycle, class-colored overlays, and Telemetry Terrain
- scene vision profiles with explicit speed enablement, optional speed-off homography, detection include/exclusion regions, and candidate quality gating
- Jetson edge compose stack and preflight tooling

The production-critical layer still missing is supervisor-backed lifecycle control. Today, local development uses copyable commands and edge development uses Compose. Production should replace both with a central or edge supervisor that starts, stops, restarts, drains, monitors, and reports camera workers.

## Dev Versus Production

Do not confuse the local dev stack with production.

### Development

- one workstation can run the full stack with `make dev-up`
- workers are started manually from Operations copy buttons or lab guide commands
- local seeded credentials such as `admin-dev` are acceptable only inside the dev stack
- stop means `Ctrl-C` or `docker compose stop`

### Production

- the master runs on Linux `amd64`, preferably through Helm/k3s or an equivalent supervised service platform
- Jetson edge nodes run a small edge stack near the cameras
- all worker processes are owned by a local supervisor, not the browser or API container
- Operations writes desired state or lifecycle requests, then displays reported runtime truth
- edge credentials are scoped, rotated, and provisioned through bootstrap, not copied from local dev tokens
- the current iMac + Jetson lab should set the edge worker's `ARGUS_NATS_URL` directly to the iMac NATS listener; the NATS leaf shape is the production target once supervisor bootstrap owns credentials and routing

Production topology:

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

## 1. Smallest Lab Setup

This is the recommended first deployment for evaluation, local validation, UI review, and basic architecture proof.

### Goal

Bring up the full Vezor control plane on one machine, run everything locally, and validate the product end to end before buying or assigning site hardware.

### Recommended hardware

- one Mac or Linux workstation for development
- if using Linux for longer-running evaluation, an `amd64` machine is preferred
- no edge node required
- no dedicated GPU required for the basic software bring-up

### Topology

- one machine runs the dev stack through `docker compose`
- cameras can be recorded loops, test streams, or a small number of reachable RTSP sources
- all cameras are treated as `central` for the first pass

### What runs

- FastAPI backend
- PostgreSQL/TimescaleDB
- Redis
- NATS JetStream
- MediaMTX
- Keycloak
- frontend
- MinIO
- OTEL collector and observability services

### How to bring it up

From [/Users/yann.moren/vision](/Users/yann.moren/vision):

```bash
make dev-up
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
corepack pnpm --dir frontend generate:api
```

Then open:

- [http://127.0.0.1:3000](http://127.0.0.1:3000) for the frontend
- [http://127.0.0.1:3000/settings](http://127.0.0.1:3000/settings) for the Operations workbench
- [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz) for backend health
- [http://127.0.0.1:8080](http://127.0.0.1:8080) for Keycloak
- [http://127.0.0.1:9001](http://127.0.0.1:9001) for MinIO console

### When this setup is enough

Use this setup for:

- product review
- frontend validation
- API and auth validation
- end-to-end functional checks
- demo preparation
- CI parity checks

Do not treat it as the final production topology for a real multi-site rollout.

### Success criteria

- backend health responds `200`
- login works through Keycloak
- you can create a site and camera
- Operations shows truthful node, worker, and delivery state for the current lab setup
- tests and Playwright pass locally

### Worker lifecycle model

The lab UI can show desired worker ownership, runtime freshness, delivery diagnostics, and copyable local-dev worker commands from the Operations page. Those shell commands are a development bridge for workstations where no supervisor is running yet.

Production lifecycle controls should not shell out from the browser or API container. Start, stop, restart, and drain should write desired state or send a constrained lifecycle request; a central or edge supervisor then owns the actual process reconciliation and reports runtime truth back through heartbeats.

### iMac + Jetson pilot interpretation

When the iMac is used as the master and the Jetson is used as edge, treat the result as a pilot proving the product flow:

- sign in and configure the site on the iMac
- run central camera workers on the iMac for comparison
- move one camera to Jetson edge mode
- confirm Live, History, Operations, and Evidence Desk all continue to work

That setup answers whether the product behaves correctly on the intended split architecture. It does not answer final production availability, backup, TLS, secret rotation, or supervisor lifecycle questions. Those belong to the Linux master production deployment.

## 2. First Production Site

This is the recommended first real deployment for one site going into production.

### Goal

Stand up a stable central Vezor node and connect one real site with a small number of cameras. Keep the rollout conservative and operationally simple.

### Recommended default choice

Start with:

- one central HQ/master node on Linux `amd64`
- cameras in `central` mode unless bandwidth or privacy clearly argues for local inference

Move to `edge` mode for specific cameras if:

- the uplink is constrained
- site-local privacy enforcement is required
- local site autonomy matters

### Recommended hardware

#### HQ/master node

- Linux `amd64`
- 8-16 CPU cores
- 32-64 GB RAM
- fast SSD storage
- optional NVIDIA L4 if you want central inference at meaningful scale
- production backup target for database and object storage
- TLS termination and stable DNS

#### Site hardware

Two supported patterns:

- no edge compute, just cameras reaching HQ
- one Jetson Orin Nano Super 8 GB for local inference

For the Jetson pattern, run the device in 25 W Super mode, validate JetPack/CUDA/TensorRT/NVDEC with the preflight script, and keep the first production profile conservative: one or two cameras per Jetson before scaling.

### Network pattern

- site-to-HQ connectivity over Tailscale or WireGuard
- HQ remains the source of truth for auth, config, history, incidents, and UI
- if using edge inference, the site runs a NATS leaf and MediaMTX locally

### Deployment recommendation

#### If the site has strong uplink

- deploy HQ/master first
- register cameras as `central`
- keep the site simple

#### If the site has weak uplink or strict privacy

- deploy HQ/master first
- add one Jetson edge node
- register selected cameras as `edge`

### Operational order

1. Deploy HQ/master and validate auth, health, and storage.
2. Add a single production site.
3. Connect one or two cameras first.
4. Validate live viewing, telemetry, privacy behavior, incidents, and history.
5. Validate Operations runtime truth: desired worker count, node health, worker heartbeat freshness, and last-error reporting.
6. Only then add the rest of the site’s cameras.

### Production lifecycle requirements

Before calling a site production-ready, the deployment needs:

- central supervisor for central and hybrid workers
- edge supervisor for Jetson-owned workers
- worker heartbeat with per-camera runtime state
- restart policy after worker crash or device reboot
- drain behavior for planned maintenance
- logs and metrics visible from the central observability stack
- backup and restore procedure for Postgres/TimescaleDB and incident object storage
- scoped edge credentials with rotation path

### Inference Runtime Overrides

By default, the worker now chooses an execution-provider policy from host capabilities:

- NVIDIA Linux `amd64`: TensorRT, then CUDA, then CPU
- NVIDIA Linux `aarch64` Jetson: TensorRT, then CUDA, then CPU
- Apple Silicon macOS: CoreML, then CPU
- Intel Linux `amd64`: OpenVINO, then CPU
- AMD Linux `amd64`: CPU in this first pass
- Intel macOS: CoreML when available, then CPU

This provider policy applies to ONNX Runtime models. Raw TensorRT `.engine` files are not selectable production models; use ONNX rows as the portable source model and attach `.engine` files as validated target-specific runtime artifacts. Stable open-vocab scenes can also use compiled scene artifacts when the camera vocabulary hash and target profile match. If no valid artifact matches, the worker falls back to the canonical ONNX or dynamic `.pt` path and Operations should show the selected backend or fallback state honestly.

For controlled benchmarking or mitigation, these environment variables can override the automatic choice:

- `ARGUS_INFERENCE_EXECUTION_PROVIDER_OVERRIDE`
- `ARGUS_INFERENCE_EXECUTION_PROFILE_OVERRIDE`
- `ARGUS_INFERENCE_SESSION_INTER_OP_THREADS`
- `ARGUS_INFERENCE_SESSION_INTRA_OP_THREADS`

Use the overrides sparingly. Prefer the automatic policy for normal deployment, and only force a provider when you are measuring performance or isolating a runtime-specific issue.

Current image packaging is narrower than the product model: `edge` remains a
portable deployment role, but `infra/docker-compose.edge.yml` currently builds
the Jetson-specific Python 3.10 edge worker image. That Python 3.10 choice is
intentional for Jetson ONNX Runtime GPU wheels. The central/backend image remains
Python 3.12. Do not assume a generic non-Jetson edge image exists until a
hardware-specific image and bootstrap path are added.

### Success criteria

- operators can log in and view the site
- at least one production camera runs cleanly for multiple days
- incidents and clip storage work
- Evidence Desk pending/reviewed state survives reloads and can be audited
- metrics and logs are visible
- Operations shows desired state versus runtime state without inventing unknown worker status
- no recurring stream/auth/database/worker-supervisor failures appear during soak

## 3. Multi-Site Rollout

This is the target Vezor topology for a real fleet.

### Goal

Operate multiple sites with a single central Vezor control plane while allowing each site to choose the right mix of `central`, `edge`, and `hybrid`.

### Recommended architecture

#### Central

One central Vezor cluster or node runs:

- API
- frontend
- PostgreSQL/TimescaleDB
- Keycloak
- Redis
- NATS JetStream
- MinIO
- central MediaMTX
- observability stack

#### Per site

Choose one of these:

- no edge node, cameras use `central`
- one edge node for a small site
- multiple edge nodes for larger or segmented sites

### Recommended mode mix

- default to `edge` for bandwidth-sensitive or privacy-sensitive cameras
- keep `central` for cameras with strong HQ connectivity and no need for local compute
- use `hybrid` only where the downstream central analytics add clear value

### Rollout pattern

Roll out in waves:

1. one site
2. a small cluster of similar sites
3. the full estate

Avoid onboarding many heterogeneous sites at once. The first 2-3 sites usually expose the real operational edge cases.

### Minimum central hardware posture

For multi-site production, prefer:

- Linux `amd64`
- strong SSD-backed storage
- reliable backups
- central GPU when running meaningful `central` inference volume
- L4-class GPU for the first serious central inference tier

### Site classification before rollout

Before onboarding each site, classify it by:

- uplink quality
- privacy requirements
- camera count
- tolerance for local hardware maintenance
- desired autonomy during WAN issues

That classification should determine whether the site defaults to `central` or `edge`.

### Operational guardrails

- standardize one edge hardware family first
- keep one canonical Jetson edge image and one canonical bootstrap process first
- do not mix many experimental edge hardware types in the first rollout
- use observability from day one, not after the fact

### Success criteria

- new sites can be onboarded repeatably
- per-site failures are isolated
- central services remain healthy as site count grows
- edge nodes rejoin cleanly after restart or transient disconnect

## 4. Scale-Up And Hardware Tiers

This section is the practical “when do I upgrade” guide.

### Tier A: Lab / pilot

- one workstation or one small Linux server
- mostly `central`
- a handful of cameras

Use this when:

- validating the product
- piloting with a small user group
- proving workflows before hardware investment

### Tier B: First production central node

- one Linux `amd64` server
- production storage and backups
- optional GPU
- one site or a few small sites

Use this when:

- running your first real deployment
- camera count is still modest
- central orchestration matters more than GPU scale

### Tier C: Central inference tier

- one Linux `amd64` server with an NVIDIA L4
- more meaningful `central` camera volume
- stronger observability and operational discipline

Use this when:

- central inference becomes a major workload
- more cameras are processed at HQ
- browser delivery, incidents, history, and API usage are all increasing together

### Tier D: Mixed multi-site fleet

- central L4-class or stronger HQ node
- multiple Jetson edge nodes at sites
- clear split between `central` and `edge` by site or camera class

Use this when:

- different sites have different uplink and privacy constraints
- you want the architecture Vezor was fundamentally designed for

### Tier E: Advanced hybrid analytics

- central compute for second-stage analytics
- capable edge compute at selected sites
- deliberate `hybrid` use for value-added analysis

Use this when:

- local site inference alone is not enough
- you want central correlation or advanced downstream analytics
- you are ready for the most sophisticated operating model

## Recommended Deployment Strategy

If you are choosing today, I recommend this progression:

1. lab setup with mostly `central`
2. first production site with either all `central` or a small `edge` footprint
3. multi-site rollout with `edge` for constrained sites
4. selective `hybrid` only after the fleet is stable

That path gives the best ratio of learning to operational risk.

## Canonical Commands

### Local/dev control plane

```bash
make dev-up
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
corepack pnpm --dir frontend generate:api
```

### Local/dev shutdown

```bash
make dev-down
```

### Edge single-node bring-up

Before starting Jetson edge:

```bash
sudo nvpmodel -m 2 && sudo jetson_clocks
/Users/yann.moren/vision/scripts/jetson-preflight.sh
```

Then:

```bash
export ARGUS_API_BASE_URL="http://<master-ip>:8000"
export ARGUS_API_BEARER_TOKEN="<fresh-access-token>"
export ARGUS_DB_URL="postgresql+asyncpg://argus:argus@<master-ip>:5432/argus"
export ARGUS_NATS_URL="nats://<master-ip>:4222"
export ARGUS_MINIO_ENDPOINT="<master-ip>:9000"
export ARGUS_EDGE_CAMERA_ID="<camera-id>"
export JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"
docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml config >/tmp/argus-edge-compose.yml
docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml up -d --build
```

This compose command is appropriate for lab and pilot edge bring-up. In production, run the same edge responsibilities under the chosen supervisor model so workers restart after reboot, expose runtime state, and receive lifecycle commands from the control plane.

### Helm render validation

```bash
helm template argus /Users/yann.moren/vision/infra/helm/argus
helm template argus /Users/yann.moren/vision/infra/helm/argus -f /Users/yann.moren/vision/infra/helm/argus/values-edge.yaml
```

## Whole-Suite Validation Flow

This is the best single pass to run after a meaningful change or before a pilot demo.

From [/Users/yann.moren/vision](/Users/yann.moren/vision):

```bash
make verify-all
```

What success looks like:

- backend checks are clean
- frontend checks are clean
- Playwright passes
- Helm renders cleanly
- compose services are up
- `/healthz` returns `{"status":"ok"}`

The command above is a wrapper over [scripts/run-full-validation.sh](/Users/yann.moren/vision/scripts/run-full-validation.sh), which runs the full local validation sequence in the correct order.

For reliability, that wrapper starts backend and infrastructure services through Docker Compose, then lets Playwright launch a local Vite dev server for the browser tests. If the Docker frontend service is already running, the wrapper temporarily stops it so the browser-test server can bind port `3000`, then restores it at the end.

## Related Documents

- [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md)
- [runbook.md](/Users/yann.moren/vision/docs/runbook.md)
- [product-spec-v4.md](/Users/yann.moren/vision/product-spec-v4.md)
