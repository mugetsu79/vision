# EVE-OS And Bare-Metal Edge Image Matrix Packaging Design

Date: 2026-06-13
Branch: `codex/sceneops-pack-registry`
Sequencing: **Last of three specs.** Depends on
`2026-06-13-tracker-continuity-improvements-design.md` and
`2026-06-13-dev-stack-stability-fixes-design.md` being merged first so
the artifact ships with the improved tracker and stable dev stack.

## Goal

Make the Vezor edge worker deployable on `linux/amd64` edge gateways
through both Linux bare-metal installs and EVE-OS VM App Instances,
with a small image matrix that keeps hardware support honest.

The shipped artifact is:

1. A **bare-metal Linux edge installer profile** selected with
   `vezor install edge --runtime-profile <profile>` on amd64 gateways.
2. A **VM app** (`vezor-edge-amd64.qcow2`) that runs that same Vezor
   edge appliance model inside a Debian 12 guest for EVE-OS.
3. A **selected edge worker image** from the amd64 image matrix that is
   used by either the bare-metal Compose appliance or the EVE-OS VM
   guest's Compose appliance.

There is **no EVE-OS OCI app artifact** in this spec. The earlier
container-app idea is intentionally removed because the current
installer is host/VM-oriented: it writes `/etc/vezor`, configures
NATS leaf and MediaMTX, claims pairing credentials, installs systemd
units, and starts a multi-container appliance. That model fits Linux
bare metal and a Debian VM guest. Running it inside a single EVE-OS OCI
app would require a separate container-native bootstrap design.

The generic image must always work on CPU. NVIDIA and Intel
acceleration live in explicit vendor images with their own packaging,
runtime checks, tests, and live evidence gates. There is no "magical
generic GPU" image.

## Why Now

The existing edge artifact (`backend/Dockerfile.edge`) is locked to
NVIDIA L4T Jetson and Python 3.10. EVE-OS hosts are usually x86_64
industrial gateways such as Advantech, Lenovo ThinkEdge, Supermicro
IoT, Intel NUC-class devices, or compact servers. Some have NVIDIA
dGPUs, some have Intel iGPUs, and many are CPU-only.

The current deployment matrix already documents the gap: there is no
generic non-Jetson Python 3.12 edge image in the Compose stack. This
spec closes that gap for amd64 bare metal first, then packages the same
path as an EVE-OS VM artifact while preserving the hardened Jetson path
and avoiding a single oversized image that mixes incompatible
acceleration runtime stacks.

## Architecture Decision

The amd64 edge path has two deployment targets that share the same
installer profile and worker image matrix:

```text
Linux bare-metal gateway
  -> /usr/local/bin/vezor install edge --runtime-profile <profile> ...
  -> systemd: vezor-edge.service
  -> Docker Compose edge appliance
       nats-leaf
       mediamtx
       vezor-supervisor

EVE-OS controller UI
  -> VM App Instance Config
       qcow2 image ref
       NoCloud user-data:
         VEZOR_API_URL
         VEZOR_SESSION_ID
         VEZOR_PAIRING_CODE
       optional device passthrough:
         NVIDIA dGPU via VFIO PCIe
         Intel iGPU/render node when supported by the host

EVE-OS host
  -> qemu/KVM VM guest
       cloud-init writes /etc/vezor/pairing.env
       systemd: vezor-eve-bootstrap.service
       -> /usr/local/sbin/vezor-eve-firstboot
       -> /usr/local/bin/vezor install edge --runtime-profile <profile> ...
       -> systemd: vezor-edge.service
       -> Docker Compose edge appliance
            nats-leaf
            mediamtx
            vezor-supervisor
```

The pairing flow ends in the same supervisor lifecycle used by the
current Linux/Jetson edge path. After pairing, control-plane behavior
is identical: Operations changes desired state or sends lifecycle
requests, and the edge supervisor owns worker processes and reports
runtime truth.

## Current Installer Status

The current installer already provides the pieces the bare-metal and
VM paths need:

- `bin/vezor install edge` delegates to `installer/linux/install-edge.sh`.
- Paired installs require `--api-url`, `--session-id`, and
  `--pairing-code`.
- The installer claims the pairing session before the long local image
  build, writes the supervisor credential, and fixes credential
  permissions for the non-root supervisor container user.
- It writes `/etc/vezor/edge.json`, `/etc/vezor/supervisor.json`,
  `/etc/vezor/edge.env`, NATS leaf config, and MediaMTX config.
- It installs systemd services and starts the edge appliance.
- The product appliance is a Compose stack with `nats-leaf`,
  `mediamtx`, and `vezor-supervisor`.

What is missing:

- an amd64 edge image matrix with generic CPU, NVIDIA, and Intel
  OpenVINO variants;
- amd64 installer profiles that skip Jetson-only preflight and select
  the correct image/runtime defaults;
- a generic Compose base that does not require NVIDIA runtime by
  default, plus vendor-specific override/profile hooks;
- bare-metal amd64 operator documentation and tests that prove the
  amd64 installer profile does not depend on EVE-OS;
- VM packaging assets for EVE-OS.

## Artifact: Bare-Metal amd64 Edge Profile

| Property | Value |
|---|---|
| Entry point | `vezor install edge --runtime-profile <profile>` |
| Architecture | `linux/amd64` |
| Runtime owner | systemd-managed Vezor edge appliance on the host |
| Worker image | one selected amd64 edge worker image from the release manifest or local build |
| Compose base | `infra/install/compose/compose.edge-amd64.yml` |
| Vendor overrides | NVIDIA and Intel OpenVINO Compose overrides selected only by explicit profile |

The bare-metal profile is the shared product path. It runs directly on
industrial PCs, NUC-class boxes, compact servers, and other Linux amd64
gateways with camera network reach. It is also the path that the
EVE-OS Debian VM calls from first boot.

## Artifact: EVE-OS `vezor-edge-amd64.qcow2`

| Property | Value |
|---|---|
| Base image | Debian 12 (`bookworm`) minimal cloud variant |
| Architecture | `linux/amd64` |
| Format | qcow2, compressed for release distribution |
| Pairing | cloud-init NoCloud user-data writes `/etc/vezor/pairing.env` |
| Runtime | systemd-managed Vezor edge appliance inside the VM |
| Worker image | one selected amd64 edge worker image, preloaded into the guest Docker daemon |
| Build tool | Packer `qemu` builder |
| Distribution | Release attachment or internal artifact store, final endpoint to confirm |

The VM is the product boundary for EVE-OS. It gives us a normal Linux
host with systemd, Docker, persistent `/etc/vezor`, persistent
`/var/lib/vezor`, and predictable Compose behavior. That matches the
current product installer and avoids creating a second pairing model.

The qcow2 includes:

- Docker Engine and Docker Compose v2;
- cloud-init NoCloud support;
- `/usr/local/bin/vezor` and installer support files;
- the selected amd64 edge worker image loaded into Docker;
- `vezor-eve-bootstrap.service`;
- `vezor-eve-firstboot`;
- optional host userspace packages needed for GPU detection, kept
  modest and documented.

## Edge Worker Image Matrix

Create an explicit image matrix instead of one generic image that tries
to carry every accelerator stack.

| Image | Purpose | Runtime promise |
|---|---|---|
| `vezor/edge-worker:VERSION-generic-amd64` | default x86_64 EVE-OS and Linux edge image | CPU inference works on a plain amd64 host or VM |
| `vezor/edge-worker:VERSION-nvidia-amd64` | x86_64 gateways with NVIDIA dGPU passthrough | CUDA is used only when the device stack is exposed and `CUDAExecutionProvider` initializes |
| `vezor/edge-worker:VERSION-intel-openvino-amd64` | Intel gateways with validated iGPU/NPU/render-device exposure | OpenVINO is used only when the selected OpenVINO device compiles and runs the model |
| existing Jetson image | Jetson/L4T edge path | Jetson-specific runtime remains separate |

All amd64 images share the same application code and supervisor entry
points. They differ only in base runtime dependencies, installed
inference packages, and default runtime profile.

### Generic amd64 image

Create `backend/Dockerfile.edge.generic-amd64` or keep
`backend/Dockerfile.edge.amd64` as the generic image if that name is
already in use by the implementation plan.

Required behavior:

- CPU inference works on a plain amd64 host or VM.
- No NVIDIA, Intel GPU, AMD, Coral, Hailo, or NPU acceleration claims.
- Runtime telemetry reports CPU fallback truthfully.
- This is the default image for EVE-OS until an operator deliberately
  selects a vendor-specific image/profile.

Image contents:

- Python 3.12 runtime;
- `ffmpeg` and the existing capture dependencies used by the edge
  worker;
- ONNX Runtime CPU path;
- Ultralytics dependencies already needed by the current worker stack;
- no Jetson-only TensorRT wheel bootstrap;
- no CUDA/OpenVINO packages unless needed for CPU-only runtime
  compatibility;
- `YOLO_CONFIG_DIR=/tmp` or another non-home writable path to prevent
  runtime writes into read-only image locations.

### NVIDIA amd64 image

Create `backend/Dockerfile.edge.nvidia-amd64`.

Required behavior:

- CUDA inference is attempted only when the VM/container exposes a
  working NVIDIA device stack and ONNX Runtime can initialize
  `CUDAExecutionProvider`.
- If CUDA provider initialization or detector session construction
  fails, the worker falls back to CPU and reports the fallback reason.
- No DeepStream implementation or claim is part of this image.
- This image is not used as the default generic edge image.

The NVIDIA image should keep the existing ONNX Runtime provider model
and use the `linux-x86_64-nvidia` runtime profile. It must not imply
central Dockerized GPU or Apple M-series acceleration.

### Intel OpenVINO amd64 image

Create `backend/Dockerfile.edge.intel-openvino-amd64` after hardware
availability and validation criteria are agreed.

Required behavior:

- OpenVINO inference is attempted only when the VM/container exposes a
  validated Intel target device and the selected OpenVINO backend can
  compile and run the deployed model.
- If OpenVINO provider or model compilation fails, the worker falls
  back to CPU and reports the fallback reason.
- The implementation may use ONNX Runtime OpenVINO Execution Provider
  in this image because the image is Intel-specific. If live testing
  shows that direct OpenVINO runtime is more reliable for the deployed
  detector, document that choice and keep it isolated to this image.
- `/dev/dri` or EVE-OS device passthrough requirements must be tested
  before claiming Intel GPU acceleration.

Intel/OpenVINO becomes a supported lane only after the image builds,
the actual Vezor detector model runs, telemetry reports the selected
OpenVINO target, CPU fallback works, and live evidence is captured on
real Intel hardware.

Do not reuse Jetson tags or publish a multi-arch manifest until each
architecture and vendor image has independent live evidence.

## Runtime Selection

Do not introduce a parallel provider framework in
`argus.inference.providers` for this phase. The repo already has the
right abstraction seam in `argus.vision.runtime`:

- `ExecutionProvider`;
- `ExecutionProfile`;
- host classification;
- provider priority by profile;
- provider override through existing settings;
- detector construction fallback in the inference engine.

This spec extends that existing runtime policy rather than replacing
it.

Required changes:

- Add or refine a generic `linux-x86_64-generic` or
  `linux-x86_64-edge` execution profile if the current profiles are too
  vendor-specific.
- Keep `linux-x86_64-nvidia` for the NVIDIA amd64 image and hosts
  where CUDA providers are actually available.
- Keep or refine `linux-x86_64-intel` for the Intel OpenVINO image only
  when the runtime can really use the selected provider/device.
- Keep CPU fallback as the guaranteed baseline.
- Log selected image/runtime profile, selected provider/backend,
  selected accelerator device when applicable, available providers, and
  fallback reason once per worker start.
- Continue reporting runtime selection through existing supervisor
  runtime reports.

Operator override should use existing settings names, not a new
parallel environment variable. Today that means:

```text
ARGUS_INFERENCE_EXECUTION_PROVIDER_OVERRIDE=CPUExecutionProvider
ARGUS_INFERENCE_EXECUTION_PROFILE_OVERRIDE=cpu-fallback
```

If we add friendlier aliases later, they must map into these existing
settings.

### What "Basic GPU If Present" Means

This does make sense if defined narrowly:

- CPU is the only universal guarantee and belongs to the generic image.
- NVIDIA dGPU acceleration is first-class in the NVIDIA image after the
  device is passed through and the CUDA provider initializes.
- Intel iGPU/NPU acceleration is first-class in the Intel OpenVINO
  image after the selected OpenVINO device compiles and runs the model
  on real hardware.
- AMD ROCm, Coral, Hailo, and other accelerators are out of scope.

The UI and docs must say "accelerator detected/selected" only from
runtime evidence, not from host inventory alone.

## Installer Changes

Add amd64 runtime profiles to the existing installer instead of
creating a new installer:

```bash
sudo /usr/local/bin/vezor install edge \
  --runtime-profile generic-amd64 \
  --api-url "$VEZOR_API_URL" \
  --session-id "$VEZOR_SESSION_ID" \
  --pairing-code "$VEZOR_PAIRING_CODE" \
  --edge-name "$(hostname)"
```

Supported amd64 profiles:

| Runtime profile | Worker image key | Dockerfile | Default acceleration behavior |
|---|---|---|---|
| `generic-amd64` | `edge-worker-generic-amd64` | `backend/Dockerfile.edge.generic-amd64` or `backend/Dockerfile.edge.amd64` | CPU only |
| `nvidia-amd64` | `edge-worker-nvidia-amd64` | `backend/Dockerfile.edge.nvidia-amd64` | CUDA if runtime evidence proves it, CPU fallback |
| `intel-openvino-amd64` | `edge-worker-intel-openvino-amd64` | `backend/Dockerfile.edge.intel-openvino-amd64` | OpenVINO target if runtime evidence proves it, CPU fallback |

All amd64 profiles do the following:

- skip `scripts/jetson-preflight.sh`;
- select the profile-specific Dockerfile for dev/local builds;
- select the profile-specific manifest image key for release builds;
- write an edge env file with the selected amd64 worker image;
- use the generic Compose base plus profile-specific overrides;
- keep NATS leaf, MediaMTX, credentials, model directory, edge-agent,
  and supervisor config behavior unchanged;
- set amd64 publish/runtime defaults rather than Jetson-specific
  defaults.

The existing Jetson path stays unchanged. If no runtime profile is
provided on an actual Jetson, current behavior remains the default. On
`linux/amd64`, the installer may default to `generic-amd64` after tests
prove that path. The installer must not auto-select NVIDIA or Intel
images from inventory alone; vendor image selection is an explicit
profile choice until fleet policy is designed.

## Compose Shape

The generic amd64 edge appliance remains a multi-container Compose
stack:

- `nats-leaf`;
- `mediamtx`;
- `vezor-supervisor`.

Create:

- `infra/install/compose/compose.edge-amd64.yml` as the generic base;
- optional vendor override/profile files only when their image evidence
  gates are ready.

Recommendation: create `compose.edge-amd64.yml` first. It avoids
changing Jetson defaults while the generic path is still new.

Differences from the Jetson compose:

- no default `runtime: nvidia`;
- no Jetson RTSP tuning env vars by default;
- selected amd64 publish profile;
- CPU thread caps still present;
- optional NVIDIA runtime/device settings enabled only through env or a
  documented `nvidia-amd64` override/profile;
- optional `/dev/dri` mapping only in the `intel-openvino-amd64`
  override/profile after OpenVINO evidence exists.

## EVE-OS First Boot

The VM first-boot service is idempotent:

1. Refuses to run if `/var/lib/vezor/paired.marker` exists.
2. Sources `/etc/vezor/pairing.env`.
3. Verifies `VEZOR_API_URL`, `VEZOR_SESSION_ID`, and
   `VEZOR_PAIRING_CODE` are present.
4. Defaults `VEZOR_RUNTIME_PROFILE` to `generic-amd64` when unset.
5. Runs `vezor install edge --runtime-profile "$VEZOR_RUNTIME_PROFILE" ...`.
6. On success, writes `/var/lib/vezor/paired.marker`.
7. Disables `vezor-eve-bootstrap.service`.
8. Leaves `vezor-edge.service` as the long-running appliance owner.

Missing env vars produce a clear non-zero exit with no secret values
printed.

## New Files And Directories

```text
backend/
├── Dockerfile.edge.generic-amd64
├── Dockerfile.edge.nvidia-amd64
└── Dockerfile.edge.intel-openvino-amd64

infra/install/compose/
├── compose.edge-amd64.yml
├── compose.edge.nvidia-amd64.override.yml
└── compose.edge.intel-openvino-amd64.override.yml

infra/install/bare-metal/
└── edge-amd64.md

infra/install/eve-os/
├── README.md
└── vm/
    ├── packer.pkr.hcl
    ├── debian-preseed.cfg
    ├── firstboot.sh
    ├── vezor-eve-bootstrap.service
    └── eve-app-manifest.json
```

Optional if we validate NVIDIA passthrough in the VM:

```text
infra/install/eve-os/vm/nvidia-firstboot.sh
```

Do not create `infra/install/eve-os/container/` in this spec.

## Build Pipeline

Add Makefile targets:

```make
edge-generic-amd64-build:
	docker buildx build \
	  --platform linux/amd64 \
	  -f backend/Dockerfile.edge.generic-amd64 \
	  -t vezor/edge-worker:dev-generic-amd64 \
	  --load \
	  .

edge-nvidia-amd64-build:
	docker buildx build \
	  --platform linux/amd64 \
	  -f backend/Dockerfile.edge.nvidia-amd64 \
	  -t vezor/edge-worker:dev-nvidia-amd64 \
	  --load \
	  .

edge-intel-openvino-amd64-build:
	docker buildx build \
	  --platform linux/amd64 \
	  -f backend/Dockerfile.edge.intel-openvino-amd64 \
	  -t vezor/edge-worker:dev-intel-openvino-amd64 \
	  --load \
	  .

eve-vm-build-generic-amd64: edge-generic-amd64-build
	cd infra/install/eve-os/vm && packer build \
	  -var vezor_runtime_profile=generic-amd64 \
	  -var vezor_edge_image=vezor/edge-worker:dev-generic-amd64 \
	  packer.pkr.hcl
```

The NVIDIA and Intel VM build targets follow the same pattern after
their image evidence gates pass.

The Docker build context should include the same paths the current
central image needs, including `backend/` and `packs/`, so runtime pack
behavior remains available.

## Acceptance Criteria

### Required merge gate

1. **Generic image builds.** `make edge-generic-amd64-build` succeeds
   on an amd64 builder or documented amd64-capable buildx builder.
2. **CPU smoke passes.** Running the generic image on a CPU-only amd64
   host starts `python -m argus.inference.engine --help` and a
   synthetic one-frame CPU inference smoke.
3. **Runtime policy tests pass.** Tests cover generic amd64 host
   classification, CPU fallback, provider override, and fallback after
   provider initialization failure.
4. **Installer profile tests pass.** Tests prove amd64 runtime
   profiles skip Jetson preflight, select the correct Dockerfile/image
   key, write the correct Compose base/override paths, and preserve
   pairing/credential behavior.
5. **Generic Compose test passes.** The generic Compose file includes
   NATS leaf, MediaMTX, and supervisor, does not default to NVIDIA
   runtime, and keeps secret/credential mounts compatible with the
   current supervisor.
6. **Bare-metal installer evidence exists.** Installer artifact tests
   prove `--runtime-profile generic-amd64` resolves the generic worker
   image, generic Compose base, and no EVE-OS-only first-boot assets.
7. **Bare-metal docs updated.** `infra/install/bare-metal/edge-amd64.md`
   documents generic, NVIDIA, and Intel profile selection, CPU baseline
   behavior, and explicit non-claims for unvalidated acceleration.
8. **VM build evidence exists.** `make eve-vm-build-generic-amd64`
   either succeeds in CI/self-hosted CI, or a manual evidence file is
   captured under
   `docs/superpowers/status/YYYY-MM-DD-eve-os-vm-build-evidence.md`.
9. **VM boot smoke passes.** Booting the qcow2 under local KVM with a
   NoCloud seed reaches paired edge supervisor state against a local
   or lab master.
10. **Idempotent first boot.** Rebooting the VM after pairing does not
   re-run the pairing claim.
11. **Jetson regression gate passes.** Existing `backend/Dockerfile.edge`
   and Jetson compose/install behavior remain unchanged and still run
   on the Jetson rig.
12. **EVE-OS docs updated.** `infra/install/eve-os/README.md` documents
    EVE-OS deployment, the image matrix, CPU baseline, optional vendor
    images, and the explicit non-claims for unvalidated acceleration.

### Recommended evidence

13. **NVIDIA image evidence.** On an amd64 Linux host or EVE-OS VM with
    NVIDIA passthrough, confirm the NVIDIA image builds, selects CUDA,
    runs one synthetic inference, and supports CPU override fallback.
14. **Intel OpenVINO image evidence.** On an Intel iGPU/NPU host or
    EVE-OS VM with render-device exposure, confirm the Intel image
    builds, selects the intended OpenVINO target, runs the actual
    detector model, and supports CPU fallback.
15. **Live EVE-OS deploy.** Once an EVE-OS test device is available,
    exercise the operator walkthrough against a real RTSP source and
    capture results.

## Test Plan

- Add runtime tests near `backend/tests/vision/test_runtime.py` for:
  - generic amd64 CPU-only classification;
  - NVIDIA amd64 profile/provider selection;
  - Intel OpenVINO profile/provider selection;
  - provider override to CPU;
  - provider initialization fallback.
- Add installer artifact tests to
  `installer/tests/test_edge_installer_artifacts.py` for:
  - `--runtime-profile generic-amd64`;
  - `--runtime-profile nvidia-amd64`;
  - `--runtime-profile intel-openvino-amd64`;
  - profile-specific image keys;
  - Jetson preflight not required on amd64 profiles;
  - base and override Compose file paths in `/etc/vezor/edge.json`;
  - no bearer tokens or raw secrets in generated assets.
- Add first-boot script tests under installer tests:
  - marker-file refusal;
  - missing env var exits non-zero;
  - generated `vezor install edge` args include
    `--runtime-profile generic-amd64`;
  - logs do not print pairing code values.
- Add Compose tests for `compose.edge-amd64.yml`.
- Add vendor Compose override tests when the NVIDIA and Intel images
  are promoted.
- Add documentation checks that the EVE-OS README does not claim OCI app
  support or unvalidated vendor acceleration.
- Add documentation checks that the bare-metal amd64 walkthrough does
  not require EVE-OS, DeepStream, central Dockerized GPU, or Apple
  M-series acceleration.

## Files Touched

| File | Change |
|---|---|
| `backend/Dockerfile.edge.generic-amd64` | new generic amd64 CPU baseline edge worker image |
| `backend/Dockerfile.edge.nvidia-amd64` | new NVIDIA amd64 edge worker image after evidence gate |
| `backend/Dockerfile.edge.intel-openvino-amd64` | new Intel OpenVINO amd64 edge worker image after evidence gate |
| `backend/src/argus/vision/runtime.py` | refine generic, NVIDIA, and Intel profile/provider selection if needed |
| `backend/src/argus/inference/engine.py` | keep existing provider fallback/reporting compatible; no parallel provider registry |
| `installer/linux/install-edge.sh` | add amd64 runtime profile paths |
| `installer/manifests/dev-example.json` | add profile-specific amd64 image keys if manifest-driven builds need them |
| `infra/install/compose/compose.edge-amd64.yml` | new generic edge appliance compose |
| `infra/install/compose/compose.edge.nvidia-amd64.override.yml` | new NVIDIA override/profile after evidence gate |
| `infra/install/compose/compose.edge.intel-openvino-amd64.override.yml` | new Intel OpenVINO override/profile after evidence gate |
| `infra/install/bare-metal/edge-amd64.md` | new bare-metal amd64 edge operator walkthrough |
| `infra/install/eve-os/README.md` | new operator walkthrough |
| `infra/install/eve-os/vm/packer.pkr.hcl` | new VM build descriptor |
| `infra/install/eve-os/vm/debian-preseed.cfg` | new unattended install seed |
| `infra/install/eve-os/vm/firstboot.sh` | new first boot pairing script |
| `infra/install/eve-os/vm/vezor-eve-bootstrap.service` | new first boot service |
| `infra/install/eve-os/vm/eve-app-manifest.json` | new sample EVE-OS app config |
| `Makefile` | add image-matrix build targets and VM build targets |
| `docs/full-installation-guide.md` | link to bare-metal amd64 and EVE-OS VM edge README |
| `installer/tests/test_edge_installer_artifacts.py` | extend installer asset assertions |
| `installer/tests/test_eve_firstboot.py` | new firstboot tests |
| `backend/tests/vision/test_runtime.py` | extend runtime policy tests |

No changes to:

- `backend/Dockerfile.edge` Jetson path;
- `infra/docker-compose.edge.yml` development Jetson compose;
- `bin/vezor` front-door CLI behavior, except it naturally passes amd64
  runtime profile args through to `install-edge.sh`.

## Out Of Scope

- EVE-OS OCI/container app artifact.
- ARM64 EVE-OS artifacts.
- DeepStream.
- Central Dockerized GPU/M4 acceleration claims.
- NVIDIA or Intel production acceleration claims without hardware
  evidence.
- AMD ROCm provider.
- Coral, Hailo, or other NPU providers.
- EVE-OS controller API automation.
- Signed artifact distribution.
- Vezor-managed fleet update/replacement of qcow2 images.

## Open Questions

1. **Distribution endpoint.** Should the qcow2 land as a GitHub
   Release attachment, internal MinIO object, or both?
2. **Image namespace.** Use `vezor/edge-worker:VERSION-<profile>` locally
   and later `ghcr.io/<org>/vezor-edge-worker:VERSION-<profile>`, or
   keep the current `edge-worker` naming from manifests?
3. **CI runner.** Is a self-hosted KVM-capable runner available for
   qcow2 build/boot smoke, or should VM build remain a manual evidence
   step?
4. **NVIDIA test host.** Which amd64 NVIDIA host should provide the
   first live CUDA evidence?
5. **Intel test host.** Is there an Intel iGPU gateway/NUC available,
   or should Intel acceleration stay explicitly exploratory?
