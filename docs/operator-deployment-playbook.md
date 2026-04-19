# Argus Operator Deployment Playbook

This is the operator-ready deployment guide for Argus.

Use it when you want to decide what to deploy, where to deploy it, and in what order to validate it.

For the shorter decision guide, use [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md).

## 1. Smallest Lab Setup

This is the recommended first deployment for evaluation, local validation, UI review, and basic architecture proof.

### Goal

Bring up the full Argus control plane on one machine, run everything locally, and validate the product end to end before buying or assigning site hardware.

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
cd backend && python3 -m uv run alembic upgrade head
cd ../frontend && corepack pnpm generate:api
```

Then open:

- [http://127.0.0.1:3000](http://127.0.0.1:3000) for the frontend
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
- tests and Playwright pass locally

## 2. First Production Site

This is the recommended first real deployment for one site going into production.

### Goal

Stand up a stable central Argus node and connect one real site with a small number of cameras. Keep the rollout conservative and operationally simple.

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

#### Site hardware

Two supported patterns:

- no edge compute, just cameras reaching HQ
- one Jetson Orin Nano Super 8 GB for local inference

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
5. Only then add the rest of the site’s cameras.

### Success criteria

- operators can log in and view the site
- at least one production camera runs cleanly for multiple days
- incidents and clip storage work
- metrics and logs are visible
- no recurring stream/auth/database failures appear during soak

## 3. Multi-Site Rollout

This is the target Argus topology for a real fleet.

### Goal

Operate multiple sites with a single central Argus control plane while allowing each site to choose the right mix of `central`, `edge`, and `hybrid`.

### Recommended architecture

#### Central

One central Argus cluster or node runs:

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
- keep one canonical edge image and one canonical bootstrap process
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
- you want the architecture Argus was fundamentally designed for

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
cd backend && python3 -m uv run alembic upgrade head
cd ../frontend && corepack pnpm generate:api
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
docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml up -d
```

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
- [argus_v4_spec.md](/Users/yann.moren/vision/argus_v4_spec.md)
