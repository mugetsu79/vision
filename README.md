# Vezor | The OmniSight Platform

Vezor is a hybrid video analytics platform for multi-camera operations. It is designed to run as a central control plane with optional edge inference nodes, giving operators one system for live visibility, configuration, history, incidents, and streaming-aware delivery.

The project supports three processing modes:

- `central`: the master node pulls the stream and performs inference centrally
- `edge`: a site-local node performs inference and sends events, telemetry, clips, and optional preview streams back to the master
- `hybrid`: edge handles primary detection while the master adds heavier downstream analytics

Vezor separates **native ingest for analytics** from **browser delivery for operators**, which means you can keep high-quality inference while serving lower-resolution or lower-FPS viewing profiles such as `1080p15`, `720p10`, or `540p5`.

## What’s In This Repo

- `backend/`: FastAPI API, services, inference worker, schema, migrations, auth, streaming integration
- `frontend/`: React operator console and admin UI
- `infra/`: Docker Compose, Helm chart, observability, Keycloak, MediaMTX, NATS, Prometheus, Alertmanager, OTEL
- `docs/`: deployment guides, runbook, lab guide, ADRs, brand docs
- `models/`: local model file location for lab and development use
- `scripts/`: validation and platform helper scripts

## Architecture At A Glance

- **Backend**: FastAPI, PostgreSQL/TimescaleDB, Redis, NATS JetStream, MinIO
- **Auth**: Keycloak with tenant-aware RBAC
- **Streaming**: MediaMTX with WebRTC, HLS, and fallback handling
- **Frontend**: React, TanStack Query, Zustand, Playwright
- **Vision pipeline**: detector, tracker, privacy, zones, rules, homography, ANPR hooks
- **Deployment targets**:
  - master/control plane: Linux `amd64` is the main production target
  - edge inference: Jetson Orin Nano Super 8 GB is the hardened reference target
  - lab/dev: macOS or Linux workstations are fine for bring-up and functional testing

## Quick Start

These steps bring up the local development stack.

### Prerequisites

- Docker + Docker Compose
- Python `3.12+`
- [`uv`](https://github.com/astral-sh/uv)
- Node `22+`
- Corepack enabled
- Helm if you want to run full validation

### Start The Dev Stack

From [/Users/yann.moren/vision](/Users/yann.moren/vision):

```bash
make dev-up
cd backend && python3 -m uv run alembic upgrade head
cd ../frontend && corepack pnpm generate:api
cd ..
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

## Hardware Guidance

### Good current targets

- **Master / HQ node**: Linux `amd64` server or workstation
- **Central inference GPU**: NVIDIA L4 24 GB is the reference target
- **Edge node**: Jetson Orin Nano Super 8 GB

### Good lab / pilot setups

- macOS workstation for local bring-up and UI/API validation
- iMac as a pilot master node
- iMac master + Jetson edge as a realistic two-node evaluation setup

### Important note

The repo supports useful lab and pilot workflows on macOS, but the long-term production central inference path is still centered on Linux + NVIDIA.

## Current State

The repo already includes:

- multi-tenant auth and RBAC
- site and camera management
- model registration
- live dashboard with query-driven filtering
- history and incidents
- incident clip storage
- edge worker support
- Docker Compose and Helm assets
- CI-oriented full validation flow

The most mature operational paths today are `central` and `edge`.

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
