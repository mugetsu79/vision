# Jetson Native Capture Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the current no-DeepStream Jetson Python worker by replacing subprocess rawvideo capture with in-process GStreamer `appsink`, then add an opt-in native NVMM/CUDA capture lane scaffold that can be built and measured separately.

**Architecture:** Keep `argus.vision.camera` as the source/reconnect/fallback orchestrator. Add a focused `argus.vision.gstreamer_appsink` backend for in-process GStreamer frames and a later `argus.vision.jetson_nvmm_capture` interface for the native lane. Runtime reports continue to expose broad `media_pipeline_mode` and add precise `media_capture_backend` diagnostics so operators can distinguish appsink, raw pipe, FFmpeg, and native NVMM behavior.

**Tech Stack:** Python, pytest, NumPy, PyGObject/GStreamer (`Gst`, `GstApp`), NVIDIA Jetson GStreamer elements (`nvv4l2decoder`, `nvvidconv`), optional C++/pybind11 native extension for NVMM/CUDA, Docker edge supervisor, real Jetson live smoke.

---

## File Map

- Create `backend/src/argus/vision/gstreamer_appsink.py`: in-process GStreamer capability probing, pipeline rendering, sample pulling, frame mapping, and sanitized diagnostics.
- Modify `backend/src/argus/vision/camera.py`: select appsink before rawvideo pipe on Jetson, expose `media_capture_backend`, preserve fallback order, pass substage timings.
- Modify `backend/src/argus/inference/engine.py`: include `media_capture_backend` in runtime reports when a frame source exposes it.
- Modify `backend/src/argus/api/contracts.py`: add optional `media_capture_backend` to runtime report request/response contracts.
- Modify `backend/src/argus/models/tables.py`: persist `media_capture_backend` on `WorkerRuntimeReport`.
- Create `backend/src/argus/migrations/versions/0047_worker_runtime_report_capture_backend.py`: add/drop the database column.
- Modify `backend/src/argus/services/supervisor_operations.py`: write and return the field.
- Modify `backend/src/argus/supervisor/operations_client.py`: include the field in worker-to-control-plane payloads.
- Modify `backend/src/argus/supervisor/reconciler.py`: include the field in summarized runtime diagnostics.
- Modify `backend/tests/vision/test_camera.py`: cover fallback ordering and runtime backend reporting.
- Create `backend/tests/vision/test_gstreamer_appsink.py`: unit-test pipeline building, probe behavior, redaction, and fake sample mapping.
- Modify `backend/tests/inference/test_engine.py`: assert runtime reports propagate `media_capture_backend`.
- Modify supervisor/API tests that assert runtime report payloads, especially `backend/tests/supervisor/test_operations_client.py`.
- Create `backend/src/argus/vision/jetson_nvmm_capture.py`: optional native-lane interface and availability probe.
- Create `backend/tests/vision/test_jetson_nvmm_capture.py`: unit-test the optional native-lane contract without requiring Jetson libraries.
- Create `backend/native/jetson_capture/README.md`: native extension design, build prerequisites, and acceptance command list.
- Update `docs/model-loading-and-configuration-guide.md`: explain appsink/native capture reporting and DeepStream separation.
- Update `docs/operator-deployment-playbook.md`: add sanitized live smoke commands and PASS/FAIL evidence requirements.

## Task 1: Add Capture Backend Reporting Contract

**Files:**
- Modify: `backend/src/argus/vision/camera.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0047_worker_runtime_report_capture_backend.py`
- Modify: `backend/src/argus/services/supervisor_operations.py`
- Modify: `backend/src/argus/supervisor/operations_client.py`
- Modify: `backend/tests/vision/test_camera.py`
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing camera backend test**

Add this test to `backend/tests/vision/test_camera.py`:

```python
def test_camera_source_reports_precise_capture_backend() -> None:
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    class _BackendCapture(_FakeCapture):
        def media_pipeline_mode(self) -> str:
            return "jetson_gstreamer_native"

        def media_capture_backend(self) -> str:
            return "gstreamer_appsink"

    def capture_factory(source: str | int, backend: int | None) -> _BackendCapture:
        del source, backend
        return _BackendCapture([frame])

    source = create_camera_source(
        CameraSourceConfig(source_uri="rtsp://camera.internal/live"),
        platform_info=PlatformInfo(machine="aarch64", jetson=True),
        capture_factory=capture_factory,
    )

    np.testing.assert_array_equal(source.next_frame(), frame)
    assert source.media_pipeline_mode() == "jetson_gstreamer_native"
    assert source.media_capture_backend() == "gstreamer_appsink"
```

- [ ] **Step 2: Run the camera test and verify it fails**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py::test_camera_source_reports_precise_capture_backend -q
```

Expected: FAIL because `CameraSource` does not expose `media_capture_backend()`.

- [ ] **Step 3: Implement the minimal camera method**

In `backend/src/argus/vision/camera.py`, extend `CaptureHandle` and add the method inside the existing `CameraSource` class near `media_pipeline_mode()`:

```python
class CaptureHandle(Protocol):
    def read(self) -> tuple[bool, Frame | None]:
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError


def media_capture_backend(self) -> str | None:
    media_capture_backend = getattr(self._capture, "media_capture_backend", None)
    if callable(media_capture_backend):
        value = media_capture_backend()
        if value is not None:
            return str(value)
    if self.mode is CameraSourceMode.X86_RTSP or self._backend == cv2.CAP_FFMPEG:
        return "ffmpeg_rawvideo"
    return None
```

Also add delegating methods to `_PrefetchedFrameCapture` and `_LatestFrameCapture`:

```python
def media_capture_backend(self) -> str | None:
    media_capture_backend = getattr(self._capture, "media_capture_backend", None)
    if not callable(media_capture_backend):
        return None
    return media_capture_backend()
```

- [ ] **Step 4: Run the camera test and verify it passes**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py::test_camera_source_reports_precise_capture_backend -q
```

Expected: PASS.

- [ ] **Step 5: Add the failing runtime-report propagation test**

In `backend/tests/inference/test_engine.py`, update the fake frame source used by runtime-report tests so it exposes:

```python
def media_capture_backend(self) -> str:
    return "gstreamer_appsink"
```

Then assert in the existing runtime report test:

```python
assert report.media_capture_backend == "gstreamer_appsink"
```

- [ ] **Step 6: Run the runtime-report test and verify it fails**

Run the narrow test containing the runtime-report assertion:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py -k "runtime_report and media_capture_backend" -q
```

Expected: FAIL because the report model or engine does not yet include the field.

- [ ] **Step 7: Implement runtime-report propagation**

In `backend/src/argus/inference/engine.py`, read the frame source value near the existing `media_pipeline_mode` code:

```python
media_capture_backend = None
capture_backend_getter = getattr(self._frame_source, "media_capture_backend", None)
if callable(capture_backend_getter):
    media_capture_backend = capture_backend_getter()
```

Pass it into the runtime report constructor:

```python
media_capture_backend=media_capture_backend,
```

Add the optional field to the report model:

```python
media_capture_backend: str | None = None
```

- [ ] **Step 8: Run targeted runtime tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py backend/tests/supervisor/test_operations_client.py -q
```

Expected: PASS.

## Task 2: Build The In-Process GStreamer AppSink Backend

**Files:**
- Create: `backend/src/argus/vision/gstreamer_appsink.py`
- Create: `backend/tests/vision/test_gstreamer_appsink.py`

- [ ] **Step 1: Write failing pipeline-rendering tests**

Create `backend/tests/vision/test_gstreamer_appsink.py`:

```python
from __future__ import annotations

import pytest

from argus.vision.gstreamer_appsink import (
    AppSinkPipelineMode,
    build_rtsp_appsink_pipeline,
    redact_pipeline,
)


def test_native_pipeline_uses_nvidia_decode_resize_and_single_frame_sink() -> None:
    source_uri = "rtsp://" + "user:pass" + "@camera.internal:8554/ch2"
    pipeline = build_rtsp_appsink_pipeline(
        source_uri,
        mode=AppSinkPipelineMode.JETSON_NATIVE,
        target_width=1280,
        target_height=720,
        protocols="tcp",
        latency_ms=80,
        drop_on_latency=True,
        appsink_supports_leaky_type=False,
        decoder_supports_disable_dpb=True,
    )

    assert f"rtspsrc location={source_uri}" in pipeline
    assert "protocols=tcp" in pipeline
    assert "latency=80" in pipeline
    assert "drop-on-latency=true" in pipeline
    assert "rtph264depay ! h264parse ! nvv4l2decoder disable-dpb=true" in pipeline
    assert "queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream" in pipeline
    assert "nvvidconv" in pipeline
    assert "video/x-raw,format=BGR,width=1280,height=720" in pipeline
    assert "appsink name=sink sync=false max-buffers=1 drop=true emit-signals=false" in pipeline


def test_software_pipeline_labels_software_decode() -> None:
    pipeline = build_rtsp_appsink_pipeline(
        "rtsp://camera.internal/live",
        mode=AppSinkPipelineMode.GSTREAMER_SOFTWARE,
        target_width=640,
        target_height=360,
        protocols="tcp",
        latency_ms=120,
        drop_on_latency=True,
        appsink_supports_leaky_type=True,
        decoder_supports_disable_dpb=False,
    )

    assert "avdec_h264" in pipeline
    assert "nvv4l2decoder" not in pipeline
    assert "leaky-type=downstream" in pipeline


def test_redact_pipeline_removes_rtsp_credentials_and_jwt() -> None:
    source_uri = "rtsp://" + "user:pass" + "@camera.internal:8554/ch2?jwt=" + "secret-token"
    pipeline = build_rtsp_appsink_pipeline(
        source_uri,
        mode=AppSinkPipelineMode.JETSON_NATIVE,
        target_width=1280,
        target_height=720,
        protocols="tcp",
        latency_ms=80,
        drop_on_latency=True,
        appsink_supports_leaky_type=False,
        decoder_supports_disable_dpb=False,
    )

    redacted = redact_pipeline(pipeline)

    assert "user:pass" not in redacted
    assert "secret-token" not in redacted
    assert "rtsp://***:***@camera.internal:8554/ch2" in redacted
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_gstreamer_appsink.py -q
```

Expected: FAIL because `argus.vision.gstreamer_appsink` does not exist.

- [ ] **Step 3: Implement pipeline rendering and redaction**

Create `backend/src/argus/vision/gstreamer_appsink.py` with:

```python
from __future__ import annotations

import re
from dataclasses import dataclass

from argus.compat import StrEnum
from argus.core.logging import redact_url_secrets


class AppSinkPipelineMode(StrEnum):
    JETSON_NATIVE = "jetson_native"
    GSTREAMER_SOFTWARE = "gstreamer_software"


@dataclass(slots=True, frozen=True)
class AppSinkCapabilities:
    available: bool
    appsink_supports_leaky_type: bool = False
    decoder_supports_disable_dpb: bool = False
    reason: str | None = None


def build_rtsp_appsink_pipeline(
    source_uri: str,
    *,
    mode: AppSinkPipelineMode,
    target_width: int | None,
    target_height: int | None,
    protocols: str,
    latency_ms: int,
    drop_on_latency: bool,
    appsink_supports_leaky_type: bool,
    decoder_supports_disable_dpb: bool,
) -> str:
    drop_value = "true" if drop_on_latency else "false"
    caps = "video/x-raw,format=BGR"
    if target_width is not None and target_height is not None:
        caps = f"{caps},width={int(target_width)},height={int(target_height)}"
    sink = "appsink name=sink sync=false max-buffers=1 drop=true emit-signals=false"
    if appsink_supports_leaky_type:
        sink = f"{sink} leaky-type=downstream"
    if mode is AppSinkPipelineMode.JETSON_NATIVE:
        decoder = "nvv4l2decoder"
        if decoder_supports_disable_dpb:
            decoder = f"{decoder} disable-dpb=true"
        decode_chain = (
            f"{decoder} ! "
            "queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! "
            "nvvidconv ! video/x-raw,format=BGRx ! videoconvert"
        )
    else:
        decode_chain = (
            "avdec_h264 ! "
            "queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! "
            "videoconvert"
        )
    return (
        f"rtspsrc location={source_uri} protocols={protocols} "
        f"latency={int(latency_ms)} drop-on-latency={drop_value} ! "
        f"rtph264depay ! h264parse ! {decode_chain} ! {caps} ! {sink}"
    )


def redact_pipeline(pipeline: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return f"location={redact_url_secrets(match.group(1))}"

    return re.sub(r"location=([^\\s]+)", replace, pipeline)
```

- [ ] **Step 4: Run pipeline tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_gstreamer_appsink.py -q
```

Expected: PASS for the pipeline/redaction tests.

## Task 3: Implement AppSink Capture With Test Doubles

**Files:**
- Modify: `backend/src/argus/vision/gstreamer_appsink.py`
- Modify: `backend/tests/vision/test_gstreamer_appsink.py`

- [ ] **Step 1: Add failing capture behavior tests**

Append to `backend/tests/vision/test_gstreamer_appsink.py`:

```python
import numpy as np

from argus.vision.gstreamer_appsink import GStreamerAppSinkCapture


class _FakeSample:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload


class _FakeRuntime:
    def __init__(self, samples: list[_FakeSample | None]) -> None:
        self.samples = samples
        self.started_pipeline: str | None = None
        self.stopped = False

    def start(self, pipeline: str) -> None:
        self.started_pipeline = pipeline

    def pull_sample(self, timeout_s: float) -> _FakeSample | None:
        del timeout_s
        return self.samples.pop(0) if self.samples else None

    def sample_to_bgr(self, sample: _FakeSample, *, width: int, height: int) -> np.ndarray:
        return np.frombuffer(sample.payload, dtype=np.uint8).reshape((height, width, 3)).copy()

    def stop(self) -> None:
        self.stopped = True


def test_appsink_capture_returns_latest_bgr_frame_and_backend_mode() -> None:
    frame = np.arange(2 * 3 * 3, dtype=np.uint8).reshape((2, 3, 3))
    runtime = _FakeRuntime([_FakeSample(frame.tobytes())])
    capture = GStreamerAppSinkCapture.create(
        pipeline="fake-pipeline",
        runtime=runtime,
        width=3,
        height=2,
        media_pipeline_mode="jetson_gstreamer_native",
        read_timeout_s=0.01,
    )

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert runtime.started_pipeline == "fake-pipeline"
    assert capture.media_pipeline_mode() == "jetson_gstreamer_native"
    assert capture.media_capture_backend() == "gstreamer_appsink"
    assert "decode_read" in capture.last_stage_timings()


def test_appsink_capture_reports_no_frame_when_sample_timeout_expires() -> None:
    runtime = _FakeRuntime([None])
    capture = GStreamerAppSinkCapture.create(
        pipeline="fake-pipeline",
        runtime=runtime,
        width=3,
        height=2,
        media_pipeline_mode="jetson_gstreamer_native",
        read_timeout_s=0.01,
    )

    ok, frame = capture.read()

    assert ok is False
    assert frame is None
    assert capture.last_stage_timings()["wait"] >= 0.0
```

- [ ] **Step 2: Run the capture tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_gstreamer_appsink.py -k "capture" -q
```

Expected: FAIL because `GStreamerAppSinkCapture` does not exist.

- [ ] **Step 3: Implement the capture class and runtime protocol**

Add to `backend/src/argus/vision/gstreamer_appsink.py`:

```python
from collections.abc import Protocol
from time import perf_counter
from typing import Any

import numpy as np

Frame = np.ndarray


class AppSinkRuntime(Protocol):
    def start(self, pipeline: str) -> None:
        raise NotImplementedError

    def pull_sample(self, timeout_s: float) -> object | None:
        raise NotImplementedError

    def sample_to_bgr(self, sample: object, *, width: int, height: int) -> Frame:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class GStreamerAppSinkCapture:
    def __init__(
        self,
        *,
        runtime: AppSinkRuntime,
        width: int,
        height: int,
        media_pipeline_mode: str,
        read_timeout_s: float,
    ) -> None:
        self._runtime = runtime
        self._width = width
        self._height = height
        self._media_pipeline_mode = media_pipeline_mode
        self._read_timeout_s = read_timeout_s
        self._last_stage_timings: dict[str, float] = {}

    @classmethod
    def create(
        cls,
        *,
        pipeline: str,
        runtime: AppSinkRuntime,
        width: int,
        height: int,
        media_pipeline_mode: str,
        read_timeout_s: float,
    ) -> "GStreamerAppSinkCapture":
        runtime.start(pipeline)
        return cls(
            runtime=runtime,
            width=width,
            height=height,
            media_pipeline_mode=media_pipeline_mode,
            read_timeout_s=read_timeout_s,
        )

    def read(self) -> tuple[bool, Frame | None]:
        started_at = perf_counter()
        sample = self._runtime.pull_sample(self._read_timeout_s)
        pulled_at = perf_counter()
        if sample is None:
            self._last_stage_timings = {"wait": max(0.0, pulled_at - started_at)}
            return False, None
        frame = self._runtime.sample_to_bgr(sample, width=self._width, height=self._height)
        completed_at = perf_counter()
        self._last_stage_timings = {
            "wait": max(0.0, pulled_at - started_at),
            "decode_read": max(0.0, completed_at - started_at),
        }
        return True, frame

    def last_stage_timings(self) -> dict[str, float]:
        return dict(self._last_stage_timings)

    def media_pipeline_mode(self) -> str:
        return self._media_pipeline_mode

    def media_capture_backend(self) -> str:
        return "gstreamer_appsink"

    def release(self) -> None:
        self._runtime.stop()
```

- [ ] **Step 4: Run the capture behavior tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_gstreamer_appsink.py -q
```

Expected: PASS.

## Task 4: Add The Real PyGObject Runtime

**Files:**
- Modify: `backend/src/argus/vision/gstreamer_appsink.py`
- Modify: `backend/tests/vision/test_gstreamer_appsink.py`

- [ ] **Step 1: Add failing availability/probe tests**

Add tests using monkeypatches rather than importing real GI:

```python
from argus.vision.gstreamer_appsink import probe_appsink_capabilities


def test_probe_reports_unavailable_when_gi_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_import(name: str) -> object:
        if name == "gi":
            raise ImportError("missing gi")
        raise AssertionError(name)

    monkeypatch.setattr("argus.vision.gstreamer_appsink.importlib.import_module", fail_import)

    caps = probe_appsink_capabilities()

    assert caps.available is False
    assert caps.reason == "missing gi"
```

- [ ] **Step 2: Run the probe test and verify it fails**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_gstreamer_appsink.py::test_probe_reports_unavailable_when_gi_is_missing -q
```

Expected: FAIL because `probe_appsink_capabilities()` does not exist.

- [ ] **Step 3: Implement capability probe and real runtime**

In `backend/src/argus/vision/gstreamer_appsink.py`, add imports and a conservative probe:

```python
import importlib


def probe_appsink_capabilities() -> AppSinkCapabilities:
    try:
        gi = importlib.import_module("gi")
        gi.require_version("Gst", "1.0")
        gi.require_version("GstApp", "1.0")
        repository = importlib.import_module("gi.repository")
        gst = repository.Gst
    except Exception as exc:
        return AppSinkCapabilities(available=False, reason=str(exc))
    gst.init(None)
    registry = gst.Registry.get()
    required = ["rtspsrc", "rtph264depay", "h264parse", "queue", "appsink"]
    missing = [name for name in required if registry.find_feature(name, gst.ElementFactory) is None]
    if missing:
        return AppSinkCapabilities(available=False, reason=f"missing GStreamer elements: {', '.join(missing)}")
    appsink_factory = registry.find_feature("appsink", gst.ElementFactory)
    decoder_factory = registry.find_feature("nvv4l2decoder", gst.ElementFactory)
    appsink_supports_leaky = False
    decoder_supports_disable_dpb = False
    if appsink_factory is not None:
        element = appsink_factory.create(None)
        appsink_supports_leaky = element.find_property("leaky-type") is not None
    if decoder_factory is not None:
        element = decoder_factory.create(None)
        decoder_supports_disable_dpb = element.find_property("disable-dpb") is not None
    return AppSinkCapabilities(
        available=True,
        appsink_supports_leaky_type=appsink_supports_leaky,
        decoder_supports_disable_dpb=decoder_supports_disable_dpb,
    )
```

Add `PyGObjectAppSinkRuntime` in the same module:

```python
class PyGObjectAppSinkRuntime:
    def __init__(self) -> None:
        gi = importlib.import_module("gi")
        gi.require_version("Gst", "1.0")
        gi.require_version("GstApp", "1.0")
        repository = importlib.import_module("gi.repository")
        self._gst = repository.Gst
        self._gst.init(None)
        self._pipeline: object | None = None
        self._sink: object | None = None

    def start(self, pipeline: str) -> None:
        parsed = self._gst.parse_launch(pipeline)
        sink = parsed.get_by_name("sink")
        if sink is None:
            parsed.set_state(self._gst.State.NULL)
            raise RuntimeError("GStreamer appsink pipeline does not contain sink named 'sink'.")
        self._pipeline = parsed
        self._sink = sink
        result = parsed.set_state(self._gst.State.PLAYING)
        if result == self._gst.StateChangeReturn.FAILURE:
            parsed.set_state(self._gst.State.NULL)
            raise RuntimeError("GStreamer appsink pipeline failed to enter PLAYING state.")

    def pull_sample(self, timeout_s: float) -> object | None:
        if self._sink is None:
            return None
        timeout_ns = int(max(0.0, timeout_s) * self._gst.SECOND)
        return self._sink.emit("try-pull-sample", timeout_ns)

    def sample_to_bgr(self, sample: object, *, width: int, height: int) -> Frame:
        buffer = sample.get_buffer()
        success, map_info = buffer.map(self._gst.MapFlags.READ)
        if not success:
            raise RuntimeError("Unable to map GStreamer appsink buffer.")
        try:
            frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape((height, width, 3))
            return frame.copy()
        finally:
            buffer.unmap(map_info)

    def stop(self) -> None:
        pipeline = self._pipeline
        self._pipeline = None
        self._sink = None
        if pipeline is not None:
            pipeline.set_state(self._gst.State.NULL)
```

- [ ] **Step 4: Run all appsink unit tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_gstreamer_appsink.py -q
```

Expected: PASS without requiring Jetson hardware because real GI paths are isolated behind tests and probes.

## Task 5: Integrate AppSink Into Jetson Capture Fallback

**Files:**
- Modify: `backend/src/argus/vision/camera.py`
- Modify: `backend/tests/vision/test_camera.py`

- [ ] **Step 1: Write failing fallback-order tests**

Add to `backend/tests/vision/test_camera.py`:

```python
def test_jetson_rtsp_prefers_in_process_appsink_before_rawvideo(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    calls: list[str] = []

    class _AppSinkCapture(_FakeCapture):
        def media_pipeline_mode(self) -> str:
            return "jetson_gstreamer_native"

        def media_capture_backend(self) -> str:
            return "gstreamer_appsink"

    def open_appsink(source: str, *, media_pipeline_mode: str) -> _AppSinkCapture:
        calls.append(f"appsink:{media_pipeline_mode}:{source}")
        return _AppSinkCapture([frame])

    def fail_rawvideo(*args: object, **kwargs: object) -> object:
        raise AssertionError("rawvideo should not run when appsink succeeds")

    monkeypatch.setattr(camera_module, "_open_gstreamer_appsink_capture", open_appsink)
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", fail_rawvideo)

    capture = _default_capture_factory(
        "rtspsrc location=rtsp://camera.internal/live ! rtph264depay ! h264parse ! "
        "nvv4l2decoder ! nvvidconv ! video/x-raw,format=BGRx,width=1280,height=720 ! "
        "videoconvert ! video/x-raw,format=BGR,width=1280,height=720 ! "
        "appsink drop=true max-buffers=1 sync=false",
        cv2.CAP_GSTREAMER,
    )

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert capture.media_capture_backend() == "gstreamer_appsink"
    assert calls
```

Also add this fallback test:

```python
def test_jetson_rtsp_falls_back_to_rawvideo_when_appsink_first_frame_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    rawvideo_calls = 0

    def fail_appsink(source: str, *, media_pipeline_mode: str) -> object:
        del source, media_pipeline_mode
        raise RuntimeError("appsink first frame timeout")

    def open_rawvideo(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        nonlocal rawvideo_calls
        assert "nvv4l2decoder" in source
        assert media_pipeline_mode == "jetson_gstreamer_native"
        rawvideo_calls += 1
        return _FakeCapture([frame])

    monkeypatch.setattr(camera_module, "_open_gstreamer_appsink_capture", fail_appsink)
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", open_rawvideo)

    capture = _default_capture_factory(
        "rtspsrc location=rtsp://camera.internal/live ! rtph264depay ! h264parse ! "
        "nvv4l2decoder ! nvvidconv ! video/x-raw,format=BGRx,width=1280,height=720 ! "
        "videoconvert ! video/x-raw,format=BGR,width=1280,height=720 ! "
        "appsink drop=true max-buffers=1 sync=false",
        cv2.CAP_GSTREAMER,
    )

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert rawvideo_calls == 1
```

- [ ] **Step 2: Run fallback-order tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py -k "appsink or rawvideo" -q
```

Expected: FAIL because `camera.py` has no `_open_gstreamer_appsink_capture`.

- [ ] **Step 3: Implement appsink open helper**

In `backend/src/argus/vision/camera.py`, import the new module and add:

```python
def _open_gstreamer_appsink_capture(
    source: str,
    *,
    media_pipeline_mode: str,
) -> CaptureHandle:
    source_uri = _extract_gstreamer_source_uri(source)
    if source_uri is None:
        raise RuntimeError("GStreamer pipeline does not include an rtspsrc location.")
    width, height = _extract_gstreamer_output_dimensions(source) or _probe_video_dimensions(source_uri)
    capabilities = probe_appsink_capabilities()
    if not capabilities.available:
        raise RuntimeError(capabilities.reason or "GStreamer appsink is unavailable")
    mode = (
        AppSinkPipelineMode.GSTREAMER_SOFTWARE
        if media_pipeline_mode == MediaPipelineMode.JETSON_GSTREAMER_SOFTWARE.value
        else AppSinkPipelineMode.JETSON_NATIVE
    )
    options = _jetson_rtsp_options_from_environment()
    pipeline = build_rtsp_appsink_pipeline(
        source_uri,
        mode=mode,
        target_width=width,
        target_height=height,
        protocols=options.protocols,
        latency_ms=options.latency_ms,
        drop_on_latency=options.drop_on_latency,
        appsink_supports_leaky_type=capabilities.appsink_supports_leaky_type,
        decoder_supports_disable_dpb=capabilities.decoder_supports_disable_dpb,
    )
    return GStreamerAppSinkCapture.create(
        pipeline=pipeline,
        runtime=PyGObjectAppSinkRuntime(),
        width=width,
        height=height,
        media_pipeline_mode=media_pipeline_mode,
        read_timeout_s=_FFMPEG_FRAME_WAIT_TIMEOUT_S,
    )
```

Then update `_open_jetson_gstreamer_capture_with_fallback()` to try `_open_gstreamer_appsink_capture()` before `_open_gstreamer_rawvideo_capture()`.

- [ ] **Step 4: Add backend methods to existing captures**

In `backend/src/argus/vision/camera.py`, add:

```python
def media_capture_backend(self) -> str:
    return "gstreamer_rawvideo_pipe"
```

to `_GStreamerRawVideoCapture`, and:

```python
def media_capture_backend(self) -> str:
    return "ffmpeg_rawvideo"
```

to `_FFmpegRawVideoCapture`.

- [ ] **Step 5: Run camera tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py backend/tests/vision/test_gstreamer_appsink.py -q
```

Expected: PASS.

## Task 6: Runtime Report And API Contract Coverage

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0047_worker_runtime_report_capture_backend.py`
- Modify: `backend/src/argus/services/supervisor_operations.py`
- Modify: `backend/src/argus/supervisor/operations_client.py`
- Modify: `backend/src/argus/supervisor/reconciler.py`
- Modify: `backend/tests/supervisor/test_operations_client.py`
- Modify: frontend OpenAPI generated files if this project regenerates them in the current branch

- [ ] **Step 1: Write failing API payload test**

In `backend/tests/supervisor/test_operations_client.py`, update the runtime report payload assertion:

```python
assert runtime_body["media_pipeline_mode"] == "jetson_gstreamer_native"
assert runtime_body["media_capture_backend"] == "gstreamer_appsink"
```

- [ ] **Step 2: Run the operations client test and verify it fails**

Run:

```bash
backend/.venv/bin/pytest backend/tests/supervisor/test_operations_client.py -k "runtime" -q
```

Expected: FAIL until the report payload model serializes `media_capture_backend`.

- [ ] **Step 3: Add serialization field**

Add the optional field wherever runtime reports are represented:

```python
media_capture_backend: str | None = None
```

In `backend/src/argus/models/tables.py`, add:

```python
media_capture_backend: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

Create `backend/src/argus/migrations/versions/0047_worker_runtime_report_capture_backend.py`:

```python
"""worker runtime report capture backend

Revision ID: 0047_worker_runtime_report_capture_backend
Revises: 0046_worker_runtime_report_media_fields
Create Date: 2026-06-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0047_worker_runtime_report_capture_backend"
down_revision = "0046_worker_runtime_report_media_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "worker_runtime_reports",
        sa.Column("media_capture_backend", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("worker_runtime_reports", "media_capture_backend")
```

When constructing outbound payloads, include the key if present:

```python
"media_capture_backend": report.media_capture_backend,
```

- [ ] **Step 4: Run contract tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/inference/test_engine.py backend/tests/supervisor/test_operations_client.py backend/tests/supervisor/test_reconciler.py -q
```

Expected: PASS.

## Task 7: Add Native NVMM/CUDA Lane Interface Without Making It Default

**Files:**
- Create: `backend/src/argus/vision/jetson_nvmm_capture.py`
- Create: `backend/tests/vision/test_jetson_nvmm_capture.py`
- Create: `backend/native/jetson_capture/README.md`

- [ ] **Step 1: Write failing native-lane contract tests**

Create `backend/tests/vision/test_jetson_nvmm_capture.py`:

```python
from __future__ import annotations

import numpy as np

from argus.vision.jetson_nvmm_capture import (
    NativeJetsonFrame,
    NativeJetsonUnavailable,
    probe_native_jetson_capture,
)


def test_native_frame_returns_bgr_numpy_copy() -> None:
    payload = np.arange(2 * 3 * 3, dtype=np.uint8).reshape((2, 3, 3))
    frame = NativeJetsonFrame(
        width=3,
        height=2,
        format="BGR",
        captured_at_monotonic=12.5,
        _bgr=payload,
    )

    observed = frame.as_bgr_numpy()

    np.testing.assert_array_equal(observed, payload)
    observed[0, 0, 0] = 255
    assert payload[0, 0, 0] != 255


def test_probe_reports_unavailable_without_native_extension() -> None:
    caps = probe_native_jetson_capture(import_name="argus_native_missing_for_test")

    assert caps.available is False
    assert caps.backend == "jetson_nvmm_native"
    assert "not installed" in caps.reason
```

- [ ] **Step 2: Run native-lane tests and verify they fail**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_jetson_nvmm_capture.py -q
```

Expected: FAIL because `argus.vision.jetson_nvmm_capture` does not exist.

- [ ] **Step 3: Implement optional native-lane Python interface**

Create `backend/src/argus/vision/jetson_nvmm_capture.py`:

```python
from __future__ import annotations

import importlib
from dataclasses import dataclass

import numpy as np


class NativeJetsonUnavailable(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class NativeJetsonCapabilities:
    available: bool
    backend: str = "jetson_nvmm_native"
    reason: str | None = None


@dataclass(slots=True)
class NativeJetsonFrame:
    width: int
    height: int
    format: str
    captured_at_monotonic: float
    _bgr: np.ndarray

    def as_bgr_numpy(self) -> np.ndarray:
        return self._bgr.copy()


def probe_native_jetson_capture(*, import_name: str = "argus_native_jetson_capture") -> NativeJetsonCapabilities:
    try:
        importlib.import_module(import_name)
    except ImportError:
        return NativeJetsonCapabilities(available=False, reason="native Jetson capture extension is not installed")
    except Exception as exc:
        return NativeJetsonCapabilities(available=False, reason=str(exc))
    return NativeJetsonCapabilities(available=True)
```

- [ ] **Step 4: Add native extension README**

Create `backend/native/jetson_capture/README.md`:

```markdown
# Jetson Native Capture Extension

This directory is reserved for the opt-in `jetson_nvmm_native` capture backend.

The extension must:

- Build only on Jetson/Linux aarch64 with NVIDIA multimedia/GStreamer development headers present.
- Keep RTSP decode and resize in NVIDIA media surfaces until the Python worker asks for a BGR NumPy frame.
- Expose the same worker semantics as `CameraSource`: `read()`, `release()`, `last_stage_timings()`, `media_pipeline_mode()`, and `media_capture_backend()`.
- Report unavailable status instead of changing the product default when the extension is absent.

The product default remains `gstreamer_appsink` until a live Jetson smoke proves that this backend improves FPS by at least 15% or lowers supervisor CPU by at least 20% at equivalent FPS.
```

- [ ] **Step 5: Run native-lane tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_jetson_nvmm_capture.py -q
```

Expected: PASS.

## Task 8: Add Config Gate For Capture Backend Selection

**Files:**
- Modify: `backend/src/argus/vision/camera.py`
- Modify: `backend/tests/vision/test_camera.py`
- Update config docs if the project has a central settings model for worker env vars

- [ ] **Step 1: Write failing config-gate tests**

Add to `backend/tests/vision/test_camera.py`:

```python
def test_jetson_capture_backend_env_can_disable_appsink(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    rawvideo_calls = 0

    def fail_appsink(*args: object, **kwargs: object) -> object:
        raise AssertionError("appsink disabled by env")

    def open_rawvideo(*args: object, **kwargs: object) -> _FakeCapture:
        nonlocal rawvideo_calls
        rawvideo_calls += 1
        return _FakeCapture([frame])

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "rawvideo")
    monkeypatch.setattr(camera_module, "_open_gstreamer_appsink_capture", fail_appsink)
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", open_rawvideo)

    capture = _default_capture_factory(
        "rtspsrc location=rtsp://camera.internal/live ! rtph264depay ! h264parse ! "
        "nvv4l2decoder ! nvvidconv ! video/x-raw,format=BGRx,width=1280,height=720 ! "
        "videoconvert ! video/x-raw,format=BGR,width=1280,height=720 ! "
        "appsink drop=true max-buffers=1 sync=false",
        cv2.CAP_GSTREAMER,
    )

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert rawvideo_calls == 1
```

- [ ] **Step 2: Run config-gate test and verify it fails**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py::test_jetson_capture_backend_env_can_disable_appsink -q
```

Expected: FAIL until the env gate exists.

- [ ] **Step 3: Implement selection parser**

In `backend/src/argus/vision/camera.py`, add:

```python
_JETSON_CAPTURE_BACKEND_ENV = "ARGUS_JETSON_CAPTURE_BACKEND"
_JETSON_CAPTURE_BACKEND_AUTO = "auto"
_JETSON_CAPTURE_BACKEND_APPSINK = "appsink"
_JETSON_CAPTURE_BACKEND_RAWVIDEO = "rawvideo"


def _jetson_capture_backend_preference() -> str:
    value = os.environ.get(_JETSON_CAPTURE_BACKEND_ENV, _JETSON_CAPTURE_BACKEND_AUTO).strip().lower()
    if value in {
        _JETSON_CAPTURE_BACKEND_AUTO,
        _JETSON_CAPTURE_BACKEND_APPSINK,
        _JETSON_CAPTURE_BACKEND_RAWVIDEO,
    }:
        return value
    LOGGER.warning(
        "Ignoring invalid %s value %r; using auto",
        _JETSON_CAPTURE_BACKEND_ENV,
        value,
    )
    return _JETSON_CAPTURE_BACKEND_AUTO
```

Use it in `_open_jetson_gstreamer_capture_with_fallback()`:

```python
backend_preference = _jetson_capture_backend_preference()
if backend_preference in {"auto", "appsink"}:
    try:
        return _open_gstreamer_appsink_capture(
            source,
            media_pipeline_mode=MediaPipelineMode.JETSON_GSTREAMER_NATIVE.value,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        if backend_preference == "appsink":
            raise
        LOGGER.warning(
            "Jetson appsink capture unavailable; falling back to rawvideo pipe: %s",
            _redact_capture_exception_message(exc, source=source),
            extra={"source_uri": _redact_gstreamer_source_uri(source)},
        )
```

- [ ] **Step 4: Run camera tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py -q
```

Expected: PASS.

## Task 9: Update Documentation

**Files:**
- Modify: `docs/model-loading-and-configuration-guide.md`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add operator-facing wording**

Document these runtime values:

```text
media_pipeline_mode=jetson_gstreamer_native
media_capture_backend=gstreamer_appsink
encoder_mode=software
```

State that Orin Nano may still report software encode even with NVIDIA decode active. The report is truthful when the hardware encoder is unavailable.

- [ ] **Step 2: Add sanitized smoke commands**

Add commands that avoid raw secrets:

```bash
ssh ai-user@192.168.1.203 'docker top vezor-supervisor -eo pid,ppid,pcpu,pmem,rss,etime,comm'
ssh ai-user@192.168.1.203 'docker stats --no-stream vezor-supervisor vezor-edge-mediamtx'
ssh ai-user@192.168.1.203 "docker exec vezor-supervisor sh -lc 'gst-inspect-1.0 nvv4l2decoder >/dev/null && gst-inspect-1.0 nvvidconv >/dev/null'"
```

Use a local note that RTSP URLs in reports must be redacted as:

```text
rtsp://***:***@<host>:8554/<path>
```

- [ ] **Step 3: Run docs grep for accidental secrets**

Run:

```bash
rg -n "rtsp://[^*][^\\s]*:[^*][^\\s]*@" docs backend/tests backend/src
```

Expected: no committed unredacted RTSP credentials.

## Task 10: Local Verification

**Files:**
- All modified files from Tasks 1-9

- [ ] **Step 1: Run formatting/lint on touched Python**

Run:

```bash
backend/.venv/bin/ruff check backend/src/argus/vision/camera.py backend/src/argus/vision/gstreamer_appsink.py backend/src/argus/vision/jetson_nvmm_capture.py backend/src/argus/inference/engine.py backend/tests/vision/test_camera.py backend/tests/vision/test_gstreamer_appsink.py backend/tests/vision/test_jetson_nvmm_capture.py backend/tests/inference/test_engine.py
```

Expected: PASS.

- [ ] **Step 2: Run targeted tests**

Run:

```bash
backend/.venv/bin/pytest backend/tests/vision/test_camera.py backend/tests/vision/test_gstreamer_appsink.py backend/tests/vision/test_jetson_nvmm_capture.py backend/tests/inference/test_engine.py backend/tests/supervisor/test_operations_client.py -q
```

Expected: PASS.

- [ ] **Step 3: Check whitespace**

Run:

```bash
git diff --check
```

Expected: no output.

## Task 11: Jetson Live Smoke And Evidence

**Files:**
- No source files changed during smoke. Rebuild/redeploy from the final branch only.

- [ ] **Step 1: Build and deploy from branch**

Run the existing edge build/deploy path for `codex/sceneops-pack-registry`. Do not hot patch files inside the running container.

- [ ] **Step 2: Confirm GStreamer runtime capabilities**

Run sanitized probes on the Jetson:

```bash
ssh ai-user@192.168.1.203 "docker exec vezor-supervisor sh -lc 'gst-inspect-1.0 --version && gst-inspect-1.0 nvv4l2decoder >/dev/null && gst-inspect-1.0 nvvidconv >/dev/null && python - <<\"PY\"
import gi
gi.require_version(\"Gst\", \"1.0\")
gi.require_version(\"GstApp\", \"1.0\")
from gi.repository import Gst
Gst.init(None)
print(\"pygobject-gstreamer-ok\")
PY'"
```

Expected: command succeeds and prints `pygobject-gstreamer-ok`.

- [ ] **Step 3: Capture before/after metrics**

For each backend (`rawvideo`, then `appsink`), run the worker long enough to collect a fresh runtime report and gather:

```bash
ssh ai-user@192.168.1.203 'docker stats --no-stream vezor-supervisor vezor-edge-mediamtx'
ssh ai-user@192.168.1.203 'docker top vezor-supervisor -eo pid,ppid,pcpu,pmem,rss,etime,comm'
ssh ai-user@192.168.1.203 'timeout 20s tegrastats'
```

Expected: no command output committed with unredacted RTSP credentials or tokens.

- [ ] **Step 4: Verify runtime report truth**

Use the existing sanitized database/API inspection command pattern and confirm:

```text
runtime_status=running
selected_inference_provider=tensorrt_engine
media_pipeline_mode=jetson_gstreamer_native
media_capture_backend=gstreamer_appsink
encoder_mode=software
heartbeat age < freshness threshold
```

Expected: all values come from a fresh per-camera runtime report.

- [ ] **Step 5: Produce closure report**

Write or update the live closure report under `docs/superpowers/status/` with sections:

```text
PASS
FAIL
BLOCKED
NOT RUN
```

Include measured FPS, CPU, memory, GR3D/VIC evidence when available, stage timing deltas, processed stream status, detections/history/evidence/billing status, and branch/commit used for deploy.

## Task 12: Commit Gate

**Files:**
- All source, test, and docs files changed by this plan

- [ ] **Step 1: Review worktree**

Run:

```bash
git status --short
git diff --stat
```

Expected: only intentional files are staged or ready to stage. Existing unrelated untracked files remain untouched.

- [ ] **Step 2: Ask before committing**

Before running `git add` or `git commit`, ask the user for explicit commit approval in the active session. Use a local commit only after approval. Do not push unless separately approved.
