# Vezor Lab Guide: iMac Master And Jetson Orin Edge

Date: 2026-04-19

This guide is written for a first lab rollout of Vezor on:

- a **2019 iMac i9 with Radeon 580 8 GB** as the Vezor master node
- a **Jetson Orin Nano Super 8 GB** on Ubuntu installed on NVMe as the Vezor edge node
- **2 RTSP cameras**

It walks through two tests:

1. **Test A: iMac only**
   The iMac runs the full Vezor stack and both camera workers.
2. **Test B: iMac master + Jetson edge**
   The iMac stays the master node, camera 1 stays central, and camera 2 moves to the Jetson.

The goal is not to prove final production performance. The goal is to prove that the full Vezor workflow works on your hardware from sign-in to live view to history and incidents.

Related documents:

- [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md)
- [operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md)
- [runbook.md](/Users/yann.moren/vision/docs/runbook.md)

## How This Lab Maps To Production

This guide uses the iMac as a temporary master because it is convenient for bring-up. The production shape is different:

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
  -> RTSP cameras on the site LAN
```

Use this lab to prove the product workflow:

- the iMac can host the control plane for evaluation
- the Jetson can own edge inference
- events, history, incident clips, and review state flow back to the master
- Operations shows the central/edge split honestly

Before production, replace:

- iMac dev compose with a Linux `amd64` master deployment
- copied worker commands with supervisor-managed workers
- local dev tokens with scoped production credentials
- ad-hoc terminal monitoring with central metrics, logs, alerts, and backup procedures

## 1. Before You Start

### 1.1 What you need

You need all of the following before you begin:

- administrator access on the iMac
- administrator access on the Jetson
- the Vezor repository on both machines
- 2 working RTSP camera URLs
- at least 1 fixed-vocab detector model file in ONNX format
- both machines and both cameras on the same local network
- enough free disk space for Docker images and logs

Recommended fixed-vocab model order for iMac central testing:

1. `YOLO26n COCO` from `models/yolo26n.onnx` is the default iMac test model.
2. `YOLO26s COCO` from `models/yolo26s.onnx` is the next accuracy step when the artifact is available and the iMac has enough headroom.
3. `YOLO11n COCO` from `models/yolo11n.onnx` is the stable fallback.
4. `YOLO12n COCO` from `models/yolo12n.onnx` is only the older compatibility baseline.

Open-vocab lab models are experimental:

1. `YOLOE-26N Open Vocab` from `models/yoloe-26n-seg.pt`.
2. `YOLOv8s-Worldv2 Open Vocab` from `models/yolov8s-worldv2.pt`.

Use ONNX files for fixed-vocab COCO testing. Files such as `yolo26n.pt` and `yolo12n.pt` are not the standard fixed-vocab runtime path in this guide; use their exported `.onnx` files instead. For open-vocab testing, use the `.pt` catalog presets. `yoloe-26n-seg.onnx` is not the active open-vocab path until an ONNX open-vocab adapter exists.

Do not register raw `.engine` files as ready camera models until the TensorRT engine detector adapter lands. ONNX models can still use TensorRT or CUDA through ONNX Runtime providers when those providers are installed.

Treat fixed-vocab ONNX files as standard COCO-style self-describing models unless you are intentionally following the advanced reduced-class path later in this guide.

This is the default COCO-first flow. The model is treated as a standard self-describing ONNX file, so registration should trust embedded metadata when it is available. You will set the persistent camera class scope in the UI instead of treating the model itself as a reduced-class custom artifact.

### 1.2 What this lab proves

After you finish:

- you can sign in to Vezor
- you can create a site
- you can create cameras
- you can run inference workers
- you can inspect worker state and copy local worker commands from **Operations** at `/settings`
- you can view live telemetry
- you can confirm history and Evidence Desk incident review
- you can compare `central` processing against `edge` processing

### 1.3 Important limits of this lab

- The iMac is being used as a **lab master node**, not the final reference production inference server.
- The Radeon 580 is **not** the hardened central GPU target for Vezor.
- This guide assumes you are doing a **functional test with 2 cameras**, not a scale test.
- The Jetson portion is the more realistic Vezor architecture test.
- Local worker commands in this guide are a dev bridge. Production start, stop, restart, and drain should be handled by a supervisor reconciler, with the Operations UI changing desired state or sending constrained lifecycle requests rather than shelling out from the API.
- The current Evidence Desk primarily reviews incident clips. Snapshot URLs are supported by the API/UI but current capture can legitimately produce clip-only incidents.

### 1.4 A few words explained in plain language

- **Master node**: the main Vezor machine. It hosts the web UI, API, database, auth, storage, and orchestration.
- **Edge node**: a machine near the camera that runs inference locally.
- **RTSP URL**: the camera stream address.
- **Terminal**: the text window where you paste commands.
- **Token**: a temporary login credential used by scripts and workers.
- **Worker**: the process that actually reads a camera stream and performs inference.
- **Central mode**: the master node does the camera processing.
- **Edge mode**: the edge node does the camera processing.

### 1.5 Fill in this worksheet before you start

Write these values down somewhere:

| Item | Your value |
|---|---|
| iMac local username | |
| Jetson local username | |
| iMac LAN IP address | |
| Jetson LAN IP address | |
| Camera 1 name | |
| Camera 1 RTSP URL | |
| Camera 2 name | |
| Camera 2 RTSP URL | |
| Primary ONNX model filename | |

### 1.6 Use these exact test names

To keep the commands simple, use these names:

- Site name: `Lab Site`
- Camera 1 name: `Lab Camera 1`
- Camera 2 name: `Lab Camera 2`
- iMac model record name: `YOLO26n COCO`
- Jetson model record name: `YOLO26n COCO Edge`

If you choose different names, you must also change the matching commands later in the guide.

### 1.7 Find the iMac IP address

On the iMac, open **Terminal** and run:

```bash
IMAC_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)"
echo "$IMAC_IP"
```

What good looks like:

- the command prints an address such as `192.168.1.50`

If it prints nothing:

1. Open **System Settings**
2. Open **Network**
3. Click your active connection
4. Write down the IPv4 address shown there

### 1.8 Recommended macOS settings for the lab

On the iMac:

1. Open **System Settings**
2. Open **Lock Screen**
3. Set sleep-related options so the iMac does not go to sleep during the test
4. Open **Privacy & Security**
5. If Firewall is enabled, either:
   - temporarily turn it off for the lab, or
   - allow Docker Desktop and terminal traffic through it

The Jetson must be able to reach these iMac ports:

- `8000` Vezor backend API
- `8080` Keycloak
- `5432` PostgreSQL
- `4222` NATS JetStream for the direct lab edge worker path
- `7422` NATS leaf upstream for future leaf-node hardening
- `9000` MinIO

### 1.9 Check for port conflicts before you start the stack

Before you run Vezor for the first time, make sure nothing else on the iMac is already using the most important local ports.

Run:

```bash
for PORT in 3000 4222 5432 6379 7422 8000 8080 9000 9001; do
  echo "Checking port $PORT"
  lsof -nP -iTCP:$PORT -sTCP:LISTEN || true
done
```

What good looks like:

- ideally, the command prints nothing except the `Checking port ...` lines

If you see a process already using one of those ports:

1. stop that process before continuing
2. if it is an old Docker container, list running containers with:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

3. stop the conflicting container or old stack

Do this especially for:

- `8080` because Keycloak needs it
- `9001` because the MinIO console needs it
- `8000` because the backend needs it

## 2. Test A: iMac Only

This test keeps everything on the iMac. Both cameras use `central` mode.

### 2.1 Prepare the iMac tools

If these tools are already installed, skip to **2.2**.

#### Step 1: Install Xcode command line tools

Open **Terminal** on the iMac and run:

```bash
xcode-select --install
```

What good looks like:

- macOS either installs the tools or tells you they are already installed

#### Step 2: Install Homebrew

In the same terminal, run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

What good looks like:

- the installer finishes without error

#### Step 3: Install Git, Python, Node, and Helm

Run:

```bash
brew install git python@3.12 node helm
```

#### Step 4: Install uv and enable Corepack

Run:

```bash
python3 -m pip install --user uv
corepack enable
```

#### Step 5: Install Docker Desktop

1. Download Docker Desktop for macOS from Docker's website
2. Install it
3. Open it
4. Wait until Docker says it is running

Verify Docker:

```bash
docker --version
docker compose version
```

What good looks like:

- both commands print a version number

### 2.2 Clone the Vezor repository on the iMac

Choose a simple location. This guide uses `$HOME/vision`.

Run:

```bash
cd "$HOME"
git clone https://github.com/mugetsu79/vision.git
cd "$HOME/vision"
git pull --rebase origin main
```

If the repository is already there, just run:

```bash
cd "$HOME/vision"
git pull --rebase origin main
```

Now install the local host-side dependencies that the guide uses later for migrations and API generation.

Run:

```bash
cd "$HOME/vision/backend"
python3 -m uv sync --group runtime --group dev --group llm --group vision

cd "$HOME/vision/frontend"
corepack pnpm install
```

Verify the two host-side tools that matter most for this guide:

```bash
cd "$HOME/vision/backend"
python3 -m uv run alembic --help >/dev/null

cd "$HOME/vision/frontend"
corepack pnpm exec openapi-typescript --version
```

What good looks like:

- the Alembic command finishes without an error
- `openapi-typescript` prints a version number

The `vision` group is required on the iMac host if you want to run the local inference worker later in this guide. That group installs packages such as `numpy`, `onnxruntime`, `torch`, `torchvision`, and `opencv-python-headless`.

On Intel Macs, the repository pins compatible `onnxruntime`, `torch`, and `torchvision` builds for the host worker because newer upstream wheels are no longer published for macOS `x86_64`.

If `openapi-typescript` is not found:

1. stay in `frontend/`
2. run `corepack pnpm install --force`
3. run `corepack pnpm exec openapi-typescript --version` again

If `pnpm install` warns that `esbuild` build scripts were ignored, that is not the blocker for API generation. You can continue with the guide.

### 2.3 Put the model file in the repository

Create the models directory:

```bash
cd "$HOME/vision"
mkdir -p models
```

Copy your preferred ONNX model files into this directory. For the default iMac test path, make sure this file exists:

```text
$HOME/vision/models/yolo26n.onnx
```

If you also want the compatibility baseline, keep `yolo12n.onnx` in the same directory. If your preferred file has a different name, keep note of the new path and replace it in the commands below.

Verify it exists:

```bash
ls -lh "$HOME/vision/models"
```

What good looks like:

- you can see the model file in the list

### 2.4 Start the Vezor control plane on the iMac

From the repository root:

```bash
cd "$HOME/vision"
make dev-up
```

Important:

- `make dev-up` already runs `docker compose -f infra/docker-compose.dev.yml up -d`
- do **not** run `docker compose ... up -d` again right after `make dev-up`
- if you just pulled a change that modifies `infra/docker-compose.dev.yml` for the backend, recreate the backend container once so new bind mounts and dependency-group installs take effect:

```bash
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend
```

Wait for the core services to become reachable:

```bash
for i in {1..60}; do
  curl -fsS http://127.0.0.1:8000/healthz && break
  sleep 1
done

for i in {1..60}; do
  curl -fsS http://127.0.0.1:8080/realms/argus-dev/.well-known/openid-configuration >/dev/null && break
  sleep 1
done

for i in {1..60}; do
  curl -fsS http://127.0.0.1:9001 >/dev/null && break
  sleep 1
done
```

Then run the setup commands:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head

cd "$HOME/vision/frontend"
corepack pnpm generate:api

cd "$HOME/vision"
```

Why this guide uses the container command:

- it guarantees Alembic talks to the same database URL as the running backend
- it avoids host-versus-container configuration drift on first-time lab setups

Now check the main pages in your browser:

- [http://127.0.0.1:3000](http://127.0.0.1:3000)
- [http://127.0.0.1:3000/settings](http://127.0.0.1:3000/settings)
- [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)
- [http://127.0.0.1:8080](http://127.0.0.1:8080)
- [http://127.0.0.1:9001](http://127.0.0.1:9001)

What good looks like:

- the frontend opens
- the Operations page opens from `/settings`
- the health URL returns `{"status":"ok"}`
- the Keycloak page opens
- the MinIO console opens
- the MinIO console accepts:
  - username: `argus`
  - password: `argus-dev-secret`

If the health URL does not work:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml ps
docker compose -f infra/docker-compose.dev.yml logs --tail 80 backend
```

If the MinIO console at `127.0.0.1:9001` does not work:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml logs --tail 40 minio
```

What good looks like in the MinIO logs:

- no `Invalid credentials` error
- a line showing `WebUI: http://127.0.0.1:9001`

If a later API call such as `GET /api/v1/models` returns `500 Internal Server Error`
and the backend logs mention `relation "models" does not exist`, rerun the migration
against the same database the backend container uses:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head

docker exec infra-postgres-1 psql -U argus -d argus -c '\dt'
docker exec infra-postgres-1 psql -U argus -d argus -c 'select * from alembic_version;'
```

What good looks like:

- the `models` table appears in `\dt`
- `alembic_version` shows `0005_source_capability`

### 2.5 Get the model metadata

Vezor needs the model hash and file size when you register a model. For a self-describing ONNX file, the backend will read the embedded class metadata during registration, so you do not need to send `classes` for the default COCO-first path.

Use a path under this checkout's `models/` directory. In local Docker development, `make dev-up` bind-mounts that same absolute host path into the backend container so registration-time ONNX validation and the later host-side worker both read the same file. It also bind-mounts the same directory at `/models` so the iMac backend can validate Jetson edge model records that use container paths such as `/models/yolo26n.onnx`.

Run:

```bash
PRIMARY_MODEL_FILENAME="${PRIMARY_MODEL_FILENAME:-yolo26n.onnx}"
MODEL_PATH="$PWD/models/$PRIMARY_MODEL_FILENAME"
MODEL_SHA="$(shasum -a 256 "$MODEL_PATH" | awk '{print $1}')"
MODEL_SIZE="$(stat -f%z "$MODEL_PATH")"
echo "$PRIMARY_MODEL_FILENAME"
echo "$MODEL_PATH"
echo "$MODEL_SHA"
echo "$MODEL_SIZE"
```

What good looks like:

- the first line is the model filename, usually `yolo26n.onnx`
- the second line is the model path
- the third line is a long SHA-256 hash
- the fourth line is a file size number

### 2.6 Get a Vezor admin token on the iMac

Vezor ships with a seeded local development admin user:

- username: `admin-dev`
- password: `argus-admin-pass`

Run:

```bash
TOKEN="$(
  curl -s \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
echo "${TOKEN:0:32}..."
```

What good looks like:

- you see the first part of a long token followed by `...`

Verify the token before using it for later copy/paste commands:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/api/v1/models |
  python3 -m json.tool | head
```

If the response says `Token verification failed`, generate a fresh token in the same terminal and rerun the API command. Backend restarts and time passing can make an older shell token stale.

Keep this iMac terminal window open. Later commands in this guide reuse:

- `TOKEN`
- `PRIMARY_MODEL_FILENAME`
- `MODEL_PATH`
- `MODEL_SHA`
- `MODEL_SIZE`

### 2.7 Register the model records you want to compare

The model catalog shown in the UI is a recommendation list. It does not download model files and it does not create selectable camera models by itself. The **Primary model** picker only shows registered `/api/v1/models` rows.

For iMac testing, register every local artifact that you want to compare, then choose the best registered model in the camera wizard. Start with `YOLO26n COCO`; keep `YOLO12n COCO` only as the older baseline.

If you pulled this branch onto an existing dev database, run migrations before registering models. This is required for `.pt` open-vocab presets and harmless for ONNX presets:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
```

Check which local model artifacts are available:

```bash
cd "$HOME/vision"
ls -lh models
```

Register the recommended iMac default:

```bash
cd "$HOME/vision/backend"
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo26n-coco-onnx \
  --artifact-path "$HOME/vision/models/yolo26n.onnx" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

Register the older baseline only when you want to compare against the previous lab setup:

```bash
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo12n-coco-onnx \
  --artifact-path "$HOME/vision/models/yolo12n.onnx" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

Register additional fixed-vocab ONNX models if the files exist locally:

```bash
# Higher accuracy than YOLO26n, if you have models/yolo26s.onnx
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo26s-coco-onnx \
  --artifact-path "$HOME/vision/models/yolo26s.onnx" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"

# Stable balanced fallback, if you have models/yolo11s.onnx
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo11s-coco-onnx \
  --artifact-path "$HOME/vision/models/yolo11s.onnx" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

For fixed-vocab ONNX registrations, do not pass `--class` unless you intentionally want to declare a custom class list. The normal COCO path leaves classes unspecified so the backend reads the embedded ONNX class metadata. That is what makes the UI class scope match the selected model.

For an experimental open-vocab model:

```bash
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yoloe-26n-open-vocab-pt \
  --artifact-path "$HOME/vision/models/yoloe-26n-seg.pt" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

Only use the `.pt` open-vocab catalog presets for open-vocab testing. Do not register `yolo26n.pt`, `yolo12n.pt`, or `yoloe-26n-seg.onnx` as the standard camera model path for this guide.

Verify what the backend registered:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/api/v1/models |
  python3 -c 'import json,sys; [print("{} {} | {} | {} | {} classes | {}".format(m["name"], m["version"], m["capability"], m["format"], len(m["classes"]), m["path"])) for m in json.load(sys.stdin)]'
```

What good looks like:

- `YOLO26n COCO 2026.1` is present
- the fixed-vocab ONNX rows show `80 classes`
- the model catalog cards for registered artifacts change from `unregistered` to `registered` or `missing artifact`

### How model choice and active class scope work in the UI

In **Cameras > Add/Edit camera > Models & Tracking**, the **Primary model** dropdown is populated from registered `/api/v1/models` rows. The catalog panel below it is only a status and recommendation panel.

For fixed-vocab models, **Active class scope** is built from the selected model row's `classes` field:

- `YOLO26n COCO`, `YOLO26s COCO`, `YOLO11n COCO`, and `YOLO12n COCO` all expose the COCO class inventory, so the UI shows the same 80 class names even though the model weights differ.
- If you switch from one fixed-vocab model to another, Vezor keeps only the checked classes that exist in the newly selected model.
- If every class is unchecked, the camera keeps the full selected model inventory active.

For open-vocab models, the UI does not show the 80-class checkbox list. It shows **Runtime vocabulary** instead. Enter the labels you want that model to detect, such as `person, forklift, pallet jack`.

For the most stable iMac tracking comparison, keep privacy strength at the default value because it only affects face/plate rendering, not detector identity. Use **Frame skip** `1`, start with **FPS cap** `20`, and raise to `25` only if both workers stay stable. Lower values such as frame skip `3` or FPS cap `5` reduce temporal evidence and usually make tracker IDs less stable.

### Legacy manual model registration path

Skip this section if you used the catalog preset helper above. This manual record uses the **iMac path** to the model file. It is only for Test A, and it is a standard self-describing COCO ONNX registration.

Run:

```bash
IMAC_MODEL_RESPONSE="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    http://127.0.0.1:8000/api/v1/models \
    -d "{
      \"name\": \"YOLO26n COCO iMac\",
      \"version\": \"lab-imac\",
      \"task\": \"detect\",
      \"path\": \"$MODEL_PATH\",
      \"format\": \"onnx\",
      \"input_shape\": {\"width\": 640, \"height\": 640},
      \"sha256\": \"$MODEL_SHA\",
      \"size_bytes\": $MODEL_SIZE,
      \"license\": \"lab\"
    }"
)"
echo "$IMAC_MODEL_RESPONSE"
IMAC_MODEL_ID="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); print(payload.get("id") or payload)' <<<"$IMAC_MODEL_RESPONSE")"
echo "$IMAC_MODEL_ID"
```

What good looks like:

- the command prints a UUID

If you get a message that the model already exists:

1. open the list of models with:

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/models | python3 -m json.tool
```

2. find the existing `YOLO26n COCO iMac` entry
3. reuse its `id`

### 2.8 Sign in to the Vezor UI

1. Open [http://127.0.0.1:3000](http://127.0.0.1:3000)
2. Click **Sign in**
3. On the Keycloak login page, enter:
   - username: `admin-dev`
   - password: `argus-admin-pass`
4. Submit the form

What good looks like:

- you land in the Vezor app shell

### 2.9 Create the site in the UI

1. In the left navigation, click **Sites**
2. Click **Add site**
3. Enter:
   - Site name: `Lab Site`
   - Description: `Initial Vezor lab site`
   - Time zone: `Europe/Zurich`
4. Click **Save site**

What good looks like:

- the new site appears in the sites table

### 2.10 Create camera 1 in the UI

1. In the left navigation, click **Cameras**
2. Click **Add camera**
3. In **Identity**:
   - Camera name: `Lab Camera 1`
   - Site: `Lab Site`
   - Processing mode: `central`
   - RTSP URL: paste your camera 1 RTSP URL
4. Click **Continue**
5. In **Models & Tracking**:
   - Primary model: choose the best registered iMac model, usually `YOLO26n COCO`
   - Persistent active classes: select `person`, `car`, `bus`, `truck`, `motorcycle`, `bicycle`
   - Tracker type: keep `botsort`
   - Secondary model: leave empty
6. Click **Continue**
7. In **Privacy, Processing & Delivery**:
   - leave privacy defaults as-is
   - Frame skip: `1`
   - FPS cap: `20`
   - Browser delivery profile: `720p10 viewer preview`
8. Click **Continue**
9. In **Calibration**:
   - click **Add source point** 4 times
   - click **Add destination point** 4 times
   - Reference distance (m): `10`
10. Click **Continue**
11. In **Review**, confirm the values
12. Click the final save button

What good looks like:

- `Lab Camera 1` appears in the cameras table

### 2.11 Create camera 2 in the UI

Repeat the same process, but use:

- Camera name: `Lab Camera 2`
- Site: `Lab Site`
- Processing mode: `central`
- RTSP URL: paste your camera 2 RTSP URL
- Primary model: choose the same registered iMac model as camera 1, usually `YOLO26n COCO`
- Persistent active classes: select `person`, `car`, `bus`, `truck`, `motorcycle`, `bicycle`
- Tracker type: `botsort`
- Browser delivery profile: `720p10 viewer preview`
- Calibration:
  - click **Add source point** 4 times
  - click **Add destination point** 4 times
  - Reference distance (m): `10`

What good looks like:

- `Lab Camera 1` and `Lab Camera 2` are both visible in the cameras table

In this iMac-only central test, `720p10 viewer preview` reduces only iMac-to-browser viewing bandwidth and browser decode load. It does not reduce camera-to-iMac ingest bandwidth because central inference still pulls the native camera stream.

### 2.12 Get the camera IDs

You need the camera IDs to start the workers.

Run:

```bash
CAMERAS_RESPONSE="$(
  curl -s -H "Authorization: Bearer $TOKEN" \
    http://127.0.0.1:8000/api/v1/cameras
)"
echo "$CAMERAS_RESPONSE"

lookup_camera_id() {
  CAMERA_NAME="$1" python3 -c '
import json, os, sys
payload = json.load(sys.stdin)
if not isinstance(payload, list):
    raise SystemExit(f"Expected camera list, got: {payload}")
name = os.environ["CAMERA_NAME"]
for camera in payload:
    if camera.get("name") == name:
        print(camera["id"])
        break
else:
    raise SystemExit(f"Camera not found: {name}")
' <<<"$CAMERAS_RESPONSE"
}

CAMERA_ONE_ID="$(lookup_camera_id 'Lab Camera 1')"
CAMERA_TWO_ID="$(lookup_camera_id 'Lab Camera 2')"

echo "$CAMERA_ONE_ID"
echo "$CAMERA_TWO_ID"
```

What good looks like:

- both commands print UUIDs

If the response says `Token verification failed`, generate a fresh `TOKEN` in this terminal and rerun the lookup.

### 2.13 Start the iMac worker for camera 1

Open a **new Terminal window or tab** on the iMac.

Preferred local-dev path: open **Operations** at [http://127.0.0.1:3000/settings](http://127.0.0.1:3000/settings) and copy the command from the camera's worker card. The copied command fetches a fresh local dev token before setting `ARGUS_API_BEARER_TOKEN`.

The explicit command below is the same idea written out for this lab guide:

Run:

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
python3 -m uv run python -m argus.inference.engine --camera-id "$CAMERA_ONE_ID"
```

Leave this terminal window open.

### 2.14 Start the iMac worker for camera 2

Open a **second new Terminal window or tab** on the iMac.

Preferred local-dev path: use the **Operations** copy button for camera 2. The explicit command below is kept for repeatable lab troubleshooting:

Run:

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
python3 -m uv run python -m argus.inference.engine --camera-id "$CAMERA_TWO_ID"
```

Leave this terminal window open.

What good looks like in the worker windows:

- the process keeps running
- there is no immediate crash
- you do not see a `401` error
- you do not see a missing-model-path error

A single first-frame message such as `ffmpeg rawvideo capture failed (no frame produced within 20s)` followed by `Camera capture lost, reconnecting` and then a successful frame is usually the RTSP cold-start retry path, not an auth failure. Treat it as a problem only if it repeats continuously or the worker never reaches detect/publish stages.

If the worker crashes immediately with `ModuleNotFoundError: No module named 'numpy'`, go back to the backend directory and install the host-side `vision` dependencies:

```bash
cd "$HOME/vision/backend"
python3 -m uv sync --group runtime --group dev --group llm --group vision
```

Then rerun the worker command.

### 2.15 Check Live

1. Go back to the browser on the iMac
2. Open **Live**
3. Wait up to 30 seconds

What good looks like:

- both camera tiles appear
- each tile eventually shows `online`
- the telemetry badge changes to a live state

### 2.16 Check History and Incidents

1. Open **History**
2. Confirm that some event data appears after the workers have been running for a short time
3. Open **Incidents**
4. Confirm the Evidence Desk layout opens with the Queue, evidence area, and Incident facts panel
5. If nothing appears yet, let the cameras run longer or create a scene that triggers a rule/event
6. When an incident exists, open the signed clip and mark the incident reviewed
7. Switch the review filter to Reviewed and confirm the reviewed incident can be reopened

What good looks like:

- clip-only incidents show a clear evidence state instead of a broken snapshot
- `Open clip` is available when clip storage succeeded
- review state survives page reloads

### 2.17 Run the full validation suite on the iMac

From a **third Terminal window** on the iMac:

```bash
cd "$HOME/vision"
make verify-all
```

What good looks like:

- the script finishes successfully
- backend tests pass
- frontend tests pass
- Playwright passes
- Helm rendering succeeds

### 2.18 Test A is a pass only if all of these are true

- you can sign in
- you can create a site
- you can create both cameras
- both workers stay up
- both cameras appear in Live
- History or Evidence Desk shows real data once a detection/rule event has occurred
- `make verify-all` succeeds

If all of that works, move to Test B.

## 3. Test B: iMac Master And Jetson Edge

This test keeps the iMac as the master and moves **camera 2** to the Jetson.

At the end of this test:

- camera 1 is still `central` on the iMac
- camera 2 is `edge` on the Jetson

### 3.1 Keep the iMac control plane running

Do **not** stop the iMac stack. The following must remain running on the iMac:

- Docker Desktop
- `make dev-up` services
- the browser session
- the worker terminal for camera 1

You **should stop** the iMac worker terminal for camera 2 before moving it to the Jetson.

In the camera 2 worker window on the iMac:

1. click the terminal window
2. press `Ctrl+C`

### 3.2 Prepare the Jetson

Boot the Jetson and log in.

Open **Terminal** on the Jetson.

#### Step 1: Install Git, curl, Docker, Compose, and JetPack runtime components

Run:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates docker.io ffmpeg \
  gstreamer1.0-tools gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-rtsp
sudo apt-get install -y docker-compose-v2 || sudo apt-get install -y docker-compose-plugin
sudo apt-get install -y nvidia-jetpack-runtime nvidia-container-toolkit nvidia-l4t-gstreamer
sudo systemctl enable --now docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker --version
docker compose version
```

On JetPack 6 / Ubuntu 22.04 ARM64, the Ubuntu package repositories can expose Docker Compose v2 as `docker-compose-v2` rather than `docker-compose-plugin`. Install Compose in its own command so a missing Compose package name does not abort the Docker install.

If `nvidia-jetpack-runtime` is not available on your image but `nvidia-jetpack` is available, install the full metapackage instead:

```bash
sudo apt-get install -y nvidia-jetpack
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

The Jetson edge stack needs the JetPack runtime components, not just Docker. The GStreamer plugin packages and FFmpeg are needed for RTSP/H264 host diagnostics and capture fallback. The preflight checks CUDA, TensorRT, NVIDIA GStreamer/NVDEC, the software H264 decoder, FFmpeg/FFprobe, and NVIDIA Container Toolkit before the edge worker starts.

#### Step 2: Ensure your user can run Docker

Run:

```bash
sudo usermod -aG docker "$USER"
```

Then:

1. log out of the Jetson desktop or terminal session
2. log back in

#### Step 3: Clone the repository on the Jetson

Run:

```bash
cd "$HOME"
git clone https://github.com/mugetsu79/vision.git
cd "$HOME/vision"
git pull --rebase origin main
```

#### Step 4: Put the model file on the Jetson

Create the models directory:

```bash
cd "$HOME/vision"
mkdir -p models
```

Copy the same ONNX model file that you selected for edge testing to:

```text
$HOME/vision/models/yolo26n.onnx
```

Verify it exists:

```bash
ls -lh "$HOME/vision/models"
```

#### Step 5: Run the Jetson preflight

Run:

```bash
cd "$HOME/vision"
./scripts/jetson-preflight.sh
```

What good looks like:

- the script ends with `Jetson preflight passed.`
- JetPack, CUDA, TensorRT, Docker, Docker Compose v2, and `nvidia-container-toolkit` checks pass
- NVDEC is present
- NVENC is reported absent, which is expected on Orin Nano

If it ends with one or more `FAIL` lines, stop here and fix those issues before continuing.

### 3.3 Create the Jetson-specific model record on the iMac

The Jetson container sees the model file at `/models/$PRIMARY_MODEL_FILENAME`, not at your home-directory path. That is why you need a second model record, even though the embedded ONNX class metadata is the same.

Back on the iMac, run this from the repository root. It recomputes the model metadata so the command does not depend on variables from an older terminal session.

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
      \"version\": \"lab-edge\",
      \"task\": \"detect\",
      \"path\": \"$EDGE_MODEL_PATH\",
      \"format\": \"onnx\",
      \"input_shape\": {\"width\": 640, \"height\": 640},
      \"sha256\": \"$MODEL_SHA\",
      \"size_bytes\": $MODEL_SIZE,
      \"license\": \"lab\"
    }"
)"
echo "$EDGE_MODEL_RESPONSE"
EDGE_MODEL_ID="$(python3 -c 'import json,sys; payload=json.load(sys.stdin); print(payload.get("id") or payload)' <<<"$EDGE_MODEL_RESPONSE")"
echo "$EDGE_MODEL_ID"
```

What good looks like:

- the command prints a UUID

If the response says the backend cannot read `/models/...`, pull the latest guide changes and recreate the backend container once:

```bash
cd "$HOME/vision"
git pull --ff-only
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend
```

### 3.4 Edit camera 2 in the Vezor UI

Back in the browser on the iMac:

1. Open **Cameras**
2. Find `Lab Camera 2`
3. Click **Edit**

Change these values:

- Processing mode: `edge`
- Primary model: `YOLO26n COCO Edge`
- Persistent active classes: select `person`, `car`, `bus`, `truck`, `motorcycle`, `bicycle`

Keep these values:

- Site: `Lab Site`
- Tracker type: `botsort`
- Browser delivery profile: `720p10 edge bandwidth saver`
- Calibration: keep the existing values

Save the changes.

What good looks like:

- `Lab Camera 2` now shows `edge` in the cameras table
- `720p10 edge bandwidth saver` means the Jetson builds the reduced viewing stream locally before remote browser delivery

### 3.5 Refresh the camera 2 ID just to be safe

Back on the iMac, run:

```bash
CAMERAS_RESPONSE="$(
  curl -s -H "Authorization: Bearer $TOKEN" \
    http://127.0.0.1:8000/api/v1/cameras
)"
echo "$CAMERAS_RESPONSE"

CAMERA_TWO_ID="$(
  CAMERA_NAME='Lab Camera 2' python3 -c '
import json, os, sys
payload = json.load(sys.stdin)
if not isinstance(payload, list):
    raise SystemExit(f"Expected camera list, got: {payload}")
name = os.environ["CAMERA_NAME"]
for camera in payload:
    if camera.get("name") == name:
        print(camera["id"])
        break
else:
    raise SystemExit(f"Camera not found: {name}")
' <<<"$CAMERAS_RESPONSE"
)"
echo "$CAMERA_TWO_ID"
```

If the response says `Token verification failed`, generate a fresh `TOKEN` on the iMac and rerun the lookup.

### 3.6 Get a fresh admin token on the Jetson

Tokens are temporary. Generate a fresh one on the Jetson. The request still uses the iMac IP for the network connection, but keeps `localhost` in the Keycloak URL through `curl --resolve`; that preserves the dev issuer that the backend trusts.

On the Jetson:

```bash
IMAC_IP="PUT_THE_IMAC_IP_HERE"
printf '<%s>\n' "$IMAC_IP"
curl -fsS "http://$IMAC_IP:8000/healthz"
JETSON_TOKEN="$(
  curl -fsS \
    --resolve "localhost:8080:$IMAC_IP" \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    "http://localhost:8080/realms/argus-dev/protocol/openid-connect/token" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
echo "${JETSON_TOKEN:0:32}..."
```

Replace `PUT_THE_IMAC_IP_HERE` with the real iMac IP address you wrote down in section **1.5**.

Use plain shell quotes (`"`) or no quotes. Do not paste smart quotes such as `“` or `”`. If `curl` says it cannot resolve a host beginning with `xn--`, the IP variable contains smart quotes; reset it with `IMAC_IP=192.168.1.229`.

Do not fetch the token from `http://$IMAC_IP:8080/...` in this dev lab. That creates a token whose issuer is the LAN IP address, and the backend rejects it with `401 Token verification failed`.

Now paste the camera 2 ID that you printed on the iMac in section **3.5**:

```bash
CAMERA_TWO_ID="PASTE_CAMERA_TWO_ID_HERE"
echo "$CAMERA_TWO_ID"
```

### 3.7 Use direct iMac NATS for this lab

For the current iMac + Jetson lab, point the edge worker directly at the iMac NATS listener on port `4222`. This is the simplest reliable path while the supervisor/leaf-node bootstrap is still being hardened.

On the Jetson:

```bash
cd "$HOME/vision"
export ARGUS_NATS_URL="nats://$IMAC_IP:4222"
echo "$ARGUS_NATS_URL"
```

What good looks like:

- the output shows the iMac IP address and port `4222`
- `docker compose ... config` in the next section succeeds without asking for `ARGUS_NATS_URL`

The edge compose file still starts a local `nats-leaf` service because that is the intended production shape. In this lab path, the worker uses `ARGUS_NATS_URL` directly and the leaf service can be treated as future hardening.

### 3.8 Start the Jetson edge stack

First configure the iMac backend to relay the Jetson's local MediaMTX browser
stream path through the iMac MediaMTX instance. `native` relays clean passthrough;
`annotated` and reduced profiles relay the worker-published processed stream. This
keeps the browser pointed at the iMac while the actual edge camera video is pulled
from Jetson MediaMTX on demand.

#### Choose the validation checkpoint

If you want to isolate the Jetson processed-stream publisher fix first, test
commit `dd66ec7b` before pulling the full edge Python runtime refactor:

```bash
cd "$HOME/vision"
git fetch origin
git switch --detach dd66ec7b
unset JETSON_ORT_WHEEL_URL
```

At `dd66ec7b`, the Jetson image still uses the previous Python runtime. Use that
checkpoint only to validate native plus annotated/reduced stream delivery.
Acceleration is still expected to resolve to CPU there.

After that test, return to the branch tip to validate the Python 3.10 Jetson edge
image and ONNX Runtime provider behavior:

```bash
cd "$HOME/vision"
git switch codex/native-passthrough-contract
git pull --ff-only origin codex/native-passthrough-contract
```

Commit `525b9824` and newer use the Jetson base image's system Python 3.10
virtualenv in `backend/Dockerfile.edge`. That replaces the previous edge image
runtime for this Compose path. The central/backend image remains Python 3.12,
but there is no separate generic non-Jetson Python 3.12 edge image in this lab
compose stack.

On the Jetson, get the Jetson LAN IP:

```bash
hostname -I
```

On the iMac, from the repository root:

```bash
cd "$HOME/vision"
JETSON_IP="PUT_THE_JETSON_IP_HERE"
export ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS="{\"*\":\"rtsp://$JETSON_IP:8554\"}"
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend
curl -fsS http://127.0.0.1:8000/healthz
```

For a multi-edge lab, replace the `*` key with the specific edge node UUID.
The wildcard is intended for this single-Jetson validation path.

On the Jetson:

```bash
cd "$HOME/vision"

# Only set this when testing the full Python 3.10 edge image and you have a
# Jetson cp310 accelerated ONNX Runtime wheel URL. Leave it unset for dd66ec7.
# export JETSON_ORT_WHEEL_URL="https://.../onnxruntime_gpu-...-cp310-cp310-linux_aarch64.whl"

docker compose -f infra/docker-compose.edge.yml build --no-cache inference-worker

docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint /app/.venv/bin/python inference-worker \
  -c "import sys, onnxruntime as ort; print(sys.version); print(ort.__version__); print(ort.get_available_providers())"

docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint gst-inspect-1.0 inference-worker rtspclientsink

# Refresh the token after the build, not before it. Large first builds can outlive a dev token.
JETSON_TOKEN="$(
  curl -fsS \
    --resolve "localhost:8080:$IMAC_IP" \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    "http://localhost:8080/realms/argus-dev/protocol/openid-connect/token" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

export ARGUS_API_BASE_URL="http://$IMAC_IP:8000"
export ARGUS_API_BEARER_TOKEN="$JETSON_TOKEN"
export ARGUS_DB_URL="postgresql+asyncpg://argus:argus@$IMAC_IP:5432/argus"
export ARGUS_MINIO_ENDPOINT="$IMAC_IP:9000"
export ARGUS_MINIO_ACCESS_KEY="argus"
export ARGUS_MINIO_SECRET_KEY="argus-dev-secret"
export ARGUS_EDGE_CAMERA_ID="$CAMERA_TWO_ID"
export ARGUS_NATS_URL="nats://$IMAC_IP:4222"

curl -fsS "$ARGUS_API_BASE_URL/healthz"
curl -fsS \
  -H "Authorization: Bearer $ARGUS_API_BEARER_TOKEN" \
  "$ARGUS_API_BASE_URL/api/v1/cameras/$ARGUS_EDGE_CAMERA_ID/worker-config" |
  python3 -m json.tool | head -40

docker compose -f infra/docker-compose.edge.yml config >/tmp/argus-edge-compose.yml
docker compose -f infra/docker-compose.edge.yml up -d --force-recreate --no-build mediamtx inference-worker
```

Now watch the logs:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

What good looks like:

- the two `curl` commands succeed before Compose starts the worker
- `docker compose ... config` succeeds, which proves the required edge variables are visible in this shell
- the container starts
- there is no `401 Unauthorized`
- there is no `httpx.ConnectError: All connection attempts failed`
- there is no `nats.errors.TimeoutError`
- there is no “model file not found”
- the worker keeps running
- the `/run/secrets` warning is harmless in this local-dev Compose path
- Jetson MediaMTX can reach `/.well-known/argus/mediamtx/jwks.json` on the iMac
  through `ARGUS_API_BASE_URL`, which lets the iMac relay read its RTSP path
- at `dd66ec7b`, annotated/reduced stream delivery should work but CPU ONNX Runtime is still expected
- at branch tip `525b9824` or newer, `/app/.venv/bin/python` should report Python 3.10 inside the Jetson worker image
- if `JETSON_ORT_WHEEL_URL` is set to a compatible cp310 Jetson ONNX Runtime GPU wheel, `onnxruntime.get_available_providers()` should include `TensorrtExecutionProvider` or at least `CUDAExecutionProvider`
- if `JETSON_ORT_WHEEL_URL` is unset, `CPUExecutionProvider` remains expected
- `gst-inspect-1.0 rtspclientsink` should succeed inside the worker image; if it says `No such element or plugin`, pull the latest branch and rebuild the edge image with `--no-cache`

### 3.9 Confirm camera 2 is now working from the Jetson

Back on the iMac browser:

1. Open **Live**
2. Wait up to 30 seconds

What good looks like:

- `Lab Camera 1` stays online
- `Lab Camera 2` comes back online
- both still render in the operator UI

If telemetry is visible but video is not, check the backend HLS proxy from the
iMac before changing inference or NATS settings:

```bash
curl -fsS \
  -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/streams/$CAMERA_TWO_ID/hls.m3u8" |
  head
docker compose -f infra/docker-compose.dev.yml logs --tail=120 mediamtx
```

If this returns a playlist, MediaMTX routing is working and the browser should
recover through WebRTC or LL-HLS. If it returns `404`, recheck
`ARGUS_EDGE_MEDIAMTX_RTSP_BASE_URLS`, the Jetson IP, and the Jetson MediaMTX
logs.

Now open **History** and **Incidents** again and confirm that data continues to arrive. In Incidents, use the Evidence Desk review filter to confirm pending/reviewed state still behaves across the central/edge split.

### 3.10 Optional: check Jetson worker metrics

On the Jetson:

```bash
curl -s http://127.0.0.1:9108/metrics | head
```

What good looks like:

- you see Prometheus-style metrics text

To check the Python and ONNX Runtime provider inside the edge image:

```bash
docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint /app/.venv/bin/python inference-worker \
  -c "import sys, onnxruntime as ort; print(sys.version); print(ort.__version__); print(ort.get_available_providers())"
```

At branch tip `525b9824` or newer, Python should report `3.10.x`. If
`JETSON_ORT_WHEEL_URL` was unset during the image build, CPU-only providers are
expected. If you exported a compatible Jetson cp310 accelerated wheel before the
build, expect `TensorrtExecutionProvider` or at least `CUDAExecutionProvider`.

### 3.11 Test B is a pass only if all of these are true

- the iMac control plane stays healthy
- camera 1 still works in `central` mode
- camera 2 works in `edge` mode from the Jetson
- the Jetson worker keeps running
- Live still shows both cameras, including camera 2 video relayed from Jetson MediaMTX
- History and Evidence Desk still work
- Operations shows the central/edge split and does not invent unknown worker state

### 3.12 Production readiness gap

This lab is clean only when the product workflow works. Production readiness still needs:

- Linux master deployment
- TLS and real OIDC realm configuration
- supervisor-managed central and edge workers
- per-worker heartbeat and last-error reporting
- backups for database and incident object storage
- edge credential rotation
- soak testing over multiple days

## 4. Pass / Fail Rules And Troubleshooting

### 4.1 Final pass criteria for the full lab

The whole lab is a success only if all of the following are true:

1. Test A passes
2. Test B passes
3. `make verify-all` succeeds on the iMac
4. the iMac stays healthy as the master node
5. the Jetson can run the edge worker without repeated crashes

### 4.2 If a worker exits immediately

Most likely causes:

- the token expired
- the camera ID is wrong
- the model path in the model record is wrong
- the RTSP URL is wrong or unreachable

What to do:

1. get a fresh token
2. confirm the camera ID again
3. confirm the model path is:
   - the full iMac path for the selected iMac model, for example `$HOME/vision/models/yolo26n.onnx`
   - `/models/yolo26n.onnx` for the matching Jetson edge model when `PRIMARY_MODEL_FILENAME=yolo26n.onnx`
4. restart the worker

### 4.3 If the worker says `401` or `403`

The worker could not fetch its runtime config.

What to do:

1. create a fresh token with `curl --resolve "localhost:8080:$IMAC_IP"` as shown in section **3.6**
2. make sure you exported `ARGUS_API_BEARER_TOKEN`
3. restart the worker

On the Jetson, a token fetched from `http://$IMAC_IP:8080/...` can look valid but still fail backend verification because its issuer is `http://$IMAC_IP:8080/realms/argus-dev`. Use the `localhost` URL plus `--resolve` so the issuer remains `http://localhost:8080/realms/argus-dev`.

For the Jetson container:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.edge.yml down
export ARGUS_API_BEARER_TOKEN="$JETSON_TOKEN"
export ARGUS_NATS_URL="nats://$IMAC_IP:4222"
docker compose -f infra/docker-compose.edge.yml up -d --force-recreate --no-build inference-worker
```

### 4.4 If the worker says `httpx.ConnectError: All connection attempts failed`

The Jetson worker could not reach the iMac/master backend API. The usual cause is that `ARGUS_API_BASE_URL` was not exported in the same terminal where you ran `docker compose`, or it still points at `host.docker.internal`, which is the Jetson host on Linux.

On the Jetson, reset the master-facing environment and test it before starting Compose:

```bash
cd "$HOME/vision"
IMAC_IP="PUT_THE_IMAC_IP_HERE"
printf '<%s>\n' "$IMAC_IP"
export ARGUS_API_BASE_URL="http://$IMAC_IP:8000"
export ARGUS_DB_URL="postgresql+asyncpg://argus:argus@$IMAC_IP:5432/argus"
export ARGUS_MINIO_ENDPOINT="$IMAC_IP:9000"
export ARGUS_API_BEARER_TOKEN="$JETSON_TOKEN"
export ARGUS_EDGE_CAMERA_ID="$CAMERA_TWO_ID"
export ARGUS_NATS_URL="nats://$IMAC_IP:4222"

curl -fsS "$ARGUS_API_BASE_URL/healthz"
curl -fsS \
  -H "Authorization: Bearer $ARGUS_API_BEARER_TOKEN" \
  "$ARGUS_API_BASE_URL/api/v1/cameras/$ARGUS_EDGE_CAMERA_ID/worker-config" |
  python3 -m json.tool | head -40

docker compose -f infra/docker-compose.edge.yml config >/tmp/argus-edge-compose.yml
docker compose -f infra/docker-compose.edge.yml up -d --force-recreate inference-worker
```

If `printf` shows anything other than `<192.168.1.229>` with your real IP, reset the variable with plain ASCII characters, for example `IMAC_IP=192.168.1.229`. If `curl` reports an `xn--...` hostname, the value still contains smart quotes. If the first `curl` fails after that, check the iMac IP, firewall, and that the backend is listening on port `8000` from the LAN. If the second `curl` fails with auth, fetch a fresh `JETSON_TOKEN` with the `curl --resolve "localhost:8080:$IMAC_IP"` command from section **3.6**.

### 4.5 If the worker repeats `Camera capture lost, reconnecting`

The worker reached the camera ingest stage, but it cannot read frames from the RTSP source. First separate a camera/network problem from a container/GStreamer problem. The Jetson worker's intended capture path is native GStreamer/NVDEC through `gst-launch-1.0` piping raw BGR frames into Python; it does not depend on pip OpenCV having GStreamer support.

On the Jetson host:

```bash
set +H 2>/dev/null || true
RTSP_URL="PASTE_THE_CAMERA_RTSP_URL_FROM_WORKER_CONFIG_HERE"

gst-launch-1.0 -v \
  rtspsrc location="$RTSP_URL" protocols=tcp latency=200 \
  ! rtph264depay ! h264parse ! fakesink
```

What the host check means:

- if it fails, the Jetson cannot reach the camera stream; check the RTSP URL, credentials, camera IP, route, and firewall
- if it runs, the camera path works from the Jetson host and the next check is decode/container behavior

If the host says `no element "h264parse"` or `no element "avdec_h264"`, install the GStreamer plugin packages and rerun the host check:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg gstreamer1.0-tools gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-rtsp
```

Then test software decode on the host:

```bash
gst-launch-1.0 -v \
  rtspsrc location="$RTSP_URL" protocols=tcp latency=200 \
  ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! fakesink
```

Then test the worker container's decode elements:

```bash
docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint gst-inspect-1.0 inference-worker nvv4l2decoder

docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint gst-inspect-1.0 inference-worker avdec_h264

docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint gst-inspect-1.0 inference-worker rtspclientsink
```

Now test both container decode paths:

```bash
docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint gst-launch-1.0 inference-worker \
  -v rtspsrc location="$RTSP_URL" protocols=tcp latency=200 \
  ! rtph264depay ! h264parse ! nvv4l2decoder ! fakesink

docker compose -f infra/docker-compose.edge.yml run --rm --no-deps \
  --entrypoint gst-launch-1.0 inference-worker \
  -v rtspsrc location="$RTSP_URL" protocols=tcp latency=200 \
  ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! fakesink
```

What the container check means:

- if `nvv4l2decoder` is missing, rerun the Jetson preflight and fix the NVIDIA runtime/NVDEC setup before relying on hardware decode
- if `avdec_h264` is missing, pull the latest repo and rebuild the edge image; the fallback path needs the `gstreamer1.0-libav` package inside the container
- if `rtspclientsink` is missing, pull the latest repo and rebuild the edge image; processed annotated/reduced profiles need the `gstreamer1.0-rtsp` package inside the container
- if the NVDEC path receives no frames but the software path works, pull the latest code and rebuild the edge worker; the worker uses a native GStreamer raw-frame reader first, then `avdec_h264`, then FFmpeg rawvideo only as a last-resort fallback
- if both container decode paths work but the worker still reconnects forever, capture the worker logs plus the GStreamer command results before changing model settings

The ONNX Runtime line `CPUExecutionProvider` is a performance concern, not the reason for `Camera capture lost`; that message happens before detection.

### 4.6 If `docker compose` is missing on the Jetson

Ubuntu's Jetson ARM64 repositories may not provide a package named `docker-compose-plugin`. First try the Ubuntu Compose v2 package:

```bash
sudo apt-get update
sudo apt-get install -y docker-compose-v2
docker compose version
```

If that package is not available on your image, try the Docker plugin package name:

```bash
sudo apt-get install -y docker-compose-plugin
docker compose version
```

Do not install Compose in the same `apt-get install` command as `docker.io`; if the Compose package name is unavailable, apt aborts the whole transaction.

### 4.7 If the Jetson says the model file does not exist

What to check:

1. the file exists at `$HOME/vision/models/yolo26n.onnx` on the Jetson, or at the filename you selected with `PRIMARY_MODEL_FILENAME`
2. the container model path in the model record is `/models/yolo26n.onnx`, or `/models/$PRIMARY_MODEL_FILENAME` for another selected ONNX file
3. the edge compose worker is using the `../models:/models:ro` volume mount

### 4.8 If model registration returns `500 Internal Server Error` on the iMac

Most likely causes:

- the backend container cannot read the model file at the path you sent
- the backend container was not recreated after a compose change that added the local `models/` bind mount or the ONNX model-metadata dependency install
- the model file path is not under this checkout's `models/` directory

What to do:

1. set `MODEL_PATH` from the repo root:

```bash
cd "$HOME/vision"
PRIMARY_MODEL_FILENAME="${PRIMARY_MODEL_FILENAME:-yolo26n.onnx}"
MODEL_PATH="$PWD/models/$PRIMARY_MODEL_FILENAME"
```

2. recreate the backend container once:

```bash
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend
```

3. wait for health again:

```bash
for i in {1..60}; do
  curl -fsS http://127.0.0.1:8000/healthz && break
  sleep 1
done
```

4. retry the model registration command

If the backend still rejects the request after that, the response should now be a readable validation error such as an unreadable ONNX path instead of a generic 500.

### 4.9 If the Live tiles stay offline

What to do:

1. confirm the worker process is still running
2. confirm the camera RTSP URL works from the machine running that worker
3. wait 30 seconds and refresh Live
4. check worker logs for connection errors

### 4.10 If the Jetson cannot reach the iMac

Check:

- the iMac IP address is correct
- both machines are on the same LAN
- the iMac firewall is not blocking the required ports
- the iMac services are still running

Useful checks from the Jetson:

```bash
curl -s "http://$IMAC_IP:8000/healthz"
curl -s "http://$IMAC_IP:8080/realms/argus-dev/.well-known/openid-configuration" | head
```

### 4.11 Advanced: reduced-class custom models

If you are intentionally testing a reduced-class custom model, treat that as an advanced optional workflow:

1. use a genuinely custom reduced-class artifact whose embedded metadata already matches the reduced inventory you want to operate, or use a model format that explicitly requires declared classes
2. choose matching persistent `active_classes` in the camera UI
3. do not treat a default self-describing COCO model such as `yolo26n.onnx` or `yolo12n.onnx` as a reduced-class model by manually declaring a smaller class list
4. do not use that reduced-class setup as the default COCO-first lab path

If you accidentally register a standard COCO model file as though it were a reduced-class model, the failure symptom is usually a metadata mismatch: the ONNX file reports the full COCO inventory, but the Vezor model record was declared with a smaller reduced-class list. Fix that by re-registering the model with its true embedded class inventory and then narrowing camera behavior through `active_classes`.

### 4.12 If `make verify-all` fails

Run it again and read the first failing section carefully. The most common failure buckets are:

- backend did not start cleanly
- frontend is still building
- Playwright cannot bind the local frontend port

The validation script already tries to manage most of that for you. If it still fails:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml ps
docker compose -f infra/docker-compose.dev.yml logs --tail 80 backend
```

### 4.13 If local API generation says `openapi-typescript: command not found`

This means the host-side frontend dependencies were not installed cleanly.

Run:

```bash
cd "$HOME/vision/frontend"
corepack pnpm install --force
corepack pnpm exec openapi-typescript --version
corepack pnpm generate:api
```

What good looks like:

- `openapi-typescript --version` prints a version
- `generate:api` writes `src/lib/api.generated.ts` without error

### 4.14 If `127.0.0.1:9001` does not open

This means MinIO is not healthy yet.

Run:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml logs --tail 40 minio
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate minio backend
curl -I http://127.0.0.1:9001
```

What good looks like:

- MinIO logs no longer show `Invalid credentials`
- `curl -I` returns an HTTP response instead of connection refused

### 4.15 What to do after a successful lab

If both tests pass:

1. keep the iMac as the master node for pilot work
2. prefer the Jetson for future camera inference tests
3. add cameras gradually, not all at once
4. move on to a more production-like deployment only after the Jetson path stays stable

### 4.16 Clean shutdown

When you are done testing:

On the iMac:

```bash
cd "$HOME/vision"
make dev-down
```

On the Jetson:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.edge.yml down
```

If you want to rerun the lab later, start again from section **2.4**.
