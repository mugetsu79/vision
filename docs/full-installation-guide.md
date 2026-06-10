# Vezor Full Installation Guide

Date: 2026-06-10
Version: 2026.1

This guide installs Vezor as a product-mode deployment: one master/control
plane, optional Jetson edge nodes, first-run tenant bootstrap, platform
superadmin bootstrap, model registration, TensorRT runtime artifacts, and a
whole-product smoke.

For expanded break-glass detail, see
[product-installer-and-first-run-guide.md](product-installer-and-first-run-guide.md).

## Supported Topologies

- **Linux master plus Jetson edge**: recommended pilot and production direction.
- **macOS master plus Jetson edge**: portable lab or demo topology.
- **Local development stack**: developer-only fallback through `make dev-up`.

The installed product path should not depend on pasted bearer tokens, foreground
worker terminals, or manual Keycloak administration.

## Secrets And Safety

Do not commit or paste:

- raw RTSP URLs with credentials
- bearer tokens
- first-run bootstrap tokens
- platform bootstrap tokens
- node credentials
- reflector secrets
- sudo passwords
- Keycloak admin secrets

Use examples such as:

```text
rtsp://<username>:<password>@CAMERA_HOST:8554/ch1
```

## Master Prerequisites

On the master host:

- Docker or compatible container engine
- Docker Compose v2
- Python 3.12 and `uv`
- Node 22 and Corepack for local builds
- network reachability from operator browsers to frontend, backend, and
  Keycloak
- network reachability from edge nodes to backend and NATS leaf port
- enough disk for Postgres, MinIO evidence, model artifacts, and support
  bundles

On Linux production pilots, prefer a stable host IP or DNS name. On macOS lab
pilots, make sure the public URL you use is reachable by both the browser and
the Jetson.

## Install The Master

From a release checkout on the master:

```bash
cd /opt/vezor/current
sudo ./bin/vezor install master --public-url http://MASTER_HOST_OR_IP:3000
./bin/vezor status
```

The installer writes local service configuration, container compose inputs,
runtime secrets, and supervisor configuration. It also configures the master UDP
reflector profile for Core Link when the deployment environment enables it.

Validate basic service health:

```bash
curl -fsS http://MASTER_HOST_OR_IP:8000/healthz
curl -fsS http://MASTER_HOST_OR_IP:3000
```

## Complete First-Run Tenant Bootstrap

Generate a one-time first-run token on the master host:

```bash
/opt/vezor/current/bin/vezor ctl bootstrap-master \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

Open:

```text
http://MASTER_HOST_OR_IP:3000/first-run
```

Use the returned `vzboot_...` token to create:

- tenant name
- first tenant admin email
- first tenant admin password
- first tenant admin first name
- first tenant admin last name
- master node name
- optional central supervisor id

After completion, sign in with the tenant account and open **Deployment**.

## Bootstrap The First Platform Superadmin

Platform superadmin is the cross-tenant role. Create the first one with a
separate local token after first-run:

```bash
/opt/vezor/current/bin/vezor ctl bootstrap-platform \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

Open:

```text
http://MASTER_HOST_OR_IP:3000/platform-bootstrap
```

Use the returned `vzplat_...` token to create the first platform superadmin.
Then go back to the sign-in page and choose **Platform sign in**.

Platform superadmins can create tenants and tenant users from **Users**. Tenant
admins remain scoped to one tenant.

## Register Bundled Models

Installed containers see model files under `/models`. Keep source model files
on the master and edge under the configured model directory, usually:

```text
/var/lib/vezor/models
```

From the UI:

1. Open **Models**.
2. On **Catalog**, register each bundled model whose artifact is present.
3. On **Registered**, confirm the source model rows are ready.
4. For Jetson scenes, open **Runtime artifacts** and build the TensorRT artifact
   against the target edge node.
5. Open **Edge distribution** and sync the source model and runtime artifact to
   the edge node.

TensorRT `.engine` files must be built on the Jetson or an identical Jetson
software stack. Do not build on the master and copy the engine to the edge.

## Install A Jetson Edge Node

On the Jetson:

```bash
sudo nvpmodel -m 2
sudo jetson_clocks
/opt/vezor/current/scripts/jetson-preflight.sh --installer --json
```

The preflight records JetPack, L4T, CUDA, TensorRT, Python ABI, Docker, NVIDIA
container runtime, FFmpeg, and GStreamer readiness.

From the master UI:

1. Open **Sites** and create or select the physical site.
2. Open **Deployment**.
3. Click **Pair Jetson edge**.
4. Select the site, enter the edge node name, and create the pairing session.
5. Copy the one-time session id and pairing code.

On the Jetson, run:

```bash
sudo /opt/vezor/current/bin/vezor install edge \
  --api-url http://MASTER_HOST_OR_IP:8000 \
  --session-id PAIRING_SESSION_ID \
  --pairing-code PAIRING_CODE \
  --edge-name EDGE_NODE_NAME \
  --model-dir /var/lib/vezor/models \
  --public-stream-host EDGE_HOST_OR_IP
```

The normal Jetson dev-manifest path resolves the Jetson GPU ONNX Runtime wheel
from the release manifest and preflight JSON. `--jetson-ort-wheel-url` remains
an override for exceptional validation. Do not use CPU ONNX Runtime for product
smokes unless the smoke is explicitly marked diagnostic-only.

The installer writes:

- `/etc/vezor/edge.json`
- `/etc/vezor/supervisor.json`
- `/etc/vezor/edge.env`
- `/etc/vezor/edge-agent.env`
- MediaMTX config
- NATS leaf config
- supervisor credential
- systemd service for `vezor-edge.service`
- systemd service file for `vezor-edge-agent.service`

Start and inspect services:

```bash
sudo systemctl status vezor-edge.service --no-pager
sudo systemctl status vezor-edge-agent.service --no-pager
```

If the edge-agent service is installed but not started by the installer, start
it after the edge package is rebuilt and paired:

```bash
sudo systemctl enable vezor-edge-agent.service
sudo systemctl start vezor-edge-agent.service
sudo systemctl status vezor-edge-agent.service --no-pager
```

## Configure Scenes

Create scenes from **Scenes**:

- central scenes use the master node for inference.
- edge scenes use the paired Jetson node for inference.
- source URIs are stored securely and are not displayed back during edit.
- class scope should match the operational use case, such as people or
  vehicles.
- browser stream profile controls what operators watch, not necessarily what
  the model receives for analytics.

After saving, use **Operations** to confirm readiness.

## TensorRT Runtime Artifact Flow

For a Jetson scene:

1. Confirm the source ONNX model is registered.
2. Confirm the Jetson node appears in **Deployment** and **Models** inventory.
3. Open **Models -> Runtime artifacts**.
4. Select source model and target node.
5. Build the TensorRT artifact.
6. Confirm the artifact is valid.
7. Sync it to the edge node.
8. Edit the edge scene and choose the TensorRT runtime.
9. Restart or let the supervisor reconcile the worker.

If TensorRT fails, preserve the job evidence and error text. Common causes are
missing model file, incompatible dynamic shape flags, missing `trtexec`, or
building on a different JetPack/TensorRT stack than the runtime target.

## Core Link And Throughput

The master can host an authenticated UDP reflector. The edge-agent retrieves
scoped config through the backend and posts packet-loss and latency samples from
the edge vantage point.

Throughput is manual. The edge installer creates the local payload support used
by the agent so operators can trigger a bandwidth sample without relying on a
generic active-connection label.

## Whole-Product Smoke

Run a fresh smoke after install, destructive reset, credential rotation, image
rebuild, or edge package change.

Minimum pass criteria:

- master frontend, backend, Keycloak, database, object store, NATS, and
  MediaMTX are healthy
- first-run tenant admin can sign in
- platform superadmin can sign in through platform sign-in
- platform superadmin can create a tenant and a tenant admin
- central supervisor is paired and reporting current service state
- Jetson edge node is paired and reporting current service state
- source models are registered
- TensorRT runtime artifact builds on Jetson
- source model and TensorRT artifact sync to Jetson
- central scene reaches stream and worker readiness
- edge scene reaches stream and worker readiness
- Live can open selected scenes
- Evidence/history have deterministic fixture or real smoke evidence
- billing usage generation is recorded when billing is in scope
- Core Link edge-agent UDP probe posts real edge-originated evidence
- support bundles redact secrets

Do not mark missing Jetson access, missing RTSP reachability, missing model
files, missing reflector secret access, missing billing usage, missing
deterministic evidence, or missing fresh-stack proof as a pass.

## Uninstall Or Reset

Use product uninstall/reset commands where available. Do not run global Docker
prune on shared machines. Do not delete unrelated Docker resources. Preserve
model files unless the reset plan explicitly says otherwise.

Before destructive reset, record:

- branch and commit
- service status
- model directory location
- support bundle or logs with secrets redacted
- known RTSP test camera placeholders
- node names and site names
