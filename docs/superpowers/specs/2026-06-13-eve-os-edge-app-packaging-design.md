# EVE-OS Edge App Packaging Design

Date: 2026-06-13
Branch: `codex/sceneops-pack-registry`
Sequencing: **Last of three specs.** Depends on
`2026-06-13-tracker-continuity-improvements-design.md` and
`2026-06-13-dev-stack-stability-fixes-design.md` being merged first so
the artifacts ship with the improved tracker and the stable dev stack.

## Goal

Make the Vezor edge worker easily deployable onto devices running
[EVE-OS](https://lfedge.org/projects/eve/) (the LF Edge KVM-based edge
hypervisor) as an EVE-OS App Instance. Two artifact shapes are shipped:

1. A **VM app** (`vezor-edge-amd64.qcow2`) with optional PCIe
   passthrough for an NVIDIA GPU on the EVE-OS host.
2. An **OCI container app** (`ghcr.io/<org>/vezor-edge:VERSION-amd64`)
   for hosts where container-app deployment is preferred.

Both target `linux/amd64` only. ARM64 and a dedicated no-cloud-init
pairing endpoint are explicit follow-up work.

## Why Now

The existing edge artifact (`backend/Dockerfile.edge`) is locked to
NVIDIA L4T Jetson and Python 3.10. EVE-OS hosts are typically x86_64
industrial gateways (Advantech, Lenovo ThinkEdge, Supermicro IoT,
generic Intel NUCs) sometimes equipped with a discrete NVIDIA GPU. None
of these can run the Jetson image as-is. A generic amd64 edge image
plus EVE-OS App Instance packaging is the smallest path to "drop the
Vezor edge onto an EVE-OS device and pair it from the master UI".

This spec also unblocks the documented gap in
`docs/deployment-modes-and-matrix.md` that "there is not currently a
separate generic non-Jetson edge image that preserves Python 3.12".

## Architecture Decision

EVE-OS supports App Instance Configs in two flavours: VM (qcow2) and
container (OCI). Both expose a *user-data* / environment-variable
channel from the controller into the guest. Vezor reuses its existing
`bin/vezor install edge --api-url … --session-id … --pairing-code …`
flow inside the guest, driven by that channel. No new pairing protocol
is designed.

```text
EVE-OS controller UI
  -> App Instance Config
       image ref         (qcow2 or OCI)
       user-data / env   (VEZOR_API_URL, VEZOR_SESSION_ID,
                          VEZOR_PAIRING_CODE)
       device passthrough (optional: NVIDIA GPU via VFIO,
                           USB Coral, etc.)
       network attach     (LAN with camera reach)

EVE-OS host (qemu/KVM under EVE-OS runtime)
  -> VM guest  (Debian 12 minimal)
       systemd: vezor-eve-bootstrap.service
       -> reads /var/lib/cloud/instance/user-data
       -> execs `bin/vezor install edge ...`
       -> systemd: vezor-edge.service takes over
  OR
  -> container guest (vezor-edge image)
       entrypoint /usr/local/bin/eve-firstboot.sh
       -> reads VEZOR_* env vars
       -> execs `bin/vezor install edge ...`
       -> exec /usr/local/bin/vezor-edge-supervisor
```

The pairing flow ends in the existing supervisor lifecycle (systemd
unit on the VM, PID-1 supervisor in the container). After pairing,
control-plane operations are identical to a Linux master pairing a
Jetson edge today.

## Artifacts

### Artifact 1 — `vezor-edge-amd64.qcow2`

| Property | Value |
|---|---|
| Base image | Debian 12 (`bookworm`) minimal cloud variant |
| Architecture | `linux/amd64` |
| Format | qcow2, ~3–5 GB compressed |
| Pairing | Cloud-init NoCloud datasource (EVE-OS user-data) |
| GPU support | Optional NVIDIA via VFIO PCIe passthrough; CPU fallback |
| Build tool | Packer with the `qemu` builder |
| Bakes in | Docker engine, `vezor-edge:VERSION-amd64` OCI image preloaded, `bin/vezor`, `vezor-eve-bootstrap.service` systemd unit |
| Runtime | The OCI image runs under Docker on the VM; pairing/supervisor lifecycle is owned by systemd; the OCI image carries the actual edge worker payload |
| Distribution | GitHub Releases attachment per tag (placeholder; see Open Questions) |

The VM exists primarily to be a *known-good Linux host* that EVE-OS can
manage as a single app, with PCIe passthrough configured at the EVE-OS
App Config level. We do not bake CUDA drivers into the qcow2; the
Debian guest pulls the matching NVIDIA driver and CUDA runtime on
first-boot if the VFIO-attached GPU is detected. This keeps the qcow2
generic across NVIDIA generations (T4, L4, A2, RTX A2000, etc.).

If no GPU is passed through, the same image runs CPU-only inference via
ONNX Runtime CPU, with capacity limits documented (2–4 cameras at
480p/5 FPS on an 8-core gateway).

### Artifact 2 — `ghcr.io/<org>/vezor-edge:VERSION-amd64`

| Property | Value |
|---|---|
| Architecture | `linux/amd64` |
| Base image | `python:3.12-slim-bookworm` |
| Inference runtime | ONNX Runtime GPU (CUDA 12.x); falls back to CPU if no GPU available at runtime |
| Pairing | Environment variables `VEZOR_API_URL`, `VEZOR_SESSION_ID`, `VEZOR_PAIRING_CODE` |
| GPU support | Requires EVE-OS host runtime to expose NVIDIA via `--gpus`-style hooks (more constrained on EVE-OS than on a stock Docker host); CPU works unconditionally |
| Build | New `backend/Dockerfile.edge.amd64` |
| Distribution | GitHub Container Registry (placeholder; see Open Questions) |

The container artifact is the lighter-weight option, suitable for
EVE-OS deployments where the host runtime is configured for containers
and where CPU-only inference is acceptable. It uses standard PyPI
PyTorch wheels (not Jetson-pinned), so the build is hermetic against
the L4T base image used by `Dockerfile.edge`.

## New Files And Directories

```
infra/install/eve-os/
├── README.md                          operator deployment walkthrough
├── vm/
│   ├── packer.pkr.hcl                 Packer build descriptor
│   ├── debian-preseed.cfg             unattended Debian install seed
│   ├── firstboot.sh                   reads cloud-init user-data, execs pairing
│   ├── vezor-eve-bootstrap.service    systemd unit invoking firstboot.sh once
│   ├── vezor-edge.service.template    systemd unit template installed by
│   │                                   `bin/vezor install edge`
│   └── eve-app-manifest.json          sample EVE-OS App Instance Config
└── container/
    ├── Dockerfile                      thin wrapper over Dockerfile.edge.amd64
    ├── eve-firstboot.sh                env-var reader, execs pairing
    └── eve-app-manifest.json           sample EVE-OS App Instance Config

backend/
└── Dockerfile.edge.amd64               generic amd64 edge image
                                         (Python 3.12, ORT GPU optional)
```

The `infra/install/eve-os/` layout mirrors the existing
`infra/install/compose/` and installer scripts, keeping packaging
assets discoverable under one tree.

## Pairing Flow Detail

### VM (cloud-init NoCloud)

EVE-OS exposes App Instance user-data to the guest as a NoCloud
datasource. The Debian image's cloud-init reads it from
`/var/lib/cloud/instance/user-data` on first boot. Operators supply
user-data as YAML in the EVE-OS controller UI:

```yaml
#cloud-config
write_files:
  - path: /etc/vezor/pairing.env
    permissions: '0600'
    content: |
      VEZOR_API_URL=https://master.example.com
      VEZOR_SESSION_ID=...
      VEZOR_PAIRING_CODE=...
runcmd:
  - systemctl enable --now vezor-eve-bootstrap.service
```

`vezor-eve-bootstrap.service` runs `firstboot.sh`, which:

1. Refuses to run if `/var/lib/vezor/paired.marker` exists (idempotent
   across reboots).
2. Sources `/etc/vezor/pairing.env`.
3. Execs `/usr/local/bin/vezor install edge --api-url
   "$VEZOR_API_URL" --session-id "$VEZOR_SESSION_ID" --pairing-code
   "$VEZOR_PAIRING_CODE" --edge-name "$(hostname)"`.
4. On success, writes `/var/lib/vezor/paired.marker` and
   `systemctl disable vezor-eve-bootstrap.service`. The
   installer-managed `vezor-edge.service` takes over.

### Container (env vars)

The OCI image's entrypoint is `/usr/local/bin/eve-firstboot.sh`:

1. Refuses to run if `/var/lib/vezor/paired.marker` exists (the marker
   lives on a persistent volume EVE-OS mounts at
   `/var/lib/vezor/`).
2. Reads `VEZOR_API_URL`, `VEZOR_SESSION_ID`, `VEZOR_PAIRING_CODE` from
   the container environment.
3. Execs `/usr/local/bin/vezor install edge --api-url … --session-id …
   --pairing-code …`.
4. On success, writes the marker and `exec`s the long-running
   `/usr/local/bin/vezor-edge-supervisor`.

If the env vars are missing on first start, the container exits
non-zero with a clear log message instructing the operator to populate
them in the App Instance Config.

### What `bin/vezor install edge` already does

The existing pairing CLI handles: token exchange, credential storage
under `/etc/vezor/edge-credentials.json`, NATS leaf config seeding,
MediaMTX config, and registering the supervisor systemd unit. None of
this needs to change for EVE-OS. The EVE-OS spec only adds the
*invocation surface* on the guest side.

## Build Pipeline

### `backend/Dockerfile.edge.amd64`

Multi-stage, mirrors `Dockerfile` (the central image) more closely than
`Dockerfile.edge`. Key differences from `Dockerfile`:

- Adds `ffmpeg`, `gstreamer1.0-tools`, `gstreamer1.0-plugins-{base,good,bad}`,
  `gstreamer1.0-libav`, `gstreamer1.0-rtsp`, `python3-gst-1.0` to the
  runtime layer (for camera capture).
- Installs `onnxruntime-gpu==1.20.*` from PyPI (not the Jetson wheel).
  Falls back to `onnxruntime` (CPU) at runtime if the GPU provider
  fails to load (`argus.inference.engine` already handles provider
  fallback).
- Installs standard `torch==2.5.*` and `torchvision==0.20.*` from PyPI
  (CUDA 12.4 build).
- Installs `ultralytics>=8.3` from PyPI.
- Entrypoint is the supervisor, not uvicorn.

Build command (added to `Makefile`):

```make
edge-amd64-build:
	docker buildx build \
	  --platform linux/amd64 \
	  -f backend/Dockerfile.edge.amd64 \
	  -t vezor-edge:dev-amd64 \
	  --load \
	  backend
```

### VM build (`infra/install/eve-os/vm/packer.pkr.hcl`)

Packer plan:

1. Boot Debian 12 minimal netinst ISO with the preseed file.
2. Install Docker engine, cloud-init NoCloud datasource, and the
   `bin/vezor` CLI.
3. `docker pull vezor-edge:VERSION-amd64` (the OCI image built in the
   previous step), tag it locally, and save it to
   `/var/lib/vezor/images/vezor-edge.tar` for offline starts.
4. Drop `vezor-eve-bootstrap.service` and `firstboot.sh` into
   `/etc/systemd/system/` and `/usr/local/sbin/`.
5. Trim apt cache, zero free space, shut down.
6. Output: `vezor-edge-amd64.qcow2`.

Build command (added to `Makefile`):

```make
eve-vm-build: edge-amd64-build
	cd infra/install/eve-os/vm && packer build \
	  -var vezor_edge_image=vezor-edge:VERSION-amd64 \
	  packer.pkr.hcl
```

The `edge-amd64-build` prerequisite is intentional: the Packer plan
loads the OCI image from the local Docker daemon, so the OCI build
must complete before the VM build starts. Same applies to
`eve-container-build`, which `FROM`s the same base.

### Container build (`infra/install/eve-os/container/Dockerfile`)

```dockerfile
FROM vezor-edge:VERSION-amd64
COPY eve-firstboot.sh /usr/local/bin/eve-firstboot.sh
RUN chmod +x /usr/local/bin/eve-firstboot.sh
ENTRYPOINT ["/usr/local/bin/eve-firstboot.sh"]
```

Build command (added to `Makefile`):

```make
eve-container-build: edge-amd64-build
	docker buildx build \
	  --platform linux/amd64 \
	  -f infra/install/eve-os/container/Dockerfile \
	  -t vezor-edge-eve:VERSION-amd64 \
	  --build-arg BASE=vezor-edge:VERSION-amd64 \
	  --load \
	  infra/install/eve-os/container
```

## Acceptance Criteria

### Required (merge gate)

1. **`make edge-amd64-build` succeeds in CI.** The image runs on a
   stock amd64 Linux host with no GPU and `python -m
   argus.inference.engine --help` exits 0 inside the container.
2. **`make eve-container-build` succeeds in CI.** Running
   `docker run --rm --env VEZOR_API_URL=http://host.docker.internal:8000
   --env VEZOR_SESSION_ID=<test> --env VEZOR_PAIRING_CODE=<test>
   vezor-edge-eve:dev-amd64` against a local `make dev-up` master
   reaches the "edge agent paired" state within 60 seconds.
3. **`make eve-vm-build` succeeds in CI** (or in a documented
   manual-run step if CI cannot run Packer + KVM; capture as
   build-evidence under
   `docs/superpowers/status/YYYY-MM-DD-eve-os-vm-build-evidence.md`).
4. **VM boot smoke.** Booting the produced qcow2 under local KVM with
   a NoCloud seed CD-ROM carrying the three pairing env vars reaches
   "edge agent paired" against a `make dev-up` master within 5
   minutes (initial boot includes apt updates and image load).
5. **Idempotent pairing.** Rebooting the VM or restarting the
   container after successful pairing does not re-trigger the pairing
   flow; `vezor-edge.service` (or the supervisor PID-1) takes over.
6. **No regressions in existing Jetson edge build.**
   `backend/Dockerfile.edge` and `infra/docker-compose.edge.yml`
   continue to build and run on the Jetson rig.
7. **Documentation.** `infra/install/eve-os/README.md` is the
   operator-facing walkthrough; `docs/full-installation-guide.md` gains
   a short section linking to it.

### Recommended evidence (not merge gate)

8. **Live EVE-OS deploy.** Once an EVE-OS test device is available,
   the operator-facing walkthrough is exercised end-to-end against a
   real RTSP source, with results captured to
   `docs/superpowers/status/YYYY-MM-DD-eve-os-live-deploy-evidence.md`.

## Test Plan

- Unit tests: `infra/install/eve-os/vm/firstboot.sh` and
  `infra/install/eve-os/container/eve-firstboot.sh` are shell scripts.
  Add a `tests/installer/test_eve_firstboot.py` (or shell-based
  `bats` test if the project standardises on that) that:
  - asserts marker-file refusal works
  - asserts missing-env-var path exits non-zero with the expected
    message
  - asserts the `bin/vezor install edge` invocation receives the
    expected arguments (mocked)
- Existing installer tests
  (`installer/tests/test_edge_installer_artifacts.py`,
  `installer/tests/test_linux_master_artifacts.py`) extended to assert
  the EVE-OS asset directory exists, the sample manifests are
  syntactically valid JSON, and the firstboot scripts are executable.
- CI: a `lint-eve-os` target validates `eve-app-manifest.json` files
  against the JSON Schema EVE-OS publishes.

## Files Touched

| File | Change |
|---|---|
| `backend/Dockerfile.edge.amd64` | new |
| `infra/install/eve-os/README.md` | new |
| `infra/install/eve-os/vm/packer.pkr.hcl` | new |
| `infra/install/eve-os/vm/debian-preseed.cfg` | new |
| `infra/install/eve-os/vm/firstboot.sh` | new |
| `infra/install/eve-os/vm/vezor-eve-bootstrap.service` | new |
| `infra/install/eve-os/vm/eve-app-manifest.json` | new |
| `infra/install/eve-os/container/Dockerfile` | new |
| `infra/install/eve-os/container/eve-firstboot.sh` | new |
| `infra/install/eve-os/container/eve-app-manifest.json` | new |
| `Makefile` | `edge-amd64-build`, `eve-vm-build`, `eve-container-build`, `lint-eve-os` |
| `docs/full-installation-guide.md` | new "EVE-OS edge app" subsection linking to the new README |
| `installer/tests/test_edge_installer_artifacts.py` | extended assertions |
| `tests/installer/test_eve_firstboot.py` (or bats equivalent) | new |

No changes to:

- `backend/Dockerfile.edge` (Jetson path stays as-is)
- `infra/docker-compose.edge.yml`
- `bin/vezor` CLI
- backend Python code

## Out Of Scope

- **ARM64 build matrix.** Adding `linux/arm64` to either artifact. The
  team does not currently have an ARM64 EVE-OS device to validate
  against; deferred until one is available.
- **Dedicated no-cloud-init pairing endpoint.** A first-boot HTTP
  listener on the guest that the EVE-OS controller POSTs to. Cleaner
  fleet ergonomics; deferred until fleet orchestration (auto-update,
  version pinning) is on the roadmap.
- **Signed artifact distribution.** Cosign / sigstore signing of the
  qcow2 and OCI artifacts. Will land with the broader "signed package
  upgrades" production-hardening item already on the roadmap, not in
  this spec.
- **EVE-OS controller automation.** Programmatic pushing of App
  Instance Configs to an EVE-OS controller via its REST API. The spec
  ships sample manifests; operators apply them manually for now.
- **Persistent-volume schema for `/var/lib/vezor/`.** The container
  artifact assumes EVE-OS mounts a persistent volume at this path; the
  schema for what lives there (model cache, credentials, clip buffer)
  is inherited from the existing edge supervisor and not redesigned
  here.
- **Fleet update mechanism.** Replacing the qcow2 or OCI image across a
  fleet of EVE-OS devices is the EVE-OS controller's job today
  (manual). Vezor-side fleet update is the documented 180–365 day
  roadmap item.

## Open Questions

1. **Distribution endpoints.** Where do the built artifacts land?
   Default proposal: OCI image on GHCR
   (`ghcr.io/<org>/vezor-edge:VERSION-amd64`), qcow2 attached to the
   GitHub Release for the matching tag. Confirm the `<org>` namespace
   and whether internal MinIO is preferred for the qcow2 due to size.
2. **Vendor-neutral edge naming.** Should the OCI image keep the
   `vezor-edge` tag suffix (current Jetson image is `vezor-edge` with
   `-aarch64` implied), gain explicit `-amd64` / `-arm64` suffixes, or
   move to a registry-level multi-arch manifest? The spec assumes
   explicit `-amd64` suffix to avoid collision with the existing
   Jetson tag; confirm before tagging.
3. **CI runner for VM build.** GitHub-hosted runners do not allow
   nested KVM. The qcow2 build will likely need either a self-hosted
   runner with KVM access or a manual-run path with evidence file
   capture. Confirm which is acceptable.
4. **NVIDIA driver baked vs. first-boot install.** The spec assumes
   first-boot pulls the matching driver to keep the qcow2 generic
   across NVIDIA generations. Alternative: bake a specific driver
   version and ship multiple qcow2 variants. Confirm before VM build.
