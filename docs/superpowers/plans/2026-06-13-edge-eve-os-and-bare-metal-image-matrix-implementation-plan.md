# Edge EVE-OS And Bare-Metal Image Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build shared amd64 edge worker image profiles for both Linux bare-metal edge installs and EVE-OS VM packaging while keeping Jetson behavior unchanged.

**Architecture:** Extend the existing Linux edge installer and `argus.vision.runtime` policy instead of creating a second installer or provider registry. The generic amd64 bare-metal install is the required merge gate; EVE-OS qcow2 packaging reuses that same installer profile inside a Debian VM, and NVIDIA/Intel paths remain explicit evidence-gated profiles.

**Tech Stack:** Bash installers, Docker/Compose, Python 3.12 backend, ONNX Runtime provider policy, pytest installer tests, Packer qemu VM packaging, systemd, cloud-init NoCloud.

---

## Execution Notes

- Preserve unrelated and untracked local files.
- Write failing tests before implementation.
- Do not commit or push unless the user explicitly asks. When a task says "commit checkpoint", skip that step unless explicit permission has been given.
- Do not create `infra/install/eve-os/container/`.
- Do not implement DeepStream.
- Do not trigger implicit ReID model downloads.
- Do not claim central Dockerized GPU or Apple M-series acceleration.
- Do not print secrets, pairing codes, bearer tokens, raw RTSP credentials, sudo passwords, or raw process arguments.

## File Structure

- Modify `installer/linux/install-edge.sh`: add `--runtime-profile`, image-key resolution, Jetson preflight gating, profile-specific Dockerfile selection, generic Compose path writing.
- Modify `installer/manifests/dev-example.json`: add `edge-worker-generic-amd64`, `edge-worker-nvidia-amd64`, and `edge-worker-intel-openvino-amd64` image keys.
- Modify `backend/src/argus/vision/runtime.py`: add or refine a generic Linux x86_64 profile and keep vendor profiles evidence-based.
- Modify `backend/tests/vision/test_runtime.py`: runtime profile selection tests.
- Modify `installer/tests/test_edge_installer_artifacts.py`: installer profile and compose artifact assertions.
- Create `installer/tests/test_eve_firstboot.py`: first-boot script behavior and redaction tests.
- Create `backend/Dockerfile.edge.generic-amd64`: CPU-only amd64 worker image.
- Create `backend/Dockerfile.edge.nvidia-amd64`: NVIDIA amd64 worker image.
- Create `backend/Dockerfile.edge.intel-openvino-amd64`: Intel OpenVINO amd64 worker image.
- Create `infra/install/compose/compose.edge-amd64.yml`: generic amd64 edge Compose base.
- Create `infra/install/compose/compose.edge.nvidia-amd64.override.yml`: NVIDIA override, evidence-gated.
- Create `infra/install/compose/compose.edge.intel-openvino-amd64.override.yml`: Intel OpenVINO override, evidence-gated.
- Create `infra/install/eve-os/README.md`: EVE-OS VM operator walkthrough and non-claims.
- Create `infra/install/bare-metal/edge-amd64.md`: bare-metal Linux edge operator walkthrough and non-claims.
- Create `infra/install/eve-os/vm/packer.pkr.hcl`: qemu qcow2 build descriptor.
- Create `infra/install/eve-os/vm/debian-preseed.cfg`: unattended Debian seed.
- Create `infra/install/eve-os/vm/firstboot.sh`: idempotent pairing bootstrap.
- Create `infra/install/eve-os/vm/vezor-eve-bootstrap.service`: first-boot systemd unit.
- Create `infra/install/eve-os/vm/eve-app-manifest.json`: sample EVE-OS VM app config.
- Modify `Makefile`: add image matrix and generic VM build targets.
- Modify `docs/full-installation-guide.md`: link to EVE-OS VM and bare-metal amd64 edge walkthroughs.

---

### Task 1: Installer Runtime Profile Contract

**Files:**
- Modify: `installer/tests/test_edge_installer_artifacts.py`
- Modify: `installer/linux/install-edge.sh`
- Modify: `installer/manifests/dev-example.json`

- [ ] **Step 1: Add failing installer profile artifact tests**

Append these tests to `installer/tests/test_edge_installer_artifacts.py`:

```python
def test_edge_install_script_accepts_amd64_runtime_profiles() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "--runtime-profile" in script
    assert "generic-amd64" in script
    assert "nvidia-amd64" in script
    assert "intel-openvino-amd64" in script
    assert "edge-worker-generic-amd64" in script
    assert "edge-worker-nvidia-amd64" in script
    assert "edge-worker-intel-openvino-amd64" in script
    assert "Dockerfile.edge.generic-amd64" in script
    assert "Dockerfile.edge.nvidia-amd64" in script
    assert "Dockerfile.edge.intel-openvino-amd64" in script


def test_edge_install_script_skips_jetson_preflight_for_amd64_profiles() -> None:
    script = _read(INSTALL_SCRIPT)

    jetson_preflight_index = script.index("scripts/jetson-preflight.sh --installer --json")
    runtime_case_index = script.index("case \"$RUNTIME_PROFILE\" in")
    assert runtime_case_index < jetson_preflight_index
    assert 'if [[ "$RUNTIME_PROFILE" == "jetson" ]]' in script


def test_edge_manifest_contains_profile_specific_amd64_image_keys() -> None:
    manifest = _read(REPO_ROOT / "installer" / "manifests" / "dev-example.json")

    assert '"edge-worker-generic-amd64"' in manifest
    assert '"edge-worker-nvidia-amd64"' in manifest
    assert '"edge-worker-intel-openvino-amd64"' in manifest
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: FAIL because `--runtime-profile` and profile-specific image keys are not present.

- [ ] **Step 3: Add runtime profile parsing and helpers**

In `installer/linux/install-edge.sh`, add near the existing variable block:

```bash
RUNTIME_PROFILE="${VEZOR_EDGE_RUNTIME_PROFILE:-jetson}"
EDGE_WORKER_IMAGE_KEY="edge-worker"
EDGE_DOCKERFILE="/opt/vezor/current/backend/Dockerfile.edge"
EDGE_BUILD_CONTEXT="/opt/vezor/current/backend"
EDGE_COMPOSE_FILE="/opt/vezor/current/infra/install/compose/compose.supervisor.yml"
EDGE_COMPOSE_OVERRIDES=""
EDGE_PUBLISH_PROFILE="jetson-nano"
```

Add usage text:

```text
  --runtime-profile PROFILE
                         Edge runtime profile: jetson, generic-amd64,
                         nvidia-amd64, or intel-openvino-amd64.
```

Add argument parsing:

```bash
    --runtime-profile)
      RUNTIME_PROFILE="${2:?--runtime-profile requires a value}"
      shift 2
      ;;
```

Add this function before image resolution:

```bash
resolve_runtime_profile() {
  case "$RUNTIME_PROFILE" in
    jetson)
      EDGE_WORKER_IMAGE_KEY="edge-worker"
      EDGE_DOCKERFILE="/opt/vezor/current/backend/Dockerfile.edge"
      EDGE_BUILD_CONTEXT="/opt/vezor/current/backend"
      EDGE_COMPOSE_FILE="/opt/vezor/current/infra/install/compose/compose.supervisor.yml"
      EDGE_COMPOSE_OVERRIDES=""
      EDGE_PUBLISH_PROFILE="jetson-nano"
      ;;
    generic-amd64)
      EDGE_WORKER_IMAGE_KEY="edge-worker-generic-amd64"
      EDGE_DOCKERFILE="/opt/vezor/current/backend/Dockerfile.edge.generic-amd64"
      EDGE_BUILD_CONTEXT="/opt/vezor/current"
      EDGE_COMPOSE_FILE="/opt/vezor/current/infra/install/compose/compose.edge-amd64.yml"
      EDGE_COMPOSE_OVERRIDES=""
      EDGE_PUBLISH_PROFILE="generic-amd64"
      ;;
    nvidia-amd64)
      EDGE_WORKER_IMAGE_KEY="edge-worker-nvidia-amd64"
      EDGE_DOCKERFILE="/opt/vezor/current/backend/Dockerfile.edge.nvidia-amd64"
      EDGE_BUILD_CONTEXT="/opt/vezor/current"
      EDGE_COMPOSE_FILE="/opt/vezor/current/infra/install/compose/compose.edge-amd64.yml"
      EDGE_COMPOSE_OVERRIDES="/opt/vezor/current/infra/install/compose/compose.edge.nvidia-amd64.override.yml"
      EDGE_PUBLISH_PROFILE="nvidia-amd64"
      ;;
    intel-openvino-amd64)
      EDGE_WORKER_IMAGE_KEY="edge-worker-intel-openvino-amd64"
      EDGE_DOCKERFILE="/opt/vezor/current/backend/Dockerfile.edge.intel-openvino-amd64"
      EDGE_BUILD_CONTEXT="/opt/vezor/current"
      EDGE_COMPOSE_FILE="/opt/vezor/current/infra/install/compose/compose.edge-amd64.yml"
      EDGE_COMPOSE_OVERRIDES="/opt/vezor/current/infra/install/compose/compose.edge.intel-openvino-amd64.override.yml"
      EDGE_PUBLISH_PROFILE="intel-openvino-amd64"
      ;;
    *)
      echo "Unsupported --runtime-profile: $RUNTIME_PROFILE" >&2
      exit 2
      ;;
  esac
}
```

- [ ] **Step 4: Wire profile image key and Jetson preflight guard**

Call `resolve_runtime_profile` before image resolution:

```bash
resolve_runtime_profile

MEDIAMTX_IMAGE="$(manifest_image_ref mediamtx bluenviron/mediamtx:latest)"
NATS_IMAGE="$(manifest_image_ref nats nats:2)"
EDGE_WORKER_IMAGE="$(manifest_image_ref "$EDGE_WORKER_IMAGE_KEY" vezor/edge-worker:portable-demo)"
```

Replace the unconditional preflight block with:

```bash
if [[ "$RUNTIME_PROFILE" == "jetson" && -x "$RELEASE_DIR/scripts/jetson-preflight.sh" ]]; then
  JETSON_PREFLIGHT_JSON="$(mktemp)"
  preflight_output="$(cd "$RELEASE_DIR" && scripts/jetson-preflight.sh --installer --json)"
  printf '%s\n' "$preflight_output"
  PREFLIGHT_OUTPUT="$preflight_output" python3 - "$JETSON_PREFLIGHT_JSON" <<'PY'
import json
import os
import sys
from pathlib import Path

target = Path(sys.argv[1])
for line in reversed(os.environ.get("PREFLIGHT_OUTPUT", "").splitlines()):
    line = line.strip()
    if not line.startswith("{"):
        continue
    payload = json.loads(line)
    target.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    break
else:
    raise SystemExit("Jetson preflight did not emit JSON.")
PY
fi
```

- [ ] **Step 5: Update local image build**

In `build_local_edge_image`, keep the Jetson wheel logic only for the Jetson profile:

```bash
  if [[ "$RUNTIME_PROFILE" == "jetson" ]]; then
    resolve_jetson_ort_from_manifest
    if [[ -z "$JETSON_ORT_WHEEL_URL" && "$ALLOW_CPU_ONNX_RUNTIME" != "1" ]]; then
      echo "Jetson ONNX Runtime GPU wheel is required for dev manifest edge builds." >&2
      echo "Provide a manifest jetson_ort_wheels entry for this Jetson, or use --allow-cpu-onnx-runtime only for diagnostics." >&2
      echo "Use --allow-cpu-onnx-runtime only for CPU-only diagnostics, not product demos." >&2
      exit 2
    fi
    run "$CONTAINER_ENGINE" build \
      -f "$EDGE_DOCKERFILE" \
      --build-arg "JETSON_ORT_WHEEL_URL=$JETSON_ORT_WHEEL_URL" \
      --build-arg "JETSON_ORT_WHEEL_SHA256=$JETSON_ORT_WHEEL_SHA256" \
      --build-arg "ALLOW_CPU_ONNX_RUNTIME=$ALLOW_CPU_ONNX_RUNTIME" \
      -t "$EDGE_WORKER_IMAGE" \
      "$EDGE_BUILD_CONTEXT"
    return 0
  fi

  echo "Building local Vezor edge image for runtime profile $RUNTIME_PROFILE..."
  run "$CONTAINER_ENGINE" build \
    -f "$EDGE_DOCKERFILE" \
    -t "$EDGE_WORKER_IMAGE" \
    "$EDGE_BUILD_CONTEXT"
```

- [ ] **Step 6: Add manifest image keys**

In `installer/manifests/dev-example.json`, add these image entries next to `edge-worker`:

```json
    "edge-worker-generic-amd64": {
      "reference": "vezor/edge-worker:dev-generic-amd64"
    },
    "edge-worker-nvidia-amd64": {
      "reference": "vezor/edge-worker:dev-nvidia-amd64"
    },
    "edge-worker-intel-openvino-amd64": {
      "reference": "vezor/edge-worker:dev-intel-openvino-amd64"
    }
```

- [ ] **Step 7: Run tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: PASS for the added tests and existing edge installer tests.

- [ ] **Step 8: Update plan checkbox and commit checkpoint if requested**

If the user has explicitly asked for commits, run:

```bash
git add installer/linux/install-edge.sh installer/manifests/dev-example.json installer/tests/test_edge_installer_artifacts.py
git commit -m "feat: add edge runtime profile contract"
```

---

### Task 2: Generic amd64 Compose Base

**Files:**
- Create: `infra/install/compose/compose.edge-amd64.yml`
- Create: `infra/install/compose/compose.edge.nvidia-amd64.override.yml`
- Create: `infra/install/compose/compose.edge.intel-openvino-amd64.override.yml`
- Modify: `installer/tests/test_edge_installer_artifacts.py`
- Modify: `installer/linux/install-edge.sh`

- [ ] **Step 1: Add failing Compose artifact tests**

Append:

```python
GENERIC_AMD64_COMPOSE = REPO_ROOT / "infra" / "install" / "compose" / "compose.edge-amd64.yml"
NVIDIA_AMD64_COMPOSE = REPO_ROOT / "infra" / "install" / "compose" / "compose.edge.nvidia-amd64.override.yml"
INTEL_AMD64_COMPOSE = REPO_ROOT / "infra" / "install" / "compose" / "compose.edge.intel-openvino-amd64.override.yml"


def test_generic_amd64_edge_compose_has_no_default_nvidia_runtime() -> None:
    compose = _read(GENERIC_AMD64_COMPOSE)

    assert "  nats-leaf:" in compose
    assert "  mediamtx:" in compose
    assert "  vezor-supervisor:" in compose
    assert "runtime: nvidia" not in compose
    assert "VEZOR_NVIDIA_RUNTIME" not in compose
    assert "ARGUS_PUBLISH_PROFILE: ${VEZOR_PUBLISH_PROFILE:-generic-amd64}" in compose
    assert "${VEZOR_SUPERVISOR_IMAGE:?set VEZOR_SUPERVISOR_IMAGE}" in compose
    assert "${VEZOR_MODEL_HOST_DIR:-/var/lib/vezor/models}:/models" in compose


def test_vendor_amd64_overrides_are_explicit_and_not_defaulted() -> None:
    nvidia = _read(NVIDIA_AMD64_COMPOSE)
    intel = _read(INTEL_AMD64_COMPOSE)

    assert "runtime: ${VEZOR_NVIDIA_RUNTIME:-nvidia}" in nvidia
    assert "NVIDIA_VISIBLE_DEVICES" in nvidia
    assert "/dev/dri:/dev/dri" in intel
    assert "ARGUS_INFERENCE_EXECUTION_PROFILE_OVERRIDE" in intel
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: FAIL because the Compose files do not exist.

- [ ] **Step 3: Create generic amd64 Compose base**

Create `infra/install/compose/compose.edge-amd64.yml`:

```yaml
name: vezor-edge

services:
  nats-leaf:
    image: ${VEZOR_NATS_IMAGE:?set VEZOR_NATS_IMAGE}
    command: ["-js", "-c", "/etc/nats/nats.conf"]
    restart: unless-stopped
    ports:
      - "${VEZOR_EDGE_NATS_BIND:-127.0.0.1}:4222:4222"
      - "${VEZOR_EDGE_NATS_HTTP_BIND:-127.0.0.1}:8222:8222"
    volumes:
      - /etc/vezor/nats/leaf.conf:/etc/nats/nats.conf:ro
      - /var/lib/vezor/nats:/data

  mediamtx:
    image: ${VEZOR_MEDIAMTX_IMAGE:?set VEZOR_MEDIAMTX_IMAGE}
    restart: unless-stopped
    ports:
      - "${VEZOR_EDGE_RTSP_BIND:-0.0.0.0}:8554:8554"
      - "${VEZOR_EDGE_HLS_BIND:-0.0.0.0}:8888:8888"
      - "${VEZOR_EDGE_WEBRTC_BIND:-0.0.0.0}:8889:8889"
      - "${VEZOR_EDGE_WEBRTC_UDP_BIND:-0.0.0.0}:8189:8189/udp"
      - "${VEZOR_EDGE_MEDIAMTX_API_BIND:-127.0.0.1}:9997:9997"
    volumes:
      - /etc/vezor/mediamtx/mediamtx.yml:/mediamtx.yml:ro
      - /var/lib/vezor/mediamtx:/data

  vezor-supervisor:
    image: ${VEZOR_SUPERVISOR_IMAGE:?set VEZOR_SUPERVISOR_IMAGE}
    restart: unless-stopped
    entrypoint: ["/app/.venv/bin/python", "-m", "argus.supervisor.runner"]
    command:
      - --config
      - /etc/vezor/supervisor.json
    environment:
      ARGUS_NATS_URL: ${ARGUS_NATS_URL:-nats://nats-leaf:4222}
      ARGUS_NATS_MANAGE_STREAMS: "false"
      ARGUS_MEDIAMTX_API_URL: http://mediamtx:9997
      ARGUS_ENABLE_WORKER_METRICS_SERVER: "true"
      ARGUS_PUBLISH_PROFILE: ${VEZOR_PUBLISH_PROFILE:-generic-amd64}
      OMP_NUM_THREADS: ${VEZOR_WORKER_OMP_NUM_THREADS:-1}
      OPENBLAS_NUM_THREADS: ${VEZOR_WORKER_OPENBLAS_NUM_THREADS:-1}
      MKL_NUM_THREADS: ${VEZOR_WORKER_MKL_NUM_THREADS:-1}
      NUMEXPR_NUM_THREADS: ${VEZOR_WORKER_NUMEXPR_NUM_THREADS:-1}
      OPENCV_FOR_THREADS_NUM: ${VEZOR_WORKER_OPENCV_THREADS:-1}
      ARGUS_INFERENCE_SESSION_INTER_OP_THREADS: ${VEZOR_WORKER_INFERENCE_SESSION_INTER_OP_THREADS:-1}
      ARGUS_INFERENCE_SESSION_INTRA_OP_THREADS: ${VEZOR_WORKER_INFERENCE_SESSION_INTRA_OP_THREADS:-2}
      ARGUS_CPU_FALLBACK_PROCESSING_FPS_CAP: ${VEZOR_CPU_FALLBACK_PROCESSING_FPS_CAP:-}
    ports:
      - "${VEZOR_WORKER_METRICS_BIND:-127.0.0.1}:9108:9108"
    volumes:
      - /etc/vezor/edge.json:/etc/vezor/edge.json:ro
      - /etc/vezor/supervisor.json:/etc/vezor/supervisor.json:ro
      - ${VEZOR_CREDENTIALS_HOST_DIR:-/var/lib/vezor/credentials}:/run/vezor/credentials:ro
      - ${VEZOR_MODEL_HOST_DIR:-/var/lib/vezor/models}:/models
      - /var/lib/vezor:/var/lib/vezor
      - /var/log/vezor:/var/log/vezor
    depends_on:
      - nats-leaf
      - mediamtx
```

- [ ] **Step 4: Create vendor override files**

Create `infra/install/compose/compose.edge.nvidia-amd64.override.yml`:

```yaml
services:
  vezor-supervisor:
    runtime: ${VEZOR_NVIDIA_RUNTIME:-nvidia}
    environment:
      NVIDIA_VISIBLE_DEVICES: ${NVIDIA_VISIBLE_DEVICES:-all}
      NVIDIA_DRIVER_CAPABILITIES: ${NVIDIA_DRIVER_CAPABILITIES:-compute,utility,video}
      ARGUS_INFERENCE_EXECUTION_PROFILE_OVERRIDE: ${ARGUS_INFERENCE_EXECUTION_PROFILE_OVERRIDE:-linux-x86_64-nvidia}
```

Create `infra/install/compose/compose.edge.intel-openvino-amd64.override.yml`:

```yaml
services:
  vezor-supervisor:
    devices:
      - ${VEZOR_INTEL_DRI_DEVICE:-/dev/dri}:/dev/dri
    environment:
      ARGUS_INFERENCE_EXECUTION_PROFILE_OVERRIDE: ${ARGUS_INFERENCE_EXECUTION_PROFILE_OVERRIDE:-linux-x86_64-intel}
      ARGUS_OPENVINO_DEVICE: ${ARGUS_OPENVINO_DEVICE:-AUTO}
```

- [ ] **Step 5: Write selected Compose fields into edge config/env**

In `installer/linux/install-edge.sh`, add to `EDGE_ENV`:

```bash
VEZOR_PUBLISH_PROFILE=$EDGE_PUBLISH_PROFILE
VEZOR_EDGE_COMPOSE=$EDGE_COMPOSE_FILE
VEZOR_EDGE_COMPOSE_OVERRIDES=$EDGE_COMPOSE_OVERRIDES
```

Update `EDGE_CONFIG` JSON to include:

```json
  "runtime_profile": "$RUNTIME_PROFILE",
  "compose_file": "$EDGE_COMPOSE_FILE",
  "compose_overrides": "$EDGE_COMPOSE_OVERRIDES"
```

- [ ] **Step 6: Run tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit checkpoint if requested**

```bash
git add infra/install/compose/compose.edge-amd64.yml infra/install/compose/compose.edge.nvidia-amd64.override.yml infra/install/compose/compose.edge.intel-openvino-amd64.override.yml installer/linux/install-edge.sh installer/tests/test_edge_installer_artifacts.py
git commit -m "feat: add amd64 edge compose profiles"
```

---

### Task 3: Runtime Policy And Telemetry Truth

**Files:**
- Modify: `backend/src/argus/vision/runtime.py`
- Modify: `backend/tests/vision/test_runtime.py`
- Optional modify: `backend/src/argus/supervisor/hardware_probe.py`

- [ ] **Step 1: Add failing generic profile tests**

Append to `backend/tests/vision/test_runtime.py`:

```python
def test_runtime_policy_uses_generic_profile_for_unknown_linux_x86_cpu_hosts() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(providers=[ExecutionProvider.CPU.value]),
        system="Linux",
        machine="x86_64",
        cpu_vendor=CpuVendor.UNKNOWN,
    )

    assert policy.profile is ExecutionProfile.LINUX_X86_64_GENERIC
    assert policy.provider == ExecutionProvider.CPU.value


def test_runtime_policy_profile_override_can_force_generic_cpu_profile() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(providers=[ExecutionProvider.CPU.value]),
        system="Linux",
        machine="x86_64",
        cpu_vendor=CpuVendor.INTEL,
        execution_profile_override=ExecutionProfile.LINUX_X86_64_GENERIC,
    )

    assert policy.profile is ExecutionProfile.LINUX_X86_64_GENERIC
    assert policy.provider == ExecutionProvider.CPU.value
    assert policy.profile_overridden is True
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_runtime.py -q
```

Expected: FAIL because `LINUX_X86_64_GENERIC` is missing.

- [ ] **Step 3: Add generic profile**

In `backend/src/argus/vision/runtime.py`, add enum value:

```python
LINUX_X86_64_GENERIC = "linux-x86_64-generic"
```

Add provider priority:

```python
ExecutionProfile.LINUX_X86_64_GENERIC: (ExecutionProvider.CPU,),
```

In `classify_host`, add this branch before AMD and fallback:

```python
    elif resolved_system == "linux" and resolved_machine == "x86_64":
        profile = ExecutionProfile.LINUX_X86_64_GENERIC
        profile_overridden = False
```

Keep NVIDIA detection above Intel/generic. Keep Intel profile only for Intel vendor. Keep AMD as CPU-specific if the code still needs `linux-x86_64-amd`.

- [ ] **Step 4: Run runtime tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_runtime.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if requested**

```bash
git add backend/src/argus/vision/runtime.py backend/tests/vision/test_runtime.py
git commit -m "feat: add generic linux x86 runtime profile"
```

---

### Task 4: Generic amd64 Worker Image

**Files:**
- Create: `backend/Dockerfile.edge.generic-amd64`
- Modify: `installer/tests/test_edge_installer_artifacts.py`
- Modify: `Makefile`

- [ ] **Step 1: Add failing Dockerfile and Make target tests**

Append:

```python
GENERIC_AMD64_DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile.edge.generic-amd64"
MAKEFILE = REPO_ROOT / "Makefile"


def test_generic_amd64_dockerfile_is_cpu_baseline() -> None:
    dockerfile = _read(GENERIC_AMD64_DOCKERFILE)

    assert "python:3.12" in dockerfile
    assert "YOLO_CONFIG_DIR=/tmp" in dockerfile
    assert "onnxruntime" in dockerfile
    assert "onnxruntime-gpu" not in dockerfile
    assert "openvino" not in dockerfile.lower()
    assert "nvidia" not in dockerfile.lower()
    assert "COPY backend" in dockerfile
    assert "COPY packs" in dockerfile


def test_makefile_has_generic_amd64_image_target() -> None:
    makefile = _read(MAKEFILE)

    assert "edge-generic-amd64-build:" in makefile
    assert "backend/Dockerfile.edge.generic-amd64" in makefile
    assert "vezor/edge-worker:dev-generic-amd64" in makefile
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: FAIL because the Dockerfile and Make target are missing.

- [ ] **Step 3: Create Dockerfile**

Create `backend/Dockerfile.edge.generic-amd64`:

```dockerfile
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      ffmpeg \
      libglib2.0-0 \
      libgl1 \
      libgomp1 \
      curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN pip install --no-cache-dir uv \
    && cd backend \
    && uv sync --frozen --no-dev

COPY backend ./backend
COPY packs ./packs

WORKDIR /app/backend

CMD ["/app/backend/.venv/bin/python", "-m", "argus.supervisor.runner", "--config", "/etc/vezor/supervisor.json"]
```

Adjust `uv sync` flags to match the existing backend Dockerfile if the project uses a different production install command.

- [ ] **Step 4: Add Make target**

In `Makefile`, add:

```make
edge-generic-amd64-build:
	docker buildx build \
	  --platform linux/amd64 \
	  -f backend/Dockerfile.edge.generic-amd64 \
	  -t vezor/edge-worker:dev-generic-amd64 \
	  --load \
	  .
```

- [ ] **Step 5: Run tests and optional build smoke**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py -q
docker buildx build --platform linux/amd64 -f backend/Dockerfile.edge.generic-amd64 -t vezor/edge-worker:dev-generic-amd64 --load .
```

Expected: tests PASS. Build PASS on an amd64-capable builder.

- [ ] **Step 6: Commit checkpoint if requested**

```bash
git add backend/Dockerfile.edge.generic-amd64 Makefile installer/tests/test_edge_installer_artifacts.py
git commit -m "feat: add generic amd64 edge worker image"
```

---

### Task 5: NVIDIA And Intel Image Artifacts With Evidence Gates

**Files:**
- Create: `backend/Dockerfile.edge.nvidia-amd64`
- Create: `backend/Dockerfile.edge.intel-openvino-amd64`
- Modify: `Makefile`
- Modify: `installer/tests/test_edge_installer_artifacts.py`

- [ ] **Step 1: Add failing artifact tests**

Append:

```python
NVIDIA_AMD64_DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile.edge.nvidia-amd64"
INTEL_OPENVINO_AMD64_DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile.edge.intel-openvino-amd64"


def test_vendor_amd64_dockerfiles_are_explicit_vendor_images() -> None:
    nvidia = _read(NVIDIA_AMD64_DOCKERFILE)
    intel = _read(INTEL_OPENVINO_AMD64_DOCKERFILE)

    assert "onnxruntime-gpu" in nvidia
    assert "DeepStream" not in nvidia
    assert "openvino" in intel.lower()
    assert "onnxruntime-gpu" not in intel
    assert "YOLO_CONFIG_DIR=/tmp" in nvidia
    assert "YOLO_CONFIG_DIR=/tmp" in intel


def test_makefile_has_vendor_amd64_image_targets() -> None:
    makefile = _read(MAKEFILE)

    assert "edge-nvidia-amd64-build:" in makefile
    assert "edge-intel-openvino-amd64-build:" in makefile
    assert "backend/Dockerfile.edge.nvidia-amd64" in makefile
    assert "backend/Dockerfile.edge.intel-openvino-amd64" in makefile
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: FAIL because vendor Dockerfiles and Make targets are missing.

- [ ] **Step 3: Create NVIDIA Dockerfile**

Create `backend/Dockerfile.edge.nvidia-amd64`:

```dockerfile
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      ffmpeg \
      libglib2.0-0 \
      libgl1 \
      libgomp1 \
      curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN pip install --no-cache-dir uv \
    && cd backend \
    && uv sync --frozen --no-dev \
    && .venv/bin/python -m pip install --no-cache-dir onnxruntime-gpu

COPY backend ./backend
COPY packs ./packs

WORKDIR /app/backend

CMD ["/app/backend/.venv/bin/python", "-m", "argus.supervisor.runner", "--config", "/etc/vezor/supervisor.json"]
```

- [ ] **Step 4: Create Intel OpenVINO Dockerfile**

Create `backend/Dockerfile.edge.intel-openvino-amd64`:

```dockerfile
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      ffmpeg \
      libglib2.0-0 \
      libgl1 \
      libgomp1 \
      libdrm2 \
      curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN pip install --no-cache-dir uv \
    && cd backend \
    && uv sync --frozen --no-dev \
    && .venv/bin/python -m pip install --no-cache-dir onnxruntime-openvino

COPY backend ./backend
COPY packs ./packs

WORKDIR /app/backend

CMD ["/app/backend/.venv/bin/python", "-m", "argus.supervisor.runner", "--config", "/etc/vezor/supervisor.json"]
```

- [ ] **Step 5: Add Make targets**

Add:

```make
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
```

- [ ] **Step 6: Run artifact tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 7: Capture vendor evidence before promotion**

Run NVIDIA evidence only on an amd64 host or VM with NVIDIA passthrough:

```bash
make edge-nvidia-amd64-build
docker run --rm --gpus all vezor/edge-worker:dev-nvidia-amd64 /app/backend/.venv/bin/python - <<'PY'
import onnxruntime as ort
providers = ort.get_available_providers()
print(providers)
raise SystemExit(0 if "CUDAExecutionProvider" in providers else 1)
PY
```

Run Intel evidence only on an Intel host or VM with render-device exposure:

```bash
make edge-intel-openvino-amd64-build
docker run --rm --device /dev/dri:/dev/dri vezor/edge-worker:dev-intel-openvino-amd64 /app/backend/.venv/bin/python - <<'PY'
import onnxruntime as ort
providers = ort.get_available_providers()
print(providers)
raise SystemExit(0 if "OpenVINOExecutionProvider" in providers else 1)
PY
```

Expected: each evidence command PASS only on matching hardware. If hardware is not available, mark vendor evidence NOT RUN and keep docs clear that only the generic image is merge-gated.

- [ ] **Step 8: Commit checkpoint if requested**

```bash
git add backend/Dockerfile.edge.nvidia-amd64 backend/Dockerfile.edge.intel-openvino-amd64 Makefile installer/tests/test_edge_installer_artifacts.py
git commit -m "feat: add vendor amd64 edge image artifacts"
```

---

### Task 6: EVE-OS First Boot Assets

**Files:**
- Create: `installer/tests/test_eve_firstboot.py`
- Create: `infra/install/eve-os/vm/firstboot.sh`
- Create: `infra/install/eve-os/vm/vezor-eve-bootstrap.service`
- Create: `infra/install/eve-os/vm/eve-app-manifest.json`

- [ ] **Step 1: Add failing firstboot tests**

Create `installer/tests/test_eve_firstboot.py`:

```python
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
FIRSTBOOT = REPO_ROOT / "infra" / "install" / "eve-os" / "vm" / "firstboot.sh"
SERVICE = REPO_ROOT / "infra" / "install" / "eve-os" / "vm" / "vezor-eve-bootstrap.service"
MANIFEST = REPO_ROOT / "infra" / "install" / "eve-os" / "vm" / "eve-app-manifest.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_eve_firstboot_defaults_to_generic_amd64_and_is_idempotent() -> None:
    script = _read(FIRSTBOOT)

    assert "/var/lib/vezor/paired.marker" in script
    assert 'VEZOR_RUNTIME_PROFILE="${VEZOR_RUNTIME_PROFILE:-generic-amd64}"' in script
    assert "--runtime-profile" in script
    assert '"$VEZOR_RUNTIME_PROFILE"' in script
    assert "systemctl disable vezor-eve-bootstrap.service" in script


def test_eve_firstboot_requires_pairing_env_without_printing_values() -> None:
    script = _read(FIRSTBOOT)

    assert "VEZOR_API_URL" in script
    assert "VEZOR_SESSION_ID" in script
    assert "VEZOR_PAIRING_CODE" in script
    assert "Missing required pairing env var" in script
    assert "set -x" not in script
    assert "echo \"$VEZOR_PAIRING_CODE\"" not in script


def test_eve_bootstrap_service_runs_firstboot_once() -> None:
    service = _read(SERVICE)

    assert "Type=oneshot" in service
    assert "ExecStart=/usr/local/sbin/vezor-eve-firstboot" in service
    assert "WantedBy=multi-user.target" in service


def test_eve_app_manifest_is_vm_not_oci_container() -> None:
    manifest = _read(MANIFEST)

    assert "qcow2" in manifest
    assert "container" not in manifest.lower()
    assert "VEZOR_RUNTIME_PROFILE" in manifest
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_eve_firstboot.py -q
```

Expected: FAIL because files do not exist.

- [ ] **Step 3: Create firstboot script**

Create `infra/install/eve-os/vm/firstboot.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PAIRING_ENV="/etc/vezor/pairing.env"
PAIRED_MARKER="/var/lib/vezor/paired.marker"

if [[ -f "$PAIRED_MARKER" ]]; then
  echo "Vezor EVE-OS firstboot already completed."
  exit 0
fi

if [[ ! -f "$PAIRING_ENV" ]]; then
  echo "Missing pairing environment file: $PAIRING_ENV" >&2
  exit 2
fi

set -a
. "$PAIRING_ENV"
set +a

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required pairing env var: $name" >&2
    exit 2
  fi
}

require_env VEZOR_API_URL
require_env VEZOR_SESSION_ID
require_env VEZOR_PAIRING_CODE

VEZOR_RUNTIME_PROFILE="${VEZOR_RUNTIME_PROFILE:-generic-amd64}"
VEZOR_EDGE_NAME="${VEZOR_EDGE_NAME:-$(hostname)}"

/usr/local/bin/vezor install edge \
  --runtime-profile "$VEZOR_RUNTIME_PROFILE" \
  --api-url "$VEZOR_API_URL" \
  --session-id "$VEZOR_SESSION_ID" \
  --pairing-code "$VEZOR_PAIRING_CODE" \
  --edge-name "$VEZOR_EDGE_NAME"

install -d -m 0755 /var/lib/vezor
touch "$PAIRED_MARKER"
systemctl disable vezor-eve-bootstrap.service >/dev/null 2>&1 || true
```

- [ ] **Step 4: Create service and manifest**

Create `infra/install/eve-os/vm/vezor-eve-bootstrap.service`:

```ini
[Unit]
Description=Vezor EVE-OS First Boot Pairing
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/vezor-eve-firstboot
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Create `infra/install/eve-os/vm/eve-app-manifest.json`:

```json
{
  "name": "vezor-edge-amd64",
  "type": "vm",
  "architecture": "amd64",
  "image_format": "qcow2",
  "runtime_env": {
    "VEZOR_RUNTIME_PROFILE": "generic-amd64",
    "VEZOR_API_URL": "https://MASTER_HOST:8000",
    "VEZOR_SESSION_ID": "REDACTED_SESSION_ID",
    "VEZOR_PAIRING_CODE": "REDACTED_PAIRING_CODE"
  }
}
```

- [ ] **Step 5: Run tests and shell syntax**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_eve_firstboot.py -q
bash -n infra/install/eve-os/vm/firstboot.sh
```

Expected: PASS.

- [ ] **Step 6: Commit checkpoint if requested**

```bash
git add installer/tests/test_eve_firstboot.py infra/install/eve-os/vm/firstboot.sh infra/install/eve-os/vm/vezor-eve-bootstrap.service infra/install/eve-os/vm/eve-app-manifest.json
git commit -m "feat: add eve os firstboot assets"
```

---

### Task 7: Bare-Metal And EVE-OS Packaging Docs

**Files:**
- Create: `infra/install/eve-os/vm/packer.pkr.hcl`
- Create: `infra/install/eve-os/vm/debian-preseed.cfg`
- Create: `infra/install/eve-os/README.md`
- Create: `infra/install/bare-metal/edge-amd64.md`
- Modify: `Makefile`
- Modify: `docs/full-installation-guide.md`
- Modify: `installer/tests/test_eve_firstboot.py`

- [ ] **Step 1: Add failing docs and Packer tests**

Append:

```python
PACKER = REPO_ROOT / "infra" / "install" / "eve-os" / "vm" / "packer.pkr.hcl"
PRESEED = REPO_ROOT / "infra" / "install" / "eve-os" / "vm" / "debian-preseed.cfg"
EVE_README = REPO_ROOT / "infra" / "install" / "eve-os" / "README.md"
BARE_METAL_DOC = REPO_ROOT / "infra" / "install" / "bare-metal" / "edge-amd64.md"
FULL_GUIDE = REPO_ROOT / "docs" / "full-installation-guide.md"
MAKEFILE = REPO_ROOT / "Makefile"


def test_packaging_docs_cover_eve_os_vm_and_bare_metal() -> None:
    packer = _read(PACKER)
    eve_readme = _read(EVE_README)
    bare_metal = _read(BARE_METAL_DOC)
    guide = _read(FULL_GUIDE)
    makefile = _read(MAKEFILE)

    assert "qemu" in packer
    assert "vezor_edge_image" in packer
    assert "vezor_runtime_profile" in packer
    assert "eve-vm-build-generic-amd64" in makefile
    assert "EVE-OS" in eve_readme
    assert "generic-amd64" in eve_readme
    assert "No EVE-OS OCI" in eve_readme
    assert "DeepStream" in eve_readme
    assert "Linux bare-metal amd64 edge" in bare_metal
    assert "vezor install edge --runtime-profile generic-amd64" in bare_metal
    assert "does not require EVE-OS" in bare_metal
    assert "DeepStream" in bare_metal
    assert "infra/install/eve-os/README.md" in guide
    assert "infra/install/bare-metal/edge-amd64.md" in guide


def test_eve_preseed_exists_for_debian_guest() -> None:
    preseed = _read(PRESEED)

    assert "Debian" in preseed
    assert "cloud-init" in preseed
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_eve_firstboot.py -q
```

Expected: FAIL because Packer, preseed, EVE-OS docs, bare-metal docs, Makefile, and full guide wiring are missing.

- [ ] **Step 3: Create Packer and preseed files**

Create `infra/install/eve-os/vm/packer.pkr.hcl`:

```hcl
packer {
  required_plugins {
    qemu = {
      version = ">= 1.1.0"
      source  = "github.com/hashicorp/qemu"
    }
  }
}

variable "vezor_edge_image" {
  type = string
}

variable "vezor_runtime_profile" {
  type    = string
  default = "generic-amd64"
}

source "qemu" "debian12" {
  vm_name          = "vezor-edge-amd64"
  output_directory = "output/vezor-edge-amd64"
  format           = "qcow2"
  accelerator      = "kvm"
  disk_size        = "20000M"
  headless         = true
  shutdown_command = "sudo shutdown -P now"
}

build {
  sources = ["source.qemu.debian12"]

  provisioner "file" {
    source      = "firstboot.sh"
    destination = "/tmp/vezor-eve-firstboot"
  }

  provisioner "file" {
    source      = "vezor-eve-bootstrap.service"
    destination = "/tmp/vezor-eve-bootstrap.service"
  }

  provisioner "shell" {
    inline = [
      "sudo install -d -m 0755 /etc/vezor /var/lib/vezor",
      "sudo install -m 0755 /tmp/vezor-eve-firstboot /usr/local/sbin/vezor-eve-firstboot",
      "sudo install -m 0644 /tmp/vezor-eve-bootstrap.service /etc/systemd/system/vezor-eve-bootstrap.service",
      "sudo systemctl enable vezor-eve-bootstrap.service",
      "echo VEZOR_RUNTIME_PROFILE=${var.vezor_runtime_profile} | sudo tee /etc/vezor/pairing.env >/dev/null",
      "sudo docker pull ${var.vezor_edge_image}",
      "sudo docker tag ${var.vezor_edge_image} vezor/edge-worker:preloaded"
    ]
  }
}
```

Create `infra/install/eve-os/vm/debian-preseed.cfg`:

```text
# Debian 12 preseed for Vezor EVE-OS edge VM.
# Installs a minimal Debian guest with cloud-init, Docker, and systemd.
d-i pkgsel/include string cloud-init docker.io
```

- [ ] **Step 4: Create bare-metal operator guide**

Create `infra/install/bare-metal/edge-amd64.md`:

````markdown
# Vezor Linux bare-metal amd64 edge

The Linux bare-metal amd64 edge path runs the normal Vezor edge
appliance directly on an amd64 Linux gateway. It uses systemd, Docker
Compose, NATS leaf, MediaMTX, and `vezor-supervisor`. It does not
require EVE-OS.

## Runtime Profiles

```bash
sudo /usr/local/bin/vezor install edge --runtime-profile generic-amd64
sudo /usr/local/bin/vezor install edge --runtime-profile nvidia-amd64
sudo /usr/local/bin/vezor install edge --runtime-profile intel-openvino-amd64
```

- `generic-amd64`: CPU baseline and default for amd64 gateways.
- `nvidia-amd64`: NVIDIA CUDA image after live NVIDIA evidence.
- `intel-openvino-amd64`: Intel OpenVINO image after live Intel evidence.

The installer must not infer NVIDIA or Intel images from inventory
alone. Operators select vendor profiles explicitly.

DeepStream is not implemented. Central Dockerized GPU and Apple
M-series acceleration are not claimed by this edge installer path.
````

- [ ] **Step 5: Create EVE-OS README**

Create `infra/install/eve-os/README.md`:

````markdown
# Vezor EVE-OS Edge VM

The EVE-OS artifact is a VM app, not an OCI container app. The VM runs
the normal Vezor edge appliance inside Debian 12 with Docker Compose,
systemd, NATS leaf, MediaMTX, and `vezor-supervisor`.

## Runtime Profiles

- `generic-amd64`: CPU baseline and default.
- `nvidia-amd64`: NVIDIA CUDA image after live NVIDIA evidence.
- `intel-openvino-amd64`: Intel OpenVINO image after live Intel evidence.

No EVE-OS OCI app artifact is provided. DeepStream is not implemented.
Central Dockerized GPU and Apple M-series acceleration are not claimed.

## Pairing Inputs

Provide these values through EVE-OS VM user-data or the generated
`/etc/vezor/pairing.env`:

```text
VEZOR_API_URL=https://MASTER_HOST:8000
VEZOR_SESSION_ID=REDACTED_SESSION_ID
VEZOR_PAIRING_CODE=REDACTED_PAIRING_CODE
VEZOR_RUNTIME_PROFILE=generic-amd64
```
````

- [ ] **Step 6: Add Make target and guide links**

Add to `Makefile`:

```make
eve-vm-build-generic-amd64: edge-generic-amd64-build
	cd infra/install/eve-os/vm && packer build \
	  -var vezor_runtime_profile=generic-amd64 \
	  -var vezor_edge_image=vezor/edge-worker:dev-generic-amd64 \
	  packer.pkr.hcl
```

Add a short section to `docs/full-installation-guide.md`:

```markdown
## Linux bare-metal amd64 edge

For amd64 Linux gateways installed directly on the host, see
`infra/install/bare-metal/edge-amd64.md`.

## EVE-OS Edge VM

For EVE-OS VM App Instance packaging, see
`infra/install/eve-os/README.md`. This path is separate from Jetson edge
installation and does not provide an EVE-OS OCI app artifact.
```

- [ ] **Step 7: Run tests**

Run:

```bash
./installer/.venv/bin/pytest installer/tests/test_eve_firstboot.py -q
git diff --check
```

Expected: PASS.

- [ ] **Step 8: Commit checkpoint if requested**

```bash
git add infra/install/eve-os/vm/packer.pkr.hcl infra/install/eve-os/vm/debian-preseed.cfg infra/install/eve-os/README.md infra/install/bare-metal/edge-amd64.md Makefile docs/full-installation-guide.md installer/tests/test_eve_firstboot.py
git commit -m "feat: add edge packaging docs"
```

---

### Task 8: Verification And Evidence Matrix

**Files:**
- Create: `docs/superpowers/status/YYYY-MM-DD-edge-amd64-bare-metal-evidence.md` when bare-metal smoke is run.
- Create: `docs/superpowers/status/YYYY-MM-DD-eve-os-vm-build-evidence.md` when VM build is run.
- Modify: plan checkboxes in this file as tasks complete.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
./backend/.venv/bin/pytest backend/tests/vision/test_runtime.py -q
./installer/.venv/bin/pytest installer/tests/test_edge_installer_artifacts.py installer/tests/test_eve_firstboot.py -q
bash -n installer/linux/install-edge.sh infra/install/eve-os/vm/firstboot.sh
rg -n "Linux bare-metal amd64 edge|infra/install/bare-metal/edge-amd64.md|infra/install/eve-os/README.md" \
  infra/install/bare-metal/edge-amd64.md infra/install/eve-os/README.md docs/full-installation-guide.md
git diff --check
```

Expected: all PASS.

- [ ] **Step 2: Run generic image build**

Run on an amd64-capable builder:

```bash
make edge-generic-amd64-build
docker run --rm vezor/edge-worker:dev-generic-amd64 /app/backend/.venv/bin/python -m argus.inference.engine --help
```

Expected: image build PASS and help command exits 0.

- [ ] **Step 3: Run generic VM build if KVM is available**

Run:

```bash
make eve-vm-build-generic-amd64
```

Expected: PASS on a KVM-capable host. If KVM is unavailable, record NOT RUN with reason in `docs/superpowers/status/YYYY-MM-DD-eve-os-vm-build-evidence.md`.

- [ ] **Step 4: Record vendor evidence status**

Create a status note with this structure:

```markdown
# Edge amd64 Image Matrix Evidence

Date: YYYY-MM-DD

| Gate | Status | Evidence |
|---|---|---|
| generic amd64 image build | PASS/FAIL/NOT RUN | command and exit summary |
| generic CPU smoke | PASS/FAIL/NOT RUN | command and exit summary |
| bare-metal amd64 installer evidence | PASS/FAIL/NOT RUN | command and exit summary |
| generic VM build | PASS/FAIL/NOT RUN | command and exit summary |
| NVIDIA amd64 CUDA evidence | PASS/FAIL/NOT RUN | hardware and command summary |
| Intel OpenVINO evidence | PASS/FAIL/NOT RUN | hardware and command summary |
| Jetson regression | PASS/FAIL/NOT RUN | rig and command summary |
```
```

- [ ] **Step 5: Final safety scan**

Run:

```bash
rg -n "DeepStream|central Dockerized GPU|M4|EVE-OS OCI|infra/install/eve-os/container|ARGUS_API_BEARER_TOKEN|Bearer |PAIRING_CODE=.*[A-Za-z0-9]" \
  docs infra installer backend/Dockerfile.edge.* Makefile
```

Expected: only intentional non-claim or redaction references. No actual secrets or raw credentials.

- [ ] **Step 6: Commit checkpoint if requested**

```bash
git add docs/superpowers/status/YYYY-MM-DD-edge-amd64-bare-metal-evidence.md docs/superpowers/status/YYYY-MM-DD-eve-os-vm-build-evidence.md docs/superpowers/plans/2026-06-13-edge-eve-os-and-bare-metal-image-matrix-implementation-plan.md
git commit -m "docs: capture edge amd64 evidence"
```
