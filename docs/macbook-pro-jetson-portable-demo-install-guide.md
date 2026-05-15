# Vezor Portable Demo Guide: MacBook Pro Master And Jetson Edge

Use this guide when you want to carry Vezor as a portable demonstration system:

- an Apple Silicon MacBook Pro, such as an M4 Pro, as the temporary master
- one Jetson Orin edge node near the cameras
- one optional central RTSP camera processed on the MacBook
- one primary Jetson camera, with a second Jetson camera only after the first
  edge path is stable

This is the recommended path when you do not have a Linux master available yet.
Use the macOS master installer on the MacBook when validating the installer
branch; keep the Docker dev commands in this guide as development fallback and
break-glass material only. Task 24 DeepStream is intentionally deferred; keep
WebGL and DeepStream off for this validation path.

For the canonical installer-managed MacBook Pro/Linux master + Jetson guide,
including package wrapper checks, see
[product-installer-and-first-run-guide.md](/Users/yann.moren/vision/docs/product-installer-and-first-run-guide.md).

## What This Setup Proves

This portable setup proves:

- sign-in, sites, scenes, camera configuration, Live, History, Operations, and
  Evidence all work from the MacBook control plane
- the Jetson can own edge inference for at least one camera
- the MacBook backend can relay the Jetson MediaMTX stream to the browser
- event clips and Evidence review continue to work across the MacBook/Jetson
  split
- Operations and Deployment show supervisor/service/admission truth honestly
- runtime artifact soak records can capture the Jetson validation result when
  TensorRT/open-vocab artifacts are present

This setup does not prove:

- Linux master field readiness
- signed final package readiness
- long-term backup/restore policy
- multi-site scale
- DeepStream/NvDCF behavior
- final Kubernetes/systemd production operations

## Topology

```text
Operator browser on MacBook
  -> http://127.0.0.1:3000 frontend
  -> MacBook installed master appliance
       backend, Postgres, Keycloak, Redis, NATS, MinIO, MediaMTX,
       observability, optional central worker
  -> LAN / travel router
  -> Jetson Orin edge node
       edge MediaMTX, edge inference worker, optional supervisor smoke
  -> RTSP or USB/UVC camera at the site
```

For a clean portable demo, use a small travel router or a stable LAN and keep
the MacBook and Jetson on the same subnet. DHCP reservations are worth the tiny
setup cost because IP changes are the most common demo-day failure.

## Current Product Readiness

The codebase now has the control-plane pieces needed for this demo:

- Deployment page at `/deployment`
- Operations page at `/settings`
- one-time node pairing and credential rotation APIs
- service report and support bundle APIs
- supervisor credential-store boundary
- hardware report and model admission records
- runtime artifact and runtime soak records

The installer branch includes macOS master, Linux master, and Jetson edge
package artifacts. Use
[product-installer-and-first-run-guide.md](/Users/yann.moren/vision/docs/product-installer-and-first-run-guide.md)
as the primary path for the portable kit:

- MacBook Pro: `installer/macos/install-master.sh`
- Jetson: `installer/linux/install-edge.sh`
- UI: `/first-run`, then Control -> Deployment, then Control -> Operations

Copied bearer tokens and hand-run Docker Compose remain acceptable for setup
smoke tests, old lab fallback, and break-glass support in this portable guide.
They are not the normal installed product path.

## Before You Leave For The Demo

Prepare all of this before you are in front of anyone:

- MacBook charger and Jetson power supply
- travel router or known LAN
- camera power and camera network access
- repository cloned on both MacBook and Jetson
- model files under `models/` on both machines
- Docker Desktop running on the MacBook
- Docker and NVIDIA Container Toolkit working on the Jetson
- Docker images built or pulled while you still have reliable internet
- Python and Node dependencies installed on the MacBook
- a fresh pull of the branch you are demonstrating
- all migrations applied
- at least one successful Jetson edge run at your desk

Recommended first demo shape:

1. one Jetson camera in edge mode
2. optional MacBook central RTSP camera only after the Jetson path works
3. no DeepStream
4. no second Jetson camera until the first camera survives Live, History,
   Evidence, Operations, and restart checks

## Worksheet

Fill these values in before starting commands:

| Item | Value |
|---|---|
| Branch or tag | `codex/omnisight-installer` or release tag |
| MacBook LAN IP | |
| Jetson LAN IP | |
| Site name | `Portable Demo Site` |
| Optional MacBook central camera name | `MacBook Central Camera` |
| Jetson camera 1 name | `Jetson Edge Camera 1` |
| Jetson camera 2 name | |
| Primary model filename | `yolo26n.onnx` |
| Open-vocab model filename | `yoloe-26n-seg.pt` |
| Jetson supervisor id | `jetson-portable-1` |

## Model Files And Formats

Do this before installing or starting services. The demo is much easier when
the MacBook and Jetson already have the same model inventory and you have
verified the exact paths each runtime will see.

### What Vezor Expects

| File | Required | Runtime role | Register as camera model? |
|---|---:|---|---|
| `models/yolo26n.onnx` | yes | fixed-vocab COCO detector | yes |
| `models/yolo26s.onnx` | optional | higher-quality fixed-vocab COCO detector | yes |
| `models/yolo11n.onnx` | optional | stable fixed-vocab fallback | yes |
| `models/yolo11s.onnx` | optional | stable balanced fallback | yes |
| `models/yolo12n.onnx` | optional | older lab compatibility fallback | yes |
| `models/yoloe-26n-seg.pt` | optional | open-vocab discovery model | yes |
| `models/yoloe-26s-seg.pt` | optional | higher-quality open-vocab discovery model | yes |
| `models/yolov8s-worldv2.pt` | optional | smaller open-vocab fallback | yes |
| `models/yolo26n.jetson.fp16.engine` | optional | Jetson TensorRT runtime artifact | no |

Register portable camera models first: ONNX for fixed vocabulary and `.pt` for
open vocabulary. A TensorRT `.engine` is not a normal camera model. It is a
target-specific runtime artifact attached to an ONNX model after the ONNX row
exists.

### Where To Get The Weights

Use official Ultralytics weight names and let the `ultralytics` package
download them, or download the same files from the Ultralytics model pages and
place them under `models/`.

Reference pages:

- Ultralytics export guide:
  `https://docs.ultralytics.com/modes/export/`
- Ultralytics YOLOE guide:
  `https://docs.ultralytics.com/models/yoloe/`
- Ultralytics YOLO-World guide:
  `https://docs.ultralytics.com/models/yolo-world/`
- NVIDIA TensorRT command-line tools:
  `https://docs.nvidia.com/deeplearning/tensorrt/latest/reference/command-line-programs.html`
- NVIDIA JetPack installation:
  `https://docs.nvidia.com/jetson/jetpack/install-setup/`

Use a local Python environment with Ultralytics installed. For a quick export
workspace on the MacBook:

```bash
cd "$HOME/vision"
mkdir -p models
python3 -m venv .venv-model-export
source .venv-model-export/bin/activate
python -m pip install --upgrade pip
python -m pip install "ultralytics>=8.0" onnx onnxruntime onnxsim
```

If your backend `.venv` already has the vision/model-metadata dependencies, you
can use that instead:

```bash
cd "$HOME/vision/backend"
python3 -m uv sync --group runtime --group dev --group model-metadata --group vision
```

### Produce Fixed-Vocab ONNX Models

Run these commands from the checkout root on the MacBook. The first command in
each block downloads the official `.pt` file if it is not already cached; the
export command writes the ONNX model that Vezor should register.

```bash
cd "$HOME/vision"
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

At minimum, confirm:

```bash
ls -lh "$HOME/vision/models/yolo26n.onnx"
```

Use `yolo26n.onnx` for the first Jetson camera because it is the smallest and
most forgiving path. Move to `yolo26s.onnx` only after the first camera is
stable.

### Download Open-Vocab PT Models

Open-vocab models remain `.pt` in the current path because Vezor uses them for
dynamic runtime vocabulary while you are still choosing terms. Keep the
original `.pt` files:

```bash
cd "$HOME/vision"
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

Open-vocab is optional for the portable demo. If you need the most reliable
demo, use fixed-vocab ONNX first and add open-vocab only after Live, History,
Evidence, and Operations are stable.

### Produce A Jetson TensorRT Engine

Build TensorRT engines on the Jetson that will run them, or on an identical
JetPack/TensorRT/CUDA stack. Do not build an engine on the MacBook and expect
it to run on the Jetson.

First copy the ONNX source to the Jetson:

```bash
rsync -av "$HOME/vision/models/yolo26n.onnx" jetson-portable-1:"$HOME/vision/models/"
```

Then on the Jetson, use one of these paths.

Ultralytics export:

```bash
cd "$HOME/vision"
source .venv-model-export/bin/activate 2>/dev/null || true
python - <<'PY'
from pathlib import Path
from ultralytics import YOLO

model = YOLO("models/yolo26n.onnx")
output = Path(model.export(format="engine", imgsz=640, half=True, device=0))
target = Path("models/yolo26n.jetson.fp16.engine")
output.replace(target)
print(f"wrote {target}")
PY
```

TensorRT `trtexec` fallback:

```bash
trtexec \
  --onnx="$HOME/vision/models/yolo26n.onnx" \
  --saveEngine="$HOME/vision/models/yolo26n.jetson.fp16.engine" \
  --fp16 \
  --shapes=images:1x3x640x640
```

After building, keep all three files if you plan to validate runtime artifacts:

```text
$HOME/vision/models/yolo26n.onnx
$HOME/vision/models/yolo26n.pt
$HOME/vision/models/yolo26n.jetson.fp16.engine
```

The camera still selects the ONNX model row. The `.engine` is registered later
as a runtime artifact and selected only when the target profile, validation
status, and model admission allow it.

### Copy Models To Both Machines

For the manual dev path, both machines use the checkout `models/` directory:

```bash
cd "$HOME/vision"
rsync -av models/ jetson-portable-1:"$HOME/vision/models/"
```

For the installer path, copy the same files into the product data directory on
each host:

```bash
sudo install -d -m 0755 /var/lib/vezor/models
sudo rsync -av "$HOME/vision/models/" /var/lib/vezor/models/
sudo chmod -R a+rX /var/lib/vezor/models
```

The installed backend and supervisor containers see those files as
`/models/<filename>`. Register installed-product model rows with `/models/...`
paths, not `$HOME/vision/models/...` paths.

## 1. Prepare The MacBook

Install the basics. Homebrew is optional, but these commands are the shortest
path on a fresh MacBook:

```bash
xcode-select --install
brew install python@3.12 uv node
corepack enable
```

Install Docker Desktop and start it before running `make dev-up`.
In Docker Desktop settings, give the demo stack enough room to breathe:

- CPUs: 4 or more
- Memory: 8 GB minimum, 12-16 GB preferred
- Disk image: enough free space for model files, clips, MinIO objects, and
  Docker layers

Clone or update the repository:

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

Put model files under the checkout:

```bash
cd "$HOME/vision"
mkdir -p models
ls -lh models
```

At minimum, have:

```text
models/yolo26n.onnx
```

Optional:

```text
models/yoloe-26n-seg.pt
models/yolo26n.jetson.fp16.engine
```

Prepare the local backend Python environment if you plan to register models
from the MacBook or run an optional central worker:

```bash
cd "$HOME/vision/backend"
python3 -m uv sync --group runtime --group dev --group model-metadata --group vision
```

Find the MacBook LAN IP:

```bash
MACBOOK_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)"
echo "$MACBOOK_IP"
```

Keep the MacBook awake:

1. Open System Settings.
2. Open Battery.
3. Disable sleep during the demo while plugged in.
4. If macOS Firewall is enabled, allow Docker and terminal traffic or turn the
   firewall off for the closed demo LAN.

For installer-managed validation, run the macOS master installer now:

```bash
cd /opt/vezor/current
sudo ./installer/macos/install-master.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://127.0.0.1:3000"
```

Then generate the first-run token locally and complete `/first-run`:

```bash
/opt/vezor/current/bin/vezorctl bootstrap-master \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

The Docker dev stack commands in the following sections are retained as
development fallback if the branch installer is not being validated.

The Jetson must reach these MacBook ports:

| Port | Purpose |
|---|---|
| `8000` | backend API |
| `8080` | Keycloak token endpoint |
| `5432` | Postgres for the edge worker lab path |
| `4222` | NATS JetStream for direct portable edge path |
| `9000` | MinIO API |

The MacBook must reach the Jetson on:

| Port | Purpose |
|---|---|
| `8554` | Jetson MediaMTX RTSP relay source |
| `9108` | worker metrics when checking directly from the Jetson |

## 2. Prepare The Jetson

On the Jetson, clone or update the same branch:

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

Copy the same model files to the Jetson:

```bash
cd "$HOME/vision"
mkdir -p models
ls -lh models
```

Run the Jetson in its high-power profile before validation:

```bash
sudo nvpmodel -m 2
sudo jetson_clocks
```

Run the checked-in preflight:

```bash
cd "$HOME/vision"
./scripts/jetson-preflight.sh
```

What good looks like:

- the script ends with `Jetson preflight passed.`
- Docker can run with NVIDIA runtime support
- CUDA/TensorRT/NVDEC/GStreamer basics are visible
- NVENC is absent on Orin Nano, which is expected

Find the Jetson LAN IP:

```bash
hostname -I
```

Write the value into the worksheet as `JETSON_IP`.

## 3. Start The MacBook Control Plane

Preferred installer path: the MacBook control plane is started by
`com.vezor.master` after `installer/macos/install-master.sh` completes. Use
Control -> Deployment for pairing and status.

Development fallback: use the commands below only when intentionally running
the old Docker dev topology.

On the MacBook:

```bash
cd "$HOME/vision"
export JETSON_IP="PUT_THE_JETSON_IP_HERE"
export ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS="{\"*\":\"rtsp://$JETSON_IP:8554\"}"
make dev-up
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
curl -fsS http://127.0.0.1:8000/healthz
```

What good looks like:

- Docker services start
- migrations complete
- `/healthz` returns `{"status":"ok"}`

If you changed `JETSON_IP` after the backend was already running, recreate the
backend so it picks up the edge MediaMTX relay mapping:

```bash
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend
curl -fsS http://127.0.0.1:8000/healthz
```

Open the UI on the MacBook:

- [http://127.0.0.1:3000](http://127.0.0.1:3000)
- username: `admin-dev`
- password: `argus-admin-pass`

Use the MacBook browser for the demo. The local dev OIDC redirect URI is
`localhost:3000`, so opening the UI from another laptop or tablet requires extra
OIDC configuration and is not part of this portable path.

## 4. Export A Local Admin Token

On the MacBook:

```bash
export ARGUS_API_BASE_URL="http://127.0.0.1:8000"
TOKEN="$(
  curl -s \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
echo "${TOKEN:0:32}..."

curl -fsS -H "Authorization: Bearer $TOKEN" \
  "$ARGUS_API_BASE_URL/api/v1/models" |
  python3 -m json.tool | head
```

If token verification fails later, regenerate `TOKEN` in the same terminal.

## 5. Register Models

Register the default MacBook/local model row:

```bash
cd "$HOME/vision/backend"
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo26n-coco-onnx \
  --artifact-path "$HOME/vision/models/yolo26n.onnx" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

Create a Jetson-visible model row. The Jetson container sees the file at
`/models/yolo26n.onnx`, not at the MacBook home-directory path:

```bash
cd "$HOME/vision"
PRIMARY_MODEL_FILENAME="${PRIMARY_MODEL_FILENAME:-yolo26n.onnx}"
MODEL_PATH="$PWD/models/$PRIMARY_MODEL_FILENAME"
MODEL_SHA="$(shasum -a 256 "$MODEL_PATH" | awk '{print $1}')"
MODEL_SIZE="$(stat -f%z "$MODEL_PATH")"
EDGE_MODEL_PATH="/models/$PRIMARY_MODEL_FILENAME"

EDGE_MODEL_RESPONSE="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    http://127.0.0.1:8000/api/v1/models \
    -d "{
      \"name\": \"YOLO26n COCO Edge\",
      \"version\": \"portable-edge\",
      \"task\": \"detect\",
      \"path\": \"$EDGE_MODEL_PATH\",
      \"format\": \"onnx\",
      \"input_shape\": {\"width\": 640, \"height\": 640},
      \"sha256\": \"$MODEL_SHA\",
      \"size_bytes\": $MODEL_SIZE,
      \"license\": \"portable-demo\"
    }"
)"
echo "$EDGE_MODEL_RESPONSE"
EDGE_MODEL_ID="$(
  python3 -c 'import json,sys; payload=json.load(sys.stdin); print(payload.get("id") or payload)' \
    <<<"$EDGE_MODEL_RESPONSE"
)"
echo "$EDGE_MODEL_ID"
```

Optional open-vocab discovery model:

```bash
cd "$HOME/vision/backend"
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yoloe-26n-open-vocab-pt \
  --artifact-path "$HOME/vision/models/yoloe-26n-seg.pt" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

Verify:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/api/v1/models |
  python3 -c 'import json,sys; [print("{} | {} | {} | {}".format(m["name"], m["capability"], m["format"], m["path"])) for m in json.load(sys.stdin)]'
```

## 6. Create The Site And Edge Node

You can create the site in the UI, or use the API:

```bash
SITE_RESPONSE="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    http://127.0.0.1:8000/api/v1/sites \
    -d '{
      "name": "Portable Demo Site",
      "description": "MacBook Pro master plus Jetson portable demo",
      "tz": "Europe/Zurich"
    }'
)"
echo "$SITE_RESPONSE"
SITE_ID="$(
  python3 -c 'import json,sys; payload=json.load(sys.stdin); print(payload.get("id") or payload)' \
    <<<"$SITE_RESPONSE"
)"
echo "$SITE_ID"
```

If the site already exists, list sites and reuse its id:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/api/v1/sites |
  python3 -m json.tool
```

Bootstrap the Jetson as an edge node. This is preferred over the older direct
edge registration route because it returns the same edge identity plus the
supervisor-oriented environment hints used by Operations:

```bash
EDGE_BOOTSTRAP_RESPONSE="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    "$ARGUS_API_BASE_URL/api/v1/operations/bootstrap" \
    -d "{
      \"site_id\": \"$SITE_ID\",
      \"hostname\": \"jetson-portable-1\",
      \"version\": \"portable-demo\"
    }"
)"
echo "$EDGE_BOOTSTRAP_RESPONSE" | python3 -m json.tool
EDGE_NODE_ID="$(
  python3 -c 'import json,sys; print(json.load(sys.stdin)["edge_node_id"])' \
    <<<"$EDGE_BOOTSTRAP_RESPONSE"
)"
echo "$EDGE_NODE_ID"
```

The returned `api_key` and `nats_nkey_seed` are legacy bootstrap material for
older edge flows. For this portable guide, keep `EDGE_NODE_ID` for camera
assignment and supervisor smoke tests, and use the manual worker token only as
a lab bridge.

## 7. Configure Cameras

Open [http://127.0.0.1:3000](http://127.0.0.1:3000), then go to Control ->
Scenes. The route is `/cameras`, but the operator surface is named Scenes.

### Optional MacBook Central Camera

For the most reliable portable demo, use an RTSP camera reachable from the
MacBook and choose:

- Source type: `RTSP`
- Processing mode: `central`
- Primary model: `YOLO26n COCO`
- Browser delivery: native or a central reduced profile
- Active classes: start with `person`, `car`, `bus`, `truck`, `bicycle`,
  `motorcycle`

When the browser delivery profile is `native`, do not select dedicated reduced
resolution or frame-rate profiles. Native means clean camera passthrough.
Choose a reduced profile only when you want Vezor to publish a processed viewing
rendition.

Do not use a directly attached MacBook USB/UVC camera as a central source in
this product path. USB/UVC is modeled as an edge source and requires
`usb:///dev/videoN` on Linux/Jetson. If you must demonstrate a MacBook camera,
expose it as RTSP with a separate local tool and then configure it as RTSP.

### Jetson Edge Camera

For the primary Jetson camera, choose:

- Source type: `RTSP`, unless the camera is physically attached to the Jetson
  as USB/UVC
- Processing mode: `edge`
- Edge node: `jetson-portable-1` / the `EDGE_NODE_ID` you registered
- Primary model: `YOLO26n COCO Edge`
- Browser delivery: `720p10 edge bandwidth saver` for a safe demo default
- Vision profile: an edge/Jetson profile, not a central GPU profile
- Active classes: start with the same small class set

When `native` browser delivery is selected for an RTSP edge camera, leave the
reduced profile controls unset. For the portable demo, `720p10 edge bandwidth
saver` is safer than native when you want a worker-published processed stream.

For a Jetson USB/UVC camera:

- Source type: `USB edge camera`
- USB device URI: `usb:///dev/video0`
- Processing mode remains `edge`
- Edge node is required
- Native RTSP passthrough is unavailable; use a worker-published processed
  stream profile

One Jetson camera is the reliable canned Compose path. A second Jetson camera
needs a second worker process with non-conflicting metrics/service wiring or
supervisor-driven lifecycle validation. Do not add the second edge camera until
the first one passes Live, History, Evidence, Operations, and restart checks.

After saving the camera, open Control -> Scenes and check the camera-specific
surfaces before starting the worker:

- Source: saved source URI, processing mode, edge node, and delivery profile
  are what you intended.
- Model: primary model is the Jetson-visible `/models/...` row for edge
  cameras.
- Privacy: blur policy matches the demo story.
- Regions and boundaries: start with simple include/exclusion shapes; avoid
  complex calibration until the first camera is stable.
- Recording: short event clips are enabled if you expect Evidence review.
- Storage: central MinIO is the simplest portable-demo default; use edge-local
  only when you are intentionally testing local-first evidence behavior.
- Rules: create one low-risk incident rule with `record_clip`, a clear severity,
  and a cooldown so Evidence has something reviewable.

## 8. Start Optional MacBook Central Worker

Only do this if you configured a central RTSP camera.

Find the camera id:

```bash
CAMERAS_RESPONSE="$(
  curl -s -H "Authorization: Bearer $TOKEN" \
    http://127.0.0.1:8000/api/v1/cameras
)"
echo "$CAMERAS_RESPONSE" | python3 -m json.tool

CENTRAL_CAMERA_ID="$(
  CAMERA_NAME='MacBook Central Camera' python3 -c '
import json, os, sys
for camera in json.load(sys.stdin):
    if camera.get("name") == os.environ["CAMERA_NAME"]:
        print(camera["id"])
        break
' <<<"$CAMERAS_RESPONSE"
)"
echo "$CENTRAL_CAMERA_ID"
```

Start the worker in a new MacBook terminal:

```bash
cd "$HOME/vision/backend"
TOKEN="$(
  curl -s \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
ARGUS_API_BASE_URL="http://127.0.0.1:8000" \
ARGUS_API_BEARER_TOKEN="$TOKEN" \
ARGUS_DB_URL="postgresql+asyncpg://argus:argus@127.0.0.1:5432/argus" \
ARGUS_NATS_URL="nats://127.0.0.1:4222" \
ARGUS_MINIO_ENDPOINT="127.0.0.1:9000" \
ARGUS_MINIO_ACCESS_KEY="argus" \
ARGUS_MINIO_SECRET_KEY="argus-dev-secret" \
ARGUS_MINIO_SECURE="false" \
python3 -m uv run python -m argus.inference.engine --camera-id "$CENTRAL_CAMERA_ID"
```

Leave that terminal running for the demo.

## 9. Start The Jetson Edge Worker

On the Jetson, set the MacBook IP and verify the API:

```bash
cd "$HOME/vision"
MACBOOK_IP="PUT_THE_MACBOOK_IP_HERE"
curl -fsS "http://$MACBOOK_IP:8000/healthz"
```

Fetch a local-dev token without changing the token issuer. This `--resolve`
detail matters:

```bash
JETSON_TOKEN="$(
  curl -fsS \
    --resolve "localhost:8080:$MACBOOK_IP" \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    "http://localhost:8080/realms/argus-dev/protocol/openid-connect/token" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
echo "${JETSON_TOKEN:0:32}..."
```

Do not fetch the token from `http://$MACBOOK_IP:8080/...`; that creates a token
with the LAN IP as issuer, and the backend rejects it.

Find the Jetson camera id and edge node id from the MacBook or paste them here:

```bash
ARGUS_EDGE_CAMERA_ID="PASTE_JETSON_CAMERA_ID_HERE"
EDGE_NODE_ID="PASTE_EDGE_NODE_ID_FROM_SECTION_6"
echo "$ARGUS_EDGE_CAMERA_ID"
echo "$EDGE_NODE_ID"
```

Set the edge environment:

```bash
export ARGUS_API_BASE_URL="http://$MACBOOK_IP:8000"
export ARGUS_API_BEARER_TOKEN="$JETSON_TOKEN"
export ARGUS_DB_URL="postgresql+asyncpg://argus:argus@$MACBOOK_IP:5432/argus"
export ARGUS_NATS_URL="nats://$MACBOOK_IP:4222"
export ARGUS_MINIO_ENDPOINT="$MACBOOK_IP:9000"
export ARGUS_MINIO_ACCESS_KEY="argus"
export ARGUS_MINIO_SECRET_KEY="argus-dev-secret"
export ARGUS_EDGE_CAMERA_ID="$ARGUS_EDGE_CAMERA_ID"

# Required accelerated Jetson ONNX Runtime wheel for the product/demo path.
# CPU ONNX Runtime fallback now requires an explicit diagnostic override.
export JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"
```

Build and inspect the edge image:

```bash
docker compose -f infra/docker-compose.edge.yml build inference-worker

docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint /app/.venv/bin/python inference-worker \
  -c "import sys, onnxruntime as ort; print(sys.version); print(ort.__version__); print(ort.get_available_providers())"

docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint /bin/sh inference-worker \
  -lc 'ffmpeg -hide_banner -encoders | grep -q libx264'
```

Check worker config before starting:

```bash
curl -fsS \
  -H "Authorization: Bearer $ARGUS_API_BEARER_TOKEN" \
  "$ARGUS_API_BASE_URL/api/v1/cameras/$ARGUS_EDGE_CAMERA_ID/worker-config" |
  python3 -m json.tool | head -60
```

Start the edge stack:

```bash
docker compose -f infra/docker-compose.edge.yml config >/tmp/vezor-edge-compose.yml
docker compose -f infra/docker-compose.edge.yml up -d --force-recreate --no-build mediamtx inference-worker
docker compose -f infra/docker-compose.edge.yml logs -f --tail=200 inference-worker
```

What good looks like:

- no `401 Unauthorized`
- no backend connection failure
- no NATS timeout loop
- no missing model file
- the worker keeps running
- the MacBook Live page shows the Jetson camera
- History receives telemetry
- Evidence shows reviewable event clips when rules fire

## 10. Optional Supervisor And Pairing Smoke

The reliable demo path above uses the manual `inference-worker` service. To
smoke the installable supervisor model, use Control -> Deployment.

From the MacBook UI:

1. Open `/deployment`.
2. Pair a central node or an existing edge deployment node.
3. Copy the pairing code immediately.

For a deterministic command-line smoke, create the edge pairing session from
the MacBook so you have both the session id and the one-time pairing code:

```bash
PAIRING_RESPONSE="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    "$ARGUS_API_BASE_URL/api/v1/deployment/pairing-sessions" \
    -d "{
      \"node_kind\": \"edge\",
      \"edge_node_id\": \"$EDGE_NODE_ID\",
      \"hostname\": \"jetson-portable-1\",
      \"requested_ttl_seconds\": 300
    }"
)"
echo "$PAIRING_RESPONSE" | python3 -m json.tool
PAIRING_SESSION_ID="$(
  python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' \
    <<<"$PAIRING_RESPONSE"
)"
PAIRING_CODE="$(
  python3 -c 'import json,sys; print(json.load(sys.stdin)["pairing_code"])' \
    <<<"$PAIRING_RESPONSE"
)"
```

To smoke a central supervisor instead, use the same endpoint with:

```json
{
  "node_kind": "central",
  "hostname": "macbook-pro-master",
  "requested_ttl_seconds": 300
}
```

Then claim the edge session from the Jetson:

```bash
PAIRING_SESSION_ID="PASTE_PAIRING_SESSION_ID_FROM_MACBOOK"
PAIRING_CODE="PASTE_PAIRING_CODE_FROM_MACBOOK"
SUPERVISOR_ID="jetson-portable-1"
HOSTNAME="$(hostname)"

CLAIM_RESPONSE="$(
  curl -s \
    -H "Content-Type: application/json" \
    -X POST \
    "$ARGUS_API_BASE_URL/api/v1/deployment/pairing-sessions/$PAIRING_SESSION_ID/claim" \
    -d "{
      \"pairing_code\": \"$PAIRING_CODE\",
      \"supervisor_id\": \"$SUPERVISOR_ID\",
      \"hostname\": \"$HOSTNAME\"
    }"
)"
echo "$CLAIM_RESPONSE" | python3 -m json.tool
```

The response contains credential material once. Store it with owner-only
permissions if you are testing product-mode supervisor config:

```bash
mkdir -p "$HOME/.vezor"
python3 -c '
import json, pathlib, sys
payload = json.load(sys.stdin)
path = pathlib.Path.home() / ".vezor" / "supervisor.credential"
path.write_text(payload["credential_material"], encoding="utf-8")
path.chmod(0o600)
' <<<"$CLAIM_RESPONSE"
```

Create a product-mode supervisor config:

```bash
cat > "$HOME/.vezor/supervisor.json" <<JSON
{
  "supervisor_id": "jetson-portable-1",
  "role": "edge",
  "edge_node_id": "$EDGE_NODE_ID",
  "api_base_url": "$ARGUS_API_BASE_URL",
  "credential_store_path": "$HOME/.vezor/supervisor.credential",
  "worker_metrics_url": "http://127.0.0.1:9108/metrics",
  "service_manager": "compose",
  "version": "portable-demo"
}
JSON
```

Run a one-shot supervisor report if the Jetson host Python environment is ready:

```bash
cd "$HOME/vision/backend"
python3 -m uv run python -m argus.supervisor.runner \
  --config "$HOME/.vezor/supervisor.json" \
  --once
```

If that host Python environment is not ready, skip this step and use the manual
edge worker. The product-mode service templates are present, but a one-command
Jetson installer is still future packaging work. Do not present the manual
bearer-token worker command as the final installed product path; it is a
portable-demo bridge until the packaged installer is completed.

## 11. Validate The Demo

Use this validation order:

1. MacBook backend health:

   ```bash
   curl -fsS http://127.0.0.1:8000/healthz
   ```

2. MacBook frontend loads:

   ```text
   http://127.0.0.1:3000
   ```

3. Deployment page:

   - `/deployment` loads
   - support bundle redacts tokens and credentials
   - paired nodes show credential status if you ran the pairing smoke

4. Control pages:

   - Sites can create, edit, and delete a throwaway location
   - Scenes can save central RTSP and Jetson edge camera settings
   - the scene setup wizard can save source, model, privacy, regions,
     recording, storage, and rules without native-profile/reduced-profile
     conflicts

5. Operations page:

   - `/settings` shows the Jetson worker ownership truth
   - manual workers are clearly labeled as manual/pilot where applicable
   - hardware/model admission is visible after supervisor reports

6. Configuration sections:

   - evidence storage profile is selected
   - stream delivery profile is selected
   - runtime selection profile is selected
   - privacy policy is selected
   - LLM provider can remain unconfigured unless prompt workflows are part of
     the demo

7. Live:

   - central RTSP camera renders if configured
   - Jetson edge camera renders
   - no browser console fetch errors during normal viewing

8. History:

   - telemetry buckets populate
   - camera filters work

9. Evidence:

   - incident rows open without route errors
   - right-side camera links do not navigate to broken routes
   - clips are reviewable
   - review/reopen state persists

10. Edge restart:

   ```bash
   docker compose -f infra/docker-compose.edge.yml restart inference-worker
   docker compose -f infra/docker-compose.edge.yml logs -f --tail=120 inference-worker
   ```

11. MacBook backend restart:

   ```bash
   cd "$HOME/vision"
   docker compose -f infra/docker-compose.dev.yml restart backend
   curl -fsS http://127.0.0.1:8000/healthz
   ```

12. Moving-network rehearsal:

    - change to the travel router
    - recompute `MACBOOK_IP` and `JETSON_IP`
    - recreate MacBook backend with the new `ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS`
    - restart the Jetson edge worker with the new `MACBOOK_IP`

## 12. Runtime Artifact And Soak Validation

If you have a Jetson TensorRT engine for `yolo26n.onnx`, register and validate
it as a runtime artifact. Do not register `.engine` files as primary camera
models.

On the Jetson:

```bash
cd "$HOME/vision/backend"
python3 -m uv run python -m argus.scripts.build_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN" \
  --model-id "$EDGE_MODEL_ID" \
  --source-model "$HOME/vision/models/yolo26n.onnx" \
  --prebuilt-engine "$HOME/vision/models/yolo26n.jetson.fp16.engine" \
  --target-profile linux-aarch64-nvidia-jetson \
  --class person --class car --class bus --class truck \
  --input-width 640 --input-height 640
```

Validate the returned artifact on the same Jetson:

```bash
python3 -m uv run python -m argus.scripts.validate_runtime_artifact \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN" \
  --model-id "$EDGE_MODEL_ID" \
  --artifact-id "$ARTIFACT_ID" \
  --artifact-path "$HOME/vision/models/yolo26n.jetson.fp16.engine" \
  --expected-sha256 "$ARTIFACT_SHA256" \
  --target-profile linux-aarch64-nvidia-jetson \
  --host-profile linux-aarch64-nvidia-jetson
```

After the real run, record the soak result from the MacBook:

```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/runtime-artifacts/soak-runs" \
  -H "Authorization: Bearer $TOKEN" \
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
      \"fps_p50\": 10.0,
      \"worker_restarts\": 0,
      \"evidence_clip_reviewed\": true,
      \"credential_rotation_checked\": true
    },
    \"notes\": \"MacBook Pro portable master plus Jetson edge soak passed.\"
  }"
```

If no TensorRT or compiled open-vocab artifact is present yet, do not pretend
the soak passed. Run the portable demo as an ONNX/CPU or CUDA fallback demo and
record the missing artifact as a limitation.

## 13. Demo-Day Checklist

Before showing the product:

- MacBook and Jetson are on the same LAN
- `MACBOOK_IP` and `JETSON_IP` are current
- VPN/firewall settings are not blocking MacBook ports from the Jetson
- Docker Desktop is running on the MacBook
- required Docker images and Python dependencies are already cached
- `make dev-up` services are healthy
- migrations are at head
- Jetson preflight passes
- model files exist on both machines
- camera RTSP URLs work from the node that will open them
- MacBook backend was recreated after setting `ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS`
- Jetson worker was restarted after any MacBook IP change
- Live renders the Jetson camera
- History receives events
- Evidence opens incident details
- Operations does not show stale or invented worker state
- Task 24 / DeepStream is not part of the demo claim

## Troubleshooting

### Jetson token works in Keycloak but backend returns 401

You probably fetched the token from `http://$MACBOOK_IP:8080/...`. Fetch it with
`--resolve "localhost:8080:$MACBOOK_IP"` so the issuer remains
`http://localhost:8080/realms/argus-dev`.

### Live shows telemetry but no edge video

On the MacBook:

```bash
echo "$ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS"
JETSON_CAMERA_ID="PASTE_JETSON_CAMERA_ID_HERE"
curl -fsS \
  -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/streams/$JETSON_CAMERA_ID/hls.m3u8" |
  head
docker compose -f infra/docker-compose.dev.yml logs --tail=120 mediamtx
```

Make sure the backend was recreated after setting the Jetson RTSP base URL.

### Jetson worker says model file is missing

The Jetson model row should point to `/models/yolo26n.onnx`, and the Jetson
checkout should have the file at:

```text
$HOME/vision/models/yolo26n.onnx
```

The edge Compose file mounts `../models:/models:ro`.

### MacBook central USB camera is not available

That is expected for the product path. USB/UVC is edge-first and Linux/Jetson
oriented. Use an RTSP camera for central processing, or expose the MacBook camera
as RTSP with separate tooling.

### Second Jetson camera is flaky

Validate one camera first. The canned `inference-worker` service is a
single-camera manual path. A second edge camera needs distinct worker process
ownership and non-conflicting metrics/service wiring.

### Moving to another network broke everything

Recompute both IPs, then rerun:

```bash
cd "$HOME/vision"
export JETSON_IP="NEW_JETSON_IP"
export ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS="{\"*\":\"rtsp://$JETSON_IP:8554\"}"
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend
```

Then on Jetson, update `MACBOOK_IP`, fetch a fresh token with `--resolve`, and
restart the edge worker.
