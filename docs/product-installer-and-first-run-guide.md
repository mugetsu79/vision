# Vezor / OmniSight Installation Guide

This is the single canonical installer-managed guide for Vezor / OmniSight. It
supersedes the narrower MacBook Pro + Jetson installer guide and the earlier
first-run-only installer guide.

Use this document for:

- MacBook Pro master installation
- Linux master installation
- Jetson edge installation
- model download, export, and placement
- first-run, node pairing, camera setup, validation, support bundles, upgrades,
  and uninstall

The legacy manual/dev path is archived because it intentionally uses
development Docker Compose commands and copied short-lived dev tokens:

- manual/dev path:
  [archive/macbook-pro-jetson-portable-demo-install-guide.md](/Users/yann.moren/vision/archive/macbook-pro-jetson-portable-demo-install-guide.md)

This document is deliberately explicit. It covers host preparation, models,
first-run, node pairing, camera setup, validation, support bundles, upgrades,
and the source-checkout details that are easy to miss.

## Start Here: Fast Install

Use `bin/vezor` as the normal operator front door. It delegates to the
host-appropriate installer and local service tools while keeping one happy path
in the docs.

From the release checkout on the master host:

```bash
sudo ./bin/vezor install master --public-url http://MASTER_HOST_OR_IP:3000
./bin/vezor ctl bootstrap-master --api-url http://MASTER_HOST_OR_IP:8000 --rotate-local-token --json
./bin/vezor ctl bootstrap-platform --api-url http://MASTER_HOST_OR_IP:8000 --rotate-local-token --json
./bin/vezor status
./bin/vezor validate
```

Open `http://MASTER_HOST_OR_IP:3000/first-run`, use the returned
`vzboot_...` token, and create the tenant and first admin account.

For a Jetson or Linux edge node, create a one-time pairing session in Control
-> Deployment, then run on the edge host:

```bash
sudo ./bin/vezor install edge \
  --api-url http://MASTER_HOST_OR_IP:8000 \
  --session-id PAIRING_SESSION_ID \
  --pairing-code PAIRING_CODE \
  --edge-name jetson-portable-1
```

The master installer copies the bundled YOLO26n and YOLO26s ONNX artifacts into
the installed model directory. After first-run, use Models -> Catalog to
register `/models/yolo26n.onnx` and `/models/yolo26s.onnx`, then use Models ->
Edge distribution and Models -> Runtime artifacts for node assignment, model
sync, TensorRT builds, and open-vocab scene artifacts. Use the manual
model-export sections only for local development, comparison, or break-glass
recovery.

The lower-level `installer/macos/install-master.sh`,
`installer/linux/install-master.sh`, `installer/linux/install-edge.sh`, and
`vezorctl` commands remain documented below for reference, automation, and
break-glass support. Prefer the wrapper commands above for new installs.

## Scope And Product Rules

The installer path is for normal product operation:

1. install a master appliance on macOS or Linux
2. complete first-run from the UI
3. pair central and edge nodes from Control -> Deployment
4. manage model registration, model sync, runtime artifacts, stream settings,
   worker runtime policy, and support bundle review from the UI
5. operate cameras and workers from Control -> Scenes and Control -> Operations
6. validate Live, History, Evidence, Sites, Configuration, Link Performance,
   FleetOps, and Deployment

The browser and backend are a control plane. They must not become a remote
shell. Host installation and diagnostics happen locally on the host through
`vezor`, the underlying installer, or `vezorctl`.

Normal installed operation must not depend on:

- copied long-lived bearer tokens
- foreground terminal supervisor processes
- hand-run development Docker Compose commands
- WebGL
- DeepStream or Task 24 work before Track A/B Jetson soak evidence exists

### Core Link Performance Packaging And Smoke

The installed product includes the Core Link Performance workspace at `/links`.
Use it to validate generic site link posture outside FleetOps:

- edge sites can own link paths, budgets, policies, monitoring targets, manual
  samples, queues, backend synthetic checks, and edge-agent samples
- the Vezor master/control-plane site is target-only and must not expose local
  link path or probe configuration
- edge-agent ICMP sequence probes can post source-side packet-count samples
- edge-agent UDP sequence probes can measure against an authenticated
  cooperating reflector
- master installers create the deterministic Core Link
  `vezor-speed-test-64MiB.bin` payload and `.sha256` sidecar for authenticated
  throughput smoke checks
- edge installers run one initial edge-agent sample with throughput enabled when
  the master edge-agent config exposes the installed payload URL, cap, and SHA
- post-install throughput checks are explicit manual operator actions, not
  interval jobs

The master appliance includes disabled-by-default reflector settings and UDP
port mapping support. A real reflector listener requires
`ARGUS_LINK_REFLECTOR_ENABLED=true`, `ARGUS_LINK_REFLECTOR_SECRET`, and an
edge-reachable public address in the master backend environment before startup.
The current UI exposes profile enable/disable/rotate controls and target
metadata, and reconciles profile changes into the running backend listener. A
later product hardening pass should add paired edge-agent credentials,
reflector secret distribution, and service packaging.

### FleetOps Pack Packaging And Smoke

Vezor FleetOps is the first product runtime pack in this installer path. The
pack manifest lives at `packs/maritime-fleet/pack.yaml`; installed backend
images must build from `/opt/vezor/current` so `backend/Dockerfile` can copy the
top-level `packs/` directory into the image. The FleetOps frontend routes
`/fleetops`, `/fleetops/vessels`, `/fleetops/evidence`, `/fleetops/billing`,
`/fleetops/support`, and `/fleetops/onboarding` must ship with the generated
OpenAPI client entries for maritime, fleet, link, billing, support, and
`/api/v1/packs/maritime-fleet/runtime`.

The installed product smoke for FleetOps covers the MacBook or Linux master plus
the normal Jetson edge path: create a vessel-linked site, apply the gangway
template, ingest AIS and managed-link terminal state, exercise link budgets and
queues, export a maritime evidence pack, record billable usage, run an invoice,
generate a support bundle, request a supervisor-polled `ssh_reverse` support
tunnel, close break-glass access, and run onboarding checks. FleetOps billing
uses the core billing baseline with the `maritime-fleet` entitlement, FleetOps
meters, and invoice/export records; it does not introduce a payment processor or
accounting integration.

Home/lab validation remains a packless, non-product path unless a later product
decision changes that status. `packs/traffic-public-space/pack.yaml` is packaged
as a manifest-only reference and must not be treated as an installed runtime
pack in this guide.

## Current Source Reality

The current source tree contains installer scripts, service templates, Compose
appliance profiles, first-run APIs, node pairing, credential storage, service
status contracts, support bundle redaction, and UI surfaces. It is not yet a
signed final package.

Latest implementation checkpoint validated before the main merge:

```text
89a8be22 Tighten live rendition UX and Jetson guidance
```

That checkpoint includes the installed Jetson NATS leaf path, LAN HTTP Keycloak
compatibility, second-scene worker startup fixes, and the Live scene delete
action, plus live rendition switching, tile sizing, configuration guidance, and
Jetson reduced-rendition handling. If Jetson worker logs show stale behavior such as
`Connect call failed ('127.0.0.1', 4222)` or a second scene failing because the
worker metrics port is already bound, update the checkout and rerun the relevant
installer; the installed compose environment or image is stale.

For source validation from a checkout, `/opt/vezor/current` must be on the
current release branch, tag, or `main` at a commit that includes the package
wrapper commands:

```bash
test -x /opt/vezor/current/bin/vezor
test -x /opt/vezor/current/bin/vezor-master
test -x /opt/vezor/current/bin/vezor-edge
test -x /opt/vezor/current/bin/vezorctl
```

If `/opt/vezor/current/bin` is missing, the checkout under `/opt/vezor/current`
is older than this guide. Update that checkout before rerunning install:

```bash
cd /opt/vezor/current
git fetch origin
git switch main
git pull --ff-only origin main
```

Then rerun the wrapper checks above.

Final production packages will include:

- signed macOS `.pkg` and Linux `.deb` or `.rpm` artifacts
- `/opt/vezor/current/bin/vezor`, `vezor-master`, `vezor-edge`, and `vezorctl`
- pinned image digests and manifest verification
- generated `/etc/vezor` configs, secrets, NATS config, and MediaMTX config
- rollback metadata
- an operator-visible model import path, or a packaged model bundle

## Reference Topologies

### Portable Demo

```text
MacBook Pro M4 Pro
  Vezor master appliance
  browser UI
  optional central RTSP camera
  local evidence, database, auth, NATS, MinIO, MediaMTX

LAN or travel router

Jetson Orin edge node
  Vezor edge appliance
  local MediaMTX relay
  edge supervisor
  one RTSP or USB/UVC camera first
```

### Production-Like Linux Master

```text
Linux amd64 master
  Vezor master appliance under systemd
  persistent /var/lib/vezor data
  operator browser from LAN or VPN

Jetson Orin edge node
  Vezor edge appliance under systemd
  local camera access
```

## Worksheet

Fill this in before you start:

| Item | Value |
|---|---|
| Source ref or release | `main` or release tag |
| Master type | `macos` or `linux-amd64` |
| Master hostname | |
| Master LAN IP | |
| Master public URL | `http://MASTER_IP:3000` |
| Master API URL | `http://MASTER_IP:8000` |
| First admin email | |
| First admin first name | |
| First admin last name | |
| Tenant name | |
| Central supervisor id | value chosen in first-run, for example `100` |
| Jetson hostname | |
| Jetson LAN IP | |
| Jetson edge name | `jetson-portable-1` |
| Site name | `Portable Demo Site` |
| First Jetson camera | |
| Optional central camera | |
| Model directory | `/var/lib/vezor/models` |
| Default model | `/models/yolo26n.onnx` |

## Hardware And Network Prerequisites

MacBook Pro master:

- Apple Silicon or Intel macOS supported by Docker Desktop
- Docker Desktop installed and running
- administrator access
- at least 8 GB Docker memory, 12-16 GB preferred
- enough disk for models, evidence clips, database, object storage, and images
- sleep disabled during the demo

Linux master:

- Linux `amd64`
- systemd
- Docker Engine or Podman with Compose compatibility
- open ports for frontend, API, auth, evidence object storage, and MediaMTX
- persistent disk mounted where `/var/lib/vezor` lives

Jetson edge:

- Jetson Orin Nano Super 8 GB or stronger Orin-class target
- JetPack 6.x compatible CUDA/TensorRT stack
- Docker and NVIDIA Container Toolkit
- camera access tested from the Jetson host
- stable power supply and cooling
- `nvpmodel` and `jetson_clocks` available

Network:

- MacBook/Linux master and Jetson on the same LAN for the portable kit
- DHCP reservations if possible
- Jetson can reach master API on port `8000`
- browser can reach master frontend on port `3000`
- master can reach Jetson MediaMTX RTSP on port `8554`
- browser can complete MediaMTX WebRTC ICE on UDP port `8189`
- VPN and firewall rules checked before the demo

## Model Files And Formats

### The Short Version

Start with one fixed-vocab ONNX model:

```text
/var/lib/vezor/models/yolo26n.onnx
```

Register it as:

```text
/models/yolo26n.onnx
```

The Linux master appliance bundles `yolo26n.onnx` and `yolo26s.onnx` in
`installer/assets/models/`. During install, the bundle is copied into
`/var/lib/vezor/models/` and mounted into containers at `/models`.
First-run smoke validation must register `/models/yolo26n.onnx` and
`/models/yolo26s.onnx`; falling back to YOLO11 is a BLOCKED result for the
YOLO26 bundle check.

Add open-vocab `.pt` models only after the first fixed-vocab camera works
through Live, History, Evidence, and Operations. Target-specific runtime
artifacts are covered with the node installation that owns them.

### Supported Source Files

| File in `/var/lib/vezor/models` | Capability | Use |
|---|---|---|
| `yolo26n.onnx` | fixed vocab | default fast detector |
| `yolo26s.onnx` | fixed vocab | higher quality after baseline works |
| `yolo11n.onnx` | fixed vocab | stable fallback |
| `yolo11s.onnx` | fixed vocab | balanced fallback |
| `yolo12n.onnx` | fixed vocab | lab compatibility fallback |
| `yoloe-26n-seg.pt` | open vocab | preferred experimental open-vocab source |
| `yoloe-26s-seg.pt` | open vocab | higher quality open-vocab source |
| `yolov8s-worldv2.pt` | open vocab | smaller open-vocab fallback |

### Where To Get Optional Models

The installed master path already bundles `yolo26n.onnx` and `yolo26s.onnx`.
Use the export flow below only when preparing optional fallback, comparison, or
open-vocab models.

Use official Ultralytics weights and exports:

- Ultralytics export docs:
  `https://docs.ultralytics.com/modes/export/`
- YOLOE docs:
  `https://docs.ultralytics.com/models/yoloe/`
- YOLO-World docs:
  `https://docs.ultralytics.com/models/yolo-world/`

Prepare an export environment on the machine that has internet:

```bash
mkdir -p "$HOME/vezor-model-export"
cd "$HOME/vezor-model-export"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "ultralytics>=8.0" onnx onnxruntime onnxsim
mkdir -p models
```

Export fixed-vocab ONNX files:

```bash
python - <<'PY'
from pathlib import Path
from ultralytics import YOLO

Path("models").mkdir(exist_ok=True)
for name in ("yolo26n", "yolo26s", "yolo11n", "yolo11s", "yolo12n"):
    try:
        model = YOLO(f"{name}.pt")
        output = Path(model.export(format="onnx", imgsz=640, simplify=True, opset=17))
        target = Path("models") / f"{name}.onnx"
        output.replace(target)
        print(f"wrote {target}")
    except Exception as exc:
        print(f"skipped {name}: {exc}")
PY
```

Download open-vocab `.pt` files:

```bash
python - <<'PY'
from pathlib import Path
from shutil import copy2
from ultralytics import YOLO, YOLOWorld

Path("models").mkdir(exist_ok=True)
for name in ("yoloe-26n-seg.pt", "yoloe-26s-seg.pt"):
    try:
        YOLO(name)
        copy2(name, Path("models") / name)
        print(f"wrote models/{name}")
    except Exception as exc:
        print(f"skipped {name}: {exc}")

try:
    YOLOWorld("yolov8s-worldv2.pt")
    copy2("yolov8s-worldv2.pt", "models/yolov8s-worldv2.pt")
    print("wrote models/yolov8s-worldv2.pt")
except Exception as exc:
    print(f"skipped yolov8s-worldv2.pt: {exc}")
PY
```

Copy the exported files to the master host:

```bash
sudo install -d -m 0755 /var/lib/vezor/models
sudo rsync -av "$HOME/vezor-model-export/models/" /var/lib/vezor/models/
sudo chmod -R a+rX /var/lib/vezor/models
```

## Prepare The Source Checkout

On every master host being validated from source:

```bash
cd "$HOME"
git clone https://github.com/mugetsu79/vision.git
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only origin main
uv python install 3.12
uv sync --project installer --python 3.12
sudo mkdir -p /opt/vezor
sudo ln -sfn "$HOME/vision" /opt/vezor/current
```

Validate installer artifacts before installing:

```bash
cd /opt/vezor/current
make verify-installers
```

Confirm the local wrapper entrypoints are present:

```bash
test -x /opt/vezor/current/bin/vezor
test -x /opt/vezor/current/bin/vezor-master
test -x /opt/vezor/current/bin/vezor-edge
test -x /opt/vezor/current/bin/vezorctl
```

If they are not present, update `/opt/vezor/current` to the latest source ref
or release tag and rerun `make verify-installers`.

For a Jetson with only the operating system installed, use the dedicated
Jetson bootstrap section below before trying `cd /opt/vezor/current`.

## Install A macOS Master

Use this for the portable MacBook Pro pilot.

On the MacBook:

If you previously ran the development stack on the same Mac, stop it before
installing so TCP ports `3000`, `8000`, `8080`, `8554`, `8888`, `8889`, and
`9000`, plus UDP port `8189`, belong to the installed appliance:

```bash
echo "Development fallback cleanup" && docker compose -f infra/docker-compose.dev.yml down
```

The macOS installer now refuses to continue when those ports are already
occupied by another service. That is intentional; otherwise the browser may
open an old development backend and skip first-run.

When using `installer/manifests/dev-example.json`, the installer builds the
local backend image from `/opt/vezor/current` with `backend/Dockerfile` so
repo-level pack manifests are included, and builds the frontend image from
`/opt/vezor/current/frontend`, before launchd starts the appliance. This avoids
pulling private or unpublished development images. The first run can take
several minutes because Docker has to build the backend and frontend images.

```bash
cd /opt/vezor/current
sudo ./bin/vezor install master \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://127.0.0.1:3000" \
  --data-dir /var/lib/vezor
```

Expected high-level output:

```text
Building local Vezor master images for dev manifest...
...
Starting local Vezor master containers...
...
Vezor macOS master install complete.
Open the first-run UI: http://127.0.0.1:3000/first-run
```

The installer creates the local service config, image env file, generated
secrets, NATS config, MediaMTX config, and central supervisor config under
`/etc/vezor`, builds the dev images when using the dev manifest, starts the
containers synchronously, then registers `com.vezor.master` through launchd for
future boots. On macOS the secret files are kept at `root:staff 0640` so Docker
Desktop can mount them into the appliance containers. The installer also
repairs Docker-writable state directories such as `/var/lib/vezor/postgres`,
`/var/lib/vezor/redis`, `/var/lib/vezor/nats`, and `/var/lib/vezor/minio` so
they are owned by the invoking macOS console user. This is required because
Docker Desktop containers cannot reliably initialize databases, object storage,
or JetStream state under root-owned macOS bind mounts. Bound appliance config
files such as `/etc/vezor/master.json` and `/etc/vezor/supervisor.json` are also
made Docker-readable.

Validate service state:

```bash
sudo launchctl print system/com.vezor.master
curl -fsS http://127.0.0.1:8000/healthz
docker ps --filter name=vezor-master
```

The `docker ps` output must show `vezor-master` containers. If it only shows
`infra-*` containers, you are still talking to the development stack, not the
installed master.

If `docker ps --filter name=vezor-master` is empty, inspect the service logs:

```bash
tail -160 /var/log/vezor/master.err.log
tail -160 /var/log/vezor/master.log
```

`pull access denied` or `403 Forbidden` for `ghcr.io/vezor/*` means the install
tree is stale; pull the latest source ref or release tag and rerun the installer
so the dev manifest uses locally built images.

`invalid mount config ... /private/etc/vezor/secrets/... permission denied`
also means the install tree is stale; the current macOS installer repairs
existing secret file ownership and mode before starting containers.

Open:

```text
http://127.0.0.1:3000/first-run
```

## Install A Linux Master

Use this for production-like validation.

On the Linux master:

When using `installer/manifests/dev-example.json`, the Linux installer also
builds the local master images before systemd starts the appliance.

```bash
cd /opt/vezor/current
sudo ./bin/vezor install master \
  --version "pilot-2026-05" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://MASTER_HOST_OR_IP:3000" \
  --data-dir /var/lib/vezor \
  --config-dir /etc/vezor
```

The installer creates `/etc/vezor/master.json`, `/etc/vezor/supervisor.json`,
`/etc/vezor/master.env`, generated secret files, NATS config, and MediaMTX
config, then starts `vezor-master.service`.

The master installer also creates a generated central supervisor credential in
`/etc/vezor/secrets/central_supervisor_credential` and mirrors it into
`/var/lib/vezor/credentials/supervisor.credential`. First-run registers only
the hashed credential for the central deployment node, so the installed central
supervisor can poll lifecycle requests and report runtime state without an
operator pasting a bearer token.

Validate:

```bash
systemctl status vezor-master.service
curl -fsS http://127.0.0.1:8000/healthz
```

Open:

```text
http://MASTER_HOST_OR_IP:3000/first-run
```

## Complete First-Run

Generate a short-lived local bootstrap token on the master host:

```bash
/opt/vezor/current/bin/vezor ctl bootstrap-master \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

Use the returned `vzboot_...` token in `/first-run`, then create:

- tenant name
- first admin email
- first admin password
- first admin first name
- first admin last name
- master node name
- optional central supervisor id

After first-run completes, sign in and open Control -> Deployment.

If the token expires, rotate another local token from the master host. Do not
try to mint bootstrap tokens from another machine.

`/opt/vezor/current/bin/vezorctl` remains available as the lower-level utility
for automation and break-glass support; new operator docs prefer
`/opt/vezor/current/bin/vezor ctl ...`.

## Bootstrap First Platform Superadmin

After first-run completes, generate a local one-time platform bootstrap token
on the master host:

```bash
/opt/vezor/current/bin/vezor ctl bootstrap-platform \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

Open `http://MASTER_HOST_OR_IP:3000/platform-bootstrap`, use the returned
`vzplat_...` token, and create the first platform superadmin account. Platform
superadmins sign in through the platform sign-in flow and can create tenants
and tenant users from the Users area. Tenant admins remain scoped to their
tenant.

Rotating a platform bootstrap token revokes earlier unconsumed platform
bootstrap tokens. Mint platform bootstrap tokens only from the master host.

## Register Models For Installed Product Testing

Installed containers see model files at `/models/<filename>`. Register model
rows with `/models/...` paths.

Current source validation still uses the backend model registration script.
Treat this as installer/bootstrap administration, not normal day-to-day
operation. Once model rows exist, camera setup and worker operation happen from
the UI.

Use a fresh admin access token for the installed tenant. This token is separate
from the first-run bootstrap token and separate from node pairing codes. It is
short-lived; if you come back later, generate a new one.

The final packaged product should replace this CLI token flow with an
operator-visible model import path or packaged model bundle.

### Validation CLI Token Client

Current first-run provisioning creates or repairs the `argus-cli` direct-grant
client and tenant-claim mappers for the installed tenant realm. Use the script
below only when validating an older install or when the fresh admin token is
missing `tenant` or `tenant_id` claims.

```bash
sudo -v

export KC_URL="http://127.0.0.1:8080"
export KC_REALM="argus-dev"

export KC_ADMIN_TOKEN="$(
  curl -fsS -X POST "$KC_URL/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=password" \
    --data-urlencode "client_id=admin-cli" \
    --data-urlencode "username=$(sudo cat /etc/vezor/secrets/keycloak_admin_username)" \
    --data-urlencode "password=$(sudo cat /etc/vezor/secrets/keycloak_admin_password)" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

export ARGUS_CLI_CLIENT_UUID="$(
  curl -fsS "$KC_URL/admin/realms/$KC_REALM/clients?clientId=argus-cli" \
    -H "Authorization: Bearer $KC_ADMIN_TOKEN" \
  | python3 -c 'import json,sys; items=json.load(sys.stdin); print(items[0]["id"] if items else "")'
)"

export ARGUS_CLI_CLIENT_PAYLOAD='{
  "clientId": "argus-cli",
  "name": "Vezor CLI bootstrap",
  "enabled": true,
  "publicClient": true,
  "protocol": "openid-connect",
  "standardFlowEnabled": false,
  "directAccessGrantsEnabled": true
}'

if [ -z "$ARGUS_CLI_CLIENT_UUID" ]; then
  curl -fsS -X POST "$KC_URL/admin/realms/$KC_REALM/clients" \
    -H "Authorization: Bearer $KC_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$ARGUS_CLI_CLIENT_PAYLOAD"
else
  curl -fsS -X PUT "$KC_URL/admin/realms/$KC_REALM/clients/$ARGUS_CLI_CLIENT_UUID" \
    -H "Authorization: Bearer $KC_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$ARGUS_CLI_CLIENT_PAYLOAD"
fi
```

### Each Time: Generate A Fresh Admin Access Token

Run this when you are ready to register models. Use the admin email and password
you created in first-run:

```bash
export ARGUS_API_BASE_URL="http://127.0.0.1:8000"
export KC_URL="http://127.0.0.1:8080"
export KC_REALM="argus-dev"

printf "Vezor admin email: "
read VEZOR_ADMIN_USERNAME

printf "Vezor admin password: "
stty -echo
read VEZOR_ADMIN_PASSWORD
stty echo
echo

export VEZOR_ADMIN_ACCESS_TOKEN="$(
  curl -fsS -X POST "$KC_URL/realms/$KC_REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=password" \
    --data-urlencode "client_id=argus-cli" \
    --data-urlencode "username=$VEZOR_ADMIN_USERNAME" \
    --data-urlencode "password=$VEZOR_ADMIN_PASSWORD" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
```

The token must include tenant context. If API calls with this token are
rejected, decode the token payload locally and confirm it contains `tenant` or
`tenant_id`; then confirm the `argus-cli` client has the user-attribute protocol
mappers and that you are using the first-run admin account, not the Keycloak
master admin account.

### Alternative: Copy A Token From The Browser Session

For installer validation, you can also copy the short-lived admin access token
from the signed-in browser session instead of using the temporary CLI client.
Use this only for installer/admin validation. Do not paste the token into chat,
screenshots, docs, tickets, or shell history.

1. Sign in to the installed master UI as the first-run admin account.
2. Open browser DevTools.
   - Chrome/Edge: View -> Developer -> Developer Tools, then Console.
   - Safari: enable Develop menu first, then Develop -> Show JavaScript
     Console.
3. Paste this in the Console:

```javascript
const entry = Object.entries(localStorage).find(
  ([key]) => key.startsWith("oidc.user:") && key.endsWith(":argus-frontend"),
);

if (!entry) {
  throw new Error("No argus-frontend OIDC session found. Sign in first.");
}

const user = JSON.parse(entry[1]);
console.log("expires", new Date(user.expires_at * 1000).toLocaleString());
copy(user.access_token);
```

The Console printing `undefined` after `copy(user.access_token)` is normal; it
means the helper copied the token to your clipboard. The important output is
the `expires` line. If the expiry is close or already past, sign in again and
repeat the snippet.

On the MacBook host, load the copied token into the current shell:

```bash
export ARGUS_API_BASE_URL="http://127.0.0.1:8000"
export VEZOR_ADMIN_ACCESS_TOKEN="$(pbpaste)"
```

If you copied the token on the MacBook but need to run an admin command from
the Jetson, paste it into the Jetson shell without echoing it:

```bash
export ARGUS_API_BASE_URL="http://<macbook-master-ip>:8000"
read -rsp "Vezor admin access token: " VEZOR_ADMIN_ACCESS_TOKEN
export VEZOR_ADMIN_ACCESS_TOKEN
echo
```

Sanity-check the token before running registration commands:

```bash
curl -fsS \
  -H "Authorization: Bearer $VEZOR_ADMIN_ACCESS_TOKEN" \
  "$ARGUS_API_BASE_URL/api/v1/models" >/dev/null
```

If this returns `401`, the browser token expired or was copied from the wrong
browser profile/session. Sign in again and copy a fresh token.

### Register From The Backend Container

Run registration from the backend container. The installed backend container
sees the model volume at `/models`, while the macOS host sees the same files at
`/var/lib/vezor/models`.

Define a helper:

```bash
register_model() {
  local catalog_id="$1"
  local artifact_path="$2"

  docker exec \
    -e ARGUS_API_BASE_URL \
    -e VEZOR_ADMIN_ACCESS_TOKEN \
    vezor-master-backend-1 sh -lc '
    /app/.venv/bin/python -m argus.scripts.register_model_preset \
      --catalog-id "$1" \
      --artifact-path "$2" \
      --api-base-url "$ARGUS_API_BASE_URL" \
      --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN"
  ' sh "$catalog_id" "$artifact_path"
}
```

Register both bundled fixed-vocab models for the first-run bundle check:

```bash
register_model yolo26n-coco-onnx /models/yolo26n.onnx
register_model yolo26s-coco-onnx /models/yolo26s.onnx
```

A successful registration prints a JSON model response that includes an `id`,
`name`, `path`, `sha256`, and `size_bytes`. If the command prints nothing, the
installed backend image is too old for this guide; pull the latest source ref or
`main`, rerun the master installer so the backend image is rebuilt, and run the
registration command again.

Optional fixed-vocab models:

```bash
register_model yolo11n-coco-onnx /models/yolo11n.onnx
```

Use YOLO11 only for fallback comparison after the YOLO26 bundle check is already
accounted for. It is not a substitute for registering and validating the bundled
YOLO26n/YOLO26s models.

Optional open-vocab model:

```bash
register_model yoloe-26n-open-vocab-pt /models/yoloe-26n-seg.pt
```

If registration returns `401`, generate a fresh `VEZOR_ADMIN_ACCESS_TOKEN` and
retry. If it returns `403`, the account is authenticated but does not have the
tenant `admin` role. If it says the file is missing, confirm the file exists on
the host under `/var/lib/vezor/models` and inside the container under
`/models`.

Confirm the UI sees the models:

1. Open Control -> Scenes.
2. Create a temporary scene.
3. Confirm the primary model dropdown includes the registered model.
4. Cancel or delete the temporary scene if it was only a check.

You can also confirm the installed database has model rows:

```bash
docker exec vezor-master-postgres-1 sh -lc \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select name, version, path from models order by name, version;"'
```

## Pair The Central Supervisor

From Control -> Deployment:

1. Create or select the central master node.
2. Click Pair central.
3. Copy both fields from the pairing panel:
   - `Session ID`
   - `Pairing code`

The short value such as `wabV2jeN` is only the pairing code. It is not enough
by itself because `vezor ctl pair` also needs the session id. If your UI shows
only the code, pull the latest source ref or release tag, rerun the master
installer to rebuild the frontend, and create a new pairing session.

On the master host:

```bash
sudo /opt/vezor/current/bin/vezor ctl pair \
  --api-url "http://127.0.0.1:8000" \
  --session-id "PAIRING_SESSION_ID" \
  --pairing-code "PAIRING_CODE" \
  --supervisor-id "CENTRAL_SUPERVISOR_ID_FROM_FIRST_RUN" \
  --hostname "$(hostname)" \
  --config /etc/vezor/supervisor.json \
  --credential-path /var/lib/vezor/credentials/supervisor.credential
```

Use the central supervisor id that first-run created. If you entered `100`
during first-run, use `--supervisor-id "100"`. Do not use
`central-master-1` unless that is the id shown for the central node in
Control -> Deployment.

The host stores the credential under `/var/lib/vezor/credentials`; the product
containers see that same directory mounted read-only as `/run/vezor/credentials`.
The credential file must contain only one raw `vzcred_...` value. If an older
build wrote the full JSON claim response into
`/var/lib/vezor/credentials/supervisor.credential`, repair it once before
restart:

```bash
sudo python3 - <<'PY'
import json
from pathlib import Path

path = Path("/var/lib/vezor/credentials/supervisor.credential")
payload = json.loads(path.read_text(encoding="utf-8"))
material = payload.get("credential_material")
if not isinstance(material, str) or not material.startswith("vzcred_"):
    raise SystemExit("credential file does not contain credential_material")
path.write_text(material + "\n", encoding="utf-8")
path.chmod(0o600)
PY
```

If `/etc/vezor/supervisor.json` still has the installer default
`central-master-1` but your central node is `100`, align the config:

```bash
sudo python3 - <<'PY'
import json
from pathlib import Path

path = Path("/etc/vezor/supervisor.json")
payload = json.loads(path.read_text(encoding="utf-8"))
payload["supervisor_id"] = "100"
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
```

Restart the master service:

Linux:

```bash
sudo systemctl restart vezor-master.service
```

macOS:

```bash
sudo launchctl kickstart -k system/com.vezor.master
```

Return to Control -> Deployment and confirm:

- credential status is active
- service report is fresh
- install status is truthful
- support bundle redacts credential material

## Install And Pair The Jetson Edge

### Bootstrap A Bare Jetson OS

Use this when the Jetson has JetPack/Ubuntu installed but no Vezor checkout,
no `/opt/vezor/current`, and no service yet.

Reference docs:

- NVIDIA JetPack installation:
  `https://docs.nvidia.com/jetson/jetpack/install-setup/`
- NVIDIA TensorRT command-line tools:
  `https://docs.nvidia.com/deeplearning/tensorrt/latest/reference/command-line-programs.html`

First confirm the base OS is a JetPack 6.x image and the network works:

```bash
uname -m
cat /etc/nv_tegra_release 2>/dev/null || true
ping -c 3 MASTER_HOST_OR_IP
```

`uname -m` must be `aarch64`. If the Jetson is not on JetPack 6.x, install or
upgrade JetPack first, then return here.

Install the host tools used by the installer and preflight:

```bash
sudo apt update
sudo apt install -y \
  ca-certificates \
  curl \
  ffmpeg \
  git \
  gstreamer1.0-libav \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-tools \
  make \
  python3 \
  python3-pip \
  python3-venv \
  rsync
```

Install Docker, Docker Compose v2, and the NVIDIA container runtime if they are
not already present:

```bash
sudo apt install -y docker.io docker-compose-plugin nvidia-container-toolkit
sudo systemctl enable --now docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
sudo usermod -aG docker "$USER"
```

If `apt` cannot find `nvidia-container-toolkit`, the JetPack/NVIDIA package
repositories are not configured correctly. Fix the JetPack installation before
continuing.

Log out and back in, or reboot, so the Docker group change applies. Then verify:

```bash
docker info >/dev/null
docker compose version
nvidia-ctk --version
```

Install `uv` for the source installer tooling:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
```

JetPack 6.x normally leaves `/usr/bin/python3` on Python 3.10. That is fine
for OS utilities, but the Vezor installer tooling requires Python 3.12. Use
`uv ... --python 3.12` or `python3.12 -m uv ...` for installer commands; do not
use `python3 -m uv ...` on the Jetson unless `python3 --version` reports
Python 3.12.

Clone and expose the checkout as `/opt/vezor/current`:

```bash
cd "$HOME"
if [ ! -d "$HOME/vision/.git" ]; then
  git clone https://github.com/mugetsu79/vision.git
fi
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only origin main
uv sync --project installer --python 3.12

sudo mkdir -p /opt/vezor
sudo ln -sfn "$HOME/vision" /opt/vezor/current
```

Confirm the Jetson now has the expected entrypoints:

```bash
test -x /opt/vezor/current/bin/vezor && echo "vezor OK"
test -x /opt/vezor/current/bin/vezor-edge && echo "vezor-edge OK"
test -x /opt/vezor/current/bin/vezorctl && echo "vezorctl OK"
```

Run the installer validation gate on the Jetson checkout:

```bash
cd /opt/vezor/current
make verify-installers
```

Create the model directory and copy model files from the master or your export
machine. From the machine that already has the models:

```bash
rsync -av /var/lib/vezor/models/ JETSON_HOST_OR_IP:/tmp/vezor-models/
```

Then on the Jetson:

```bash
sudo install -d -m 0755 /var/lib/vezor/models
sudo rsync -av /tmp/vezor-models/ /var/lib/vezor/models/
sudo chmod -R a+rX /var/lib/vezor/models
ls -lh /var/lib/vezor/models
```

At minimum, the Jetson should have:

```text
/var/lib/vezor/models/yolo26n.onnx
```

Do not copy a TensorRT `.engine` from the MacBook to the Jetson. TensorRT
engines are tied to the Jetson hardware, JetPack, TensorRT, CUDA, and driver
stack. Build them on the Jetson that will run them, or on an identical Jetson
stack.

Now run preflight:

```bash
cd /opt/vezor/current
sudo nvpmodel -m 2
sudo jetson_clocks
./scripts/jetson-preflight.sh --installer --json
```

From the master UI:

1. Open Control -> Sites.
2. Create the physical location for the demo, for example
   `Portable Demo Site`, if it does not exist yet.
3. Open Control -> Deployment.
4. Click Pair Jetson edge.
5. Select the Site, enter the Jetson edge name, and click Create edge pairing.
6. Copy the session id and one-time pairing code.

The Sites page is the physical location layer. Sites own the time zone and are
where scenes, cameras, and edge nodes are grouped. For the portable kit, one
site is enough.

On the Jetson:

```bash
MASTER_API_URL="http://MASTER_HOST_OR_IP:8000"
JETSON_STREAM_HOST="JETSON_HOST_OR_IP_REACHABLE_FROM_MASTER"

sudo ./bin/vezor install edge \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --api-url "$MASTER_API_URL" \
  --session-id "PAIRING_SESSION_ID" \
  --pairing-code "PAIRING_CODE" \
  --edge-name "jetson-portable-1" \
  --model-dir /var/lib/vezor/models \
  --public-stream-host "$JETSON_STREAM_HOST"
```

For dev manifests, the edge installer runs Jetson preflight, resolves the
Jetson GPU ONNX Runtime wheel from `installer/manifests/dev-example.json`, and
passes the verified URL and SHA256 into `backend/Dockerfile.edge`. Use
`--jetson-ort-wheel-url` only as a manual override for exceptional validation.
Use `--allow-cpu-onnx-runtime` only for diagnostic runs that are explicitly not
product smokes.

The edge installer writes `/etc/vezor/edge.json`,
`/etc/vezor/supervisor.json`, `/etc/vezor/edge.env`, MediaMTX config, local
NATS leaf config, and the claimed supervisor credential. For paired installs,
it claims the pairing session before the long local image build so the
short-lived code is not lost while Docker downloads packages. When the manifest
release channel is `dev`, it also builds the local Jetson edge image from
`backend/Dockerfile.edge` before starting `vezor-edge.service`; this avoids
depending on unpublished `ghcr.io/vezor/*:dev` images during branch testing.

The edge installer scope is intentionally narrow: prerequisite checks, local
service/config installation, pairing claim, credential write, and supervisor
startup. It does not choose camera models, build TensorRT engines, set worker
concurrency, choose runtime preference, or configure scenes. After the service
is paired, finish all of that from Control -> Deployment, Models, and Control
-> Scenes. `--model-dir` is the local storage root that the supervisor and
worker mount; it is not a model selection or assignment flag.

`--public-stream-host` should be the Jetson LAN IP or hostname that the master
can reach. The edge supervisor reports `rtsp://HOST:8554` back to the master so
Live can relay Jetson native and processed streams through the master MediaMTX
service. If you omit it, the installer uses the first address from
`hostname -I`; pass it explicitly whenever the portable kit changes networks or
the Jetson has more than one interface.

The installer also rewrites the Jetson MediaMTX JWT JWKS endpoint to
`$MASTER_API_URL/.well-known/argus/mediamtx/jwks.json`. Do not leave the edge
MediaMTX config pointing at `http://backend:8000`; that hostname only exists
inside the master compose network and will cause master-to-Jetson stream relay
requests to fail with `401 Unauthorized`.

The installer also creates a local `vezor-edge-nats-leaf` container. Edge
workers connect to `nats://nats-leaf:4222` inside the Jetson compose network;
that leaf node connects back to the master leaf listener at
`nats://MASTER_HOST_OR_IP:7422`. Do not point edge workers at
`nats://127.0.0.1:4222`; inside the worker container, `127.0.0.1` is the worker
container itself and will produce `ConnectionRefusedError`.

The Jetson ONNX Runtime GPU wheel is required for the portable product path.
For dev manifests, the installer resolves the compatible `cp310` Linux
`aarch64` wheel from the manifest and Jetson preflight JSON. The installer only
allows a CPU ONNX Runtime fallback when you explicitly pass
`--allow-cpu-onnx-runtime`; treat that as a diagnostic escape hatch, not as a
demo or production mode.

Validate:

```bash
systemctl status vezor-edge.service
/opt/vezor/current/bin/vezor status --json
docker ps --filter name=vezor
docker logs --tail 60 vezor-edge-nats-leaf
```

Back in Control -> Deployment, confirm:

- service manager is `systemd`
- service state is fresh
- credential status is active
- hardware report arrives
- edge configuration revision is current or reports a clear apply error
- Models -> Edge distribution can see the node inventory after a sync job
- Models -> Runtime artifacts can queue target-profile builds for the node
- model admission can evaluate the Jetson camera
- `vezor-edge-nats-leaf` is running and does not log repeated master leaf
  connection failures

### Optional: Build A Jetson TensorRT Engine

Skip this until the basic ONNX path is stable. The camera still selects the
ONNX model row. The `.engine` is attached later as a target-specific runtime
artifact and must never be selected as the primary scene model.

Preferred path: open Models -> Runtime artifacts, select the source ONNX model,
Jetson node, and `linux-aarch64-nvidia-jetson` target profile, then queue the
TensorRT build from the UI. The supervisor builds on the Jetson and reports job
status and artifact inventory back to the master. Use the command-line steps
below only when debugging TensorRT tooling directly on the Jetson or importing a
prebuilt artifact.

Diagnostic command-line build on the Jetson:

```bash
cd /var/lib/vezor/models
ls -lh yolo26n.onnx
```

Install the TensorRT command-line builder if `trtexec` is not available on the
host. JetPack may include TensorRT runtime libraries without putting `trtexec`
on the normal shell path.

```bash
command -v trtexec || true
dpkg -l | grep -Ei 'tensorrt|nvinfer'

sudo apt update
sudo apt install -y libnvinfer-bin

dpkg -L libnvinfer-bin | grep trtexec
```

On JetPack 6.2 / TensorRT 10.3 this usually installs:

```text
/usr/src/tensorrt/bin/trtexec
```

Build the FP16 engine from the static 640x640 ONNX export:

```bash
rm -f /var/lib/vezor/models/yolo26n.jetson.fp16.engine

/usr/src/tensorrt/bin/trtexec \
  --onnx=/var/lib/vezor/models/yolo26n.onnx \
  --saveEngine=/var/lib/vezor/models/yolo26n.jetson.fp16.engine \
  --fp16
```

Do not pass `--shapes=images:1x3x640x640` for the default exported
`yolo26n.onnx`; it is a static-shape ONNX model and TensorRT will reject
explicit shape overrides with `Static model does not take explicit shapes`.

A first build can take several minutes while TensorRT profiles tactics. A
successful run should include lines similar to:

```text
Engine generation completed
Created engine with size
&&&& PASSED TensorRT.trtexec
```

Verify the engine file and sanity-load it:

```bash
ls -lh /var/lib/vezor/models/yolo26n.jetson.fp16.engine

/usr/src/tensorrt/bin/trtexec \
  --loadEngine=/var/lib/vezor/models/yolo26n.jetson.fp16.engine
```

### Optional: CLI Register Jetson Runtime Artifact And Soak Evidence

Only do this after the basic ONNX path is stable through camera setup, Live,
History, Evidence, and Operations.

Normal installed operation should use Models -> Runtime artifacts to create and
track the artifact. Attach a manually built Jetson TensorRT engine to the ONNX
model row only for break-glass registration or when comparing a prebuilt engine
against the UI-created artifact:

The commands below are admin/control-plane scripts from the backend project.
They use Python 3.12 because the backend project is pinned to Python 3.12.
This does not change the Jetson worker runtime: the installed edge worker image
still uses Python 3.10 so it can load the Jetson `cp310` ONNX Runtime GPU wheel.
These scripts only hash files and call the master API; actual TensorRT
compatibility is proven by `trtexec --loadEngine` and by the worker running the
camera.

Resolve the real model id from the master API. Do not use the literal
`THE_YOLO26N_MODEL_ID` placeholder.

```bash
export MODEL_ID="$(
  curl -fsS \
    -H "Authorization: Bearer $VEZOR_ADMIN_ACCESS_TOKEN" \
    "$ARGUS_API_BASE_URL/api/v1/models" |
    python3 -c 'import json, sys
payload = json.load(sys.stdin)
models = payload.get("items", payload) if isinstance(payload, dict) else payload
print(next(model["id"] for model in models if model.get("name") == "YOLO26n COCO" or "YOLO26n" in model.get("name", "")))'
)"
echo "$MODEL_ID"
```

The backend project declares dependencies in groups, so these one-off admin
script commands add `httpx` explicitly. Use the registered model row's class
inventory when attaching a fixed-vocab artifact. Do not pass a reduced class
subset such as only `person`, `car`, `bus`, and `truck`; the API rejects that
because the artifact must match the source model inventory exactly.

```bash
cd /opt/vezor/current/backend
uv run --python 3.12 --with httpx python - <<'PY'
import json
import os
from pathlib import Path

import httpx

from argus.scripts.build_runtime_artifact import (
    build_fixed_vocab_artifact_payload,
)

api = os.environ["ARGUS_API_BASE_URL"].rstrip("/")
token = os.environ["VEZOR_ADMIN_ACCESS_TOKEN"]
model_id = os.environ["MODEL_ID"]
headers = {"Authorization": f"Bearer {token}"}

models_response = httpx.get(f"{api}/api/v1/models", headers=headers, timeout=30)
models_response.raise_for_status()
models = models_response.json()
model = next(item for item in models if item["id"] == model_id)

payload = build_fixed_vocab_artifact_payload(
    source_model_path=Path("/var/lib/vezor/models/yolo26n.onnx"),
    prebuilt_engine_path=Path("/var/lib/vezor/models/yolo26n.jetson.fp16.engine"),
    classes=list(model["classes"]),
    input_shape=dict(model["input_shape"]),
    target_profile="linux-aarch64-nvidia-jetson",
)
response = httpx.post(
    f"{api}/api/v1/models/{model_id}/runtime-artifacts",
    headers=headers,
    json=payload,
    timeout=30,
)
if response.is_error:
    print(response.text)
response.raise_for_status()
artifact = response.json()
print(json.dumps(artifact, indent=2, sort_keys=True))
Path("/tmp/vezor-runtime-artifact.env").write_text(
    f"export ARTIFACT_ID='{artifact['id']}'\n"
    f"export ARTIFACT_SHA256='{artifact['sha256']}'\n",
    encoding="utf-8",
)
print("wrote /tmp/vezor-runtime-artifact.env")
PY
```

Validate on the same Jetson:

```bash
source /tmp/vezor-runtime-artifact.env

uv run --python 3.12 --with httpx python -m argus.scripts.validate_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN" \
  --model-id "$MODEL_ID" \
  --artifact-id "$ARTIFACT_ID" \
  --artifact-path /var/lib/vezor/models/yolo26n.jetson.fp16.engine \
  --expected-sha256 "$ARTIFACT_SHA256" \
  --target-profile linux-aarch64-nvidia-jetson \
  --host-profile linux-aarch64-nvidia-jetson
```

Then run a real soak before recording a pass:

- at least one Jetson camera
- real camera source
- stable worker lifecycle
- Live visible
- telemetry present
- one evidence clip reviewed
- no repeated worker crashes
- no credential/service regression

Record the soak only after the run happened:

```bash
curl -s -X POST "$ARGUS_API_BASE_URL/api/v1/runtime-artifacts/soak-runs" \
  -H "Authorization: Bearer $VEZOR_ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"edge_node_id\": \"$EDGE_NODE_ID\",
    \"runtime_artifact_id\": \"$ARTIFACT_ID\",
    \"operations_assignment_id\": \"$WORKER_ASSIGNMENT_ID\",
    \"runtime_selection_profile_id\": \"$RUNTIME_SELECTION_PROFILE_ID\",
    \"hardware_report_id\": \"$HARDWARE_REPORT_ID\",
    \"model_admission_report_id\": \"$MODEL_ADMISSION_REPORT_ID\",
    \"status\": \"passed\",
    \"started_at\": \"$SOAK_STARTED_AT\",
    \"ended_at\": \"$SOAK_ENDED_AT\",
    \"metrics\": {
      \"duration_minutes\": 60,
      \"worker_restarts\": 0,
      \"evidence_clip_reviewed\": true
    },
    \"notes\": \"Installer-managed MacBook/Linux master plus Jetson edge soak passed.\"
  }"
```

Do not start Task 24 / DeepStream until Track A/B Jetson soak evidence exists
or the risk is explicitly accepted.

## Configure Cameras From The UI

Use Control -> Scenes.

Recommended first setup:

1. Confirm the site exists, for example `Portable Demo Site`.
2. Add one Jetson camera.
3. Set processing mode to `edge`.
4. Assign the Jetson edge node in the camera source step.
5. Use a source the Jetson can open directly:
   - RTSP URL reachable from the Jetson, or
   - USB/UVC if the camera is physically attached to the Jetson.
6. Choose the fixed-vocab ONNX model first, usually `YOLO26n COCO`.
7. Choose active classes or leave the full fixed vocabulary active.
8. Configure privacy.
9. Configure include/exclusion regions if needed.
10. Enable event clips if Evidence validation is part of the test.
11. Add one simple rule that can be triggered safely.
12. Save.

For native stream delivery, keep native. Do not select dedicated reduced
resolution or frame-rate profiles when the stream profile is native. Reduced
profiles are for worker-published processed viewing renditions.

Add a second Jetson camera only after the first camera survives the complete
validation loop.

Optional MacBook central camera:

- use RTSP, not direct MacBook USB, for the installed product path
- set processing mode to central
- choose the same ONNX model row if the master can read `/models/yolo26n.onnx`

## Operate Workers From Control -> Operations

Open Control -> Operations.

For each camera:

1. confirm the assigned node is correct
2. confirm model admission is `recommended`, `supported`, or `degraded`
3. do not start if admission is `unknown` or `unsupported`
4. click Start
5. verify runtime state and heartbeat
6. verify delivery diagnostics
7. verify rule runtime status
8. click Restart and confirm a new runtime report arrives
9. click Stop or Drain when done

Normal installed operation should show lifecycle controls. It should not ask
the operator to paste a bearer token or leave a foreground supervisor terminal
running.

## Validate The Whole Product

Run this checklist before taking the kit to a demo.

Start with deterministic smoke. This mode must register the bundled
`/models/yolo26n.onnx` and `/models/yolo26s.onnx` models and must not fall back
to YOLO11 for the YOLO26 bundle check:

```bash
scripts/validation/whole_product_live_smoke.py \
  --api-url http://127.0.0.1:8000 \
  --report /tmp/vezor-whole-smoke/report.json \
  --real-rtsp none
```

Use real RTSP only after deterministic smoke passes. Store camera URLs in a
local env file outside the repository and source it before running. Keep real
camera URLs local and uncommitted; the local-only env var names are
`VEZOR_SMOKE_REAL_RTSP_720P_URL` and
`VEZOR_SMOKE_REAL_RTSP_1296P_URL`.

```bash
set -a
. /tmp/vezor-real-camera.env
set +a
scripts/validation/whole_product_live_smoke.py \
  --api-url http://127.0.0.1:8000 \
  --report /tmp/vezor-whole-smoke/report-real-720p.json \
  --real-rtsp 720p
```

Deployment:

- `/deployment` loads
- central master node is present
- Jetson edge node is present
- credentials are active
- service reports are fresh
- support bundles redact token-like and credential-like values

Sites:

- create a throwaway location
- edit it
- delete it

Scenes:

- create one Jetson camera
- save source, model, privacy, regions, recording policy, rules, and stream
  delivery
- verify native profile does not allow reduced profile conflicts
- edit the camera and save again

Configuration:

- evidence storage profile is selected
- stream delivery profile is selected
- runtime selection profile is selected
- privacy policy profile is selected
- LLM provider can remain unconfigured unless prompt workflows are in the demo

Operations:

- worker lifecycle controls are enabled only where an installed supervisor owns
  the worker
- model admission is visible
- hardware report is visible
- restart and stop update runtime state truthfully

Live:

- Jetson camera video renders
- browser delivery has no normal fetch errors
- telemetry overlays update

History:

- telemetry buckets populate
- camera filters work
- class filters match the selected model or runtime vocabulary

Evidence:

- incident rows open
- right-side camera links do not route to errors
- clip artifacts are reviewable
- review and reopen state persists

Reboot:

```bash
sudo reboot
```

After reboot:

Linux master:

```bash
systemctl status vezor-master.service
curl -fsS http://127.0.0.1:8000/healthz
```

macOS master:

```bash
sudo launchctl print system/com.vezor.master
curl -fsS http://127.0.0.1:8000/healthz
```

Jetson:

```bash
systemctl status vezor-edge.service
```

A reboot test passes only when the system returns without copied bearer tokens
or foreground terminal supervisors.

## Support Bundle And Diagnostics

Use Control -> Deployment first. For a local redaction check:

```bash
/opt/vezor/current/bin/vezor ctl support-bundle \
  --input /var/lib/vezor/support/latest.json \
  --redact \
  --json
```

Use `vezor ctl doctor` locally:

```bash
/opt/vezor/current/bin/vezor ctl doctor --json
```

Never send unredacted bundles outside the trusted operator boundary.

## Upgrade

Source checkout upgrade:

1. stop the master or edge service
2. update `/opt/vezor/current`
3. restart the service
4. validate `/healthz`
5. validate Deployment, Operations, Live, History, Evidence, Sites, and
   Configuration
6. restart one worker from Control -> Operations

Linux:

```bash
sudo systemctl stop vezor-master.service
cd /opt/vezor/current
git fetch origin
git pull --ff-only origin main
sudo systemctl start vezor-master.service
```

macOS:

```bash
cd /opt/vezor/current
git fetch origin
git pull --ff-only origin main
sudo ./bin/vezor install master \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://127.0.0.1:3000" \
  --data-dir /var/lib/vezor
```

Jetson edge source update:

```bash
sudo systemctl stop vezor-edge.service
cd /opt/vezor/current
git fetch origin
git pull --ff-only origin main

sudo ./bin/vezor install edge \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --api-url "$MASTER_API_URL" \
  --unpaired \
  --edge-name "jetson-portable-1" \
  --model-dir /var/lib/vezor/models \
  --public-stream-host "$JETSON_STREAM_HOST"
```

Use the same source ref on the master and Jetson. While validating a pre-merge
branch, replace `main` with that branch name on both hosts. Use `--unpaired`
only after the Jetson has already paired successfully and
`/etc/vezor/supervisor.json` contains an `edge_node_id`; otherwise create a
fresh Pair Jetson edge session from Deployment and rerun the paired install
command.

Final packages should use signed package upgrades with rollback metadata
instead of git pulls.

## Uninstall

Linux master:

```bash
cd /opt/vezor/current
sudo ./installer/linux/uninstall.sh
```

macOS master:

```bash
cd /opt/vezor/current
sudo ./installer/macos/uninstall.sh
```

Default uninstall preserves `/var/lib/vezor` and `/etc/vezor`. To delete data,
you must provide the confirmation string:

```bash
sudo ./installer/linux/uninstall.sh --purge-data delete-vezor-data
sudo ./installer/macos/uninstall.sh --purge-data delete-vezor-data
```

For a Jetson edge source install:

```bash
sudo systemctl stop vezor-edge.service
sudo systemctl disable vezor-edge.service
sudo rm -f /etc/systemd/system/vezor-edge.service
sudo systemctl daemon-reload
```

Preserve `/var/lib/vezor/models` unless you intentionally want to recopy model
files.

## Troubleshooting

For a short recovery checklist when Operations reports a running scene but the
Live page is blank, or when a rendition change appears stuck, use
[live-video-troubleshooting.md](/Users/yann.moren/vision/docs/live-video-troubleshooting.md).

### The installer service does not start

Check wrapper commands first:

```bash
ls -l /opt/vezor/current/bin/vezor /opt/vezor/current/bin/vezor-master /opt/vezor/current/bin/vezor-edge
```

If they are missing, update `/opt/vezor/current` to a newer source checkout or
release tag. The installer service files call these local wrappers directly.

### The backend cannot see a model file

Installed containers see:

```text
/models/<filename>
```

The host stores:

```text
/var/lib/vezor/models/<filename>
```

Fix the model row if it points to `$HOME/vision/models/...` in an installed
deployment.

### macOS install stops on an unhealthy Postgres container

If the installer prints `dependency failed to start: container
vezor-master-postgres-1 is unhealthy`, inspect the container log:

```bash
docker logs vezor-master-postgres-1 --tail 80
```

When the log contains `chmod` or `chown` permission errors under
`/var/lib/postgresql/data`, the host data directory was prepared in a way Docker
Desktop cannot write through. Pull the latest source ref or release tag and
rerun the macOS installer. The installer stops the partial appliance and repairs
ownership for the Docker-writable state directories automatically.
Do not replace this with a development-stack compose flow.

### macOS install stops on an unhealthy NATS container

If the NATS log says `Server is ready` but Docker still reports
`vezor-master-nats-1 is unhealthy`, inspect the container health log:

```bash
docker inspect -f '{{json .State.Health}}' vezor-master-nats-1
```

The installable compose healthcheck must use `/nats-server` directly because the
official NATS image does not include `wget`, `curl`, or a shell. Pull the latest
source ref or release tag and rerun the installer if the health log mentions
`exec: "wget": executable file not found`.

### Backend is unhealthy during Alembic migrations

Inspect the backend log:

```bash
docker logs vezor-master-backend-1 --tail 120
```

If Alembic is trying to connect to `localhost:5432` from inside the backend
container, the backend image is too old to read `/run/secrets/ARGUS_DB_URL`.
Pull the latest source ref or release tag and rerun the installer so the local
backend image is rebuilt.

If the log says `extension "timescaledb" is not available`, the master was
started with a plain PostgreSQL image. The installable master must use a
TimescaleDB PostgreSQL image because the migrations create Timescale extensions,
hypertables, and aggregates. Pull the latest source ref or `main` and rerun the
installer; the dev manifest now uses `timescale/timescaledb:latest-pg16`.

If the PostgreSQL log says `extension "timescaledb" must be preloaded`, the data
directory was created before the TimescaleDB preload setting was enforced. Pull
the latest source ref or `main` and rerun the installer; the master compose
profile now starts PostgreSQL with `shared_preload_libraries=timescaledb`, so upgraded data
directories do not need manual `postgresql.conf` edits.

### Keycloak restarts on first boot

If `docker logs vezor-master-keycloak-1` repeatedly says the `--optimized` flag
was used on the first server start, pull the latest source ref or release tag
and rerun the installer. First boot must use `start`; optimized mode is only
valid after a Keycloak build step.

If the log says PostgreSQL requested SCRAM authentication but no password was
provided, the Keycloak container is too old or using stale compose config that
expects `KC_DB_PASSWORD_FILE`. Pull the latest source ref or `main` and rerun
the installer; Keycloak now exports the mounted secret file into `KC_DB_PASSWORD` before
starting.

### Supervisor is unhealthy before first-run pairing

Before first-run completes, the installed supervisor has local credential
material but the backend may not have registered its hash yet. It should stay
alive and report healthy while waiting for first-run to bind that credential to
the central deployment node. If the health log says
`unrecognized arguments: --healthcheck`, `Supervisor API bearer token is not
configured`, or `Invalid supervisor credential` after first-run, pull the latest
source ref or `main`, rerun the installer, and confirm the central supervisor id
in `/etc/vezor/supervisor.json` matches the central deployment node.

### The Jetson says the TensorRT engine is invalid

In the normal UI path, open Models -> Runtime artifacts and read the failed
build job error before retrying. Rebuild the engine on the same Jetson and same
JetPack/TensorRT stack. If you manually registered a prebuilt artifact, rerun
`validate_runtime_artifact` and only record a soak pass after validation and
runtime operation both succeed.

If `trtexec` fails with `Static model does not take explicit shapes`, remove
the `--shapes=...` argument. The default Vezor `yolo26n.onnx` export is already
static at 640x640.

### Model or edge lifecycle setup fails after install

Use these checks before rerunning the installer:

- Model import job failed hash check: verify the expected SHA/source in Models
  -> Catalog, confirm the file exists under the mounted model directory, and
  retry the import only after the mismatch is understood.
- Model assigned but not synced: open Models -> Edge distribution, confirm the
  node credential is active in Control -> Deployment, start a new sync job, and
  confirm the supervisor can poll lifecycle jobs.
- TensorRT build failed on Jetson: inspect the Models -> Runtime artifacts job
  error, verify TensorRT/CUDA/trtexec on the Jetson, confirm the source model is
  synced locally, and rebuild for `linux-aarch64-nvidia-jetson`.
- Open-vocab artifact stale after vocabulary edit: save the scene vocabulary,
  then queue a new scene artifact from Models -> Runtime artifacts.
- Edge configuration revision failed to apply: read the apply error in Control
  -> Deployment, revert unsupported fields, and wait for the supervisor's next
  configuration report.
- Node credential cannot poll jobs: confirm credential status is active, rotate
  the node credential if needed, check the edge clock and API URL, and restart
  `vezor-edge.service` after the credential store is corrected.

### Live works centrally but not from the Jetson

Check:

- master can reach `rtsp://JETSON_IP:8554`
- Jetson local NATS leaf is running and the supervisor/worker environment uses
  `ARGUS_NATS_URL=nats://nats-leaf:4222`
- Jetson service is running
- Jetson MediaMTX is exposing the camera path
- Jetson MediaMTX is using the master JWKS URL, not
  `http://backend:8000/.well-known/argus/mediamtx/jwks.json`
- the camera setup has the Jetson edge node assigned, not only an Operations
  worker binding
- Control -> Deployment shows a fresh Jetson heartbeat with service manager
  `systemd`
- stream delivery profile is not forcing a reduced profile while native is
  selected
- the browser is using the master frontend URL, not a stale IP from another
  network

Useful checks on the Jetson:

```bash
docker ps --filter name=vezor
docker logs --tail 120 vezor-supervisor
docker logs --tail 80 vezor-edge-nats-leaf
curl -fsS http://127.0.0.1:9997/v3/paths/list
```

If `vezor-supervisor` logs `Connect call failed ('127.0.0.1', 4222)`, the edge
compose environment is stale. Pull the latest source ref or release tag and
rerun `./bin/vezor install edge`; the installed worker must inherit
`ARGUS_NATS_URL=nats://nats-leaf:4222`.

If `vezor-supervisor` can post fleet, service, hardware, and runtime reports but
the worker process exits with:

```text
GET /api/v1/cameras/<camera-id>/worker-config "HTTP/1.1 401 Unauthorized"
```

the worker-config endpoint is rejecting the paired supervisor credential. Pull
the latest source ref or release tag on the master, rerun the master installer
so the backend image includes the route fix, then rerun the Jetson edge
installer as an unpaired update.

If the same endpoint returns:

```text
GET /api/v1/cameras/<camera-id>/worker-config "HTTP/1.1 422 Unprocessable Entity"
Privacy policy residency does not match evidence storage residency
```

and the camera's evidence recording is disabled, the master backend image is
older than the disabled-recording residency fix. Pull the latest source ref or
release tag on the master and rerun the master installer so the backend image no
longer blocks live workers on an unused evidence storage profile.

### Jetson edge reinstall says installer ports are already in use

The edge installer stops the existing `vezor-edge` appliance before Jetson
preflight checks ports. During branch upgrades, an older `/etc/vezor/edge.env`
may be missing new compose variables, which can prevent an old script from
rendering the new edge compose file during `down`. Pull the latest source ref or
`main` and rerun the installer; current installers export transition-safe image
variables and remove stale product-owned edge containers before preflight.

If you need to clear the stale containers before pulling the fixed installer,
run this on the Jetson:

```bash
cd /opt/vezor/current

sudo env \
  VEZOR_MEDIAMTX_IMAGE=bluenviron/mediamtx:latest \
  VEZOR_NATS_IMAGE=nats:2 \
  VEZOR_SUPERVISOR_IMAGE=vezor/edge-worker:portable-demo \
  /opt/vezor/current/bin/vezor-edge down --config /etc/vezor/edge.json || true

sudo docker rm -f vezor-supervisor vezor-edge-mediamtx vezor-edge-nats-leaf || true
```

Then rerun `./bin/vezor install edge`. Do not delete `/var/lib/vezor/models` or
`/var/lib/vezor/credentials` for this case.

If the portable network changed, rerun the edge installer with
`--unpaired --public-stream-host JETSON_NEW_IP_OR_HOSTNAME` so the existing
credential is preserved and the supervisor reports the new stream relay base
URL. Use `--unpaired` only after one successful paired install has written
`edge_node_id` into `/etc/vezor/supervisor.json`; the installer refuses
unpaired updates when that paired identity is missing.

### The edge node cannot pair

Check:

- the pairing code has not expired
- the session id matches the UI row
- Jetson can reach `http://MASTER_HOST_OR_IP:8000/healthz`
- the edge install command uses the same master URL shown in the worksheet

If an older installer expired the pairing session after a long Jetson image
build, that attempt usually built `vezor/edge-worker:portable-demo` but did not
claim a credential or complete the systemd service install. Pull the latest
source ref or `main` on the Jetson, create a fresh Pair Jetson edge session in
the UI, and rerun `./bin/vezor install edge` with the new session id and pairing
code. The current dev-manifest installer resolves the Jetson GPU ONNX Runtime
wheel automatically from manifest and preflight data.

### The edge node pairs but has no heartbeat

`vezor-edge.service` is a systemd oneshot wrapper around Docker Compose, so
`active (exited)` is normal. Check the containers and supervisor logs:

```bash
docker ps --filter name=vezor
docker logs --tail 120 vezor-supervisor
ls -l /etc/vezor/edge.json /etc/vezor/supervisor.json
sudo ls -l /var/lib/vezor/credentials/supervisor.credential
```

The supervisor config should be world-readable because it contains no secret,
and the credential file should be owned by container UID `10001` with mode
`0600`. If the log says `edge supervisor config requires edge_node_id`, or if a
normal `vezor status --json` cannot read `/etc/vezor/supervisor.json`, pull
the latest source ref or `main`, create a fresh Pair Jetson edge session, and
rerun the edge installer without `--unpaired`. A current installer preserves the claimed
`edge_node_id` during later unpaired updates, fixes config permissions, and
makes the credential readable only to the non-root supervisor container user.

If a rerun fails preflight because TCP ports `8554`, `8888`, or `8889`, or UDP
port `8189`, are already in use, the previous edge MediaMTX container is still
running. Pull the latest source ref or `main` and rerun the installer; the
updated installer stops the existing `vezor-edge.service` and Compose stack
before preflight so the port checks see a clean host.

### A demo network change breaks the kit

Recompute the master and Jetson IPs, update the worksheet, restart services,
and repeat the Jetson health check before opening the product in front of
others.
