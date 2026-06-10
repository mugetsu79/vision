# Jetson No-DeepStream And DeepStream Edge Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** First optimize the current no-DeepStream Jetson Python worker so the existing edge installer can use NVIDIA media/inference acceleration where available, then add an optional Jetson DeepStream edge installer/runtime family that deploys Ultralytics YOLO fixed-vocabulary models through NVIDIA Metropolis / DeepStream.

**Architecture:** Keep `python` as the default edge runtime family. Add a `media_acceleration` policy inside that family (`auto`, `jetson-hw`, `software`) and make runtime reports expose the actual media and inference path. Add `deepstream` later as an explicit installer/runtime family. DeepStream scenes use a `deepstream_bundle` runtime artifact, a DeepStream-specific edge image, generated `nvinfer`/pipeline configs, a native YOLO parser library, and a Vezor bridge that publishes the same detections/history/evidence/billing signals as the current worker.

**Tech Stack:** Bash installer, Pydantic manifest models, Docker/Compose/systemd, NVIDIA DeepStream 7.1 `deepstream-l4t`, GStreamer, `nvinfer`, TensorRT, C++ custom parser library, Python bridge/orchestration, FastAPI/Pydantic contracts, React/TypeScript UI, pytest/vitest, real Jetson smoke.

---

## File Map

- Modify `backend/src/argus/vision/camera.py`: make Jetson native/software/FFmpeg capture selection deterministic and truthfully reported.
- Modify `backend/src/argus/vision/stream_publisher.py` or the current processed-stream publisher module: prefer Jetson hardware H.264 encode when available.
- Modify `backend/src/argus/inference/engine.py`: pass selected media pipeline and encoder mode into runtime reports.
- Modify `backend/src/argus/supervisor/hardware_probe.py` or equivalent probe module: report NVIDIA media plugins, TensorRT/CUDA providers, and central provider capabilities.
- Modify `backend/src/argus/services/supervisor_operations.py`: persist/report runtime media pipeline, encoder mode, selected provider, runtime artifact id, scene contract hash, and heartbeat freshness.
- Modify `frontend/src/components/cameras/CameraWizard.tsx`: scope runtime-artifact display by scene target/profile so central Mac scenes do not show a Jetson TensorRT artifact as their effective runtime.
- Modify `docs/core-link-performance-guide.md`: document the installed `.bin` throughput fixture and installation-time link sample.
- Modify `installer/vezor_installer/manifest.py`: add runtime-family and DeepStream compatibility manifest schema.
- Modify `installer/manifests/dev-example.json`: add `edge-worker-deepstream` image and DeepStream compatibility metadata.
- Modify `installer/linux/install-edge.sh`: add `--runtime-family`, DeepStream compatibility preflight, image/Dockerfile selection, and config persistence.
- Create `backend/Dockerfile.edge.deepstream`: cache-friendly DeepStream worker image.
- Create `backend/deepstream/yolo_parser/Makefile`: parser build entrypoint.
- Create `backend/deepstream/yolo_parser/nvdsinfer_custom_impl_vezor_yolo.cpp`: Vezor YOLO parser shared library.
- Create `backend/deepstream/templates/nvinfer_primary.txt`: generated `nvinfer` template.
- Create `backend/deepstream/templates/deepstream_app.txt`: generated single-scene pipeline template.
- Create `backend/src/argus/vision/deepstream_bundle.py`: build/render/validate DeepStream bundle metadata.
- Modify `backend/src/argus/models/enums.py`: add `RuntimeArtifactKind.DEEPSTREAM_BUNDLE`.
- Create `backend/src/argus/migrations/versions/0031_deepstream_runtime_artifact_kind.py`: database enum migration.
- Modify `backend/src/argus/api/contracts.py`: add `deepstream_tensorrt` runtime backend.
- Modify `backend/src/argus/vision/runtime_selection.py`: prefer and validate DeepStream artifacts when requested.
- Modify `backend/src/argus/services/app.py`: include DeepStream artifact paths in worker config and scene readiness.
- Create `backend/src/argus/inference/deepstream_bridge.py`: edge-side process that renders configs, launches DeepStream runner, and forwards normalized output.
- Modify `backend/src/argus/supervisor/process_adapter.py`: route worker launch by runtime family.
- Modify `backend/src/argus/supervisor/runner.py`: persist/report DeepStream runtime family and hardware capability.
- Modify `scripts/jetson-preflight.sh`: detect DeepStream version/plugins/container runtime.
- Modify `frontend/src/lib/api.generated.ts` and `frontend/src/lib/openapi.json`: regenerate OpenAPI after backend contract changes.
- Modify `frontend/src/components/cameras/CameraWizard.tsx`: show DeepStream runtime readiness reasons.
- Modify `frontend/src/pages/Models.tsx`: show/build DeepStream bundle artifacts.
- Modify `docs/model-loading-and-configuration-guide.md`: document DeepStream runtime lane.
- Modify `docs/product-installer-and-first-run-guide.md`: document `--runtime-family deepstream`.
- Modify `docs/operator-deployment-playbook.md`: document DeepStream live smoke and service evidence.

## Preflight Fixes Already Applied In Current Session

These fixes unblock the supervised central-worker poll path before performance work starts:

- `backend/src/argus/services/app.py` now promotes a central camera to `WorkerDesiredState.SUPERVISED` when operations mode resolves to `central_supervisor` and supervisor mode is enabled.
- `backend/tests/services/test_operations_service.py` asserts the central-supervisor fleet row is supervised, not manual.
- `backend/tests/supervisor/test_runner.py` asserts a running central worker without an assignment row still refreshes runtime reports.

Next implementation should preserve these invariants while changing media/inference performance.

## Task 0: No-DeepStream Jetson Python Runtime Optimization

**Files:**
- Modify: `backend/tests/vision/test_camera_capture.py` or nearest existing camera pipeline tests
- Modify: `backend/tests/vision/test_stream_publisher.py` or nearest existing processed-stream publisher tests
- Modify: `backend/tests/supervisor/test_hardware_probe.py`
- Modify: `backend/tests/supervisor/test_runner.py`
- Modify: `backend/src/argus/vision/camera.py`
- Modify: current processed-stream publisher module
- Modify: hardware probe module
- Modify: runtime report contracts/services as needed

- [ ] **Step 1: Write failing Jetson media pipeline tests**

Cover these cases:

```python
def test_jetson_rtsp_capture_prefers_nvv4l2decoder_and_nvvidconv_when_available() -> None:
    ...


def test_jetson_rtsp_capture_labels_software_gstreamer_fallback_truthfully() -> None:
    ...


def test_jetson_processed_stream_prefers_nvv4l2h264enc_when_available() -> None:
    ...
```

Expected initial state: at least the fallback-label test fails because current logs can report a software fallback as native.

- [ ] **Step 2: Add runtime-report contract tests**

Runtime reports must include or derive these fields without exposing secrets:

- selected inference provider
- runtime artifact id
- scene contract hash
- media pipeline mode: `jetson_gstreamer_native`, `jetson_gstreamer_software`, or `ffmpeg_software`
- encoder mode: `hardware` or `software`
- heartbeat timestamp refreshed by the supervisor poll loop

- [ ] **Step 3: Implement deterministic Jetson media selection**

In the current camera capture module:

- Probe `nvv4l2decoder`, `nvvidconv`, and `nvv4l2h264enc` inside the running container.
- Prefer the native Jetson GStreamer path for RTSP/H.264.
- Resize in the NVIDIA media path before frames enter Python when the scene profile requests lower resolution.
- Fall back to software GStreamer only when native path fails to produce a first frame.
- Fall back to FFmpeg only when both GStreamer paths fail.
- Emit distinct runtime diagnostics for each path. Do not log raw RTSP credentials.

- [ ] **Step 4: Implement hardware processed-stream encode**

Use `nvv4l2h264enc` for processed browser renditions when available. If it is missing or fails first-frame smoke, fall back to software encode and report that fallback.

- [ ] **Step 5: Add the Core Link installation throughput fixture**

Create a local `.bin` fixture during edge installation, store it under the edge appliance data directory, and run one manual-trigger-compatible throughput sample at install time. Core Link UI/API must display a meaningful measured Mbps value after the first install sample instead of `0 Mbps` when the link has actually been tested.

- [ ] **Step 6: Run local tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision backend/tests/supervisor -q
```

- [ ] **Step 7: Run Jetson live performance smoke**

Before and after the optimization, capture:

- `docker stats --no-stream` for edge containers
- sanitized `docker top vezor-supervisor -eo pid,ppid,pcpu,pmem,rss,etime,comm`
- `tegrastats`
- worker runtime report payloads
- processed stream availability
- detections/history/evidence/billing usage

PASS requires real RTSP frames, TensorRT artifact selected, hardware decode active, runtime reports heartbeating after restart, and measurable CPU reduction. Provider availability alone is not a pass.

## Task 1: Central Runtime Target Scoping And Mac Acceleration Design

**Files:**
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: backend runtime summary/model option tests
- Modify: docs/model-loading-and-configuration-guide.md
- Modify: docs/operator-deployment-playbook.md

- [ ] **Step 1: Write failing UI/runtime summary test**

Central scenes running in Docker on a MacBook Pro M4 must not show a Jetson TensorRT artifact as the effective runtime. Shared model records may still list that artifact in model management, but scene setup must filter by scene target profile and selected node.

- [ ] **Step 2: Fix runtime artifact display scoping**

Filter runtime artifact summaries by:

- processing mode
- assigned node id
- target profile
- selected backend/provider

For central Docker mode on M4, display the ONNX Runtime CPU provider honestly unless a native macOS/CoreML worker package has reported CoreML capability.

- [ ] **Step 3: Document native central acceleration lane**

Add a future `central-native-macos` lane that probes `CoreMLExecutionProvider` outside Docker. Mark this NOT RUN until a native supervisor/worker package is implemented and live-smoked.

## Task 2: Manifest Contract For DeepStream Runtime Family

**Files:**
- Modify: `installer/tests/test_manifest.py`
- Modify: `installer/vezor_installer/manifest.py`
- Modify: `installer/manifests/dev-example.json`

- [ ] **Step 1: Write failing manifest tests**

Add these tests to `installer/tests/test_manifest.py`:

```python
def test_manifest_parses_deepstream_runtime_family_metadata() -> None:
    payload = _base_manifest_payload()
    payload["images"]["edge-worker-deepstream"] = {
        "reference": "ghcr.io/vezor/edge-worker-deepstream@sha256:" + "5" * 64
    }
    payload["deepstream"] = {
        "supported_l4t": [
            {
                "l4t": "36.4",
                "jetpack": "6.1",
                "deepstream": "7.1",
                "base_image": "nvcr.io/nvidia/deepstream-l4t:7.1",
            }
        ],
        "candidate_l4t": [
            {
                "l4t": "36.5",
                "jetpack": "6.2",
                "deepstream": "7.1",
                "requires_accept_flag": True,
            }
        ],
    }

    manifest = Manifest.model_validate(payload)

    assert manifest.deepstream is not None
    assert manifest.deepstream.supported_l4t[0].l4t == "36.4"
    assert manifest.deepstream.candidate_l4t[0].requires_accept_flag is True
    assert "edge-worker-deepstream" in manifest.image_names


def test_manifest_rejects_deepstream_metadata_without_deepstream_image() -> None:
    payload = _base_manifest_payload()
    payload["deepstream"] = {
        "supported_l4t": [
            {
                "l4t": "36.4",
                "jetpack": "6.1",
                "deepstream": "7.1",
                "base_image": "nvcr.io/nvidia/deepstream-l4t:7.1",
            }
        ]
    }

    with pytest.raises(ValueError, match="edge-worker-deepstream"):
        Manifest.model_validate(payload)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --project installer pytest installer/tests/test_manifest.py -q
```

Expected: failure because `Manifest` has no `deepstream` field and no image validation.

- [ ] **Step 3: Add manifest models**

Add these types to `installer/vezor_installer/manifest.py`:

```python
RuntimeFamily = Literal["python", "deepstream"]


class DeepStreamL4TSupport(BaseModel):
    model_config = ConfigDict(frozen=True)

    l4t: str = Field(min_length=1)
    jetpack: str = Field(min_length=1)
    deepstream: str = Field(min_length=1)
    base_image: str | None = Field(default=None, min_length=1)
    requires_accept_flag: bool = False


class DeepStreamConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    supported_l4t: list[DeepStreamL4TSupport] = Field(default_factory=list)
    candidate_l4t: list[DeepStreamL4TSupport] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_deepstream_entries(self) -> Self:
        if not self.supported_l4t and not self.candidate_l4t:
            raise ValueError("deepstream requires supported_l4t or candidate_l4t")
        for entry in self.supported_l4t:
            if entry.requires_accept_flag:
                raise ValueError("supported_l4t entries must not require accept flag")
        return self
```

Add the field and validation to `Manifest`:

```python
    deepstream: DeepStreamConfig | None = None
```

Inside `validate_product_manifest`, after release-channel validation:

```python
        if self.deepstream is not None and "edge-worker-deepstream" not in self.images:
            raise ValueError(
                "deepstream metadata requires an edge-worker-deepstream image"
            )
```

- [ ] **Step 4: Add dev manifest metadata**

Add this to `installer/manifests/dev-example.json`:

```json
    "edge-worker-deepstream": {
      "reference": "vezor/edge-worker-deepstream:portable-demo"
    }
```

Add the top-level DeepStream block:

```json
  "deepstream": {
    "supported_l4t": [
      {
        "l4t": "36.4",
        "jetpack": "6.1",
        "deepstream": "7.1",
        "base_image": "nvcr.io/nvidia/deepstream-l4t:7.1"
      }
    ],
    "candidate_l4t": [
      {
        "l4t": "36.5",
        "jetpack": "6.2",
        "deepstream": "7.1",
        "requires_accept_flag": true
      }
    ]
  }
```

- [ ] **Step 5: Run manifest tests**

Run:

```bash
uv run --project installer pytest installer/tests/test_manifest.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit manifest contract**

```bash
git add installer/vezor_installer/manifest.py installer/manifests/dev-example.json installer/tests/test_manifest.py
git commit -m "feat: add deepstream manifest contract"
```

## Task 3: Edge Installer Runtime-Family Switch

**Files:**
- Modify: `installer/tests/test_edge_installer_artifacts.py`
- Modify: `installer/linux/install-edge.sh`

- [ ] **Step 1: Write failing installer tests**

Add to `installer/tests/test_edge_installer_artifacts.py`:

```python
def test_edge_install_script_accepts_deepstream_runtime_family() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "--runtime-family" in script
    assert "EDGE_RUNTIME_FAMILY" in script
    assert "python|deepstream" in script
    assert "edge-worker-deepstream" in script
    assert "Dockerfile.edge.deepstream" in script
    assert "VEZOR_EDGE_RUNTIME_FAMILY" in script


def test_edge_install_script_requires_candidate_flag_for_candidate_deepstream_l4t() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "--accept-candidate-deepstream-l4t" in script
    assert "ACCEPT_CANDIDATE_DEEPSTREAM_L4T" in script
    assert "validate_deepstream_l4t_support" in script
    assert "candidate DeepStream L4T" in script
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --project installer pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: failure because the installer does not expose DeepStream runtime selection.

- [ ] **Step 3: Add CLI variables and help**

Add near the top of `installer/linux/install-edge.sh`:

```bash
EDGE_RUNTIME_FAMILY="${VEZOR_EDGE_RUNTIME_FAMILY:-python}"
ACCEPT_CANDIDATE_DEEPSTREAM_L4T=0
```

Add to `usage()`:

```text
  --runtime-family python|deepstream
                         Edge worker runtime family. Default: python.
  --accept-candidate-deepstream-l4t
                         Allow candidate DeepStream/L4T combinations after explicit operator approval.
```

- [ ] **Step 4: Parse the new flags**

Add cases to the argument parser:

```bash
    --runtime-family)
      EDGE_RUNTIME_FAMILY="${2:?--runtime-family requires a value}"
      case "$EDGE_RUNTIME_FAMILY" in
        python|deepstream) ;;
        *) echo "--runtime-family must be python|deepstream" >&2; exit 2 ;;
      esac
      shift 2
      ;;
    --accept-candidate-deepstream-l4t)
      ACCEPT_CANDIDATE_DEEPSTREAM_L4T=1
      shift
      ;;
```

- [ ] **Step 5: Add DeepStream manifest lookup**

Add a function after `manifest_release_channel()`:

```bash
validate_deepstream_l4t_support() {
  if [[ "$EDGE_RUNTIME_FAMILY" != "deepstream" ]]; then
    return 0
  fi
  if [[ -z "$MANIFEST" ]]; then
    echo "DeepStream runtime requires a manifest with deepstream compatibility metadata." >&2
    exit 2
  fi
  if [[ -z "$JETSON_PREFLIGHT_JSON" || ! -s "$JETSON_PREFLIGHT_JSON" ]]; then
    echo "DeepStream runtime requires Jetson preflight JSON." >&2
    exit 2
  fi

  python3 - "$MANIFEST" "$JETSON_PREFLIGHT_JSON" "$ACCEPT_CANDIDATE_DEEPSTREAM_L4T" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
preflight = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
accept_candidate = sys.argv[3] == "1"
l4t = str(preflight.get("l4t_release") or preflight.get("l4t") or "")
deepstream = manifest.get("deepstream") or {}

supported = {str(entry.get("l4t")) for entry in deepstream.get("supported_l4t", [])}
candidate = {str(entry.get("l4t")) for entry in deepstream.get("candidate_l4t", [])}
if l4t in supported:
    raise SystemExit(0)
if l4t in candidate and accept_candidate:
    raise SystemExit(0)
if l4t in candidate:
    raise SystemExit(
        "This Jetson is on a candidate DeepStream L4T combination. "
        "Pass --accept-candidate-deepstream-l4t only after recording operator approval."
    )
raise SystemExit(f"DeepStream runtime is not supported for this Jetson L4T release: {l4t}")
PY
}
```

- [ ] **Step 6: Select the correct image and Dockerfile**

Replace the `EDGE_WORKER_IMAGE` assignment with:

```bash
EDGE_WORKER_IMAGE_KEY="edge-worker"
EDGE_DOCKERFILE="/opt/vezor/current/backend/Dockerfile.edge"
if [[ "$EDGE_RUNTIME_FAMILY" == "deepstream" ]]; then
  EDGE_WORKER_IMAGE_KEY="edge-worker-deepstream"
  EDGE_DOCKERFILE="/opt/vezor/current/backend/Dockerfile.edge.deepstream"
fi
EDGE_WORKER_IMAGE="$(manifest_image_ref "$EDGE_WORKER_IMAGE_KEY" vezor/edge-worker:portable-demo)"
```

Change the Docker build line in `build_local_edge_image()` to:

```bash
    -f "$EDGE_DOCKERFILE" \
```

Call `validate_deepstream_l4t_support` immediately after the preflight JSON is written and before `build_local_edge_image`.

- [ ] **Step 7: Persist runtime family**

Add the runtime family into generated edge/supervisor config JSON and environment:

```bash
"runtime_family": "$EDGE_RUNTIME_FAMILY",
```

Add:

```bash
VEZOR_EDGE_RUNTIME_FAMILY=$EDGE_RUNTIME_FAMILY
```

to the generated edge env file.

- [ ] **Step 8: Run installer syntax and tests**

Run:

```bash
bash -n installer/linux/install-edge.sh
uv run --project installer pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit installer switch**

```bash
git add installer/linux/install-edge.sh installer/tests/test_edge_installer_artifacts.py
git commit -m "feat: add edge runtime family installer switch"
```

## Task 4: DeepStream Edge Image And Parser Build

**Files:**
- Create: `backend/tests/core/test_deepstream_dockerfile.py`
- Create: `backend/Dockerfile.edge.deepstream`
- Create: `backend/deepstream/yolo_parser/Makefile`
- Create: `backend/deepstream/yolo_parser/nvdsinfer_custom_impl_vezor_yolo.cpp`
- Create: `backend/deepstream/templates/nvinfer_primary.txt`
- Create: `backend/deepstream/templates/deepstream_app.txt`

- [ ] **Step 1: Write failing Dockerfile tests**

Create `backend/tests/core/test_deepstream_dockerfile.py`:

```python
from pathlib import Path


DOCKERFILE = Path(__file__).resolve().parents[2] / "Dockerfile.edge.deepstream"


def _read() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def test_deepstream_dockerfile_uses_deepstream_l4t_base() -> None:
    dockerfile = _read()

    assert "ARG DEEPSTREAM_BASE_IMAGE=nvcr.io/nvidia/deepstream-l4t:7.1" in dockerfile
    assert "FROM ${DEEPSTREAM_BASE_IMAGE}" in dockerfile


def test_deepstream_dockerfile_installs_multimedia_deps_and_builds_parser_before_source_copy() -> None:
    dockerfile = _read()

    assert "/opt/nvidia/deepstream/deepstream/user_additional_install.sh" in dockerfile
    assert "COPY deepstream ./deepstream" in dockerfile
    assert "make -C /app/deepstream/yolo_parser" in dockerfile
    assert dockerfile.index("COPY pyproject.toml") < dockerfile.index("COPY src ./src")
    assert dockerfile.index("COPY deepstream ./deepstream") < dockerfile.index("COPY src ./src")


def test_deepstream_dockerfile_uses_bridge_entrypoint() -> None:
    dockerfile = _read()

    assert 'ENTRYPOINT ["/app/.venv/bin/python", "-m", "argus.inference.deepstream_bridge"]' in dockerfile
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --project backend pytest backend/tests/core/test_deepstream_dockerfile.py -q
```

Expected: failure because the Dockerfile does not exist.

- [ ] **Step 3: Add DeepStream Dockerfile**

Create `backend/Dockerfile.edge.deepstream`:

```dockerfile
ARG DEEPSTREAM_BASE_IMAGE=nvcr.io/nvidia/deepstream-l4t:7.1
FROM ${DEEPSTREAM_BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONPATH=/app/src \
    VEZOR_EDGE_RUNTIME_FAMILY=deepstream

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        pkg-config \
        curl \
        ca-certificates \
        libglib2.0-dev \
        libjson-glib-dev \
        gstreamer1.0-tools \
    && /opt/nvidia/deepstream/deepstream/user_additional_install.sh \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock alembic.ini README.md requirements-edge.txt ./

RUN python3 -m pip install --no-cache-dir uv \
    && python3 -m venv --system-site-packages "$UV_PROJECT_ENVIRONMENT" \
    && uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" --no-cache -r requirements-edge.txt

COPY deepstream ./deepstream
RUN make -C /app/deepstream/yolo_parser \
    && install -Dm755 /app/deepstream/yolo_parser/libnvdsinfer_custom_impl_vezor_yolo.so \
        /opt/vezor/deepstream/lib/libnvdsinfer_custom_impl_vezor_yolo.so

COPY src ./src
RUN groupadd --system --gid 10001 argus \
    && useradd --system --uid 10001 --gid 10001 --create-home argus \
    && mkdir -p /var/lib/vezor/runtime/deepstream \
    && chown -R argus:argus /app /opt/vezor /var/lib/vezor

USER argus

ENTRYPOINT ["/app/.venv/bin/python", "-m", "argus.inference.deepstream_bridge"]
```

- [ ] **Step 4: Add parser build skeleton**

Create `backend/deepstream/yolo_parser/Makefile`:

```makefile
NVDS_VERSION ?= 7.1
DEEPSTREAM_ROOT ?= /opt/nvidia/deepstream/deepstream
CXX ?= g++
CXXFLAGS += -std=c++17 -Wall -Wextra -fPIC \
	-I$(DEEPSTREAM_ROOT)/sources/includes \
	-I/usr/local/cuda/include
LDFLAGS += -shared
TARGET := libnvdsinfer_custom_impl_vezor_yolo.so
SOURCES := nvdsinfer_custom_impl_vezor_yolo.cpp

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $^

clean:
	rm -f $(TARGET)
.PHONY: all clean
```

Create `backend/deepstream/yolo_parser/nvdsinfer_custom_impl_vezor_yolo.cpp`:

```cpp
#include "nvdsinfer_custom_impl.h"

#include <algorithm>
#include <cstring>
#include <vector>

extern "C" bool NvDsInferParseVezorYolo(
    std::vector<NvDsInferLayerInfo> const& outputLayersInfo,
    NvDsInferNetworkInfo const& networkInfo,
    NvDsInferParseDetectionParams const& detectionParams,
    std::vector<NvDsInferObjectDetectionInfo>& objectList) {
  (void)outputLayersInfo;
  (void)networkInfo;
  (void)detectionParams;
  objectList.clear();
  return true;
}

CHECK_CUSTOM_PARSE_FUNC_PROTOTYPE(NvDsInferParseVezorYolo);
```

The first parser intentionally compiles and returns no objects. Task 11 replaces this with a tested parser implementation against recorded YOLO tensors before live smoke.

- [ ] **Step 5: Add DeepStream templates**

Create `backend/deepstream/templates/nvinfer_primary.txt`:

```ini
[property]
gpu-id=0
network-type=0
process-mode=1
batch-size=1
model-engine-file={{ model_engine_file }}
labelfile-path={{ labels_file }}
custom-lib-path={{ parser_library }}
parse-bbox-func-name=NvDsInferParseVezorYolo
num-detected-classes={{ class_count }}
interval=0
gie-unique-id=1
maintain-aspect-ratio=1
symmetric-padding=1
```

Create `backend/deepstream/templates/deepstream_app.txt`:

```ini
[application]
enable-perf-measurement=1
perf-measurement-interval-sec=5

[source0]
enable=1
type=4
uri={{ redacted_source_uri }}
latency=200

[streammux]
batch-size=1
width={{ stream_width }}
height={{ stream_height }}
live-source=1
batched-push-timeout=40000

[primary-gie]
enable=1
config-file={{ nvinfer_config_file }}

[tracker]
enable=1
tracker-width=640
tracker-height=384
ll-lib-file=/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so

[osd]
enable=1

[sink0]
enable=1
type=6
msg-conv-payload-type=0
```

- [ ] **Step 6: Run Dockerfile tests**

Run:

```bash
uv run --project backend pytest backend/tests/core/test_deepstream_dockerfile.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit image scaffold**

```bash
git add backend/Dockerfile.edge.deepstream backend/deepstream backend/tests/core/test_deepstream_dockerfile.py
git commit -m "feat: scaffold deepstream edge image"
```

## Task 5: DeepStream Runtime Artifact Schema

**Files:**
- Modify: `backend/tests/vision/test_runtime_selection.py`
- Modify: `backend/tests/services/test_runtime_artifacts.py`
- Modify: `backend/src/argus/models/enums.py`
- Create: `backend/src/argus/migrations/versions/0031_deepstream_runtime_artifact_kind.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/vision/runtime_selection.py`

- [ ] **Step 1: Write failing runtime selection tests**

Add to `backend/tests/vision/test_runtime_selection.py`:

```python
def test_selects_deepstream_bundle_when_preferred_backend_matches_target() -> None:
    model = _model(backend="onnxruntime")
    artifact = _artifact(
        kind=RuntimeArtifactKind.DEEPSTREAM_BUNDLE,
        runtime_backend="deepstream_tensorrt",
        target_profile="linux-aarch64-nvidia-jetson",
    )
    profile = _runtime_profile(
        preferred_backend="deepstream_tensorrt",
        artifact_preference="tensorrt_first",
        fallback_allowed=False,
    )

    selection = select_runtime_artifact(
        model=model,
        host_profile="linux-aarch64-nvidia-jetson",
        artifacts=[artifact],
        runtime_vocabulary_hash=None,
        runtime_profile=profile,
    )

    assert selection.selected_backend == "deepstream_tensorrt"
    assert selection.artifact is artifact
    assert selection.fallback is False
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --project backend pytest backend/tests/vision/test_runtime_selection.py -q
```

Expected: failure because `DEEPSTREAM_BUNDLE` does not exist and preference ordering does not include DeepStream.

- [ ] **Step 3: Add enum and migration**

Add to `RuntimeArtifactKind` in `backend/src/argus/models/enums.py`:

```python
    DEEPSTREAM_BUNDLE = "deepstream_bundle"
```

Create `backend/src/argus/migrations/versions/0031_deepstream_runtime_artifact_kind.py`:

```python
"""add deepstream runtime artifact kind

Revision ID: 0031_deepstream_runtime_artifact_kind
Revises: 0030_platform_superadmin_bootstrap
Create Date: 2026-06-10 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0031_deepstream_runtime_artifact_kind"
down_revision = "0030_platform_superadmin_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE runtime_artifact_kind_enum ADD VALUE IF NOT EXISTS 'deepstream_bundle'"
    )


def downgrade() -> None:
    # PostgreSQL enum value removal is intentionally not attempted.
    pass
```

If the current migration head is not `0030_platform_superadmin_bootstrap`, set `down_revision` to the actual head found with:

```bash
uv run --project backend alembic heads
```

- [ ] **Step 4: Add backend contract literal**

In `backend/src/argus/api/contracts.py`, extend runtime backend literals to include:

```python
"deepstream_tensorrt"
```

in every `RuntimeBackend` / `runtime_backend` literal list.

- [ ] **Step 5: Update artifact preference ordering**

In `backend/src/argus/vision/runtime_selection.py`, change `_preferred_artifact_kinds` to return a tuple that includes DeepStream when the preferred backend requests it:

```python
def _preferred_artifact_kinds(
    artifact_preference: RuntimeArtifactPreference,
) -> tuple[RuntimeArtifactKind, ...]:
    if artifact_preference == "onnx_first":
        return (
            RuntimeArtifactKind.ONNX_EXPORT,
            RuntimeArtifactKind.TENSORRT_ENGINE,
            RuntimeArtifactKind.DEEPSTREAM_BUNDLE,
        )
    return (
        RuntimeArtifactKind.DEEPSTREAM_BUNDLE,
        RuntimeArtifactKind.TENSORRT_ENGINE,
        RuntimeArtifactKind.ONNX_EXPORT,
    )
```

Then update `_first_kind` call sites for the wider tuple type.

- [ ] **Step 6: Run runtime tests**

Run:

```bash
uv run --project backend pytest backend/tests/vision/test_runtime_selection.py backend/tests/services/test_runtime_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit runtime schema**

```bash
git add backend/src/argus/models/enums.py backend/src/argus/migrations/versions/0031_deepstream_runtime_artifact_kind.py backend/src/argus/api/contracts.py backend/src/argus/vision/runtime_selection.py backend/tests/vision/test_runtime_selection.py backend/tests/services/test_runtime_artifacts.py
git commit -m "feat: add deepstream runtime artifact kind"
```

## Task 6: DeepStream Bundle Renderer

**Files:**
- Create: `backend/tests/vision/test_deepstream_bundle.py`
- Create: `backend/src/argus/vision/deepstream_bundle.py`

- [ ] **Step 1: Write failing bundle tests**

Create `backend/tests/vision/test_deepstream_bundle.py`:

```python
from pathlib import Path
from uuid import uuid4

from argus.vision.deepstream_bundle import (
    DeepStreamBundleInput,
    render_deepstream_bundle,
)


def test_render_deepstream_bundle_writes_manifest_and_redacts_rtsp(tmp_path: Path) -> None:
    secret_user = "sample_user"
    secret_password = "sample_password"
    bundle = render_deepstream_bundle(
        DeepStreamBundleInput(
            artifact_id=uuid4(),
            model_id=uuid4(),
            model_name="YOLO26n COCO",
            source_model_sha256="a" * 64,
            target_profile="linux-aarch64-nvidia-jetson",
            deepstream_version="7.1",
            tensorrt_version="10.3",
            precision="fp16",
            input_shape=[1, 3, 640, 640],
            classes=["person", "car"],
            engine_path=tmp_path / "model.engine",
            parser_library_path=Path("/opt/vezor/deepstream/lib/libnvdsinfer_custom_impl_vezor_yolo.so"),
            output_dir=tmp_path / "bundle",
            source_uri=f"{'rtsp'}://{secret_user}:{secret_password}@example.local:8554/path",
            stream_width=1280,
            stream_height=720,
        )
    )

    manifest = (bundle.output_dir / "manifest.json").read_text(encoding="utf-8")
    nvinfer = (bundle.output_dir / "nvinfer_primary.txt").read_text(encoding="utf-8")
    app_config = (bundle.output_dir / "deepstream_app.txt").read_text(encoding="utf-8")

    assert bundle.runtime_backend == "deepstream_tensorrt"
    assert "deepstream_bundle" in manifest
    assert f"{secret_user}:{secret_password}" not in manifest
    assert f"{secret_user}:{secret_password}" not in nvinfer
    assert f"{secret_user}:{secret_password}" not in app_config
    assert "rtsp://***:***@example.local:8554/path" in app_config
    assert "NvDsInferParseVezorYolo" in nvinfer
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --project backend pytest backend/tests/vision/test_deepstream_bundle.py -q
```

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement bundle renderer**

Create `backend/src/argus/vision/deepstream_bundle.py`:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DeepStreamBundleInput:
    artifact_id: UUID
    model_id: UUID
    model_name: str
    source_model_sha256: str
    target_profile: str
    deepstream_version: str
    tensorrt_version: str
    precision: str
    input_shape: list[int]
    classes: list[str]
    engine_path: Path
    parser_library_path: Path
    output_dir: Path
    source_uri: str
    stream_width: int
    stream_height: int


@dataclass(frozen=True, slots=True)
class DeepStreamBundle:
    output_dir: Path
    manifest_path: Path
    nvinfer_config_path: Path
    app_config_path: Path
    labels_path: Path
    runtime_backend: str = "deepstream_tensorrt"


def render_deepstream_bundle(input: DeepStreamBundleInput) -> DeepStreamBundle:
    output_dir = input.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    labels_path = output_dir / "labels.txt"
    nvinfer_path = output_dir / "nvinfer_primary.txt"
    app_path = output_dir / "deepstream_app.txt"
    manifest_path = output_dir / "manifest.json"

    labels_path.write_text("\n".join(input.classes) + "\n", encoding="utf-8")
    class_hash = hashlib.sha256(labels_path.read_bytes()).hexdigest()

    nvinfer_path.write_text(
        _render_nvinfer(input=input, labels_path=labels_path),
        encoding="utf-8",
    )
    app_path.write_text(
        _render_app(input=input, nvinfer_path=nvinfer_path),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "deepstream_bundle",
                "runtime_backend": "deepstream_tensorrt",
                "artifact_id": str(input.artifact_id),
                "model_id": str(input.model_id),
                "model_name": input.model_name,
                "source_model_sha256": input.source_model_sha256,
                "target_profile": input.target_profile,
                "deepstream_version": input.deepstream_version,
                "tensorrt_version": input.tensorrt_version,
                "precision": input.precision,
                "input_shape": input.input_shape,
                "class_count": len(input.classes),
                "class_hash": class_hash,
                "parser_symbol": "NvDsInferParseVezorYolo",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return DeepStreamBundle(
        output_dir=output_dir,
        manifest_path=manifest_path,
        nvinfer_config_path=nvinfer_path,
        app_config_path=app_path,
        labels_path=labels_path,
    )


def _render_nvinfer(*, input: DeepStreamBundleInput, labels_path: Path) -> str:
    return "\n".join(
        [
            "[property]",
            "gpu-id=0",
            "network-type=0",
            "process-mode=1",
            "batch-size=1",
            f"model-engine-file={input.engine_path}",
            f"labelfile-path={labels_path}",
            f"custom-lib-path={input.parser_library_path}",
            "parse-bbox-func-name=NvDsInferParseVezorYolo",
            f"num-detected-classes={len(input.classes)}",
            "interval=0",
            "gie-unique-id=1",
            "maintain-aspect-ratio=1",
            "symmetric-padding=1",
            "",
        ]
    )


def _render_app(*, input: DeepStreamBundleInput, nvinfer_path: Path) -> str:
    return "\n".join(
        [
            "[application]",
            "enable-perf-measurement=1",
            "perf-measurement-interval-sec=5",
            "",
            "[source0]",
            "enable=1",
            "type=4",
            f"uri={_redact_uri(input.source_uri)}",
            "latency=200",
            "",
            "[streammux]",
            "batch-size=1",
            f"width={input.stream_width}",
            f"height={input.stream_height}",
            "live-source=1",
            "batched-push-timeout=40000",
            "",
            "[primary-gie]",
            "enable=1",
            f"config-file={nvinfer_path}",
            "",
        ]
    )


def _redact_uri(uri: str) -> str:
    parsed = urlsplit(uri)
    if parsed.username is None and parsed.password is None:
        return uri
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, f"***:***@{host}", parsed.path, parsed.query, parsed.fragment))
```

- [ ] **Step 4: Run bundle tests**

Run:

```bash
uv run --project backend pytest backend/tests/vision/test_deepstream_bundle.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit bundle renderer**

```bash
git add backend/src/argus/vision/deepstream_bundle.py backend/tests/vision/test_deepstream_bundle.py
git commit -m "feat: render deepstream runtime bundles"
```

## Task 7: Worker Launcher Runtime Family Routing

**Files:**
- Modify: `backend/tests/supervisor/test_process_adapter.py`
- Modify: `backend/src/argus/supervisor/process_adapter.py`
- Create: `backend/tests/inference/test_deepstream_bridge.py`
- Create: `backend/src/argus/inference/deepstream_bridge.py`

- [ ] **Step 1: Write failing process adapter tests**

Add to `backend/tests/supervisor/test_process_adapter.py`:

```python
async def test_process_adapter_uses_deepstream_module_for_deepstream_camera() -> None:
    camera_id = uuid4()
    calls: list[list[str]] = []

    async def fake_exec(*argv: str, env: dict[str, str]) -> object:
        calls.append(list(argv))
        return _FakeProcess()

    config = WorkerLaunchConfig(
        python_executable="/venv/bin/python",
        runtime_family_provider=lambda requested_camera_id: (
            "deepstream" if requested_camera_id == camera_id else "python"
        ),
    )
    adapter = LocalWorkerProcessAdapter(config, subprocess_exec=fake_exec)

    result = await adapter.start(camera_id)

    assert result.runtime_state == "running"
    assert calls[0][:3] == ["/venv/bin/python", "-m", "argus.inference.deepstream_bridge"]
    assert calls[0][-2:] == ["--camera-id", str(camera_id)]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --project backend pytest backend/tests/supervisor/test_process_adapter.py -q
```

Expected: failure because `runtime_family_provider` does not exist.

- [ ] **Step 3: Add runtime family provider**

In `backend/src/argus/supervisor/process_adapter.py`, add:

```python
RuntimeFamilyProvider = Callable[[UUID], str | Awaitable[str]]
```

Add fields to `WorkerLaunchConfig`:

```python
    deepstream_module_name: str = "argus.inference.deepstream_bridge"
    runtime_family_provider: RuntimeFamilyProvider | None = None
```

Change `start()`:

```python
        argv = await self._argv(camera_id)
```

Change `_argv`:

```python
    async def _argv(self, camera_id: UUID) -> list[str]:
        module_name = await self._module_name(camera_id)
        return [
            self.config.python_executable,
            "-m",
            module_name,
            "--camera-id",
            str(camera_id),
        ]

    async def _module_name(self, camera_id: UUID) -> str:
        family = "python"
        if self.config.runtime_family_provider is not None:
            provided = self.config.runtime_family_provider(camera_id)
            family = await provided if inspect.isawaitable(provided) else provided
        if family == "deepstream":
            return self.config.deepstream_module_name
        return self.config.module_name
```

- [ ] **Step 4: Add bridge smoke test**

Create `backend/tests/inference/test_deepstream_bridge.py`:

```python
import subprocess
from uuid import uuid4


def test_deepstream_bridge_help_exits_successfully() -> None:
    result = subprocess.run(
        [
            "python",
            "-m",
            "argus.inference.deepstream_bridge",
            "--camera-id",
            str(uuid4()),
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "deepstream bridge dry run" in result.stdout
```

- [ ] **Step 5: Implement bridge entrypoint**

Create `backend/src/argus/inference/deepstream_bridge.py`:

```python
from __future__ import annotations

import argparse
from uuid import UUID


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vezor DeepStream worker bridge")
    parser.add_argument("--camera-id", required=True, type=UUID)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        print(f"deepstream bridge dry run camera_id={args.camera_id}")
        return 0
    raise SystemExit(
        "DeepStream bridge runtime requires generated bundle and live edge config."
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run launcher and bridge tests**

Run:

```bash
uv run --project backend pytest backend/tests/supervisor/test_process_adapter.py backend/tests/inference/test_deepstream_bridge.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit worker routing**

```bash
git add backend/src/argus/supervisor/process_adapter.py backend/src/argus/inference/deepstream_bridge.py backend/tests/supervisor/test_process_adapter.py backend/tests/inference/test_deepstream_bridge.py
git commit -m "feat: route deepstream worker launches"
```

## Task 8: Worker Config And Readiness Reasons

**Files:**
- Modify: `backend/tests/services/test_camera_worker_config.py`
- Modify: `backend/tests/services/test_runtime_selection.py`
- Modify: `backend/src/argus/services/app.py`

- [ ] **Step 1: Write failing worker config tests**

Add to `backend/tests/services/test_camera_worker_config.py`:

```python
async def test_worker_config_includes_deepstream_bundle_without_source_secret(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    camera, model, artifact = await _create_camera_with_runtime_artifact(
        db_session,
        kind=RuntimeArtifactKind.DEEPSTREAM_BUNDLE,
        runtime_backend="deepstream_tensorrt",
        target_profile="linux-aarch64-nvidia-jetson",
        artifact_path="/var/lib/vezor/models/runtime-artifacts/bundle/manifest.json",
    )

    response = await async_client.get(f"/api/v1/cameras/{camera.id}/worker-config")

    assert response.status_code == 200
    body = response.json()
    assert body["model"]["runtime_backend"] == "deepstream_tensorrt"
    assert body["runtime_artifacts"][0]["kind"] == "deepstream_bundle"
    assert "sample_password" not in response.text
```

Add a readiness test that expects a concrete missing-sync reason:

```python
async def test_edge_scene_reports_deepstream_bundle_not_synced_reason(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    camera, model = await _create_edge_camera_with_runtime_profile(
        db_session,
        preferred_backend="deepstream_tensorrt",
        target_profile="linux-aarch64-nvidia-jetson",
        fallback_allowed=False,
    )

    response = await async_client.get("/api/v1/cameras")

    assert response.status_code == 200
    camera_row = next(row for row in response.json()["items"] if row["id"] == str(camera.id))
    assert "DeepStream bundle not synced to edge node" in camera_row["readiness_reasons"]
```

If `_create_edge_camera_with_runtime_profile` does not exist, add it beside the existing camera/model test factories in the same file and have it create one edge-mode camera, one fixed-vocabulary model, and one runtime selection profile with the arguments shown above.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --project backend pytest backend/tests/services/test_camera_worker_config.py -q
```

Expected: failure because DeepStream bundle is not handled.

- [ ] **Step 3: Update worker config serialization**

In `backend/src/argus/services/app.py`, update `_runtime_artifact_to_worker_payload` to preserve:

```python
"kind": artifact.kind.value,
"runtime_backend": artifact.runtime_backend,
"path": artifact.path,
"target_profile": artifact.target_profile,
```

Ensure no source URI or credentials are copied into artifact payloads.

- [ ] **Step 4: Update readiness reasons**

In the scene readiness path, add exact reasons:

```python
DEEPSTREAM_MISSING_RUNTIME = "DeepStream runtime not installed on edge node"
DEEPSTREAM_MISSING_BUNDLE = "DeepStream bundle not built for linux-aarch64-nvidia-jetson"
DEEPSTREAM_NOT_SYNCED = "DeepStream bundle not synced to edge node"
DEEPSTREAM_OPEN_VOCAB_UNSUPPORTED = "Open-vocabulary models are not supported by DeepStream runtime"
```

Attach them only when the scene or runtime profile selects `deepstream_tensorrt`.

- [ ] **Step 5: Run service tests**

Run:

```bash
uv run --project backend pytest backend/tests/services/test_camera_worker_config.py backend/tests/services/test_runtime_selection.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit config/readiness**

```bash
git add backend/src/argus/services/app.py backend/tests/services/test_camera_worker_config.py backend/tests/services/test_runtime_selection.py
git commit -m "feat: expose deepstream worker readiness"
```

## Task 9: DeepStream Hardware Probe And Service Evidence

**Files:**
- Modify: `backend/tests/supervisor/test_hardware_probe.py`
- Modify: `backend/src/argus/supervisor/runner.py`
- Modify: `scripts/jetson-preflight.sh`

- [ ] **Step 1: Write failing hardware probe tests**

Add to `backend/tests/supervisor/test_hardware_probe.py`:

```python
def test_hardware_probe_reports_deepstream_capability_when_plugins_exist(monkeypatch) -> None:
    monkeypatch.setenv("VEZOR_EDGE_RUNTIME_FAMILY", "deepstream")
    probe = _probe_with_commands(
        {
            ("deepstream-app", "--version-all"): "DeepStreamSDK 7.1\n",
            ("gst-inspect-1.0", "nvinfer"): "Plugin Details:\n  Name nvinfer\n",
            ("gst-inspect-1.0", "nvtracker"): "Plugin Details:\n  Name nvtracker\n",
            ("gst-inspect-1.0", "nvurisrcbin"): "Plugin Details:\n  Name nvurisrcbin\n",
            ("gst-inspect-1.0", "nvdsosd"): "Plugin Details:\n  Name nvdsosd\n",
        }
    )

    sample = probe.collect()

    assert "deepstream" in sample.runtime_families
    assert sample.deepstream["installed"] is True
    assert sample.deepstream["version"] == "7.1"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run --project backend pytest backend/tests/supervisor/test_hardware_probe.py -q
```

Expected: failure because the probe has no DeepStream block.

- [ ] **Step 3: Add preflight output**

Extend `scripts/jetson-preflight.sh --json` output with:

```json
"deepstream": {
  "installed": true,
  "version": "7.1",
  "plugins": ["nvinfer", "nvtracker", "nvurisrcbin", "nvdsosd"]
}
```

Implement with guarded command checks:

```bash
if command -v deepstream-app >/dev/null 2>&1; then
  deepstream_version="$(deepstream-app --version-all 2>/dev/null | awk '/DeepStreamSDK/ {print $NF; exit}')"
fi
```

and plugin checks through `gst-inspect-1.0`.

- [ ] **Step 4: Add supervisor reporting**

Extend the hardware probe data model in `backend/src/argus/supervisor/runner.py` to include:

```python
runtime_families: list[str]
deepstream: dict[str, object] | None
```

Populate `runtime_families` with `["python"]` by default and include `deepstream` only when installed and plugin checks pass.

- [ ] **Step 5: Run probe tests and shell syntax**

Run:

```bash
bash -n scripts/jetson-preflight.sh
uv run --project backend pytest backend/tests/supervisor/test_hardware_probe.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit hardware probe**

```bash
git add scripts/jetson-preflight.sh backend/src/argus/supervisor/runner.py backend/tests/supervisor/test_hardware_probe.py
git commit -m "feat: report deepstream edge capabilities"
```

## Task 10: UI DeepStream Readiness And Model Management

**Files:**
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Modify: `frontend/src/pages/Models.test.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/pages/Models.tsx`
- Regenerate: `frontend/src/lib/api.generated.ts`
- Regenerate: `frontend/src/lib/openapi.json`

- [ ] **Step 1: Write failing UI tests**

Add to `frontend/src/components/cameras/CameraWizard.test.tsx`:

```tsx
it("shows DeepStream readiness reasons for edge scenes", async () => {
  renderCameraWizard({
    models: [
      {
        id: "model-1",
        name: "YOLO26n COCO",
        capability: "fixed_vocab",
        capability_config: { runtime_backend: "onnxruntime" },
        runtime_artifacts: [],
      },
    ],
    readiness: ["DeepStream bundle not synced to edge node"],
  });

  expect(await screen.findByText("DeepStream bundle not synced to edge node")).toBeInTheDocument();
});
```

Add to `frontend/src/pages/Models.test.tsx`:

```tsx
it("labels DeepStream bundles as runtime artifacts", async () => {
  renderModelsPage({
    runtimeArtifacts: [
      {
        id: "artifact-1",
        kind: "deepstream_bundle",
        runtime_backend: "deepstream_tensorrt",
        target_profile: "linux-aarch64-nvidia-jetson",
        validation_status: "valid",
      },
    ],
  });

  expect(await screen.findByText(/DeepStream TensorRT bundle/i)).toBeInTheDocument();
});
```

Use the local render helpers in each test file and keep the expected text exact.

- [ ] **Step 2: Run UI tests and verify failure**

Run:

```bash
npm --prefix frontend test -- CameraWizard.test.tsx Models.test.tsx --runInBand
```

Expected: failure because generated API types and display labels do not include DeepStream.

- [ ] **Step 3: Regenerate OpenAPI**

Run:

```bash
python3 -m uv run --project backend python - <<'PY' > frontend/src/lib/openapi.json
import json
from argus.services.app import create_app

print(json.dumps(create_app().openapi(), sort_keys=True))
PY
corepack pnpm --dir frontend generate:api
```

Expected: `frontend/src/lib/openapi.json` and `frontend/src/lib/api.generated.ts` are updated.

Verify `RuntimeArtifactKind` includes:

```ts
"deepstream_bundle"
```

and runtime backend unions include:

```ts
"deepstream_tensorrt"
```

- [ ] **Step 4: Add UI labels and readiness display**

In `frontend/src/pages/Models.tsx`, map:

```ts
deepstream_bundle -> "DeepStream TensorRT bundle"
deepstream_tensorrt -> "DeepStream TensorRT"
```

In `frontend/src/components/cameras/CameraWizard.tsx`, display backend readiness messages returned by the API without collapsing them into generic `Model not synced`.

- [ ] **Step 5: Run UI tests**

Run:

```bash
npm --prefix frontend test -- CameraWizard.test.tsx Models.test.tsx --runInBand
```

Expected: PASS.

- [ ] **Step 6: Commit UI updates**

```bash
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/pages/Models.tsx frontend/src/pages/Models.test.tsx frontend/src/lib/api.generated.ts frontend/src/lib/openapi.json
git commit -m "feat: surface deepstream runtime readiness"
```

## Task 11: Release Gate And Documentation

**Files:**
- Modify: `installer/tests/test_release_gate.py`
- Modify: `scripts/validate-installers.sh`
- Modify: `docs/model-loading-and-configuration-guide.md`
- Modify: `docs/product-installer-and-first-run-guide.md`
- Modify: `docs/operator-deployment-playbook.md`

- [ ] **Step 1: Update release gate test**

Replace `test_release_gate_required_files_exist_without_deepstream_dependency` with:

```python
def test_release_gate_keeps_deepstream_optional_for_default_installer() -> None:
    missing = [str(path.relative_to(REPO_ROOT)) for path in REQUIRED_FILES if not path.exists()]

    assert missing == []
    validate_script = _read(VALIDATE_SCRIPT).lower()
    assert "dockerfile.edge.deepstream" in validate_script
    assert "--runtime-family deepstream" not in validate_script
```

This keeps DeepStream artifacts syntax-checked while preventing the default release gate from requiring an NGC pull or a Jetson GPU host.

- [ ] **Step 2: Update installer validation script**

In `scripts/validate-installers.sh`, add:

```bash
test -f backend/Dockerfile.edge.deepstream
grep -q "Dockerfile.edge.deepstream" backend/tests/core/test_deepstream_dockerfile.py
```

Add a Python/pytest path for DeepStream manifest/schema tests without running Docker builds.

- [ ] **Step 3: Update docs**

Add sections:

- `docs/model-loading-and-configuration-guide.md`: explain `deepstream_bundle`, `deepstream_tensorrt`, YOLO fixed-vocabulary support, and why this is distinct from a plain TensorRT engine.
- `docs/product-installer-and-first-run-guide.md`: add `--runtime-family deepstream`, NGC/DeepStream compatibility preflight, and candidate L4T behavior.
- `docs/operator-deployment-playbook.md`: add DeepStream smoke evidence list and PASS/FAIL/BLOCKED rules.

Use redacted examples only:

```text
rtsp://***:***@camera.local:8554/ch1
```

- [ ] **Step 4: Run documentation and release tests**

Run:

```bash
uv run --project installer pytest installer/tests/test_release_gate.py installer/tests/test_manifest.py -q
git diff --check
```

Expected: PASS.

- [ ] **Step 5: Commit release/docs**

```bash
git add installer/tests/test_release_gate.py scripts/validate-installers.sh docs/model-loading-and-configuration-guide.md docs/product-installer-and-first-run-guide.md docs/operator-deployment-playbook.md
git commit -m "docs: document optional deepstream edge lane"
```

## Task 12: Real YOLO Parser And Fixture Validation

**Files:**
- Create: `backend/tests/vision/fixtures/deepstream_yolo26_output.json`
- Modify: `backend/tests/vision/test_deepstream_bundle.py`
- Modify: `backend/deepstream/yolo_parser/nvdsinfer_custom_impl_vezor_yolo.cpp`
- Create: `backend/deepstream/yolo_parser/test_parser.cpp`
- Modify: `backend/deepstream/yolo_parser/Makefile`

- [ ] **Step 1: Add deterministic parser fixture**

Create `backend/tests/vision/fixtures/deepstream_yolo26_output.json` with a small recorded output tensor fixture from the exact exported YOLO model used in the smoke. Include only tensor dimensions and numeric outputs needed to assert two detections; do not include images or RTSP-derived frames.

- [ ] **Step 2: Add parser unit executable**

Create `backend/deepstream/yolo_parser/test_parser.cpp` that loads the fixture, calls `NvDsInferParseVezorYolo`, and asserts:

```text
object_count == 2
classes == ["person", "car"]
confidence >= 0.25
left/top/width/height within frame bounds
```

- [ ] **Step 3: Update Makefile**

Add:

```makefile
test-parser: test_parser
	./test_parser

test_parser: test_parser.cpp $(TARGET)
	$(CXX) $(CXXFLAGS) -o $@ test_parser.cpp -L. -lnvdsinfer_custom_impl_vezor_yolo
```

- [ ] **Step 4: Implement parser math**

Replace the empty parser with YOLO26 output parsing that:

- reads class logits and boxes from the known exported tensor layout,
- applies confidence threshold from `detectionParams.perClassPreclusterThreshold`,
- converts center-width-height boxes to DeepStream left-top-width-height,
- clamps boxes to network dimensions,
- returns `NvDsInferObjectDetectionInfo` objects in deterministic score order.

- [ ] **Step 5: Run parser tests on Jetson image**

Run on Jetson or in the DeepStream image:

```bash
make -C backend/deepstream/yolo_parser clean all test-parser
```

Expected: PASS with two detections.

- [ ] **Step 6: Commit parser implementation**

```bash
git add backend/deepstream/yolo_parser backend/tests/vision/fixtures/deepstream_yolo26_output.json backend/tests/vision/test_deepstream_bundle.py
git commit -m "feat: parse yolo detections for deepstream"
```

## Task 13: Whole-Product DeepStream Live Smoke

**Files:**
- Create: `docs/superpowers/status/YYYY-MM-DD-deepstream-jetson-live-smoke-report.md`

- [ ] **Step 1: Rebuild from committed branch**

Run from a clean committed branch:

```bash
git status --short
git rev-parse --abbrev-ref HEAD
```

Expected: no uncommitted implementation changes.

- [ ] **Step 2: Install DeepStream edge runtime on Jetson**

Run the packaged installer with:

```bash
sudo /opt/vezor/current/installer/linux/install-edge.sh \
  --api-url "$VEZOR_MASTER_API_URL" \
  --pairing-code "$VEZOR_PAIRING_CODE" \
  --session-id "$VEZOR_PAIRING_SESSION_ID" \
  --edge-name EDGE \
  --runtime-family deepstream \
  --manifest /opt/vezor/current/installer/manifests/dev-example.json
```

Expected: installer records `runtime_family=deepstream`, starts `vezor-edge.service`, and does not print RTSP credentials or tokens.

- [ ] **Step 3: Capture service-manager evidence**

Run on Jetson:

```bash
systemctl status vezor-edge.service --no-pager
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
docker exec vezor-supervisor deepstream-app --version-all
docker exec vezor-supervisor gst-inspect-1.0 nvinfer nvtracker nvurisrcbin nvdsosd
```

Expected: service active, DeepStream image running, DeepStream 7.1 version reported, plugin inspections return success.

- [ ] **Step 4: Build/register/sync bundle**

From the Vezor UI or API:

- build `deepstream_bundle` for YOLO26 fixed-vocabulary model,
- target `linux-aarch64-nvidia-jetson`,
- precision `fp16`,
- sync the artifact to `EDGE`.

Expected: model management shows `DeepStream TensorRT bundle`, validation `valid`, and edge sync complete.

- [ ] **Step 5: Run real RTSP scene**

Create or update an EDGE scene with the local-only RTSP credential stored through the product UI. Use the DeepStream runtime artifact. Do not paste the full RTSP URL into the smoke report.

Expected:

- worker runtime state `running`,
- detections appear for the selected class scope,
- history gets new samples,
- evidence appears when a rule triggers,
- billing usage increments,
- processed stream is visible in Live,
- Core Link remains healthy.

- [ ] **Step 6: Write closure report**

Create `docs/superpowers/status/YYYY-MM-DD-deepstream-jetson-live-smoke-report.md` with sections:

```markdown
# DeepStream Jetson Live Smoke Report

## Summary
- Result: PASS | FAIL | BLOCKED | NOT RUN
- Branch:
- Commit:
- Master host:
- Edge host:
- Jetson L4T / JetPack:
- DeepStream:
- Model:
- Runtime artifact:

## Evidence
- Installer:
- Service manager:
- DeepStream version/plugins:
- Model artifact:
- Scene readiness:
- Detection/history/evidence:
- Billing usage:
- Core Link:

## Failures Or Blocks
- None recorded before execution.

## Secret Handling
- Raw RTSP credentials: not present
- Bearer/bootstrap/node credentials: not present
- Reflector secrets: not present
```

Do not mark PASS if Jetson access, RTSP access, model files, DeepStream bundle, service evidence, billing usage, deterministic evidence, or fresh-stack proof is missing.

- [ ] **Step 7: Commit smoke report after user approval**

Ask before committing the live smoke report because it may mention hostnames, local IPs, or operational details.

```bash
git add docs/superpowers/status/YYYY-MM-DD-deepstream-jetson-live-smoke-report.md
git commit -m "docs: record deepstream jetson live smoke"
```

## Verification Matrix

Run before asking for review:

```bash
uv run --project installer pytest installer/tests -q
uv run --project backend pytest backend/tests/vision/test_runtime_selection.py backend/tests/vision/test_deepstream_bundle.py backend/tests/supervisor/test_process_adapter.py backend/tests/supervisor/test_hardware_probe.py -q
npm --prefix frontend test -- CameraWizard.test.tsx Models.test.tsx --runInBand
bash -n installer/linux/install-edge.sh
bash -n scripts/jetson-preflight.sh
git diff --check
```

Expected: all commands pass. If Docker/DeepStream live validation is unavailable, mark only the live DeepStream smoke as BLOCKED and keep unit/integration results separate.

## Review Notes

- Keep DeepStream optional in default release gates.
- Do not classify candidate L4T as PASS without the real Jetson smoke.
- Do not commit raw RTSP credentials, bearer tokens, bootstrap tokens, node credentials, reflector secrets, NGC credentials, or local sudo passwords.
- Do not use global Docker prune during validation.
