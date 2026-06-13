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

1. A **VM app** (`vezor-edge-amd64.qcow2`) with optional accelerator
   passthrough (NVIDIA GPU via VFIO PCIe, Intel iGPU via VFIO-mediated
   passthrough, or no passthrough at all).
2. An **OCI container app** (`ghcr.io/<org>/vezor-edge:VERSION-amd64`)
   for hosts where container-app deployment is preferred.

Both target `linux/amd64` only and ship a **multi-vendor inference
runtime** that auto-selects the best available acceleration at startup:
NVIDIA CUDA, Intel via OpenVINO, or CPU fallback. The provider
selection is built as a **pluggable registry** so future acceleration
families (AMD ROCm, Coral, Hailo) can be added by dropping a wheel in,
without re-architecting the EVE-OS artifacts. ARM64 and a dedicated
no-cloud-init pairing endpoint remain explicit follow-up work.

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
| Acceleration | Multi-vendor runtime (see "Inference runtime" section): NVIDIA CUDA, Intel OpenVINO, or CPU fallback — auto-detected |
| Build tool | Packer with the `qemu` builder |
| Bakes in | Docker engine, `vezor-edge:VERSION-amd64` OCI image preloaded, `bin/vezor`, `vezor-eve-bootstrap.service` systemd unit, Intel GPU userspace drivers |
| Runtime | The OCI image runs under Docker on the VM; pairing/supervisor lifecycle is owned by systemd; the OCI image carries the actual edge worker payload |
| Distribution | GitHub Releases attachment per tag (placeholder; see Open Questions) |

The VM exists primarily to be a *known-good Linux host* that EVE-OS can
manage as a single app, with accelerator passthrough configured at the
EVE-OS App Config level (VFIO for NVIDIA, VFIO-mediated devices for
Intel iGPU). The qcow2 bakes in:

- Intel GPU userspace drivers: `intel-opencl-icd`,
  `intel-media-va-driver-non-free`, `libze1`, `libze-intel-gpu1` —
  these are small and cover both iGPU and discrete Intel Arc.
- A first-boot NVIDIA driver fetch script that runs only if a VFIO
  NVIDIA device is detected. This keeps the qcow2 generic across
  NVIDIA generations (T4, L4, A2, RTX A2000, etc.) instead of locking
  one driver version into the image.

If no accelerator is passed through, the same image runs CPU-only
inference, with capacity limits documented (2–4 cameras at 480p/5 FPS
on an 8-core gateway).

### Artifact 2 — `ghcr.io/<org>/vezor-edge:VERSION-amd64`

| Property | Value |
|---|---|
| Architecture | `linux/amd64` |
| Base image | `python:3.12-slim-bookworm` |
| Inference runtime | Multi-vendor: `onnxruntime-gpu` (CUDA EPs) + `openvino` (Intel) + CPU; auto-selected at startup (see "Inference runtime" section) |
| Pairing | Environment variables `VEZOR_API_URL`, `VEZOR_SESSION_ID`, `VEZOR_PAIRING_CODE` |
| Accelerator access | NVIDIA: EVE-OS host runtime exposes the GPU via `--gpus`-style hooks (more constrained on EVE-OS than stock Docker; tested via the VM path as the recommended deployment shape for NVIDIA). Intel iGPU: host must expose `/dev/dri/renderD*` to the container. CPU works unconditionally. |
| Build | New `backend/Dockerfile.edge.amd64` |
| Distribution | GitHub Container Registry (placeholder; see Open Questions) |

The container artifact is the lighter-weight option, suitable for
EVE-OS deployments where the host runtime is configured for containers.
It uses standard PyPI PyTorch and ONNX Runtime wheels (not
Jetson-pinned), so the build is hermetic against the L4T base image
used by `Dockerfile.edge`. The Intel-acceleration path is via the
`openvino` Python toolkit; the NVIDIA path is via ONNX Runtime GPU's
CUDA execution provider.

## Inference Runtime: Pluggable Multi-Vendor Provider Registry

### Motivation

The existing edge image (`Dockerfile.edge`) is Jetson-only and binds
the inference path to TensorRT + ONNX Runtime GPU. EVE-OS hosts span
NVIDIA dGPU, Intel iGPU/Arc, plain Intel CPU, and (later) AMD or
USB/M.2 NPU accelerators. The edge worker needs a runtime layer that:

- detects available acceleration at startup
- picks the highest-priority working provider
- falls back cleanly to CPU
- is extensible to new accelerators without re-baking the image

### Built-in providers (first release)

| Provider | Package | Detected by | Priority |
|---|---|---|---|
| `cuda` | `onnxruntime-gpu` (`CUDAExecutionProvider`) | `nvidia-smi` exits 0 and `CUDAExecutionProvider` loads | 100 |
| `openvino` | `openvino` (Python toolkit, used directly — not via an ORT EP) | `/dev/dri/renderD*` exists and `openvino.Core().available_devices` includes `GPU` or `CPU` with vector extensions | 80 |
| `cpu` | `onnxruntime` (`CPUExecutionProvider`) | always | 10 |

The Jetson edge image (`Dockerfile.edge`) keeps its own dedicated
provider (`tensorrt`) registered with priority 150 and remains
unaffected by this work.

### Registry interface

A new module `backend/src/argus/inference/providers/` exposes:

```python
class InferenceProvider(Protocol):
    name: str
    priority: int

    def is_available(self) -> bool: ...
    def build_detector(self, model_path: Path,
                       *, config: DetectorConfig) -> Detector: ...
```

Built-in providers register themselves on import:

```
backend/src/argus/inference/providers/
├── __init__.py        # registry + selection logic
├── cuda.py            # CUDAExecutionProvider via ORT
├── openvino.py        # openvino toolkit direct
├── cpu.py             # CPUExecutionProvider via ORT
└── tensorrt.py        # Jetson-only (already exists, moved here)
```

Third-party providers can register via the Python entry-point group
`argus.inference.providers`:

```toml
# in a third-party package's pyproject.toml
[project.entry-points."argus.inference.providers"]
coral = "vezor_provider_coral:CoralEdgeTPUProvider"
hailo = "vezor_provider_hailo:HailoProvider"
```

At startup, `backend/src/argus/inference/engine.py` calls
`select_provider()`, which:

1. Imports the providers module (built-ins register).
2. Loads any entry-point providers from the `argus.inference.providers`
   group.
3. Filters by `is_available()`.
4. Sorts by `priority` descending.
5. Returns the highest-priority available provider.

The selection is logged once at startup with the chosen provider name,
detected device, and any providers that failed `is_available()` with
their reason. An operator override is available via the
`ARGUS_INFERENCE_PROVIDER` env var (e.g.
`ARGUS_INFERENCE_PROVIDER=cpu` to force CPU even when a GPU is
present).

### What this replaces

The existing `backend/src/argus/vision/detector_factory.py` already
picks between detector implementations based on the model file type
(`.onnx` vs `.pt` vs `.engine`). It keeps that responsibility. The
new provider registry sits *underneath* it, choosing which ONNX
Runtime execution provider (or OpenVINO toolkit invocation) the
ONNX-based detectors use.

The macOS host-worker CoreML preference noted in commit `c763230` is
folded into a new `coreml` provider for the macOS dev path only — same
registry pattern, registered when `sys.platform == "darwin"`. This is
a small extension of existing logic, not a rewrite.

### Failure handling

If `is_available()` returns `True` but `build_detector()` raises at
session-construction time, the engine catches the exception, logs it,
falls back to the next provider in the sorted list, and continues.
This means a misconfigured Intel GPU driver does not crash the worker
— it degrades to CPU and surfaces the failure in logs and the
operations dashboard.

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
│   ├── nvidia-firstboot.sh            optional NVIDIA driver fetch (skipped
│   │                                   if no VFIO NVIDIA device detected)
│   └── eve-app-manifest.json          sample EVE-OS App Instance Config
└── container/
    ├── Dockerfile                      thin wrapper over Dockerfile.edge.amd64
    ├── eve-firstboot.sh                env-var reader, execs pairing
    └── eve-app-manifest.json           sample EVE-OS App Instance Config

backend/
├── Dockerfile.edge.amd64               generic amd64 edge image (Python 3.12,
│                                        onnxruntime-gpu + openvino + cpu)
└── src/argus/inference/providers/      pluggable provider registry
    ├── __init__.py                     registry + select_provider()
    ├── cuda.py
    ├── openvino.py
    ├── cpu.py
    └── tensorrt.py                     existing TensorRT path moved here
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
- Adds Intel GPU userspace drivers: `intel-opencl-icd`,
  `intel-media-va-driver-non-free`, `libze1`, `libze-intel-gpu1` (all
  small; enables OpenVINO `GPU` device when the host exposes
  `/dev/dri/renderD*`).
- Installs `onnxruntime-gpu==1.20.*` from PyPI (CUDA + CPU EPs in one
  package).
- Installs `openvino==2025.*` from PyPI (Intel toolkit; used directly,
  not via an ORT EP).
- Installs standard `torch==2.5.*` and `torchvision==0.20.*` from PyPI
  (CUDA 12.4 build; used by Ultralytics for the detector graph
  pre-conversion to ONNX).
- Installs `ultralytics>=8.3` from PyPI.
- Entrypoint is the supervisor, not uvicorn.
- Image size budget: ≤ 3.5 GB compressed. `onnxruntime-gpu` and
  `openvino` together account for ~1.6 GB of that; the Intel userspace
  drivers are ~150 MB.

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
2. **Provider selection unit tests.** New tests in
   `backend/tests/inference/test_providers.py` cover: priority order,
   `is_available()` failure handling, entry-point loading,
   `ARGUS_INFERENCE_PROVIDER` override, and graceful fallback when
   `build_detector()` raises. CPU provider always returns available.
3. **CPU-path integration test.** `python -m argus.inference.engine`
   inside the container with no accelerators reachable selects the
   `cpu` provider, logs the selection, and processes one synthetic
   frame end-to-end.
4. **NVIDIA-path live evidence (recommended, see below).**
5. **Intel-path live evidence (recommended, see below).**
6. **`make eve-container-build` succeeds in CI.** Running
   `docker run --rm --env VEZOR_API_URL=http://host.docker.internal:8000
   --env VEZOR_SESSION_ID=<test> --env VEZOR_PAIRING_CODE=<test>
   vezor-edge-eve:dev-amd64` against a local `make dev-up` master
   reaches the "edge agent paired" state within 60 seconds.
7. **`make eve-vm-build` succeeds in CI** (or in a documented
   manual-run step if CI cannot run Packer + KVM; capture as
   build-evidence under
   `docs/superpowers/status/YYYY-MM-DD-eve-os-vm-build-evidence.md`).
8. **VM boot smoke.** Booting the produced qcow2 under local KVM with
   a NoCloud seed CD-ROM carrying the three pairing env vars reaches
   "edge agent paired" against a `make dev-up` master within 5
   minutes (initial boot includes apt updates and image load).
9. **Idempotent pairing.** Rebooting the VM or restarting the
   container after successful pairing does not re-trigger the pairing
   flow; `vezor-edge.service` (or the supervisor PID-1) takes over.
10. **No regressions in existing Jetson edge build.**
    `backend/Dockerfile.edge` and `infra/docker-compose.edge.yml`
    continue to build and run on the Jetson rig. The `tensorrt`
    provider continues to be selected on Jetson with priority 150.
11. **Documentation.** `infra/install/eve-os/README.md` is the
    operator-facing walkthrough including the multi-vendor matrix;
    `docs/full-installation-guide.md` gains a short section linking
    to it.

### Recommended evidence (not merge gate)

12. **NVIDIA-path live evidence.** On a Linux host with an NVIDIA GPU
    (Codex's existing access), run the container artifact and confirm
    the `cuda` provider is selected, one synthetic-frame inference
    succeeds, and the provider falls back to `cpu` when
    `ARGUS_INFERENCE_PROVIDER=cpu` is set. Capture to
    `docs/superpowers/status/YYYY-MM-DD-eve-os-nvidia-evidence.md`.
13. **Intel-path live evidence.** If an Intel-iGPU host is available
    (any modern Intel desktop or NUC), exercise the same flow with
    `openvino` provider selected. If unavailable at merge time, this
    is a follow-up.
14. **Live EVE-OS deploy.** Once an EVE-OS test device is available,
    the operator-facing walkthrough is exercised end-to-end against a
    real RTSP source on at least one accelerator vendor, with results
    captured to
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
| `backend/src/argus/inference/providers/__init__.py` | new — registry + `select_provider()` |
| `backend/src/argus/inference/providers/cuda.py` | new |
| `backend/src/argus/inference/providers/openvino.py` | new |
| `backend/src/argus/inference/providers/cpu.py` | new |
| `backend/src/argus/inference/providers/tensorrt.py` | move existing TensorRT detector path here, register at priority 150 |
| `backend/src/argus/inference/providers/coreml.py` | new — folds the existing macOS CoreML preference (`c763230`) into the registry, registered only on `sys.platform == "darwin"` |
| `backend/src/argus/inference/engine.py` | call `select_provider()` at detector-build time; honour `ARGUS_INFERENCE_PROVIDER` override |
| `backend/src/argus/vision/detector_factory.py` | route ONNX detectors through the selected provider |
| `backend/src/argus/core/config.py` | new `ARGUS_INFERENCE_PROVIDER` setting (optional override) |
| `backend/pyproject.toml` | declare `argus.inference.providers` entry-point group; pin `openvino` and `onnxruntime-gpu` for the edge.amd64 extra |
| `backend/tests/inference/test_providers.py` | new |
| `infra/install/eve-os/README.md` | new |
| `infra/install/eve-os/vm/packer.pkr.hcl` | new |
| `infra/install/eve-os/vm/debian-preseed.cfg` | new |
| `infra/install/eve-os/vm/firstboot.sh` | new |
| `infra/install/eve-os/vm/nvidia-firstboot.sh` | new |
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
- **AMD ROCm provider.** Architecturally enabled by the pluggable
  registry, but no `rocm.py` provider implementation ships in this
  spec. ROCm consumer-GPU support on Linux is still patchy; add when
  a target AMD device is in hand.
- **Coral / Hailo / other USB+M.2 NPU providers.** Same as above:
  the entry-point hook is in place, no built-in provider ships. These
  accelerators also need different model-artifact pipelines
  (edgetpu-compiled `.tflite` for Coral, Hailo HEF for Hailo) which
  is a separate concern.
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
4. **Intel iGPU test vector.** Codex's known accessible hardware is
   the Jetson rig and the macOS control plane. Is an Intel-iGPU host
   available for the recommended Intel-path evidence, or does that
   evidence wait for an EVE-OS test device?
