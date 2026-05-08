# Vezor | The OmniSight Platform

Vezor is a hybrid video analytics platform for multi-camera operations. It is designed to run as a central control plane with optional edge inference nodes, giving operators one system for live visibility, configuration, history, incidents, and streaming-aware delivery.

The project supports three processing modes:

- `central`: the master node pulls the stream and performs inference centrally
- `edge`: a site-local node performs inference and sends events, telemetry, clips, and optional preview streams back to the master
- `hybrid`: edge handles primary detection while the master adds heavier downstream analytics

Vezor separates **native ingest for analytics** from **browser delivery for operators**, which means you can keep high-quality inference while serving lower-resolution or lower-FPS viewing profiles such as `1080p15`, `720p10`, or `540p5`.

The Operations workbench at `/settings` shows the current fleet model: desired camera workers, node/runtime state, delivery diagnostics, and edge bootstrap material. In local development, workers are still launched from copyable commands because there is no local supervisor process yet. In production, Start/Stop/Restart controls should go through a central or edge supervisor that reconciles desired state and reports actual runtime state back to the control plane.

The current codebase has moved beyond a pure dev scaffold. The main operator workflows exist, including Live, History, Operations, and the Evidence Desk incident review queue. The main production gap is lifecycle automation: a production supervisor or edge agent still needs to own worker start/stop/restart/drain and report per-worker runtime truth.

## What’s In This Repo

- `backend/`: FastAPI API, services, inference worker, schema, migrations, auth, streaming integration
- `frontend/`: React operator console and admin UI
- `infra/`: Docker Compose, Helm chart, observability, Keycloak, MediaMTX, NATS, Prometheus, Alertmanager, OTEL
- `docs/`: deployment guides, runbook, lab guide, ADRs, brand docs
- `models/`: local ONNX model files for lab and development use
- `scripts/`: validation and platform helper scripts

## Architecture At A Glance

- **Backend**: FastAPI, PostgreSQL/TimescaleDB, Redis, NATS JetStream, MinIO
- **Auth**: Keycloak with tenant-aware RBAC
- **Streaming**: MediaMTX with WebRTC, HLS, and fallback handling
- **Frontend**: React, TanStack Query, Zustand, Playwright
- **Vision pipeline**: detector, tracker, privacy, zones, rules, homography, ANPR hooks
- **Deployment targets**:
  - master/control plane: Linux `amd64` is the main production target
  - edge inference: Jetson Orin Nano Super 8 GB is the hardened packaged target
  - lab/dev: macOS or Linux workstations are fine for bring-up and functional testing

The central/backend image and local development environment use Python 3.12. The
current `infra/docker-compose.edge.yml` path builds `backend/Dockerfile.edge`,
which is a Jetson-oriented edge worker image that uses the Jetson base image's
system Python 3.10 so cp310 Jetson ONNX Runtime GPU wheels can be installed.
There is not currently a separate generic non-Jetson edge image that preserves
Python 3.12.

For the current JetPack 6 / Python 3.10 lab path, use this wheel URL before
building the edge image when validating Jetson GPU providers:

```bash
export JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"
```

## Quick Start

These steps bring up the local development stack.

### Prerequisites

- Docker + Docker Compose
- Python `3.12+` for local development and the central/backend image
- [`uv`](https://github.com/astral-sh/uv)
- Node `22+`
- Corepack enabled
- Helm if you want to run full validation

### Start The Dev Stack

From [/Users/yann.moren/vision](/Users/yann.moren/vision):

```bash
make dev-up
until docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv --version >/dev/null 2>&1; do
  echo "waiting for backend Python environment..."
  sleep 3
done
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
until curl -fsS http://127.0.0.1:8000/healthz >/dev/null; do
  echo "waiting for backend health..."
  sleep 3
done
corepack pnpm --dir frontend generate:api
```

Open:

- [http://127.0.0.1:3000](http://127.0.0.1:3000) for the frontend
- [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz) for backend health
- [http://127.0.0.1:8080](http://127.0.0.1:8080) for Keycloak
- [http://127.0.0.1:9001](http://127.0.0.1:9001) for MinIO console

### Local Dev Login

The local stack ships with seeded development credentials:

- username: `admin-dev`
- password: `argus-admin-pass`

Use those only for local development.

### Local Worker Lifecycle

The dev stack starts platform services, not per-camera inference workers. To run a central worker locally:

1. Open [http://127.0.0.1:3000/settings](http://127.0.0.1:3000/settings).
2. Use the Operations page's copyable camera-worker command.
3. Run that command in a terminal on the machine that should own the worker.
4. Stop the worker with `Ctrl-C`.

Those commands fetch a local development bearer token and set `ARGUS_API_BEARER_TOKEN="$TOKEN"` for you. They are a development bridge, not the production control model.

In production, UI lifecycle controls should update desired state or send a constrained lifecycle request. A central or edge supervisor should start, stop, restart, monitor, and report worker runtime state. The backend API should not become a generic remote shell runner.

## Common Commands

From [/Users/yann.moren/vision](/Users/yann.moren/vision):

```bash
make dev-up          # start local development services
make dev-down        # stop local development services
make migrate         # run backend migrations
make lint            # backend + frontend lint/type checks
make test            # backend + frontend tests
make verify-all      # full validation flow, including Playwright and Helm render
make helm-template   # render the Helm chart locally
```

The full validation flow is implemented in [scripts/run-full-validation.sh](/Users/yann.moren/vision/scripts/run-full-validation.sh).

## Recommended Reading

Start here if you are new to the repo:

- [product-spec-v4.md](/Users/yann.moren/vision/product-spec-v4.md): current architecture and product spec
- [docs/runbook.md](/Users/yann.moren/vision/docs/runbook.md): operations starting point
- [docs/deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md): short decision guide for `central`, `edge`, and `hybrid`
- [docs/operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md): operator-ready deployment guidance
- [docs/imac-master-orin-lab-test-guide.md](/Users/yann.moren/vision/docs/imac-master-orin-lab-test-guide.md): step-by-step lab guide for a 2019 iMac master and Jetson Orin Nano edge test

## Deployment Modes

### `central`

Use this when:

- the camera can reliably reach the master node
- you want the simplest site setup
- privacy policy allows central inference

### `edge`

Use this when:

- bandwidth is constrained
- privacy should be enforced before frames leave the site
- site-local inference resilience matters

### `hybrid`

Use this when:

- you want local responsiveness and heavier downstream master-side analytics
- you are comfortable with a more advanced deployment pattern

For the detailed decision matrix, see [docs/deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md).

## Production Deployment Shape

The development stack is intentionally convenient, but it is not the final production shape.

In production, deploy Vezor as:

- **Production master / HQ node** on Linux `amd64`
  - frontend
  - FastAPI backend
  - PostgreSQL/TimescaleDB
  - Keycloak
  - NATS JetStream
  - MinIO
  - Redis
  - MediaMTX
  - OpenTelemetry, Prometheus, Grafana, Loki, Tempo, Alertmanager
  - central supervisor for central and selected hybrid workers
- **Jetson Orin edge node** per site when local inference is needed
  - edge supervisor
  - inference worker container or service
  - local MediaMTX
  - NATS leaf
  - OTEL collector
  - Jetson 25 W Super mode with TensorRT/NVDEC enabled
- **Overlay network**
  - Tailscale or WireGuard between sites and HQ
  - TLS/OIDC for operators
  - scoped edge credentials, not copied local dev tokens

The iMac + Jetson path documented in the lab guide is a valuable pilot topology: the iMac can act as a temporary master while the Jetson validates edge inference. For production, replace the iMac dev stack with a Linux master deployment and replace copied worker commands with supervisor-managed workers.

## Hardware Guidance

### Good current targets

- **Master / HQ node**: Linux `amd64` server or workstation
- **Central inference GPU**: NVIDIA L4 24 GB is the reference target
- **Edge node**: Jetson Orin Nano Super 8 GB with the Python 3.10 Jetson edge image

### Good lab / pilot setups

- macOS workstation for local bring-up and UI/API validation
- iMac as a pilot master node
- iMac master + Jetson edge as a realistic two-node evaluation setup

### Important note

The repo supports useful lab and pilot workflows on macOS, but the long-term production central inference path is still centered on Linux + NVIDIA.

`edge` is a deployment role, not a synonym for Jetson in the product model. In
this repository's current packaging, however, the canonical edge Compose image
is Jetson-specific. For non-Jetson edge hardware, either run a host worker with
the central/backend Python 3.12 environment for lab testing, or add a dedicated
edge image for that hardware family before treating it as a supported deployment
target.

## Current State

The repo already includes:

- multi-tenant auth and RBAC
- site and camera management
- model registration
- unified live workspace at `/live` with NL query-driven filtering, per-camera video tiles, and 30-minute occupancy sparklines (`/dashboard` now redirects)
- shared telemetry WebSocket state that survives route changes and keeps the live wall warm across short navigation hops
- metric-aware history and incidents, including URL-backed history filters, class discovery, optional speed telemetry, CSV/Parquet export, and a clear split between `occupancy`, `count_events`, and raw `observations`
- Evidence Desk incident review at `/incidents`, including pending/reviewed state, review/reopen actions, signed clip access, clip-only evidence handling, and review audit entries
- incident clip storage; snapshot fields exist but current capture primarily stores clips
- Fleet and Operations workbench at `/settings`, including node summaries, camera worker lifecycle state, delivery diagnostics, edge bootstrap material, and copy/paste-safe local worker commands
- edge worker support and a production-oriented supervisor lifecycle model
- model catalog presets, fixed-vocab and open-vocab detector capability contracts, runtime vocabulary persistence, vocabulary snapshot attribution, capability-aware query commands, and an experimental Ultralytics-backed open-vocab `.pt` runtime path
- hybrid ingest: processed workers read camera RTSP directly, while MediaMTX remains the distribution/publication layer for passthrough, annotated, and preview renditions
- Docker Compose and Helm assets
- CI-oriented full validation flow

The most mature operational paths today are `central` and `edge`.

Still missing for production hardening:

- supervisor-backed Start/Stop/Restart/Drain actions in Operations
- per-worker runtime heartbeat and last-error reporting from central and edge supervisors
- persistent worker assignment/reassignment workflows
- production edge credential rotation automation
- validated raw TensorRT `.engine` runtime artifacts; TensorRT remains an ONNX Runtime provider path today, while standalone `.engine` files are documented as planned follow-up work
- incident still snapshot generation, if still previews become required evidence rather than optional convenience

## Model And Camera Scope

- `occupancy` means objects currently visible in the scene or peak visible occupancy within a bucketed history window.
- Precise cumulative traffic-style counts come from durable `count_events` such as `line_cross`, `zone_enter`, and `zone_exit`, not from aggregating raw frame observations.

- `models/` is just where local ONNX files live during lab and development work.
- In local Docker development, the backend bind-mounts this checkout's `models/` path so registration-time ONNX validation can read the same absolute host path that host-side workers use later.
- For standard deployment, self-describing ONNX metadata is the source of truth for model classes.
- If an operator supplies `classes` for a self-describing ONNX model and they disagree with embedded metadata, registration should fail closed instead of warning and proceeding.
- `Model.classes` is the full model inventory.
- `Camera.active_classes` narrows the operational scope for a camera or site.
- Custom reduced-class models are an advanced optional path, not the default deployment story.

## Repo Structure

```text
vision/
├── backend/
│   └── src/argus/
├── frontend/
│   └── src/
├── infra/
├── docs/
├── models/
└── scripts/
```

## Validation

For a strong local confidence check, run:

```bash
make verify-all
```

This currently covers:

- backend linting and mypy
- backend test suite
- frontend linting, tests, and production build
- Playwright end-to-end flows
- Helm chart rendering
- runtime health checks

## Brand And Design

Brand guidance lives in:

- [docs/brand/logo-brand-spec.md](/Users/yann.moren/vision/docs/brand/logo-brand-spec.md)
- [docs/brand/logo-usage-guide.md](/Users/yann.moren/vision/docs/brand/logo-usage-guide.md)
- [docs/brand/logo-generation-prompts.md](/Users/yann.moren/vision/docs/brand/logo-generation-prompts.md)

## License And Usage

No top-level license file is currently present in this repository. Treat the codebase as private/internal until a formal license is added.
