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

The manual/dev path remains separate because it intentionally uses development
Docker Compose commands and copied short-lived dev tokens:

- manual/dev path:
  [macbook-pro-jetson-portable-demo-install-guide.md](/Users/yann.moren/vision/docs/macbook-pro-jetson-portable-demo-install-guide.md)

This document is deliberately explicit. It covers host preparation, models,
first-run, node pairing, camera setup, validation, support bundles, upgrades,
and the branch-validation details that are easy to miss.

## Scope And Product Rules

The installer path is for normal product operation:

1. install a master appliance on macOS or Linux
2. complete first-run from the UI
3. pair central and edge nodes from Control -> Deployment
4. operate cameras and workers from Control -> Scenes and Control -> Operations
5. validate Live, History, Evidence, Sites, Configuration, and Deployment

The browser and backend are a control plane. They must not become a remote
shell. Host installation and diagnostics happen locally on the host through the
installer or `vezorctl`.

Normal installed operation must not depend on:

- copied long-lived bearer tokens
- foreground terminal supervisor processes
- hand-run development Docker Compose commands
- WebGL
- DeepStream or Task 24 work before Track A/B Jetson soak evidence exists

## Current Branch Reality

The `codex/omnisight-installer` branch contains installer scripts, service
templates, Compose appliance profiles, first-run APIs, node pairing, credential
storage, service status contracts, support bundle redaction, and UI surfaces.
It is not yet a signed final package.

For branch validation from a checkout, `/opt/vezor/current` must be this branch
at a commit that includes the package wrapper commands:

```bash
test -x /opt/vezor/current/bin/vezor-master
test -x /opt/vezor/current/bin/vezor-edge
test -x /opt/vezor/current/bin/vezorctl
```

If `/opt/vezor/current/bin` is missing, the checkout under `/opt/vezor/current`
is older than this guide. Update that checkout before rerunning install:

```bash
cd /opt/vezor/current
git fetch origin
git pull --ff-only origin codex/omnisight-installer
```

Then rerun the wrapper checks above.

Final production packages will include:

- signed macOS `.pkg` and Linux `.deb` or `.rpm` artifacts
- `/opt/vezor/current/bin/vezor-master`, `vezor-edge`, and `vezorctl`
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
| Branch or release | `codex/omnisight-installer` or release tag |
| Master type | `macos` or `linux-amd64` |
| Master hostname | |
| Master LAN IP | |
| Master public URL | `http://MASTER_IP:3000` |
| Master API URL | `http://MASTER_IP:8000` |
| First admin email | |
| Tenant name | |
| Central supervisor id | `central-master-1` |
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

### Where To Get The Models

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

## Prepare The Branch Checkout

On every master host being validated from source:

```bash
cd "$HOME"
git clone https://github.com/mugetsu79/vision.git
cd "$HOME/vision"
git fetch origin
git switch codex/omnisight-installer
git pull --ff-only origin codex/omnisight-installer
python3 -m uv sync --project installer
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
test -x /opt/vezor/current/bin/vezor-master
test -x /opt/vezor/current/bin/vezor-edge
test -x /opt/vezor/current/bin/vezorctl
```

If they are not present, update `/opt/vezor/current` to the latest
`codex/omnisight-installer` branch and rerun `make verify-installers`.

For a Jetson with only the operating system installed, use the dedicated
Jetson bootstrap section below before trying `cd /opt/vezor/current`.

## Install A macOS Master

Use this for the portable MacBook Pro pilot.

On the MacBook:

If you previously ran the development stack on the same Mac, stop it before
installing so ports `3000`, `8000`, `8080`, `8554`, `8888`, `8889`, and `9000`
belong to the installed appliance:

```bash
echo "Development fallback cleanup" && docker compose -f infra/docker-compose.dev.yml down
```

The macOS installer now refuses to continue when those ports are already
occupied by another service. That is intentional; otherwise the browser may
open an old development backend and skip first-run.

```bash
cd /opt/vezor/current
sudo ./installer/macos/install-master.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://127.0.0.1:3000" \
  --data-dir /var/lib/vezor
```

The installer creates the local service config, image env file, generated
secrets, NATS config, MediaMTX config, and central supervisor config under
`/etc/vezor`, then starts `com.vezor.master` through launchd.

Validate service state:

```bash
sudo launchctl print system/com.vezor.master
curl -fsS http://127.0.0.1:8000/healthz
docker ps --filter name=vezor-master
```

The `docker ps` output must show `vezor-master` containers. If it only shows
`infra-*` containers, you are still talking to the development stack, not the
installed master.

Open:

```text
http://127.0.0.1:3000/first-run
```

## Install A Linux Master

Use this for production-like validation.

On the Linux master:

```bash
cd /opt/vezor/current
sudo ./installer/linux/install-master.sh \
  --version "pilot-2026-05" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://MASTER_HOST_OR_IP:3000" \
  --data-dir /var/lib/vezor \
  --config-dir /etc/vezor
```

The installer creates `/etc/vezor/master.json`, `/etc/vezor/supervisor.json`,
`/etc/vezor/master.env`, generated secret files, NATS config, and MediaMTX
config, then starts `vezor-master.service`.

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
/opt/vezor/current/bin/vezorctl bootstrap-master \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

Use the returned `vzboot_...` token in `/first-run`, then create:

- tenant name
- first admin email
- first admin password
- master node name
- optional central supervisor id

After first-run completes, sign in and open Control -> Deployment.

If the token expires, rotate another local token from the master host. Do not
try to mint bootstrap tokens from another machine.

## Register Models For Installed Product Testing

Installed containers see model files at `/models/<filename>`. Register model
rows with `/models/...` paths.

Current branch validation still uses the backend model registration script.
Treat this as installer/bootstrap administration, not normal day-to-day
operation. Once model rows exist, camera setup and worker operation happen from
the UI.

Use an admin access token for the installed tenant. The exact token command
depends on the final packaged Keycloak realm/client configuration; for branch
validation, use the same authenticated admin session or CLI mechanism you use
for other admin API checks.

Set:

```bash
export ARGUS_API_BASE_URL="http://127.0.0.1:8000"
export VEZOR_ADMIN_ACCESS_TOKEN="REPLACE_WITH_SHORT_LIVED_ADMIN_ACCESS_TOKEN"
```

Register the default fixed-vocab model:

```bash
cd /opt/vezor/current/backend
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo26n-coco-onnx \
  --artifact-path /models/yolo26n.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN"
```

Optional fixed-vocab models:

```bash
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo26s-coco-onnx \
  --artifact-path /models/yolo26s.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN"

python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo11n-coco-onnx \
  --artifact-path /models/yolo11n.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN"
```

Optional open-vocab model:

```bash
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yoloe-26n-open-vocab-pt \
  --artifact-path /models/yoloe-26n-seg.pt \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN"
```

Confirm the UI sees the models:

1. Open Control -> Scenes.
2. Create a temporary scene.
3. Confirm the primary model dropdown includes the registered model.
4. Cancel or delete the temporary scene if it was only a check.

## Pair The Central Supervisor

From Control -> Deployment:

1. Create or select the central master node.
2. Click Pair central.
3. Copy the pairing session id and one-time pairing code.

On the master host:

```bash
/opt/vezor/current/bin/vezorctl pair \
  --api-url "http://127.0.0.1:8000" \
  --session-id "PAIRING_SESSION_ID" \
  --pairing-code "PAIRING_CODE" \
  --supervisor-id "central-master-1" \
  --hostname "$(hostname)" \
  --credential-path /var/lib/vezor/credentials/supervisor.credential
```

The host stores the credential under `/var/lib/vezor/credentials`; the product
containers see that same directory mounted read-only as `/run/vezor/credentials`.

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

Install `uv` for the branch installer tooling:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
```

Clone and expose the checkout as `/opt/vezor/current`:

```bash
cd "$HOME"
if [ ! -d "$HOME/vision/.git" ]; then
  git clone https://github.com/mugetsu79/vision.git
fi
cd "$HOME/vision"
git fetch origin
git switch codex/omnisight-installer
git pull --ff-only origin codex/omnisight-installer
uv sync --project installer

sudo mkdir -p /opt/vezor
sudo ln -sfn "$HOME/vision" /opt/vezor/current
```

Confirm the Jetson now has the expected entrypoints:

```bash
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

From Control -> Deployment on the master:

1. Create or select the Jetson edge node.
2. Start an edge pairing session for that node.
3. Copy the session id and one-time pairing code.

On the Jetson:

```bash
MASTER_API_URL="http://MASTER_HOST_OR_IP:8000"

sudo ./installer/linux/install-edge.sh \
  --api-url "$MASTER_API_URL" \
  --session-id "PAIRING_SESSION_ID" \
  --pairing-code "PAIRING_CODE" \
  --edge-name "jetson-portable-1" \
  --model-dir /var/lib/vezor/models
```

The edge installer writes `/etc/vezor/edge.json`,
`/etc/vezor/supervisor.json`, `/etc/vezor/edge.env`, MediaMTX config, and the
claimed supervisor credential, then starts `vezor-edge.service`.

Validate:

```bash
systemctl status vezor-edge.service
/opt/vezor/current/bin/vezorctl status --json
```

Back in Control -> Deployment, confirm:

- service manager is `systemd`
- service state is fresh
- credential status is active
- hardware report arrives
- model admission can evaluate the Jetson camera

### Optional: Build A Jetson TensorRT Engine

Skip this until the basic ONNX path is stable. The camera still selects the
ONNX model row. The `.engine` is attached later as a target-specific runtime
artifact and must never be selected as the primary scene model.

Build the engine on the Jetson:

```bash
cd /var/lib/vezor
python3 -m venv model-export
source model-export/bin/activate
python -m pip install --upgrade pip
python -m pip install "ultralytics>=8.0"
python - <<'PY'
from pathlib import Path
from ultralytics import YOLO

model = YOLO("/var/lib/vezor/models/yolo26n.onnx")
output = Path(model.export(format="engine", imgsz=640, half=True, device=0))
target = Path("/var/lib/vezor/models/yolo26n.jetson.fp16.engine")
output.replace(target)
print(f"wrote {target}")
PY
```

If Ultralytics export fails but TensorRT tools are installed:

```bash
trtexec \
  --onnx=/var/lib/vezor/models/yolo26n.onnx \
  --saveEngine=/var/lib/vezor/models/yolo26n.jetson.fp16.engine \
  --fp16 \
  --shapes=images:1x3x640x640
```

### Optional: Register Jetson Runtime Artifact And Soak Evidence

Only do this after the basic ONNX path is stable through camera setup, Live,
History, Evidence, and Operations.

Attach the Jetson TensorRT engine to the ONNX model row:

```bash
cd /opt/vezor/current/backend
python3 -m uv run python -m argus.scripts.build_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN" \
  --model-id "$MODEL_ID" \
  --source-model /var/lib/vezor/models/yolo26n.onnx \
  --prebuilt-engine /var/lib/vezor/models/yolo26n.jetson.fp16.engine \
  --target-profile linux-aarch64-nvidia-jetson \
  --class person --class car --class bus --class truck \
  --input-width 640 --input-height 640
```

Validate on the same Jetson:

```bash
python3 -m uv run python -m argus.scripts.validate_runtime_artifact \
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

1. Create one site, for example `Portable Demo Site`.
2. Add one Jetson camera.
3. Set processing mode to `edge`.
4. Assign the Jetson edge node.
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
/opt/vezor/current/bin/vezorctl support-bundle \
  --input /var/lib/vezor/support/latest.json \
  --redact \
  --json
```

Use `vezorctl doctor` locally:

```bash
/opt/vezor/current/bin/vezorctl doctor --json
```

Never send unredacted bundles outside the trusted operator boundary.

## Upgrade

Branch validation upgrade:

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
git pull --ff-only origin codex/omnisight-installer
sudo systemctl start vezor-master.service
```

macOS:

```bash
cd /opt/vezor/current
git fetch origin
git pull --ff-only origin codex/omnisight-installer
sudo ./installer/macos/install-master.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://127.0.0.1:3000" \
  --data-dir /var/lib/vezor
```

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

For a Jetson edge branch install:

```bash
sudo systemctl stop vezor-edge.service
sudo systemctl disable vezor-edge.service
sudo rm -f /etc/systemd/system/vezor-edge.service
sudo systemctl daemon-reload
```

Preserve `/var/lib/vezor/models` unless you intentionally want to recopy model
files.

## Troubleshooting

### The installer service does not start

Check wrapper commands first:

```bash
ls -l /opt/vezor/current/bin/vezor-master /opt/vezor/current/bin/vezor-edge
```

If they are missing, update `/opt/vezor/current` to a newer
`codex/omnisight-installer` checkout. The installer service files call these
local wrappers directly.

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

### The Jetson says the TensorRT engine is invalid

Rebuild the engine on the same Jetson and same JetPack/TensorRT stack. Then
rerun `validate_runtime_artifact` and only record a soak pass after validation
and runtime operation both succeed.

### Live works centrally but not from the Jetson

Check:

- master can reach `rtsp://JETSON_IP:8554`
- Jetson service is running
- Jetson MediaMTX is exposing the camera path
- stream delivery profile is not forcing a reduced profile while native is
  selected
- the browser is using the master frontend URL, not a stale IP from another
  network

### The edge node cannot pair

Check:

- the pairing code has not expired
- the session id matches the UI row
- Jetson can reach `http://MASTER_HOST_OR_IP:8000/healthz`
- the edge install command uses the same master URL shown in the worksheet

### A demo network change breaks the kit

Recompute the master and Jetson IPs, update the worksheet, restart services,
and repeat the Jetson health check before opening the product in front of
others.
