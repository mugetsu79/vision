# Argus Lab Guide: iMac Master And Jetson Orin Edge

Date: 2026-04-19

This guide is written for a first lab rollout of Argus on:

- a **2019 iMac i9 with Radeon 580 8 GB** as the Argus master node
- a **Jetson Orin Nano Super 8 GB** on Ubuntu installed on NVMe as the Argus edge node
- **2 RTSP cameras**

It walks through two tests:

1. **Test A: iMac only**
   The iMac runs the full Argus stack and both camera workers.
2. **Test B: iMac master + Jetson edge**
   The iMac stays the master node, camera 1 stays central, and camera 2 moves to the Jetson.

The goal is not to prove final production performance. The goal is to prove that the full Argus workflow works on your hardware from sign-in to live view to history and incidents.

Related documents:

- [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md)
- [operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md)
- [runbook.md](/Users/yann.moren/vision/docs/runbook.md)

## 1. Before You Start

### 1.1 What you need

You need all of the following before you begin:

- administrator access on the iMac
- administrator access on the Jetson
- the Argus repository on both machines
- 2 working RTSP camera URLs
- 1 detector model file in ONNX format
- both machines and both cameras on the same local network
- enough free disk space for Docker images and logs

This guide assumes the model file is called `yolo12n.onnx`. If your file has a different name, replace it everywhere in the commands below.

### 1.2 What this lab proves

After you finish:

- you can sign in to Argus
- you can create a site
- you can create cameras
- you can run inference workers
- you can view live telemetry
- you can confirm history and incidents
- you can compare `central` processing against `edge` processing

### 1.3 Important limits of this lab

- The iMac is being used as a **lab master node**, not the final reference production inference server.
- The Radeon 580 is **not** the hardened central GPU target for Argus.
- This guide assumes you are doing a **functional test with 2 cameras**, not a scale test.
- The Jetson portion is the more realistic Argus architecture test.

### 1.4 A few words explained in plain language

- **Master node**: the main Argus machine. It hosts the web UI, API, database, auth, storage, and orchestration.
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
| ONNX model filename | |

### 1.6 Use these exact test names

To keep the commands simple, use these names:

- Site name: `Lab Site`
- Camera 1 name: `Lab Camera 1`
- Camera 2 name: `Lab Camera 2`
- iMac model record name: `YOLO12n iMac`
- Jetson model record name: `YOLO12n Edge`

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

- `8000` Argus backend API
- `8080` Keycloak
- `5432` PostgreSQL
- `7422` NATS leaf upstream
- `9000` MinIO

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

#### Step 3: Install Git, Python, and Node

Run:

```bash
brew install git python@3.12 node
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

### 2.2 Clone the Argus repository on the iMac

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

### 2.3 Put the model file in the repository

Create the models directory:

```bash
cd "$HOME/vision"
mkdir -p models
```

Copy your ONNX model file into:

```text
$HOME/vision/models/yolo12n.onnx
```

If your file has a different name, keep note of the new path and replace it in the commands below.

Verify it exists:

```bash
ls -lh "$HOME/vision/models"
```

What good looks like:

- you can see the model file in the list

### 2.4 Start the Argus control plane on the iMac

From the repository root:

```bash
cd "$HOME/vision"
make dev-up
cd backend && python3 -m uv run alembic upgrade head
cd ../frontend && corepack pnpm generate:api
cd ..
```

Wait about 30 to 60 seconds on the first run.

Now check the main pages in your browser:

- [http://127.0.0.1:3000](http://127.0.0.1:3000)
- [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)
- [http://127.0.0.1:8080](http://127.0.0.1:8080)
- [http://127.0.0.1:9001](http://127.0.0.1:9001)

What good looks like:

- the frontend opens
- the health URL returns `{"status":"ok"}`
- the Keycloak page opens
- the MinIO console opens

If the health URL does not work:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.dev.yml ps
docker compose -f infra/docker-compose.dev.yml logs --tail 80 backend
```

### 2.5 Get the model metadata

Argus needs the model hash and file size when you register a model.

Run:

```bash
MODEL_PATH="$HOME/vision/models/yolo12n.onnx"
MODEL_SHA="$(shasum -a 256 "$MODEL_PATH" | awk '{print $1}')"
MODEL_SIZE="$(stat -f%z "$MODEL_PATH")"
echo "$MODEL_PATH"
echo "$MODEL_SHA"
echo "$MODEL_SIZE"
```

What good looks like:

- the first line is the model path
- the second line is a long SHA-256 hash
- the third line is a file size number

### 2.6 Get an Argus admin token on the iMac

Argus ships with a seeded local development admin user:

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

Keep this iMac terminal window open. Later commands in this guide reuse:

- `TOKEN`
- `MODEL_PATH`
- `MODEL_SHA`
- `MODEL_SIZE`

### 2.7 Register the iMac model record

This model record uses the **iMac path** to the model file. It is only for Test A.

Run:

```bash
IMAC_MODEL_ID="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    http://127.0.0.1:8000/api/v1/models \
    -d "{
      \"name\": \"YOLO12n iMac\",
      \"version\": \"lab-imac\",
      \"task\": \"detect\",
      \"path\": \"$MODEL_PATH\",
      \"format\": \"onnx\",
      \"classes\": [\"person\", \"car\", \"bus\", \"truck\", \"motorcycle\", \"bicycle\"],
      \"input_shape\": {\"width\": 640, \"height\": 640},
      \"sha256\": \"$MODEL_SHA\",
      \"size_bytes\": $MODEL_SIZE,
      \"license\": \"lab\"
    }" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"
echo "$IMAC_MODEL_ID"
```

What good looks like:

- the command prints a UUID

If you get a message that the model already exists:

1. open the list of models with:

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/models | python3 -m json.tool
```

2. find the existing `YOLO12n iMac` entry
3. reuse its `id`

### 2.8 Sign in to the Argus UI

1. Open [http://127.0.0.1:3000](http://127.0.0.1:3000)
2. Click **Sign in**
3. On the Keycloak login page, enter:
   - username: `admin-dev`
   - password: `argus-admin-pass`
4. Submit the form

What good looks like:

- you land in the Argus app shell

### 2.9 Create the site in the UI

1. In the left navigation, click **Sites**
2. Click **Add site**
3. Enter:
   - Site name: `Lab Site`
   - Description: `Initial Argus lab site`
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
   - Primary model: `YOLO12n iMac`
   - Tracker type: keep `botsort`
   - Secondary model: leave empty
6. Click **Continue**
7. In **Privacy, Processing & Delivery**:
   - leave privacy defaults as-is
   - Frame skip: `1`
   - FPS cap: `25`
   - Browser delivery profile: `720p10`
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
- Primary model: `YOLO12n iMac`
- Tracker type: `botsort`
- Browser delivery profile: `720p10`
- Calibration:
  - click **Add source point** 4 times
  - click **Add destination point** 4 times
  - Reference distance (m): `10`

What good looks like:

- `Lab Camera 1` and `Lab Camera 2` are both visible in the cameras table

### 2.12 Get the camera IDs

You need the camera IDs to start the workers.

Run:

```bash
CAMERA_ONE_ID="$(
  curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/cameras |
  CAMERA_NAME='Lab Camera 1' python3 -c 'import json,os,sys; name=os.environ["CAMERA_NAME"]; cameras=json.load(sys.stdin); print(next(camera["id"] for camera in cameras if camera["name"] == name))'
)"

CAMERA_TWO_ID="$(
  curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/cameras |
  CAMERA_NAME='Lab Camera 2' python3 -c 'import json,os,sys; name=os.environ["CAMERA_NAME"]; cameras=json.load(sys.stdin); print(next(camera["id"] for camera in cameras if camera["name"] == name))'
)"

echo "$CAMERA_ONE_ID"
echo "$CAMERA_TWO_ID"
```

What good looks like:

- both commands print UUIDs

### 2.13 Start the iMac worker for camera 1

Open a **new Terminal window or tab** on the iMac.

Run:

```bash
cd "$HOME/vision/backend"
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

Run:

```bash
cd "$HOME/vision/backend"
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

### 2.15 Check the live dashboard

1. Go back to the browser on the iMac
2. Open the **Dashboard**
3. Wait up to 30 seconds

What good looks like:

- both camera tiles appear
- each tile eventually shows `online`
- the telemetry badge changes to a live state

### 2.16 Check History and Incidents

1. Open **History**
2. Confirm that some event data appears after the workers have been running for a short time
3. Open **Incidents**
4. If nothing appears yet, let the cameras run longer or create a scene that triggers detections

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
- health checks succeed

### 2.18 Test A is a pass only if all of these are true

- you can sign in
- you can create a site
- you can create both cameras
- both workers stay up
- both cameras appear in Dashboard
- at least one of History or Incidents shows real data
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

#### Step 1: Install Git, curl, Docker, and GStreamer tools

Run:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates docker.io docker-compose-plugin gstreamer1.0-tools
```

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

Copy the same ONNX model file to:

```text
$HOME/vision/models/yolo12n.onnx
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

If it ends with one or more `FAIL` lines, stop here and fix those issues before continuing.

### 3.3 Create the Jetson-specific model record on the iMac

The Jetson container sees the model file at `/models/yolo12n.onnx`, not at your home-directory path. That is why you need a second model record.

Back on the iMac, in any Terminal window where `TOKEN`, `MODEL_SHA`, and `MODEL_SIZE` still exist, run:

```bash
EDGE_MODEL_ID="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    http://127.0.0.1:8000/api/v1/models \
    -d "{
      \"name\": \"YOLO12n Edge\",
      \"version\": \"lab-edge\",
      \"task\": \"detect\",
      \"path\": \"/models/yolo12n.onnx\",
      \"format\": \"onnx\",
      \"classes\": [\"person\", \"car\", \"bus\", \"truck\", \"motorcycle\", \"bicycle\"],
      \"input_shape\": {\"width\": 640, \"height\": 640},
      \"sha256\": \"$MODEL_SHA\",
      \"size_bytes\": $MODEL_SIZE,
      \"license\": \"lab\"
    }" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"
echo "$EDGE_MODEL_ID"
```

What good looks like:

- the command prints a UUID

### 3.4 Edit camera 2 in the Argus UI

Back in the browser on the iMac:

1. Open **Cameras**
2. Find `Lab Camera 2`
3. Click **Edit**

Change these values:

- Processing mode: `edge`
- Primary model: `YOLO12n Edge`

Keep these values:

- Site: `Lab Site`
- Tracker type: `botsort`
- Browser delivery profile: `720p10`
- Calibration: keep the existing values

Save the changes.

What good looks like:

- `Lab Camera 2` now shows `edge` in the cameras table

### 3.5 Refresh the camera 2 ID just to be safe

Back on the iMac, run:

```bash
CAMERA_TWO_ID="$(
  curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/cameras |
  CAMERA_NAME='Lab Camera 2' python3 -c 'import json,os,sys; name=os.environ["CAMERA_NAME"]; cameras=json.load(sys.stdin); print(next(camera["id"] for camera in cameras if camera["name"] == name))'
)"
echo "$CAMERA_TWO_ID"
```

### 3.6 Get a fresh admin token on the Jetson

Tokens are temporary. Generate a fresh one on the Jetson, using the iMac IP address.

On the Jetson:

```bash
IMAC_IP="PUT_THE_IMAC_IP_HERE"
JETSON_TOKEN="$(
  curl -s \
    --data 'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' \
    "http://$IMAC_IP:8080/realms/argus-dev/protocol/openid-connect/token" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
echo "${JETSON_TOKEN:0:32}..."
```

Replace `PUT_THE_IMAC_IP_HERE` with the real iMac IP address you wrote down in section **1.5**.

Now paste the camera 2 ID that you printed on the iMac in section **3.5**:

```bash
CAMERA_TWO_ID="PASTE_CAMERA_TWO_ID_HERE"
echo "$CAMERA_TWO_ID"
```

### 3.7 Point the Jetson NATS leaf config to the iMac

On the Jetson:

```bash
cd "$HOME/vision"
sed -i "s#nats://host.docker.internal:7422#nats://$IMAC_IP:7422#" infra/nats/leaf.conf
grep -n "urls" infra/nats/leaf.conf
```

What good looks like:

- the `grep` output shows the iMac IP address and port `7422`

### 3.8 Start the Jetson edge stack

On the Jetson:

```bash
cd "$HOME/vision"
export ARGUS_API_BASE_URL="http://$IMAC_IP:8000"
export ARGUS_API_BEARER_TOKEN="$JETSON_TOKEN"
export ARGUS_DB_URL="postgresql+asyncpg://argus:argus@$IMAC_IP:5432/argus"
export ARGUS_MINIO_ENDPOINT="$IMAC_IP:9000"
export ARGUS_EDGE_CAMERA_ID="$CAMERA_TWO_ID"
docker compose -f infra/docker-compose.edge.yml up -d --build
```

Now watch the logs:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

What good looks like:

- the container starts
- there is no `401 Unauthorized`
- there is no “model file not found”
- the worker keeps running

### 3.9 Confirm camera 2 is now working from the Jetson

Back on the iMac browser:

1. Open **Dashboard**
2. Wait up to 30 seconds

What good looks like:

- `Lab Camera 1` stays online
- `Lab Camera 2` comes back online
- both still render in the operator UI

Now open **History** and **Incidents** again and confirm that data continues to arrive.

### 3.10 Optional: check Jetson worker metrics

On the Jetson:

```bash
curl -s http://127.0.0.1:9108/metrics | head
```

What good looks like:

- you see Prometheus-style metrics text

### 3.11 Test B is a pass only if all of these are true

- the iMac control plane stays healthy
- camera 1 still works in `central` mode
- camera 2 works in `edge` mode from the Jetson
- the Jetson worker keeps running
- the Dashboard still shows both cameras
- History and Incidents still work

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
   - the full iMac path for `YOLO12n iMac`
   - `/models/yolo12n.onnx` for `YOLO12n Edge`
4. restart the worker

### 4.3 If the worker says `401` or `403`

The worker could not fetch its runtime config.

What to do:

1. create a fresh token
2. make sure you exported `ARGUS_API_BEARER_TOKEN`
3. restart the worker

For the Jetson container:

```bash
cd "$HOME/vision"
docker compose -f infra/docker-compose.edge.yml down
docker compose -f infra/docker-compose.edge.yml up -d
```

### 4.4 If the Jetson says the model file does not exist

What to check:

1. the file exists at `$HOME/vision/models/yolo12n.onnx` on the Jetson
2. the container model path in the model record is `/models/yolo12n.onnx`
3. the edge compose worker is using the `../models:/models:ro` volume mount

### 4.5 If the Dashboard tiles stay offline

What to do:

1. confirm the worker process is still running
2. confirm the camera RTSP URL works from the machine running that worker
3. wait 30 seconds and refresh the Dashboard
4. check worker logs for connection errors

### 4.6 If the Jetson cannot reach the iMac

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

### 4.7 If `make verify-all` fails

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

### 4.8 What to do after a successful lab

If both tests pass:

1. keep the iMac as the master node for pilot work
2. prefer the Jetson for future camera inference tests
3. add cameras gradually, not all at once
4. move on to a more production-like deployment only after the Jetson path stays stable

### 4.9 Clean shutdown

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
