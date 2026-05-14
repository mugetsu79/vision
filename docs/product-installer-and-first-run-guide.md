# Vezor Product Installer And First-Run Guide

Use this guide for the installer-managed product path on:

- a Linux `amd64` master for production or production-like validation
- a macOS master for portable MacBook Pro pilot and demo systems
- a Jetson Orin edge node for site-local inference

For the full MacBook Pro/Linux master + Jetson installer checklist, model
download/export steps, and current branch-validation caveats, use
[omnisight-installer-macbook-pro-jetson-install-guide.md](/Users/yann.moren/vision/docs/omnisight-installer-macbook-pro-jetson-install-guide.md).

The normal installed product flow is:

1. install the local service package on each host
2. generate the local first-run master bootstrap token on the master
3. complete `/first-run` in the browser
4. pair central and edge nodes from Control -> Deployment
5. operate workers from Control -> Operations

The browser and backend are a control plane. They do not run arbitrary host
shell commands. Installers and `vezorctl` run locally on the host being
installed or serviced.

## Current Branch Validation Shape

The branch installer artifacts are checked in as scripts and service templates,
not as signed `.pkg` or `.deb` packages yet. For branch validation, place the
checkout at the same path the product package will use:

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

The final production installer will lay down `/opt/vezor/current`, image
manifests, service wrappers, secrets, and wrapper commands itself. The branch
validation shape keeps that layout visible while you test the flow. The branch
uses `installer/.venv/bin/vezorctl`; final packages should install an operator
wrapper on `PATH`.

## Before Installing

Prepare these values:

| Item | Example |
|---|---|
| Release path | `/opt/vezor/current` |
| Master public URL | `http://127.0.0.1:3000` for local pilot, `https://vezor.example.com` for production |
| Master API URL | `http://127.0.0.1:8000` locally, or the production API URL |
| Master data directory | `/var/lib/vezor` |
| Master config directory | `/etc/vezor` |
| Jetson edge name | `jetson-portable-1` |
| Jetson model directory | `/var/lib/vezor/models` |

Master prerequisites:

- Linux master: Linux `amd64`, `systemd`, Docker or Podman, open product ports
- macOS master: Apple Silicon or Intel macOS, Docker Desktop installed and
  started, administrator access for LaunchDaemon installation
- both master paths: release files available under `/opt/vezor/current`

Jetson prerequisites:

- Jetson Orin Nano Super 8 GB or equivalent Jetson target
- JetPack 6 compatible CUDA/TensorRT stack
- Docker and NVIDIA Container Toolkit
- camera access validated from the Jetson
- model files copied to the chosen model directory

Run the Jetson preflight before the edge install:

```bash
cd /opt/vezor/current
sudo nvpmodel -m 2
sudo jetson_clocks
./scripts/jetson-preflight.sh --installer --json
```

## Install A Linux Master

Linux is the production master path.

On the Linux master:

```bash
cd /opt/vezor/current
sudo installer/linux/install-master.sh \
  --version "pilot-2026-05" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://MASTER_HOST_OR_IP:3000" \
  --data-dir /var/lib/vezor \
  --config-dir /etc/vezor
```

What the installer owns:

- creates `/etc/vezor`, `/var/lib/vezor`, `/var/log/vezor`, and `/run/vezor`
- writes `/etc/vezor/master.json`
- installs `infra/install/systemd/vezor-master.service`
- starts and enables `vezor-master.service`
- uses the product Compose appliance profile under
  `infra/install/compose/compose.master.yml`

Validate locally:

```bash
systemctl status vezor-master.service
curl -fsS http://127.0.0.1:8000/healthz
```

Open the first-run UI:

```text
http://MASTER_HOST_OR_IP:3000/first-run
```

## Install A macOS Master

macOS is the portable pilot and demonstration master path. It is the right path
for the M4 Pro MacBook Pro plus Jetson kit when no Linux master is available.

On the MacBook:

```bash
cd /opt/vezor/current
sudo installer/macos/install-master.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "http://127.0.0.1:3000" \
  --data-dir /var/lib/vezor
```

What the installer owns:

- writes `/etc/vezor/master.json`
- installs `infra/install/launchd/com.vezor.master.plist`
- starts the `com.vezor.master` LaunchDaemon
- writes logs under `/var/log/vezor`

Validate locally:

```bash
sudo launchctl print system/com.vezor.master
curl -fsS http://127.0.0.1:8000/healthz
```

Open:

```text
http://127.0.0.1:3000/first-run
```

## Complete Master First-Run

The bootstrap token is local-only. Generate it on the master host:

```bash
/opt/vezor/current/installer/.venv/bin/vezorctl bootstrap-master \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

The response includes a `vzboot_...` token and expiry. Use it immediately in
`/first-run`, then fill in:

- tenant name
- first administrator email
- first administrator password
- master node name
- optional central supervisor id

After setup completes, sign in and open Control -> Deployment. If the token
expires, rotate another local token from the master host and retry. Token
rotation is intentionally restricted to local requests.

## Pair A Central Supervisor

From Control -> Deployment:

1. Click `Pair central`.
2. Copy the pairing session id and one-time pairing code.
3. Run pairing locally on the master host.

On the master host:

```bash
/opt/vezor/current/installer/.venv/bin/vezorctl pair \
  --api-url "http://127.0.0.1:8000" \
  --session-id "PAIRING_SESSION_ID" \
  --pairing-code "PAIRING_CODE" \
  --supervisor-id "central-master-1" \
  --hostname "$(hostname)" \
  --credential-path /run/vezor/credentials/supervisor.credential
```

Then restart or reload the master service so the supervisor picks up the node
credential:

```bash
sudo systemctl restart vezor-master.service
```

On macOS:

```bash
sudo launchctl kickstart -k system/com.vezor.master
```

Return to Control -> Deployment and confirm the node shows an installed or
healthy service state, a fresh heartbeat, and an active credential status.

## Install And Pair A Jetson Edge Node

Create or select the edge node in the UI first:

1. Open Control -> Deployment.
2. Pair the edge node row, or create an edge pairing session for the selected
   edge node.
3. Copy the session id and one-time pairing code.

On the Jetson:

```bash
cd /opt/vezor/current
sudo installer/linux/install-edge.sh \
  --api-url "http://MASTER_HOST_OR_IP:8000" \
  --session-id "PAIRING_SESSION_ID" \
  --pairing-code "PAIRING_CODE" \
  --edge-name "jetson-portable-1" \
  --model-dir /var/lib/vezor/models
```

The edge installer:

- validates Jetson prerequisites with `scripts/jetson-preflight.sh --installer --json`
- writes `/etc/vezor/edge.json`
- writes `/etc/vezor/supervisor.json`
- claims the pairing session with `vezorctl pair`
- installs `infra/install/systemd/vezor-edge.service`
- starts and enables the service

Validate on the Jetson:

```bash
systemctl status vezor-edge.service
/opt/vezor/current/installer/.venv/bin/vezorctl status --json
```

Return to Control -> Deployment and confirm:

- service manager is `systemd`
- install status is installed, healthy, or another truthful non-dev state
- credential status is active
- support bundle redacts credential material

## Configure Cameras

Use Control -> Scenes.

For the MacBook portable pilot:

- optional central camera: use an RTSP camera reachable from the MacBook
- primary Jetson camera: use RTSP or USB/UVC on the Jetson, assign the Jetson
  edge node, and use `edge` processing mode
- one Jetson camera first; add the second only after the first survives the
  validation checklist

For native browser delivery, do not select dedicated reduced resolution or
frame-rate profiles. Native means clean passthrough. Choose a reduced profile
only when you want a worker-published processed viewing rendition.

Before starting workers, save:

- camera source and processing mode
- model selection
- privacy policy
- include/exclusion regions
- recording policy
- evidence storage profile
- at least one reviewable incident rule if Evidence is part of validation

## Validate Lifecycle From The UI

Use Control -> Operations after node pairing.

For each test camera:

1. confirm desired worker location is the intended node
2. confirm model admission is not `unknown` or `unsupported`
3. click Start
4. verify runtime state, heartbeat, restart count, rule count, and delivery
   diagnostics
5. click Restart and verify a new runtime report arrives
6. click Stop or Drain for maintenance behavior

If a camera has no eligible installed supervisor, Operations should send you
back to Control -> Deployment to install or pair one. It should not show a raw
Docker command or copied bearer-token worker command during normal installed
operation.

## Validate Live, History, Evidence, And Configuration

Before taking the kit to a demo, validate:

- Live renders the Jetson camera without browser fetch errors
- History receives telemetry buckets
- Evidence opens incident detail pages and camera links without route errors
- clips are reviewable when recording is enabled
- Sites can create, edit, and delete a throwaway location
- Scenes can save all camera setup options
- Settings configuration profiles are selected for evidence storage, stream
  delivery, runtime selection, privacy, and optional LLM provider
- Deployment support bundles redact tokens, passwords, pairing codes, and node
  credentials

## Reboot And Service Validation

Master:

```bash
sudo reboot
```

After reboot:

```bash
curl -fsS http://127.0.0.1:8000/healthz
```

Linux master:

```bash
systemctl status vezor-master.service
```

macOS master:

```bash
sudo launchctl print system/com.vezor.master
```

Jetson:

```bash
sudo reboot
systemctl status vezor-edge.service
```

Then check Control -> Deployment for fresh service reports and Control ->
Operations for truthful worker state. A reboot test passes only when no
foreground terminal supervisor process is needed.

## Credential Rotation

From Control -> Deployment:

1. Click `Rotate credential` for the node.
2. Copy the credential material shown once.
3. Write it into the node-local credential store on that host.
4. Restart the owning service.
5. Confirm the node reports with the new credential.

Old credentials are revoked by the backend. Supervisors that keep the old
credential should stop polling successfully until the local credential store is
updated.

## Support Bundle

Use Control -> Deployment for normal support bundles. It should include
service state, install state, lifecycle/runtime summaries, hardware/model
admission summaries, config references, selected logs, and diagnostics.

For a local-only support check:

```bash
/opt/vezor/current/installer/.venv/bin/vezorctl support-bundle \
  --input /var/lib/vezor/support/latest.json \
  --redact \
  --json
```

Never send an unredacted bundle outside the trusted operator boundary.

## Upgrade

For branch validation:

1. stop product services
2. update `/opt/vezor/current` to the target branch or release
3. run database migrations through the installed backend startup path
4. restart the service
5. verify `/healthz`, sign-in, Deployment, Operations, Live, History, Evidence,
   and one worker restart

Linux:

```bash
sudo systemctl stop vezor-master.service
cd /opt/vezor/current
git fetch origin
git switch codex/omnisight-installer
git pull --ff-only origin codex/omnisight-installer
sudo systemctl start vezor-master.service
```

macOS:

```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.vezor.master.plist
cd /opt/vezor/current
git fetch origin
git switch codex/omnisight-installer
git pull --ff-only origin codex/omnisight-installer
sudo launchctl bootstrap system /Library/LaunchDaemons/com.vezor.master.plist
```

Final production installers will replace this branch-update shape with signed
packages, pinned image digests, rollback metadata, and release manifests.

## Uninstall

Linux master service:

```bash
cd /opt/vezor/current
sudo installer/linux/uninstall.sh
```

Jetson edge service during branch validation:

```bash
sudo systemctl stop vezor-edge.service
sudo systemctl disable vezor-edge.service
sudo rm -f /etc/systemd/system/vezor-edge.service
sudo systemctl daemon-reload
```

macOS master:

```bash
cd /opt/vezor/current
sudo installer/macos/uninstall.sh
```

Default uninstall preserves `/var/lib/vezor` and `/etc/vezor`. To delete data,
you must provide the exact confirmation string:

```bash
sudo installer/linux/uninstall.sh --purge-data delete-vezor-data
sudo installer/macos/uninstall.sh --purge-data delete-vezor-data
```

## What Remains Development Fallback Or Break-Glass

Development fallback: `make dev-up` and hand-run `docker compose` commands are
for local development, old portable lab flows, installer debugging, and CI
validation. They are not the final operator path.

Break-glass: `ARGUS_API_BEARER_TOKEN` shell workers and foreground
`argus.supervisor.runner` commands are acceptable for deterministic smoke tests
or emergency support while an installer issue is diagnosed. They must not be
copied into service files or required for normal operation after installation.

Deferred: Task 24 / DeepStream remains out of scope until the installer-managed
Track A/B Jetson soak evidence is recorded or the risk is explicitly accepted.
