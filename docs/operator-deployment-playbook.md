# Vezor Operator Deployment Playbook

This is the operator-ready deployment guide for Vezor.

Use it when you want to decide what to deploy, where to deploy it, and in what order to validate it.

For the shorter decision guide, use [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md). For the product installer and first-run path, use [product-installer-and-first-run-guide.md](/Users/yann.moren/vision/docs/product-installer-and-first-run-guide.md). For the portable MacBook Pro + Jetson field demo, use [macbook-pro-jetson-portable-demo-install-guide.md](/Users/yann.moren/vision/docs/macbook-pro-jetson-portable-demo-install-guide.md). For the no-console installer design, use [2026-05-14-product-installer-and-no-console-first-run-design.md](/Users/yann.moren/vision/docs/superpowers/specs/2026-05-14-product-installer-and-no-console-first-run-design.md).

## Current Implementation Snapshot

The current product includes the operator workflows needed for a serious pilot:

- Live wall with source-aware browser delivery
- metric-aware History with exports
- Fleet and Operations workbench at `/settings`
- first-run Deployment workbench at `/deployment` for install health, node
  pairing, credential status, and redacted support bundles
- Evidence Desk incident review queue at `/incidents`
- central and edge worker configuration paths
- model catalog presets and registration helper
- fixed-vocab and open-vocab detector capability contracts
- experimental Ultralytics-backed open-vocab `.pt` runtime path
- stabilized Live track lifecycle, class-colored overlays, and Telemetry Terrain
- scene vision profiles with explicit speed enablement, optional speed-off homography, detection include/exclusion regions, and candidate quality gating
- accountable scene contracts, privacy manifests, evidence ledger entries, and short event clip recording policy
- per-scene incident rule authoring in Control -> Scenes, worker rule
  consumption in Control -> Operations, and trigger rule summaries in
  Intelligence -> Evidence
- supervisor lifecycle request contracts, claim/complete transitions, and
  hardware model-admission reporting in Control -> Operations
- deployment-node service reports, one-time pairing sessions, node credentials,
  and credential audit events in Control -> Deployment
- RTSP and edge USB/UVC camera source configuration
- Jetson edge compose stack and preflight tooling

The supervisor lifecycle MVP is now present as API contracts, database records,
UI admission status, a reconciler library, a runnable child-process supervisor,
and an installable-node control plane. Local development can still use manual
terminal workers, but installed product operation should use install-once
macOS/Linux/container supervisor services, short-lived node pairing, platform
credential storage, service health reports, diagnostics, and no normal
copied-token terminal workflow after installation.

## Dev Versus Production

Do not confuse the local dev stack with production.

Normal installed operation begins in Control -> Deployment. Operators install
the macOS master, Linux master, or Jetson edge service locally, pair the node
from the UI, and then use Control -> Operations for lifecycle requests. If a
camera has no eligible installed supervisor, Operations should send the
operator back to Deployment to install or pair one. Copied bearer-token
commands, foreground supervisor runners, and ad hoc Docker commands are
development fallback or break-glass material only.

### Development

- one workstation can run the full stack with `make dev-up`
- workers can be started manually from lab guide commands when no supervisor is
  installed
- local seeded credentials such as `admin-dev` are acceptable only inside the dev stack
- stop means `Ctrl-C` or `docker compose stop`

### Production

- the master runs on Linux `amd64`, preferably through the Linux master
  installer or a later Helm/k3s production platform
- the MacBook Pro installer path is a portable pilot/demo master when no Linux
  master is available
- Jetson edge nodes run a small edge stack near the cameras
- all worker processes are owned by a local supervisor, not the browser or API container
- central and edge supervisors are installed as durable macOS/Linux services or
  production container services, then paired from the UI
- Operations writes desired state or lifecycle requests, then displays reported runtime truth
- supervisors report host hardware capability and observed model performance so
  unsupported models do not start on unsuitable hardware
- edge and central supervisor credentials are scoped, rotated, revocable, and
  provisioned through one-time pairing or credential rotation, not copied from
  local dev tokens
- the current MacBook/iMac + Jetson lab should set the edge worker's `ARGUS_NATS_URL` directly to the macOS master NATS listener; the NATS leaf shape is the production target once supervisor bootstrap owns credentials and routing

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
  uv run alembic upgrade head
corepack pnpm --dir frontend generate:api
```

Then open:

- [http://127.0.0.1:3000](http://127.0.0.1:3000) for the frontend
- [http://127.0.0.1:3000/settings](http://127.0.0.1:3000/settings) for the Operations workbench
- [http://127.0.0.1:3000/deployment](http://127.0.0.1:3000/deployment) for install health, pairing, and support bundles
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
- you can define an enabled incident rule for that camera from Control -> Scenes
- Operations shows truthful node, worker, and delivery state for the current lab setup
- Operations shows worker rule count/hash/readiness for cameras with incident
  rules
- Operations shows either a manual production-admission bypass note or the
  latest hardware/model admission status for supervised workers
- a rule-generated incident is reviewable in Evidence with trigger rule context
- tests and Playwright pass locally

### Worker lifecycle model

The lab UI can show desired worker ownership, runtime freshness, delivery
diagnostics, and production admission. Manual shell commands remain a
development bridge documented in lab guides for workstations where no
supervisor is running yet.

Production lifecycle controls should not shell out from the browser or API container. Start, stop, restart, and drain should write desired state or send a constrained lifecycle request; a central or edge supervisor then owns the actual process reconciliation and reports runtime truth back through heartbeats.

For final-product operation, the supervisor itself must be installed once as a
durable system service or production container service. After that installation,
operators should pair the node and manage workers from the UI. Command-line
runner invocations remain lab, smoke-test, or break-glass workflows only.

### Installable Supervisor Service Shape

Band 7.5 introduces checked-in service templates under
`infra/install/`. They are product templates, not backend-executed commands.
The browser and API continue to act as a control plane: they record desired
state, pairing state, service reports, and diagnostics. They must not run
generic host shell commands.

Supported ownership shapes:

- Linux production nodes use `systemd` with a dedicated `vezor` user,
  restart-on-failure behavior, explicit state/log/runtime directories, and a
  credential file reference such as `LoadCredential=`.
- macOS pilot or packaged-server nodes use `launchd` with a daemon plist that
  restarts the supervisor and points at `/etc/vezor/supervisor.json`.
- Containerized edge or appliance deployments use the Compose supervisor
  profile with a healthcheck, restart policy, mounted config, and mounted
  credential directory.

None of the service templates embeds a long-lived bearer token. Product
credentials are paired, stored behind the node-local credential boundary, and
rotated through Control -> Deployment. Direct child process
mode remains for local development, deterministic smoke tests, and break-glass
support only.

### Node Pairing And Credential Lifecycle

Installable supervisors are admitted through short-lived pairing sessions
created from Control -> Deployment. A pairing session is
scoped to one central node or one known edge node, stores only a hash of the
one-time pairing code, and returns node credential material only during the
claim response. The backend stores the credential hash and credential lifecycle
events, not reusable plaintext credential material.

The installed supervisor reads its API URL, supervisor id, role, optional edge
node id, and credential store path from the local product config file. The
pairing claim writes the returned credential into the node-local credential
store with owner-only permissions. Service templates reference that local
credential boundary; they do not require an operator to paste a bearer token
into a unit file, launch daemon, Compose file, or long-running terminal.

Credential rotation uses the same bounded path. Control -> Deployment calls the
node credential rotation endpoint, the backend revokes every prior credential
for that deployment node, creates the next credential version, and returns the
new secret material only in that response. The operator must write the returned
material through the node-local credential store and let the supervisor reload
or restart under its service manager; old connected supervisors receive
authentication failures until they pick up the rotated credential. Revocation
marks all active credentials for the deployment node as revoked, appends a
credential event, and causes future supervisor authentication with that material
to fail. Password grant and static bearer runner modes remain development or
break-glass flows, not the normal product operating model.

Start and restart also require model admission. The supervisor reports hardware
capability and recent performance samples. The backend records a model-admission
decision for each worker, and the Operations UI disables production Start and
Restart when admission is `unknown` or `unsupported`. Manual macOS lab workers
are explicitly labeled as a production-admission bypass because the operator is
starting the process directly from a terminal.

### First-Run Deployment UI And Diagnostics

After the supervisor package or service files are installed on a node, normal
setup moves to Control -> Deployment:

1. create a short-lived pairing session for the central node or selected edge
   node
2. claim the session from the installed supervisor so the credential is written
   into the local credential store
3. verify the node row reports the expected OS, service manager, version,
   heartbeat, install status, and credential status
4. inspect the support bundle for service reports, lifecycle and runtime
   summaries, hardware/model-admission summaries, config references, selected
   log excerpts, and redacted diagnostics

The support bundle must redact bearer tokens, passwords, secrets, pairing
codes, and credential material. It is an operator diagnostic artifact, not a
remote-shell channel.

To verify restart behavior after a host reboot, reboot the node through the
normal OS mechanism, then return to Control -> Deployment and confirm the
service manager still reports the supervisor as running with a fresh heartbeat.
On Linux this proves the `systemd` unit is enabled and its restart policy works.
On macOS this proves the `launchd` daemon loaded at boot. For production
Compose/appliance mode, confirm the supervisor container is healthy after Docker
starts and that the Deployment row receives a new service report.

### MacBook Pro Or iMac + Jetson Pilot Interpretation

When a MacBook Pro or iMac is used as the master and the Jetson is used as
edge, treat the result as a pilot proving the product flow:

- sign in and configure the site on the macOS master
- run central camera workers on the macOS master for comparison
- move one camera to Jetson edge mode
- confirm Live, History, Operations, and Evidence Desk all continue to work

That setup answers whether the product behaves correctly on the intended split
architecture. It does not answer final production availability, backup, TLS, or
packaged installer questions. Those belong to the Linux master production
deployment.

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
3. Choose the source type and evidence storage posture for one or two cameras.
4. Connect those cameras first.
5. Define the first production incident rules for each scene from Control ->
   Scenes.
6. Validate live viewing, telemetry, privacy behavior, incidents, evidence
   clips, trigger rule summaries, ledger context, and history.
7. Validate Operations runtime truth: desired worker count, node health, worker
   heartbeat freshness, rule count/hash/readiness, and last-error reporting.
8. Only then add the rest of the site’s cameras.

### Production lifecycle requirements

Before calling a site production-ready, the deployment needs:

- central supervisor for central and hybrid workers
- edge supervisor for Jetson-owned workers
- systemd, launchd, or production container ownership for each supervisor
- UI-created one-time pairing material for central and edge nodes
- node-bound credentials that are scoped, rotated, revocable, and not embedded
  as long-lived bearer tokens in service files
- credential rotation tested end to end, including credential-store pickup on
  central and edge supervisor services
- worker heartbeat with per-camera runtime state
- hardware capability reports from every central and edge supervisor
- model admission reports before production Start or Restart
- restart policy after worker crash or device reboot
- drain behavior for planned maintenance
- logs and metrics visible from the central observability stack
- backup and restore procedure for Postgres/TimescaleDB and incident object storage
- scoped supervisor credentials with rotation path

### Camera Source And Evidence Storage Choices

Choose RTSP for network cameras that the central or edge worker can reach over a
stable network path. Choose edge USB/UVC when the camera is attached directly to
a Jetson or other edge node, when the site has constrained uplink, or when the
raw camera feed should remain local to the site. USB/UVC cameras must be assigned
to an edge node and run in `edge` processing mode because `/dev/video*` exists on
that node, not on the master.

For a quick pilot with one USB camera, `usb:///dev/video0` is acceptable. For a
production installation, map the camera to a stable path under `/dev/v4l/by-id/`
or `/dev/v4l/by-path/`, then record the mapping in the site handoff. Avoid
depending on enumeration order when multiple capture devices, hubs, or JetPack
updates are involved.

Choose evidence storage by operational responsibility:

| Storage choice | Choose when | Backup and review implication |
|---|---|---|
| Edge local | clips should stay at the site, uplink is limited, or privacy policy requires local custody | the edge node needs retention, disk monitoring, and backup/export procedure |
| Central MinIO | the master is the normal review and retention point | central object storage backup covers event clips |
| Cloud/S3-compatible | off-site retention, managed lifecycle, or multi-site evidence custody is required | bucket lifecycle, IAM, encryption, and egress cost become production responsibilities |
| Local first | edge should record immediately and upload later when available | operators must track local-only artifacts until upload succeeds |

The Evidence Desk can review local-only edge clips as accountable artifacts when
recording is enabled. A local-only artifact should still have its incident,
scene contract, privacy manifest, and ledger context centrally visible; only the
clip bytes may remain on the edge node until retrieval or upload.

### Incident Rule Choices

Create incident rules in Control -> Scenes because rules are scene semantics:
they bind model vocabulary, zones, confidence thresholds, severity, action, and
cooldown to one camera worker. Use Control -> Operations to confirm that the
worker has loaded the enabled rules and is reporting the expected active rule
count, effective hash, latest rule event, and load status.

Choose `record_clip` as the default rule action when the incident must be
reviewable. The rule action does not choose storage by itself; the camera's
recording policy and evidence storage profile decide whether clip and optional
snapshot artifacts are written locally, to edge local storage, central
MinIO/S3-compatible storage, cloud S3-compatible storage, or local-first storage.

After a rule fires, Intelligence -> Evidence should show the trigger rule
summary with the incident type, severity, action, cooldown, rule hash, scene
contract hash, and detection context. Prompt-To-Policy may later draft rule
changes, but operators must approve and apply those changes explicitly; prompt
workflows are not allowed to auto-apply production rules.

### Supervisor And Hardware Admission Operation

The hardware-admission MVP has two parts:

- supervisors post capability/performance reports through
  `POST /api/v1/operations/supervisors/{supervisor_id}/hardware-reports`
- the control plane evaluates a worker with
  `POST /api/v1/operations/workers/{camera_id}/model-admission/evaluate`

For central ownership, run one central supervisor on the master host with a
stable `supervisor_id`, no `edge_node_id`, and access to the same worker runtime
environment as central camera workers. For edge ownership, run one supervisor on
the edge node with both a stable `supervisor_id` and the node's `edge_node_id`.
The runnable pilot supervisor is `argus.supervisor.runner`. It reports host
capability on startup, scrapes worker metrics when configured, evaluates
admission before Start/Restart, and owns only direct child worker processes. Do
not invent a browser/API shell bridge as a shortcut.

Development fallback / break-glass macOS central smoke command:

```bash
cd /Users/yann.moren/vision/backend
TOKEN="PUT_FRESH_ADMIN_OR_SUPERVISOR_TOKEN_HERE"
python3 -m uv run python -m argus.supervisor.runner \
  --supervisor-id central-macos \
  --role central \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN" \
  --worker-metrics-url http://127.0.0.1:9108/metrics \
  --once
```

Development fallback / break-glass Jetson edge smoke command:

```bash
cd "$HOME/vision"
export ARGUS_SUPERVISOR_ID="jetson-lab-1"
export ARGUS_EDGE_NODE_ID="PUT_EDGE_NODE_UUID_HERE"
export ARGUS_API_BASE_URL="http://PUT_MACBOOK_OR_IMAC_IP_HERE:8000"
export ARGUS_API_BEARER_TOKEN="$JETSON_TOKEN"
docker compose -f infra/docker-compose.edge.yml --profile supervisor \
  up -d --no-build mediamtx nats-leaf otel-collector supervisor
```

Run the named `supervisor` service, not a broad `--profile supervisor up`,
because the manual `inference-worker` service remains available and also binds
the worker metrics port. Stop the supervisor with:

```bash
docker compose -f infra/docker-compose.edge.yml stop supervisor
```

After the first hardware report, Control -> Operations should show the
supervisor host profile and model admission as `supported` when the backend is
available but no p95/p99 performance sample exists yet. After a worker has run
long enough to expose metrics, the next report should move matching models to
`recommended` or `degraded` based on p95 against the stream frame budget.

Known limitation: this MVP starts and stops workers that are direct children of
the supervisor process. It does not yet manage systemd units, Kubernetes pods,
or Docker daemon lifecycle outside its own container/process tree.

Interpret admission statuses this way:

| Status | Meaning | Production Start/Restart |
|---|---|---|
| `recommended` | backend is available and recent p95 fits the frame budget | allowed |
| `supported` | backend is available, but no matching performance sample exists yet | allowed, watch the first run |
| `degraded` | fallback can run, but recent p95 exceeds the frame budget | allowed with warning |
| `unsupported` | required backend/artifact/target profile is missing or unsafe | blocked |
| `unknown` | no fresh hardware report exists for the target supervisor/node | blocked |

Examples:

- macOS with CoreML and a fixed-vocab YOLO26n model should normally be
  `recommended` or `supported` when CoreML is reported.
- Jetson with a validated TensorRT artifact should prefer the TensorRT runtime
  and report `recommended` after p95 fits the stream frame budget.
- CPU/ONNX fallback is acceptable for small fixed-vocab models only when p95
  stays inside the stream budget; otherwise it becomes `degraded`.
- open-world YOLOE on CPU-only hardware at 720p10 or higher should be
  `unsupported`, with a recommendation to use a smaller fixed-vocab model or a
  hardware-backed runtime.

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

### Product installer path

Use [product-installer-and-first-run-guide.md](/Users/yann.moren/vision/docs/product-installer-and-first-run-guide.md) for the normal installed flow:

1. install Linux master or macOS master locally
2. complete `/first-run`
3. pair central and Jetson edge nodes from Control -> Deployment
4. validate lifecycle from Control -> Operations
5. run reboot, support bundle, credential rotation, upgrade, and uninstall
   checks

### Development fallback: local/dev control plane

```bash
make dev-up
docker compose -f infra/docker-compose.dev.yml exec backend \
  uv run alembic upgrade head
corepack pnpm --dir frontend generate:api
```

### Development fallback: local/dev shutdown

```bash
make dev-down
```

### Development fallback: edge single-node bring-up

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
