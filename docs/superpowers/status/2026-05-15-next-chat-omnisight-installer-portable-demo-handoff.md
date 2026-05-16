# Next Chat Handoff: OmniSight Installer Portable Demo

Date: 2026-05-15

Purpose: paste this document into a fresh chat to continue the installer-managed
MacBook Pro master plus Jetson edge validation from the current branch. Do not
merge to `main` yet.

## Repository State

Continue from the pushed branch:

```text
codex/omnisight-installer
```

Latest pushed branch tip at this handoff includes:

```text
Worker-config supervisor credential route fix
07b958c9 fix(installer): clear stale edge containers before preflight
8c37f50e Wire installed edge NATS leaf
```

Recent relevant checkpoints:

```text
c30f4c6f docs(installer): record live stream validation
49a4cbba fix(workers): allow disabled recording storage mismatch
34ea9272 fix(workers): allow supervisor credentials for worker config
07b958c9 fix(installer): clear stale edge containers before preflight
8c37f50e Wire installed edge NATS leaf
9b1cfade Fix edge runtime Python 3.10 UTC import
7d8098a7 Resolve edge-owned operations profiles
62af6ae5 Point edge MediaMTX auth at master JWKS
a27e3721 Preserve edge identity on unpaired installer updates
f7fa3b0a Fix edge camera live relay setup
c309de69 fix(scenes): show runtime artifacts in setup
01172609 docs(installer): document browser token copy flow
3438e657 fix(models): timestamp runtime artifacts on create
5c10632a docs(installer): use registered model classes for TensorRT artifacts
a68ac698 docs(installer): fix runtime artifact admin script commands
2a19064e docs(installer): update Jetson TensorRT build steps
6608e320 fix(operations): use deployment health for fleet nodes
3c8a88b4 fix(installer): run model preset registration module
334abd52 fix(frontend): add deployment unpair and site delete feedback
```

Start the next chat with:

```bash
cd "$HOME/vision"
git fetch origin
git switch codex/omnisight-installer
git pull --ff-only origin codex/omnisight-installer
git status -sb
git log --oneline -12
```

Known local state:

- unrelated untracked scratch files may exist locally
- do not use `git add -A`
- stage only files needed for the current task
- keep WebGL off

## Primary Docs

Use this guide as the canonical install path:

```text
docs/product-installer-and-first-run-guide.md
```

The older portable guide is now only a dev/manual fallback pointer:

```text
docs/macbook-pro-jetson-portable-demo-install-guide.md
```

The current product-installer implementation plan is:

```text
docs/superpowers/plans/2026-05-14-product-installer-and-no-console-first-run-implementation-plan.md
```

## Verification At Handoff

Last local validation after the installed edge NATS leaf fix:

```bash
make verify-installers
```

Result:

```text
59 installer tests passed
shell syntax passed
manifest validation passed
product secret scan passed
master compose render passed
edge compose render passed
installer validation passed
```

Full repo lint/test was not rerun for this handoff-only doc update. Earlier
full lint had known backend strict mypy debt outside the installer release-gate
surface.

## What Is Working

Implemented on `codex/omnisight-installer`:

- macOS master installer and launchd wrapper
- Linux master installer and systemd wrapper
- Jetson edge installer and systemd wrapper
- `vezor-master`, `vezor-edge`, and `vezorctl` appliance wrappers
- product Compose profiles for master and edge
- first-run bootstrap UI/API
- central and edge pairing with session id plus one-time code
- raw `vzcred_...` supervisor credential storage
- central supervisor id preservation from first-run
- unpaired Jetson updates that preserve paired `edge_node_id`
- public Jetson stream host reporting
- Jetson MediaMTX JWKS pointed at the master backend
- local installed edge NATS leaf container
- Deployment unpair action
- Sites delete button and feedback
- Deployment/Operations empty states and deployment-health status logic
- model registration docs and backend-container helper
- browser dev-tools token copy flow in the installer guide
- TensorRT engine build instructions using `trtexec` on Jetson
- runtime artifact registration and validation docs

Validated by the user during the session:

- MacBook master can install and expose first-run
- first-run can create the tenant/admin
- sign-in works after installer/config fixes
- Deployment page shows central and Jetson nodes
- Jetson edge install succeeds with ONNX Runtime GPU wheel
- Jetson reports hardware/service health after pairing
- model rows can be registered and appear in scene setup
- TensorRT engines for YOLO26n and YOLO26s were built on Jetson and registered
  as valid runtime artifacts

## Current Live Issue And Latest Fix

The last observed Jetson failure before this handoff:

```text
vezor-supervisor logs:
ConnectionRefusedError: Connect call failed ('127.0.0.1', 4222)
nats: encountered error
MediaMTX paths/list: itemCount 0
```

Root cause: the installed edge supervisor/worker container inherited the default
`ARGUS_NATS_URL=nats://127.0.0.1:4222`. Inside the container, `127.0.0.1` is the
container itself, not the master NATS service.

Fix pushed in `8c37f50e`:

- `infra/install/compose/compose.supervisor.yml` now includes
  `vezor-edge-nats-leaf`
- the supervisor container now gets
  `ARGUS_NATS_URL=nats://nats-leaf:4222`
- `installer/linux/install-edge.sh` writes `/etc/vezor/nats/leaf.conf`
- edge NATS leaf connects back to the master leaf listener at
  `nats://MASTER_HOST_OR_IP:7422`
- `make verify-installers` now renders edge compose with `VEZOR_NATS_IMAGE`

2026-05-16 follow-up: after pulling `8c37f50e` on the Jetson, reinstall could
still fail preflight with ports `8554`, `8888`, `8889`, and `9108` in use. The
edge service had been installed before `VEZOR_NATS_IMAGE` existed, so the
installer's stop-old-stack step could fail to render the new compose file and
leave stale product-owned containers bound to the ports.

Latest installer fix:

- `installer/linux/install-edge.sh` exports transition-safe compose image
  variables when it calls `vezor-edge down`
- the installer removes stale product-owned edge containers
  (`vezor-supervisor`, `vezor-edge-mediamtx`, `vezor-edge-nats-leaf`) before
  Jetson preflight
- `docs/product-installer-and-first-run-guide.md` includes the manual cleanup
  fallback for Jetsons that hit this state before pulling the fix

This port cleanup fix has not yet been validated on the physical Jetson. That
is the first next step.

2026-05-16 live-video follow-up: after the port cleanup and NATS leaf fix, the
Jetson logs showed the local NATS leaf connected, the supervisor posted fleet,
service, hardware, and runtime reports, and then the worker process failed on:

```text
GET /api/v1/cameras/<camera-id>/worker-config "HTTP/1.1 401 Unauthorized"
```

Root cause: `/api/v1/cameras/{camera_id}/worker-config` still required a normal
admin JWT, while installed workers only receive the paired supervisor
credential. The next backend fix changes that route to use the same
admin-or-supervisor-credential tenant dependency as the Operations endpoints,
while preserving viewer rejection.

This worker-config credential fix must be pulled on the MacBook master and the
master installer rerun before revalidating the Jetson stream.

2026-05-16 disabled-recording follow-up: after the credential fix was present
on the MacBook master, the Jetson worker reached the worker-config route but
received:

```text
GET /api/v1/cameras/be93bed8-ee2d-4aea-b8bf-e1133e16653e/worker-config "HTTP/1.1 422 Unprocessable Entity"
```

The live response body was:

```text
Privacy policy residency does not match evidence storage residency: 'central' != 'edge'.
```

Root cause: the camera had evidence recording and snapshots disabled, but still
carried an edge-local evidence storage profile from setup. Worker-config
validated privacy/storage residency even though no evidence artifact would be
written, blocking live startup on an unused storage profile.

Fix: skip privacy/storage residency enforcement when evidence recording is
disabled. Keep the existing 422 guard for enabled evidence capture where
artifacts may actually be written.

Validation after applying the fix locally on the MacBook master:

```text
GET /api/v1/cameras/be93bed8-ee2d-4aea-b8bf-e1133e16653e/worker-config -> 200
recording_enabled=false storage_profile=edge_local privacy_residency=central
```

The master MediaMTX relay path then became available:

```text
cameras/be93bed8-ee2d-4aea-b8bf-e1133e16653e/passthrough
ready=true available=true tracks=["MPEG-4 Audio", "H264"]
```

If Live is still not visible after this point, continue at the browser/WebRTC
delivery layer. Before the source became ready, master MediaMTX logged repeated
RTSP source `404`; after the fix it logged the stream as available, then some
WebRTC sessions closed with `deadline exceeded while waiting connection`.

2026-05-16 YOLO11n model follow-up: the Jetson then reached runtime startup
but selected the canonical `YOLO11n COCO` row and failed on:

```text
Load model from /models/yolo11n.onnx failed. File doesn't exist
```

Root cause: the model row on the MacBook master points at
`/models/yolo11n.onnx`, while the edge installer stores host-side models under
`/var/lib/vezor/models`. The edge supervisor compose file mounted
`/var/lib/vezor` but did not expose the runtime alias `/models`, so copying the
file to `/var/lib/vezor/models/yolo11n.onnx` still left
`docker exec vezor-supervisor ls /models/yolo11n.onnx` failing.

Fix: the edge installer now writes `VEZOR_MODEL_HOST_DIR=$MODEL_DIR` to
`/etc/vezor/edge.env`, and `compose.supervisor.yml` mounts
`${VEZOR_MODEL_HOST_DIR:-/var/lib/vezor/models}:/models:ro`.

Validation:

```text
python3 -m uv run --project backend pytest installer/tests/test_edge_installer_artifacts.py -q -> 7 passed
make verify-installers -> 59 installer tests passed and compose render passed
```

2026-05-16 WebRTC delivery follow-up: after the model mount fix, the Jetson
worker reached runtime startup and master MediaMTX could pull the camera RTSP
path, but browser sessions still showed blank video. Master MediaMTX logged
repeated:

```text
WebRTC session closed: deadline exceeded while waiting connection
```

Root cause: the installed product compose files exposed MediaMTX WebRTC HTTP on
`8889/tcp` but did not expose MediaMTX's ICE UDP mux port `8189/udp`. The dev
compose files already exposed `8189/udp`, which is why this was product-install
specific.

Fix: product master and edge supervisor compose profiles now expose
`8189:8189/udp`, and macOS/Linux master plus Jetson preflight checks now verify
UDP port `8189` availability.

Validation:

```text
python3 -m uv run --project backend pytest installer/tests/test_edge_installer_artifacts.py installer/tests/test_linux_master_artifacts.py installer/tests/test_macos_master_artifacts.py -q -> 31 passed
make verify-installers -> 59 installer tests passed and compose render passed
```

## Immediate Next Step

On the MacBook master, pull latest and rerun the master installer so Docker
recreates MediaMTX with UDP `8189` published:

```bash
cd /opt/vezor/current
git fetch origin
git pull --ff-only origin codex/omnisight-installer
sudo ./installer/macos/install-master.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://192.168.1.166:3000"
docker inspect vezor-master-mediamtx-1 --format '{{json .NetworkSettings.Ports}}'
```

Expected: the Docker port map includes `8189/udp`.

On the Jetson, pull latest and rerun the edge installer as an unpaired update:

```bash
cd /opt/vezor/current
git fetch origin
git pull --ff-only origin codex/omnisight-installer

MASTER_API_URL="http://192.168.1.166:8000"
JETSON_STREAM_HOST="$(hostname -I | awk '{print $1}')"
JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"

sudo ./installer/linux/install-edge.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --api-url "$MASTER_API_URL" \
  --unpaired \
  --edge-name "jetson-portable-1" \
  --model-dir /var/lib/vezor/models \
  --public-stream-host "$JETSON_STREAM_HOST" \
  --jetson-ort-wheel-url "$JETSON_ORT_WHEEL_URL"
```

Then make sure the selected ONNX model exists on the Jetson runtime model
directory and is visible at `/models` inside the supervisor container:

```bash
sudo install -d -m 0755 /var/lib/vezor/models
sudo install -m 0644 /tmp/yolo11n.onnx /var/lib/vezor/models/yolo11n.onnx
docker exec vezor-supervisor ls -lh /models/yolo11n.onnx
```

If `/tmp/yolo11n.onnx` is not present on the Jetson, copy the master machine's
registered `/var/lib/vezor/models/yolo11n.onnx` to the Jetson first, or switch
the camera to a model file already present on the Jetson such as `YOLO26n COCO`.

Then check:

```bash
docker ps --filter name=vezor
docker logs --tail 80 vezor-edge-nats-leaf
docker logs --tail 120 vezor-supervisor
curl -fsS http://127.0.0.1:9997/v3/paths/list
```

Expected:

- `vezor-edge-nats-leaf` is running
- no repeated `127.0.0.1:4222` NATS connection errors
- `vezor-supervisor` continues polling and model admission succeeds
- after a Jetson-owned camera is started, MediaMTX exposes the camera path
- Live transitions from negotiating/awaiting telemetry to visible video and
  telemetry

If the leaf logs cannot connect to the master, verify the Mac master exposes
the NATS leaf listener:

```bash
docker ps --filter name=vezor-master-nats
docker port vezor-master-nats-1
```

The master compose is expected to bind `7422` on `0.0.0.0` for leaf nodes.

## Known Operational Guidance

- For Jetson-owned cameras, the Operations lifecycle owner must be
  `Edge supervisor`. `Central supervisor` only owns centrally run workers.
- Camera setup should assign the Jetson edge node in the scene/camera flow; an
  Operations profile binding alone does not make the source edge-owned.
- The scene model dropdown selects canonical model rows such as `YOLO26n COCO`.
  TensorRT is a runtime artifact attached to that row, not a separate model
  dropdown option.
- The default ONNX export is static 640x640. Build TensorRT engines with
  `trtexec --onnx ... --fp16` and do not pass `--shapes=...`.
- The installed Jetson worker image uses Python 3.10 to load the `cp310`
  ONNX Runtime GPU wheel. Installer/admin tooling uses Python 3.12.
- Use short-lived browser tokens only for branch-validation admin scripts such
  as model/runtime artifact registration. This remains setup/admin tooling, not
  normal product operation.
- If the portable network changes, rerun the Jetson installer with
  `--unpaired --public-stream-host NEW_JETSON_IP_OR_HOSTNAME`.

## Next Product Work After Live Is Stable

1. Validate Jetson live video and telemetry after the NATS leaf fix.
2. Confirm native passthrough and processed stream modes from Live.
3. Create one real evidence clip and review it in Evidence.
4. Exercise Operations Start/Stop/Restart/Drain for the Jetson camera.
5. Run a small reboot validation: Mac master service, Jetson edge service,
   Deployment heartbeat, Operations status, Live stream.
6. If stable, record Track A/B Jetson soak evidence for registered runtime
   artifacts.
7. Only after soak evidence exists, decide whether Task 24 / DeepStream can be
   opened. It remains deferred for now.

## Guardrails To Carry Forward

- Stay on `codex/omnisight-installer`; no merge to `main` yet.
- Execute one task at a time.
- Commit and push after each completed task.
- Do not stage unrelated untracked scratch files.
- Keep WebGL off.
- Keep the backend/browser as a control plane, not a remote shell.
- Final product operation must not depend on copied bearer tokens or foreground
  terminal supervisor processes after installation.
- Do not start Task 24 / DeepStream before Track A/B Jetson soak evidence unless
  the user explicitly accepts that risk.

## Suggested Next Prompt

```text
We are continuing Vezor/OmniSight installer validation from branch codex/omnisight-installer.

Read the handoff first:
docs/superpowers/status/2026-05-15-next-chat-omnisight-installer-portable-demo-handoff.md

Use the canonical installer guide:
docs/product-installer-and-first-run-guide.md

We are at the point where commit 8c37f50e fixed installed Jetson edge NATS by adding a local nats-leaf service. First, help me validate the Jetson after rerunning install-edge.sh --unpaired. Do not start Task 24 / DeepStream. Keep WebGL off. Stay on this branch and do not merge to main.
```
