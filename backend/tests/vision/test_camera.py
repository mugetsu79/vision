from __future__ import annotations

import io
import logging
import os
import subprocess
import threading
from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np
import pytest

import argus.vision.camera as camera_module
from argus.vision.camera import (
    CameraSourceConfig,
    PlatformInfo,
    _default_capture_factory,
    _FFmpegRawVideoCapture,
    _GStreamerRawVideoCapture,
    _LatestFrameCapture,
    _PrefetchedFrameCapture,
    create_camera_source,
)
from argus.vision.gstreamer_appsink import AppSinkCapabilities, AppSinkPipelineMode


class _FakeCapture:
    def __init__(self, frames: list[np.ndarray | None]) -> None:
        self._frames = deque(frames)
        self.released = False
        self.properties: dict[int, float] = {}
        self.read_count = 0

    def read(self) -> tuple[bool, np.ndarray | None]:
        self.read_count += 1
        if not self._frames:
            return False, None
        frame = self._frames.popleft()
        return (frame is not None, frame)

    def set(self, prop_id: int, value: float) -> bool:
        self.properties[prop_id] = value
        return True

    def release(self) -> None:
        self.released = True


class _TimedFakeCapture(_FakeCapture):
    def __init__(
        self,
        frames: list[np.ndarray | None],
        *,
        stage_timings: dict[str, float],
    ) -> None:
        super().__init__(frames)
        self._stage_timings = dict(stage_timings)

    def last_stage_timings(self) -> dict[str, float]:
        return dict(self._stage_timings)


class _ModeCapture(_FakeCapture):
    def __init__(self, frames: list[np.ndarray | None], *, media_pipeline_mode: str) -> None:
        super().__init__(frames)
        self._media_pipeline_mode = media_pipeline_mode

    def media_pipeline_mode(self) -> str:
        return self._media_pipeline_mode


class _UnknownModeCapture(_FakeCapture):
    def media_pipeline_mode(self) -> None:
        return None


class _BlockingReadCapture:
    def __init__(self) -> None:
        self.read_started = threading.Event()
        self.allow_read_exit = threading.Event()
        self.released = threading.Event()
        self.release_calls = 0

    def read(self) -> tuple[bool, np.ndarray | None]:
        self.read_started.set()
        self.allow_read_exit.wait(timeout=2.0)
        return False, None

    def release(self) -> None:
        self.release_calls += 1
        self.released.set()


@dataclass(slots=True)
class _CaptureCall:
    source: str | int
    backend: int | None


def _jetson_rtsp_pipeline() -> str:
    return (
        "rtspsrc location=rtsp://camera.internal/live protocols=tcp latency=200 "
        "drop-on-latency=true ! rtph264depay ! h264parse ! nvv4l2decoder ! "
        "nvvidconv ! video/x-raw,format=BGRx,width=1280,height=720 ! "
        "videoconvert ! video/x-raw,format=BGR,width=1280,height=720 ! "
        "appsink drop=true max-buffers=1 sync=false"
    )


def _quoted_secret_rtsp_pipeline() -> tuple[str, str, str, str, str]:
    user = "quoted" + "-user"
    password = "quoted" + "-password"
    jwt_value = "quoted" + "-jwt"
    source_uri = (
        "rtsp"
        + "://"
        + f"{user}:{password}"
        + '@camera.internal/live path/with"quote'
        + f"?jwt={jwt_value}&label=front\\door"
    )
    quoted_uri = source_uri.replace("\\", "\\\\").replace('"', '\\"')
    pipeline = (
        f'rtspsrc location="{quoted_uri}" protocols=tcp latency=200 '
        "drop-on-latency=true ! rtph264depay ! h264parse ! nvv4l2decoder ! "
        "nvvidconv ! video/x-raw,format=BGRx,width=1280,height=720 ! "
        "videoconvert ! video/x-raw,format=BGR,width=1280,height=720 ! "
        "appsink drop=true max-buffers=1 sync=false"
    )
    return pipeline, source_uri, user, password, jwt_value


def test_create_camera_source_uses_ffmpeg_capture_on_x86() -> None:
    calls: list[_CaptureCall] = []
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        calls.append(_CaptureCall(source=source, backend=backend))
        return _FakeCapture([frame])

    source = create_camera_source(
        CameraSourceConfig(source_uri="rtsp://camera.internal/live"),
        platform_info=PlatformInfo(machine="x86_64", jetson=False),
        capture_factory=capture_factory,
    )

    np.testing.assert_array_equal(source.next_frame(), frame)
    assert calls[0].source == "rtsp://camera.internal/live"
    assert calls[0].backend is not None
    assert source.mode.value == "x86-rtsp"
    assert source.media_pipeline_mode() == "ffmpeg_software"


def test_create_camera_source_reports_ffmpeg_when_x86_capture_mode_is_unknown() -> None:
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    def capture_factory(source: str | int, backend: int | None) -> _UnknownModeCapture:
        del source, backend
        return _UnknownModeCapture([frame])

    source = create_camera_source(
        CameraSourceConfig(source_uri="rtsp://camera.internal/live"),
        platform_info=PlatformInfo(machine="x86_64", jetson=False),
        capture_factory=capture_factory,
    )

    np.testing.assert_array_equal(source.next_frame(), frame)
    assert source.media_pipeline_mode() == "ffmpeg_software"


def test_create_camera_source_reports_opencv_ffmpeg_capture_backend_when_unknown() -> None:
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    def capture_factory(source: str | int, backend: int | None) -> _UnknownModeCapture:
        del source, backend
        return _UnknownModeCapture([frame])

    source = create_camera_source(
        CameraSourceConfig(source_uri="rtsp://camera.internal/live"),
        platform_info=PlatformInfo(machine="x86_64", jetson=False),
        capture_factory=capture_factory,
    )

    np.testing.assert_array_equal(source.next_frame(), frame)
    assert source.media_capture_backend() == "opencv_ffmpeg"


def test_create_camera_source_builds_jetson_rtsp_pipeline() -> None:
    calls: list[_CaptureCall] = []
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        calls.append(_CaptureCall(source=source, backend=backend))
        return _FakeCapture([frame])

    source = create_camera_source(
        CameraSourceConfig(source_uri="rtsp://camera.internal/live"),
        platform_info=PlatformInfo(machine="aarch64", jetson=True),
        capture_factory=capture_factory,
    )

    np.testing.assert_array_equal(source.next_frame(), frame)
    pipeline = str(calls[0].source)
    assert "rtspsrc location=rtsp://camera.internal/live" in pipeline
    assert "protocols=tcp" in pipeline
    assert "latency=200" in pipeline
    assert "nvv4l2decoder" in pipeline
    assert "appsink drop=true max-buffers=1 sync=false" in pipeline
    assert source.mode.value == "jetson-rtsp"


def test_create_camera_source_resizes_jetson_rtsp_in_gstreamer_pipeline() -> None:
    calls: list[_CaptureCall] = []
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        calls.append(_CaptureCall(source=source, backend=backend))
        return _FakeCapture([frame])

    source = create_camera_source(
        CameraSourceConfig(
            source_uri="rtsp://camera.internal/live",
            target_width=1280,
            target_height=720,
        ),
        platform_info=PlatformInfo(machine="aarch64", jetson=True),
        capture_factory=capture_factory,
    )

    np.testing.assert_array_equal(source.next_frame(), frame)
    pipeline = str(calls[0].source)
    assert "nvv4l2decoder ! nvvidconv" in pipeline
    assert "video/x-raw,format=BGRx,width=1280,height=720" in pipeline
    assert "video/x-raw,format=BGR,width=1280,height=720" in pipeline


def test_camera_source_reconfigures_jetson_rtsp_capture_dimensions() -> None:
    captures = [
        _FakeCapture([np.full((2, 2, 3), 1, dtype=np.uint8)]),
        _FakeCapture([np.full((3, 3, 3), 2, dtype=np.uint8)]),
    ]
    calls: list[_CaptureCall] = []

    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        calls.append(_CaptureCall(source=source, backend=backend))
        return captures.pop(0)

    source = create_camera_source(
        CameraSourceConfig(
            source_uri="rtsp://camera.internal/live",
            target_width=1280,
            target_height=720,
            fps_cap=25,
        ),
        platform_info=PlatformInfo(machine="aarch64", jetson=True),
        capture_factory=capture_factory,
    )

    source.reconfigure(target_width=1920, target_height=1080, fps_cap=20)

    frame = source.next_frame()
    initial_pipeline = str(calls[0].source)
    reconfigured_pipeline = str(calls[1].source)
    assert captures == []
    assert "video/x-raw,format=BGR,width=1280,height=720" in initial_pipeline
    assert "video/x-raw,format=BGR,width=1920,height=1080" in reconfigured_pipeline
    assert source.config.target_width == 1920
    assert source.config.target_height == 1080
    assert source.config.fps_cap == 20
    assert int(frame[0, 0, 0]) == 2


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


def test_capture_wrappers_delegate_precise_capture_backend() -> None:
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    class _BackendCapture(_FakeCapture):
        def media_capture_backend(self) -> str:
            return "gstreamer_rawvideo_pipe"

    prefetched = _PrefetchedFrameCapture(_BackendCapture([frame]), frame)
    latest = _LatestFrameCapture(_capture=_BackendCapture([frame]))

    assert prefetched.media_capture_backend() == "gstreamer_rawvideo_pipe"
    assert latest.media_capture_backend() == "gstreamer_rawvideo_pipe"


def test_rawvideo_captures_report_precise_capture_backend_names() -> None:
    gstreamer_capture = _GStreamerRawVideoCapture(
        _process=object(),
        _width=4,
        _height=4,
        _source_uri="rtsp://camera.internal/live",
        _redacted_source_uri="rtsp://camera.internal/live",
        _media_pipeline_mode="jetson_gstreamer_native",
    )
    ffmpeg_capture = _FFmpegRawVideoCapture(
        _process=object(),
        _width=4,
        _height=4,
        _source_uri="rtsp://camera.internal/live",
        _redacted_source_uri="rtsp://camera.internal/live",
    )

    assert gstreamer_capture.media_capture_backend() == "gstreamer_rawvideo_pipe"
    assert ffmpeg_capture.media_capture_backend() == "ffmpeg_rawvideo"


def test_create_camera_source_applies_jetson_rtsp_tuning_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[_CaptureCall] = []
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        calls.append(_CaptureCall(source=source, backend=backend))
        return _FakeCapture([frame])

    monkeypatch.setenv("ARGUS_JETSON_RTSP_PROTOCOLS", "udp")
    monkeypatch.setenv("ARGUS_JETSON_RTSP_LATENCY_MS", "50")
    monkeypatch.setenv("ARGUS_JETSON_RTSP_DROP_ON_LATENCY", "false")

    source = create_camera_source(
        CameraSourceConfig(source_uri="rtsp://camera.internal/live"),
        platform_info=PlatformInfo(machine="aarch64", jetson=True),
        capture_factory=capture_factory,
    )

    np.testing.assert_array_equal(source.next_frame(), frame)
    pipeline = str(calls[0].source)
    assert "protocols=udp" in pipeline
    assert "latency=50" in pipeline
    assert "drop-on-latency=false" in pipeline


def test_create_camera_source_builds_jetson_csi_pipeline() -> None:
    calls: list[_CaptureCall] = []
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        calls.append(_CaptureCall(source=source, backend=backend))
        return _FakeCapture([frame])

    source = create_camera_source(
        CameraSourceConfig(source_uri="csi://1"),
        platform_info=PlatformInfo(machine="aarch64", jetson=True),
        capture_factory=capture_factory,
    )

    np.testing.assert_array_equal(source.next_frame(), frame)
    assert "nvarguscamerasrc sensor-id=1" in str(calls[0].source)
    assert "appsink" in str(calls[0].source)
    assert source.mode.value == "jetson-csi"


def test_jetson_rtsp_capture_falls_back_to_software_decode_when_nvdec_has_no_frame(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    frame = np.full((4, 4, 3), 5, dtype=np.uint8)
    opened_sources: list[str] = []
    opened_modes: list[str] = []

    def open_raw_capture(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        opened_sources.append(source)
        opened_modes.append(media_pipeline_mode)
        if len(opened_sources) == 1:
            raise RuntimeError("NVDEC produced no first frame")
        return _ModeCapture([frame], media_pipeline_mode=media_pipeline_mode)

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "rawvideo")
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", open_raw_capture)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory(
        (
            "rtspsrc location=rtsp://camera.internal/live protocols=tcp latency=200 "
            "drop-on-latency=true ! rtph264depay ! h264parse ! nvv4l2decoder ! "
            "nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
            "video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false"
        ),
        cv2.CAP_GSTREAMER,
    )

    ok, actual_frame = capture.read()

    assert ok is True
    np.testing.assert_array_equal(actual_frame, frame)
    assert "nvv4l2decoder" in str(opened_sources[0])
    assert "avdec_h264" in str(opened_sources[1])
    assert "nvv4l2decoder" not in str(opened_sources[1])
    assert opened_modes == ["jetson_gstreamer_native", "jetson_gstreamer_software"]
    assert capture.media_pipeline_mode() == "jetson_gstreamer_software"
    assert any("falling back to software decode" in record.message for record in caplog.records)


def test_jetson_rtsp_capture_uses_native_gstreamer_rawvideo_before_opencv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.full((4, 4, 3), 6, dtype=np.uint8)
    opened_sources: list[str] = []
    opened_modes: list[str] = []

    def open_raw_capture(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        opened_sources.append(source)
        opened_modes.append(media_pipeline_mode)
        return _ModeCapture([frame], media_pipeline_mode=media_pipeline_mode)

    def fail_opencv_capture(source: str | int, backend: int | None) -> _FakeCapture:
        raise AssertionError(f"OpenCV should not read Jetson GStreamer RTSP: {source}, {backend}")

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "rawvideo")
    monkeypatch.setattr(
        camera_module,
        "_open_gstreamer_rawvideo_capture",
        open_raw_capture,
        raising=False,
    )
    monkeypatch.setattr(camera_module, "_open_opencv_capture", fail_opencv_capture)

    capture = _default_capture_factory(
        (
            "rtspsrc location=rtsp://camera.internal/live protocols=tcp latency=200 "
            "drop-on-latency=true ! rtph264depay ! h264parse ! nvv4l2decoder ! "
            "nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
            "video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false"
        ),
        cv2.CAP_GSTREAMER,
    )

    ok, actual_frame = capture.read()

    assert ok is True
    np.testing.assert_array_equal(actual_frame, frame)
    assert opened_sources == [
        (
            "rtspsrc location=rtsp://camera.internal/live protocols=tcp latency=200 "
            "drop-on-latency=true ! rtph264depay ! h264parse ! nvv4l2decoder ! "
            "nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
            "video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false"
        )
    ]
    assert opened_modes == ["jetson_gstreamer_native"]
    assert capture.media_pipeline_mode() == "jetson_gstreamer_native"


def test_jetson_rtsp_prefers_in_process_appsink_before_rawvideo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    calls: list[tuple[str, str]] = []

    class _AppSinkCapture(_FakeCapture):
        def media_pipeline_mode(self) -> str:
            return "jetson_gstreamer_native"

        def media_capture_backend(self) -> str:
            return "gstreamer_appsink"

    def open_appsink(source: str, *, media_pipeline_mode: str) -> _AppSinkCapture:
        calls.append((media_pipeline_mode, source))
        return _AppSinkCapture([frame])

    def fail_rawvideo(*args: object, **kwargs: object) -> object:
        raise AssertionError("rawvideo should not run when appsink succeeds")

    monkeypatch.setattr(
        camera_module,
        "_open_gstreamer_appsink_capture",
        open_appsink,
        raising=False,
    )
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", fail_rawvideo)

    capture = _default_capture_factory(_jetson_rtsp_pipeline(), cv2.CAP_GSTREAMER)

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert capture.media_pipeline_mode() == "jetson_gstreamer_native"
    assert capture.media_capture_backend() == "gstreamer_appsink"
    assert calls == [("jetson_gstreamer_native", _jetson_rtsp_pipeline())]


def test_jetson_rtsp_falls_back_to_rawvideo_when_appsink_first_frame_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    appsink_calls = 0
    rawvideo_calls = 0

    def fail_appsink(source: str, *, media_pipeline_mode: str) -> object:
        nonlocal appsink_calls
        assert source == _jetson_rtsp_pipeline()
        assert media_pipeline_mode == "jetson_gstreamer_native"
        appsink_calls += 1
        raise RuntimeError("appsink first frame timeout")

    def open_rawvideo(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        nonlocal rawvideo_calls
        assert source == _jetson_rtsp_pipeline()
        assert media_pipeline_mode == "jetson_gstreamer_native"
        rawvideo_calls += 1
        return _FakeCapture([frame])

    monkeypatch.setattr(
        camera_module,
        "_open_gstreamer_appsink_capture",
        fail_appsink,
        raising=False,
    )
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", open_rawvideo)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory(_jetson_rtsp_pipeline(), cv2.CAP_GSTREAMER)

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert appsink_calls == 1
    assert rawvideo_calls == 1
    assert any(
        "falling back to rawvideo pipe" in record.message
        and "appsink first frame timeout" in record.message
        for record in caplog.records
    )


def test_jetson_appsink_fallback_log_redacts_inner_rtsp_uri(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    user = "camera-user"
    password = "camera-secret"
    token_key = "jwt"
    token_value = "camera-token"
    source_uri = (
        "rtsp"
        + "://"
        + f"{user}:{password}"
        + "@camera.internal/live"
        + f"?{token_key}={token_value}"
    )
    pipeline_source = (
        f"rtspsrc location={source_uri} protocols=tcp latency=200 "
        "drop-on-latency=true ! rtph264depay ! h264parse ! nvv4l2decoder ! "
        "nvvidconv ! video/x-raw,format=BGRx,width=1280,height=720 ! "
        "videoconvert ! video/x-raw,format=BGR,width=1280,height=720 ! "
        "appsink drop=true max-buffers=1 sync=false"
    )

    def fail_appsink(source: str, *, media_pipeline_mode: str) -> object:
        assert source == pipeline_source
        assert media_pipeline_mode == "jetson_gstreamer_native"
        raise RuntimeError(f"appsink failed opening {source_uri}")

    def open_rawvideo(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        assert source == pipeline_source
        assert media_pipeline_mode == "jetson_gstreamer_native"
        return _FakeCapture([frame])

    monkeypatch.delenv("ARGUS_JETSON_CAPTURE_BACKEND", raising=False)
    monkeypatch.setattr(
        camera_module,
        "_open_gstreamer_appsink_capture",
        fail_appsink,
        raising=False,
    )
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", open_rawvideo)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory(pipeline_source, cv2.CAP_GSTREAMER)

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert any(
        "Jetson appsink capture unavailable; falling back to rawvideo pipe"
        in record.message
        for record in caplog.records
    )
    for record in caplog.records:
        assert password not in record.message
        assert token_value not in record.message
        assert password not in str(getattr(record, "source_uri", ""))
        assert token_value not in str(getattr(record, "source_uri", ""))


def test_jetson_appsink_fallback_log_redacts_full_pipeline_rtsp_uri(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    user = "pipeline" + "-user"
    password = "pipeline" + "-password"
    jwt_value = "pipeline" + "-jwt"
    source_uri = (
        "rtsp"
        + "://"
        + f"{user}:{password}"
        + "@camera.internal/live"
        + "?jwt="
        + jwt_value
    )
    pipeline_source = (
        f"rtspsrc location={source_uri} protocols=tcp latency=200 "
        "drop-on-latency=true ! rtph264depay ! h264parse ! nvv4l2decoder ! "
        "nvvidconv ! video/x-raw,format=BGRx,width=1280,height=720 ! "
        "videoconvert ! video/x-raw,format=BGR,width=1280,height=720 ! "
        "appsink drop=true max-buffers=1 sync=false"
    )

    def fail_appsink(source: str, *, media_pipeline_mode: str) -> object:
        assert source == pipeline_source
        assert media_pipeline_mode == "jetson_gstreamer_native"
        raise RuntimeError(f"pipeline failed: {source}")

    def open_rawvideo(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        assert source == pipeline_source
        assert media_pipeline_mode == "jetson_gstreamer_native"
        return _FakeCapture([frame])

    monkeypatch.delenv("ARGUS_JETSON_CAPTURE_BACKEND", raising=False)
    monkeypatch.setattr(
        camera_module,
        "_open_gstreamer_appsink_capture",
        fail_appsink,
        raising=False,
    )
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", open_rawvideo)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory(pipeline_source, cv2.CAP_GSTREAMER)

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert any(
        "Jetson appsink capture unavailable; falling back to rawvideo pipe"
        in record.message
        for record in caplog.records
    )
    for record in caplog.records:
        assert user not in record.message
        assert password not in record.message
        assert jwt_value not in record.message


def test_open_gstreamer_appsink_capture_builds_pipeline_from_jetson_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    probed_modes: list[AppSinkPipelineMode] = []
    build_kwargs: dict[str, object] = {}
    create_kwargs: dict[str, object] = {}
    runtime = object()

    class _AppSinkCaptureFactory:
        @classmethod
        def create(cls, **kwargs: object) -> _FakeCapture:
            create_kwargs.update(kwargs)
            return _FakeCapture([frame])

    def fake_probe(*, mode: AppSinkPipelineMode) -> AppSinkCapabilities:
        probed_modes.append(mode)
        return AppSinkCapabilities(
            available=True,
            appsink_supports_leaky_type=True,
            decoder_supports_disable_dpb=True,
        )

    def fake_build_rtsp_appsink_pipeline(source_uri: str, **kwargs: object) -> str:
        build_kwargs["source_uri"] = source_uri
        build_kwargs.update(kwargs)
        return "appsink-pipeline"

    monkeypatch.setenv("ARGUS_JETSON_RTSP_PROTOCOLS", "udp")
    monkeypatch.setenv("ARGUS_JETSON_RTSP_LATENCY_MS", "50")
    monkeypatch.setenv("ARGUS_JETSON_RTSP_DROP_ON_LATENCY", "false")
    monkeypatch.setattr(camera_module, "probe_appsink_capabilities", fake_probe, raising=False)
    monkeypatch.setattr(
        camera_module,
        "build_rtsp_appsink_pipeline",
        fake_build_rtsp_appsink_pipeline,
        raising=False,
    )
    monkeypatch.setattr(
        camera_module,
        "GStreamerAppSinkCapture",
        _AppSinkCaptureFactory,
        raising=False,
    )
    monkeypatch.setattr(
        camera_module,
        "PyGObjectAppSinkRuntime",
        lambda: runtime,
        raising=False,
    )
    monkeypatch.setattr(
        camera_module,
        "_probe_video_dimensions",
        lambda source_uri: (_ for _ in ()).throw(  # noqa: ARG005
            AssertionError("explicit BGR caps should avoid probing dimensions")
        ),
    )

    capture = camera_module._open_gstreamer_appsink_capture(
        _jetson_rtsp_pipeline(),
        media_pipeline_mode="jetson_gstreamer_native",
    )

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert probed_modes == [AppSinkPipelineMode.JETSON_NATIVE]
    assert build_kwargs == {
        "source_uri": "rtsp://camera.internal/live",
        "mode": AppSinkPipelineMode.JETSON_NATIVE,
        "target_width": 1280,
        "target_height": 720,
        "protocols": "udp",
        "latency_ms": 50,
        "drop_on_latency": False,
        "appsink_supports_leaky_type": True,
        "decoder_supports_disable_dpb": True,
    }
    assert create_kwargs == {
        "pipeline": "appsink-pipeline",
        "runtime": runtime,
        "width": 1280,
        "height": 720,
        "media_pipeline_mode": "jetson_gstreamer_native",
        "read_timeout_s": camera_module._FFMPEG_FRAME_WAIT_TIMEOUT_S,
    }


def test_open_gstreamer_appsink_capture_releases_capture_when_initial_read_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    released: list[bool] = []

    class _ReadRaisesCapture:
        def read(self) -> tuple[bool, np.ndarray | None]:
            raise RuntimeError("appsink buffer map failed")

        def release(self) -> None:
            released.append(True)

    class _AppSinkCaptureFactory:
        @classmethod
        def create(cls, **kwargs: object) -> _ReadRaisesCapture:
            del kwargs
            return _ReadRaisesCapture()

    monkeypatch.setattr(
        camera_module,
        "probe_appsink_capabilities",
        lambda *, mode: AppSinkCapabilities(available=True),  # noqa: ARG005
        raising=False,
    )
    monkeypatch.setattr(
        camera_module,
        "build_rtsp_appsink_pipeline",
        lambda *args, **kwargs: "appsink-pipeline",
        raising=False,
    )
    monkeypatch.setattr(
        camera_module,
        "GStreamerAppSinkCapture",
        _AppSinkCaptureFactory,
        raising=False,
    )
    monkeypatch.setattr(
        camera_module,
        "PyGObjectAppSinkRuntime",
        lambda: object(),
        raising=False,
    )

    with pytest.raises(RuntimeError, match="appsink buffer map failed"):
        camera_module._open_gstreamer_appsink_capture(
            _jetson_rtsp_pipeline(),
            media_pipeline_mode="jetson_gstreamer_native",
        )

    assert released == [True]


def test_extract_gstreamer_source_uri_unquotes_quoted_location() -> None:
    pipeline, source_uri, _user, _password, _jwt_value = _quoted_secret_rtsp_pipeline()

    assert camera_module._extract_gstreamer_source_uri(pipeline) == source_uri


def test_redact_gstreamer_source_uri_redacts_quoted_location_and_exception_messages() -> None:
    pipeline, source_uri, user, password, jwt_value = _quoted_secret_rtsp_pipeline()

    redacted_pipeline = camera_module._redact_gstreamer_source_uri(pipeline)
    redacted_message = camera_module._redact_gstreamer_capture_exception_message(
        RuntimeError(f"pipeline failed: {pipeline}; inner uri: {source_uri}"),
        source=pipeline,
    )

    assert 'location="' in redacted_pipeline
    assert "rtsp://redacted@camera.internal" in redacted_pipeline
    assert "jwt=redacted" in redacted_pipeline
    assert camera_module._extract_gstreamer_source_uri(redacted_pipeline) is not None
    for secret in (user, password, jwt_value):
        assert secret not in redacted_pipeline
        assert secret not in redacted_message


def test_redact_gstreamer_exception_message_redacts_nested_quoted_location() -> None:
    pipeline, _source_uri, user, password, jwt_value = _quoted_secret_rtsp_pipeline()

    redacted_message = camera_module._redact_gstreamer_capture_exception_message(
        RuntimeError(f"outer capture failed; nested error: {pipeline}"),
        source=_jetson_rtsp_pipeline(),
    )

    leaked_secrets = [
        name
        for name, value in {
            "user": user,
            "password": password,
            "jwt": jwt_value,
        }.items()
        if value in redacted_message
    ]
    assert leaked_secrets == []
    assert 'location="' in redacted_message
    assert "rtsp://redacted@camera.internal" in redacted_message
    assert "jwt=redacted" in redacted_message
    assert camera_module._extract_gstreamer_source_uri(redacted_message) is not None


def test_jetson_software_gstreamer_prefers_appsink_before_rawvideo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    appsink_modes: list[str] = []
    rawvideo_modes: list[str] = []

    class _SoftwareAppSinkCapture(_FakeCapture):
        def media_pipeline_mode(self) -> str:
            return "jetson_gstreamer_software"

        def media_capture_backend(self) -> str:
            return "gstreamer_appsink"

    def open_appsink(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        appsink_modes.append(media_pipeline_mode)
        if media_pipeline_mode == "jetson_gstreamer_native":
            raise RuntimeError("native appsink unavailable")
        assert "avdec_h264" in source
        return _SoftwareAppSinkCapture([frame])

    def fail_rawvideo(source: str, *, media_pipeline_mode: str) -> object:
        rawvideo_modes.append(media_pipeline_mode)
        if media_pipeline_mode == "jetson_gstreamer_native":
            raise RuntimeError("native rawvideo unavailable")
        raise AssertionError("software rawvideo should not run when appsink succeeds")

    monkeypatch.setattr(
        camera_module,
        "_open_gstreamer_appsink_capture",
        open_appsink,
        raising=False,
    )
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", fail_rawvideo)

    capture = _default_capture_factory(_jetson_rtsp_pipeline(), cv2.CAP_GSTREAMER)

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert appsink_modes == ["jetson_gstreamer_native", "jetson_gstreamer_software"]
    assert rawvideo_modes == ["jetson_gstreamer_native"]
    assert capture.media_pipeline_mode() == "jetson_gstreamer_software"
    assert capture.media_capture_backend() == "gstreamer_appsink"


def test_jetson_capture_backend_env_can_disable_appsink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    rawvideo_calls = 0

    def fail_appsink(*args: object, **kwargs: object) -> object:
        raise AssertionError("appsink disabled by env")

    def open_rawvideo(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        nonlocal rawvideo_calls
        assert source == _jetson_rtsp_pipeline()
        assert media_pipeline_mode == "jetson_gstreamer_native"
        rawvideo_calls += 1
        return _FakeCapture([frame])

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "rawvideo")
    monkeypatch.setattr(camera_module, "_open_gstreamer_appsink_capture", fail_appsink)
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", open_rawvideo)

    capture = _default_capture_factory(_jetson_rtsp_pipeline(), cv2.CAP_GSTREAMER)

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert rawvideo_calls == 1


def test_jetson_capture_backend_env_requires_appsink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rawvideo_calls = 0

    def fail_appsink(source: str, *, media_pipeline_mode: str) -> object:
        assert source == _jetson_rtsp_pipeline()
        assert media_pipeline_mode == "jetson_gstreamer_native"
        raise RuntimeError("appsink first frame timeout")

    def open_rawvideo(*args: object, **kwargs: object) -> _FakeCapture:
        nonlocal rawvideo_calls
        rawvideo_calls += 1
        return _FakeCapture([np.zeros((720, 1280, 3), dtype=np.uint8)])

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "appsink")
    monkeypatch.setattr(camera_module, "_open_gstreamer_appsink_capture", fail_appsink)
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", open_rawvideo)

    with pytest.raises(RuntimeError, match="appsink first frame timeout"):
        _default_capture_factory(_jetson_rtsp_pipeline(), cv2.CAP_GSTREAMER)

    assert rawvideo_calls == 0


def test_jetson_capture_backend_invalid_env_warns_and_uses_auto(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    appsink_calls = 0

    class _AppSinkCapture(_FakeCapture):
        def media_capture_backend(self) -> str:
            return "gstreamer_appsink"

    def open_appsink(source: str, *, media_pipeline_mode: str) -> _AppSinkCapture:
        nonlocal appsink_calls
        assert source == _jetson_rtsp_pipeline()
        assert media_pipeline_mode == "jetson_gstreamer_native"
        appsink_calls += 1
        return _AppSinkCapture([frame])

    def fail_rawvideo(*args: object, **kwargs: object) -> object:
        raise AssertionError("auto mode should prefer appsink before rawvideo")

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "sideways")
    monkeypatch.setattr(camera_module, "_open_gstreamer_appsink_capture", open_appsink)
    monkeypatch.setattr(camera_module, "_open_gstreamer_rawvideo_capture", fail_rawvideo)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory(_jetson_rtsp_pipeline(), cv2.CAP_GSTREAMER)

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert appsink_calls == 1
    assert any(
        "Ignoring invalid ARGUS_JETSON_CAPTURE_BACKEND value" in record.message
        and "sideways" in record.message
        and "using auto" in record.message
        for record in caplog.records
    )


def test_jetson_rtsp_capture_falls_back_to_ffmpeg_rawvideo_when_gstreamer_has_no_frame(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    frame = np.full((4, 4, 3), 7, dtype=np.uint8)
    username = "user"
    password = "secret"
    source_uri = (
        "rtsp"
        + "://"
        + f"{username}:{password}"
        + "@camera.internal/live"
    )
    gstreamer_sources: list[str] = []
    raw_sources: list[str] = []

    def open_raw_gstreamer_capture(source: str, *, media_pipeline_mode: str) -> _FakeCapture:
        del media_pipeline_mode
        gstreamer_sources.append(source)
        raise RuntimeError("GStreamer produced no first frame")

    def create_raw_capture(cls: type[object], source_uri: str) -> _FakeCapture:
        del cls
        raw_sources.append(source_uri)
        return _ModeCapture([frame], media_pipeline_mode="ffmpeg_software")

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "rawvideo")
    monkeypatch.setattr(
        camera_module,
        "_open_gstreamer_rawvideo_capture",
        open_raw_gstreamer_capture,
    )
    monkeypatch.setattr(
        camera_module,
        "_open_opencv_capture",
        lambda source, backend: (_ for _ in ()).throw(  # noqa: ARG005
            AssertionError("OpenCV fallback should not run when ffmpeg rawvideo works")
        ),
    )
    monkeypatch.setattr(
        camera_module._FFmpegRawVideoCapture,
        "create",
        classmethod(create_raw_capture),
    )
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory(
        (
            f"rtspsrc location={source_uri} protocols=tcp latency=200 "
            "drop-on-latency=true ! rtph264depay ! h264parse ! "
            "nvv4l2decoder ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
            "video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false"
        ),
        cv2.CAP_GSTREAMER,
    )

    ok, actual_frame = capture.read()

    assert ok is True
    np.testing.assert_array_equal(actual_frame, frame)
    assert "nvv4l2decoder" in gstreamer_sources[0]
    assert "avdec_h264" in gstreamer_sources[1]
    assert raw_sources == [source_uri]
    assert capture.media_pipeline_mode() == "ffmpeg_software"
    assert any("ffmpeg rawvideo fallback is active" in record.message for record in caplog.records)
    assert all(
        password not in str(getattr(record, "source_uri", ""))
        for record in caplog.records
    )


def test_jetson_final_opencv_gstreamer_fallback_reports_capture_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.full((4, 4, 3), 8, dtype=np.uint8)
    opencv_capture = _FakeCapture([frame])
    opencv_calls: list[_CaptureCall] = []

    def fail_raw_gstreamer_capture(source: str, *, media_pipeline_mode: str) -> object:
        del source, media_pipeline_mode
        raise RuntimeError("GStreamer unavailable")

    def open_opencv_capture(source: str | int, backend: int | None) -> _FakeCapture:
        opencv_calls.append(_CaptureCall(source=source, backend=backend))
        return opencv_capture

    monkeypatch.setenv("ARGUS_JETSON_CAPTURE_BACKEND", "rawvideo")
    monkeypatch.setattr(
        camera_module,
        "_open_gstreamer_rawvideo_capture",
        fail_raw_gstreamer_capture,
    )
    monkeypatch.setattr(
        camera_module,
        "_try_open_rawvideo_capture_from_gstreamer_source",
        lambda source: None,  # noqa: ARG005
    )
    monkeypatch.setattr(camera_module, "_open_opencv_capture", open_opencv_capture)

    capture = _default_capture_factory(_jetson_rtsp_pipeline(), cv2.CAP_GSTREAMER)

    ok, observed = capture.read()

    assert ok is True
    np.testing.assert_array_equal(observed, frame)
    assert opencv_calls == [
        _CaptureCall(
            source=camera_module._jetson_software_decode_pipeline(_jetson_rtsp_pipeline()),
            backend=cv2.CAP_GSTREAMER,
        )
    ]
    assert capture.media_capture_backend() == "opencv_gstreamer"


def test_camera_source_honors_frame_skip_and_reconnect_backoff() -> None:
    capture_attempts = [
        _FakeCapture(
            [
                np.full((2, 2, 3), 1, dtype=np.uint8),
                np.full((2, 2, 3), 2, dtype=np.uint8),
                None,
            ]
        ),
        _FakeCapture(
            [
                np.full((2, 2, 3), 3, dtype=np.uint8),
                np.full((2, 2, 3), 4, dtype=np.uint8),
            ]
        ),
    ]
    sleep_calls: list[float] = []
    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        return capture_attempts.pop(0)

    source = create_camera_source(
        CameraSourceConfig(
            source_uri="rtsp://camera.internal/live",
            frame_skip=2,
            fps_cap=2,
        ),
        platform_info=PlatformInfo(machine="x86_64", jetson=False),
        capture_factory=capture_factory,
        monotonic=lambda: 0.0,
        sleep=sleep_calls.append,
    )

    first = source.next_frame()
    second = source.next_frame()

    assert int(first[0, 0, 0]) == 1
    assert int(second[0, 0, 0]) == 3
    assert sleep_calls == [0.5, 1.0]
    assert source.reconnect_attempts == 0


def test_camera_source_exposes_capture_substage_timings() -> None:
    frame = np.full((2, 2, 3), 8, dtype=np.uint8)
    clock_values = iter([0.0, 0.0, 1.0, 1.02, 1.02])

    def capture_factory(source: str | int, backend: int | None) -> _TimedFakeCapture:
        del source, backend
        return _TimedFakeCapture(
            [frame],
            stage_timings={"wait": 0.125, "decode_read": 0.025},
        )

    source = create_camera_source(
        CameraSourceConfig(source_uri="rtsp://camera.internal/live", fps_cap=0),
        platform_info=PlatformInfo(machine="x86_64", jetson=False),
        capture_factory=capture_factory,
        monotonic=lambda: next(clock_values),
    )

    np.testing.assert_array_equal(source.next_frame(), frame)

    assert source.last_stage_timings()["throttle"] == pytest.approx(0.0)
    assert source.last_stage_timings()["read"] == pytest.approx(0.02)
    assert source.last_stage_timings()["wait"] == pytest.approx(0.125)
    assert source.last_stage_timings()["decode_read"] == pytest.approx(0.025)
    assert source.last_stage_timings()["reconnect"] == pytest.approx(0.0)


def test_camera_source_refreshes_source_uri_on_reconnect_and_redacts_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    capture_attempts = [
        _FakeCapture([None]),
        _FakeCapture([np.full((2, 2, 3), 7, dtype=np.uint8)]),
    ]
    capture_calls: list[_CaptureCall] = []
    source_uris = iter(
        [
            "rtsp://mediamtx.internal:8554/cameras/cam/passthrough?jwt=stale-token",
            "rtsp://mediamtx.internal:8554/cameras/cam/passthrough?jwt=fresh-token",
        ]
    )
    sleep_calls: list[float] = []

    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        capture_calls.append(_CaptureCall(source=source, backend=backend))
        return capture_attempts.pop(0)

    caplog.set_level(logging.WARNING, logger="argus.vision.camera")
    source = create_camera_source(
        CameraSourceConfig(
            source_uri="rtsp://mediamtx.internal:8554/cameras/cam/passthrough?jwt=initial-token",
            source_uri_factory=lambda: next(source_uris),
            reconnect_backoff_base=0.25,
            reconnect_backoff_max=0.25,
        ),
        platform_info=PlatformInfo(machine="x86_64", jetson=False),
        capture_factory=capture_factory,
        sleep=sleep_calls.append,
    )

    frame = source.next_frame()

    assert int(frame[0, 0, 0]) == 7
    assert [call.source for call in capture_calls] == [
        "rtsp://mediamtx.internal:8554/cameras/cam/passthrough?jwt=stale-token",
        "rtsp://mediamtx.internal:8554/cameras/cam/passthrough?jwt=fresh-token",
    ]
    assert sleep_calls == [0.25]
    assert any(
        "Camera capture lost, reconnecting" in record.message
        and "jwt=redacted" in str(record.source_uri)
        and "stale-token" not in str(record.source_uri)
        for record in caplog.records
    )


def test_camera_source_retries_when_reconnect_open_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reconnect_frame = np.full((2, 2, 3), 9, dtype=np.uint8)
    capture_attempts: list[_FakeCapture | RuntimeError] = [
        _FakeCapture([None]),
        RuntimeError("temporary RTSP open failure"),
        _FakeCapture([reconnect_frame]),
    ]
    sleep_calls: list[float] = []

    def capture_factory(source: str | int, backend: int | None) -> _FakeCapture:
        del source, backend
        attempt = capture_attempts.pop(0)
        if isinstance(attempt, RuntimeError):
            raise attempt
        return attempt

    caplog.set_level(logging.WARNING, logger="argus.vision.camera")
    source = create_camera_source(
        CameraSourceConfig(
            source_uri="rtsp://camera.internal/live",
            reconnect_backoff_base=0.25,
            reconnect_backoff_max=1.0,
        ),
        platform_info=PlatformInfo(machine="x86_64", jetson=False),
        capture_factory=capture_factory,
        sleep=sleep_calls.append,
    )

    frame = source.next_frame()

    np.testing.assert_array_equal(frame, reconnect_frame)
    assert sleep_calls == [0.25, 0.5]
    assert source.reconnect_attempts == 0
    assert any(
        "Camera reconnect attempt failed" in record.message
        and "temporary RTSP open failure" not in record.message
        for record in caplog.records
    )


def test_default_capture_factory_prefers_tcp_for_x86_rtsp(monkeypatch: object) -> None:
    calls: list[_CaptureCall] = []
    capture = _FakeCapture([])

    def fake_video_capture(source: str | int, backend: int | None = None) -> _FakeCapture:
        calls.append(_CaptureCall(source=source, backend=backend))
        return capture

    monkeypatch.setattr(cv2, "VideoCapture", fake_video_capture)
    monkeypatch.delenv("OPENCV_FFMPEG_CAPTURE_OPTIONS", raising=False)

    _default_capture_factory("rtsp://camera.internal/live", cv2.CAP_FFMPEG)

    assert calls[0].source == "rtsp://camera.internal/live"
    assert calls[0].backend == cv2.CAP_FFMPEG
    assert os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] == (
        "rtsp_transport;tcp|analyzeduration;60000000|probesize;64000000|timeout;20000000"
    )
    assert capture.properties[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC] == 20000
    assert capture.properties[cv2.CAP_PROP_READ_TIMEOUT_MSEC] == 20000


def test_ffmpeg_rtsp_timeout_covers_worker_first_frame_wait() -> None:
    assert camera_module._FFMPEG_RTSP_TIMEOUT_US == str(
        int(camera_module._FFMPEG_FRAME_WAIT_TIMEOUT_S * 1_000_000)
    )


def test_ffmpeg_rtsp_timeout_uses_socket_io_timeout_on_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(camera_module.platform, "system", lambda: "Linux")

    timeout_args = camera_module._ffmpeg_rtsp_timeout_args()

    assert timeout_args == ["-stimeout", "20000000"]


def test_latest_frame_capture_release_waits_for_pump_before_releasing() -> None:
    raw_capture = _BlockingReadCapture()
    capture = camera_module._LatestFrameCapture.create(
        raw_capture,
        read_timeout_s=0.01,
        release_join_timeout_s=0.01,
    )
    assert raw_capture.read_started.wait(timeout=1.0)

    capture.release()

    assert raw_capture.release_calls == 0
    raw_capture.allow_read_exit.set()
    assert raw_capture.released.wait(timeout=1.0)
    assert raw_capture.release_calls == 1


def test_default_capture_factory_uses_ffmpeg_rawvideo_on_intel_macos_rtsp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.arange(2 * 4 * 3, dtype=np.uint8).reshape(2, 4, 3)
    created_commands: list[list[str]] = []
    created_bufsizes: list[int] = []

    class _FakeStdout:
        def __init__(self, chunks: list[bytes]) -> None:
            self._chunks = deque(chunks)

        def read(self, size: int) -> bytes:
            if not self._chunks:
                return b""
            chunk = self._chunks.popleft()
            assert len(chunk) == size
            return chunk

    class _FakeProcess:
        def __init__(self, payload: bytes) -> None:
            self.stdout = _FakeStdout([payload])
            self.stderr = io.BytesIO(b"")
            self._returncode: int | None = None

        def poll(self) -> int | None:
            return self._returncode

        def terminate(self) -> None:
            self._returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            self._returncode = 0
            return 0

        def kill(self) -> None:
            self._returncode = -9

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ):
        assert check is True
        assert capture_output is True
        assert text is True
        assert timeout == 20.0
        assert command[:4] == ["ffprobe", "-v", "error", "-rtsp_transport"]
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"streams":[{"width":4,"height":2}]}',
            stderr="",
        )

    def fake_popen(command: list[str], stdout: object, stderr: object, bufsize: int):
        del stdout, stderr
        created_commands.append(command)
        created_bufsizes.append(bufsize)
        return _FakeProcess(frame.tobytes())

    monkeypatch.setattr(camera_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(camera_module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(camera_module.subprocess, "run", fake_run)
    monkeypatch.setattr(camera_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("OpenCV VideoCapture should not be used on Intel macOS RTSP.")
        ),
    )

    capture = _default_capture_factory("rtsp://camera.internal/live", cv2.CAP_FFMPEG)
    ok, decoded = capture.read()

    assert ok is True
    assert decoded is not None
    assert np.array_equal(decoded, frame)
    capture.release()
    assert created_commands[0][:4] == ["ffmpeg", "-loglevel", "error", "-rtsp_transport"]
    assert "-rw_timeout" not in created_commands[0]
    assert "-timeout" not in created_commands[0]
    assert "-stimeout" in created_commands[0]
    timeout_index = created_commands[0].index("-stimeout")
    assert created_commands[0][timeout_index + 1] == "20000000"
    assert "-analyzeduration" in created_commands[0]
    analyze_index = created_commands[0].index("-analyzeduration")
    assert created_commands[0][analyze_index + 1] == "60000000"
    assert "-probesize" in created_commands[0]
    probesize_index = created_commands[0].index("-probesize")
    assert created_commands[0][probesize_index + 1] == "64000000"
    assert created_bufsizes == [0]


def test_gstreamer_rawvideo_capture_uses_nvdec_pipeline_with_fdsink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.arange(2 * 4 * 3, dtype=np.uint8).reshape(2, 4, 3)
    created_commands: list[list[str]] = []
    created_bufsizes: list[int] = []

    class _FakeStdout:
        def __init__(self, chunks: list[bytes]) -> None:
            self._chunks = deque(chunks)

        def read(self, size: int) -> bytes:
            if not self._chunks:
                return b""
            chunk = self._chunks.popleft()
            assert len(chunk) == size
            return chunk

    class _FakeProcess:
        def __init__(self, payload: bytes) -> None:
            self.stdout = _FakeStdout([payload])
            self.stderr = io.BytesIO(b"")
            self._returncode: int | None = None

        def poll(self) -> int | None:
            return self._returncode

        def terminate(self) -> None:
            self._returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            self._returncode = 0
            return 0

        def kill(self) -> None:
            self._returncode = -9

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ):
        assert check is True
        assert capture_output is True
        assert text is True
        assert timeout == 20.0
        assert command[0] == "ffprobe"
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"streams":[{"width":4,"height":2}]}',
            stderr="",
        )

    def fake_popen(command: list[str], stdout: object, stderr: object, bufsize: int):
        del stdout, stderr
        created_commands.append(command)
        created_bufsizes.append(bufsize)
        return _FakeProcess(frame.tobytes())

    monkeypatch.setattr(camera_module.subprocess, "run", fake_run)
    monkeypatch.setattr(camera_module.subprocess, "Popen", fake_popen)

    capture = camera_module._GStreamerRawVideoCapture.create(
        "rtspsrc location=rtsp://camera.internal/live protocols=tcp latency=200 "
        "drop-on-latency=true ! rtph264depay ! h264parse ! nvv4l2decoder ! "
        "nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
        "video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false"
    )
    ok, decoded = capture.read()

    assert ok is True
    assert decoded is not None
    assert np.array_equal(decoded, frame)
    capture.release()
    assert created_commands[0][:2] == ["gst-launch-1.0", "-q"]
    assert "nvv4l2decoder" in created_commands[0]
    assert "fdsink" in created_commands[0]
    assert "appsink" not in created_commands[0]
    assert "video/x-raw,format=BGR,width=4,height=2" in created_commands[0]
    assert created_bufsizes == [0]


def test_default_capture_factory_logs_ffmpeg_rawvideo_failure_reason(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fallback_capture = _FakeCapture([])

    monkeypatch.setattr(camera_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(camera_module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(
        camera_module._FFmpegRawVideoCapture,
        "create",
        classmethod(
            lambda cls, source_uri: (_ for _ in ()).throw(  # noqa: ARG005
                RuntimeError("ffprobe did not return a video stream.")
            )
        ),
    )
    monkeypatch.setattr(cv2, "VideoCapture", lambda source, backend=None: fallback_capture)
    monkeypatch.delenv("OPENCV_FFMPEG_CAPTURE_OPTIONS", raising=False)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory("rtsp://camera.internal/live", cv2.CAP_FFMPEG)

    assert capture is not fallback_capture
    capture.release()
    assert fallback_capture.released is True
    assert any(
        "FFmpeg rawvideo capture unavailable, falling back to OpenCV"
        in record.message
        and "ffprobe did not return a video stream." in record.message
        for record in caplog.records
    )


def test_default_capture_factory_falls_back_when_rawvideo_has_no_first_frame(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _NoFrameCapture:
        released = False

        def read(self) -> tuple[bool, np.ndarray | None]:
            return False, None

        def release(self) -> None:
            self.released = True

    raw_capture = _NoFrameCapture()
    fallback_capture = _FakeCapture([np.zeros((4, 4, 3), dtype=np.uint8)])

    monkeypatch.setattr(camera_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(camera_module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(
        camera_module._FFmpegRawVideoCapture,
        "create",
        classmethod(lambda cls, source_uri: raw_capture),  # noqa: ARG005
    )
    monkeypatch.setattr(cv2, "VideoCapture", lambda source, backend=None: fallback_capture)
    monkeypatch.delenv("OPENCV_FFMPEG_CAPTURE_OPTIONS", raising=False)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory("rtsp://camera.internal/live", cv2.CAP_FFMPEG)

    for _ in range(20):
        if fallback_capture.read_count > 0:
            break
        import time as _time

        _time.sleep(0.01)

    assert capture is not raw_capture
    assert fallback_capture.read_count > 0
    assert raw_capture.released is True
    assert any(
        "FFmpeg rawvideo capture unavailable, falling back to OpenCV"
        in record.message
        and "produced no first frame" in record.message
        for record in caplog.records
    )


def test_default_capture_factory_redacts_probe_timeout_source_uri(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fallback_capture = _FakeCapture([])
    source_uri = "rtsp://camera.internal/live?jwt=super-secret-token"

    monkeypatch.setattr(camera_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(camera_module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(
        camera_module._FFmpegRawVideoCapture,
        "create",
        classmethod(
            lambda cls, source_uri: (_ for _ in ()).throw(  # noqa: ARG005
                subprocess.TimeoutExpired(
                    cmd=["ffmpeg", "-i", source_uri],
                    timeout=120,
                )
            )
        ),
    )
    monkeypatch.setattr(cv2, "VideoCapture", lambda source, backend=None: fallback_capture)
    monkeypatch.delenv("OPENCV_FFMPEG_CAPTURE_OPTIONS", raising=False)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = _default_capture_factory(source_uri, cv2.CAP_FFMPEG)

    assert capture is not fallback_capture
    capture.release()
    assert fallback_capture.released is True
    assert any(
        "FFmpeg rawvideo capture unavailable, falling back to OpenCV"
        in record.message
        and "jwt=redacted" in record.message
        and "super-secret-token" not in record.message
        for record in caplog.records
    )


def test_ffmpeg_rawvideo_capture_logs_stderr_when_process_exits(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    stderr_payload = (
        b"[rtsp @ 0x1] method DESCRIBE failed: 401 Unauthorized\n"
        b"rtsp://camera.internal/live: Server returned 401 Unauthorized\n"
    )

    class _ExitedProcess:
        def __init__(self) -> None:
            self.stdout = io.BytesIO(b"")
            self.stderr = io.BytesIO(stderr_payload)
            self._returncode: int | None = 1

        def poll(self) -> int | None:
            return self._returncode

        def terminate(self) -> None:
            self._returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            return self._returncode or 0

        def kill(self) -> None:
            self._returncode = -9

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ):
        del check, capture_output, text
        assert timeout == 20.0
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"streams":[{"width":16,"height":12}]}',
            stderr="",
        )

    def fake_popen(command: list[str], stdout: object, stderr: object, bufsize: int):
        del command, stdout, stderr, bufsize
        return _ExitedProcess()

    monkeypatch.setattr(camera_module.subprocess, "run", fake_run)
    monkeypatch.setattr(camera_module.subprocess, "Popen", fake_popen)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = camera_module._FFmpegRawVideoCapture.create("rtsp://camera.internal/live")
    # Give the stderr pump a chance to drain before we probe read().
    import time as _time

    for _ in range(20):
        if capture._stderr_tail:
            break
        _time.sleep(0.01)

    ok, frame = capture.read()

    assert ok is False
    assert frame is None
    assert any(
        "ffmpeg rawvideo capture failed" in record.message
        and "401 Unauthorized" in record.message
        for record in caplog.records
    )


def test_ffmpeg_rawvideo_capture_redacts_source_uri_in_stderr_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source_uri = "rtsp://camera.internal/live?jwt=super-secret-token"
    stderr_payload = f"{source_uri}: Connection timed out\n".encode()

    class _ExitedProcess:
        def __init__(self) -> None:
            self.stdout = io.BytesIO(b"")
            self.stderr = io.BytesIO(stderr_payload)
            self._returncode: int | None = 1

        def poll(self) -> int | None:
            return self._returncode

        def terminate(self) -> None:
            self._returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            return self._returncode or 0

        def kill(self) -> None:
            self._returncode = -9

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ):
        del check, capture_output, text
        assert timeout == 20.0
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"streams":[{"width":16,"height":12}]}',
            stderr="",
        )

    def fake_popen(command: list[str], stdout: object, stderr: object, bufsize: int):
        del command, stdout, stderr, bufsize
        return _ExitedProcess()

    monkeypatch.setattr(camera_module.subprocess, "run", fake_run)
    monkeypatch.setattr(camera_module.subprocess, "Popen", fake_popen)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    capture = camera_module._FFmpegRawVideoCapture.create(source_uri)
    import time as _time

    for _ in range(20):
        if capture._stderr_tail:
            break
        _time.sleep(0.01)

    ok, frame = capture.read()

    assert ok is False
    assert frame is None
    assert any(
        "ffmpeg rawvideo capture failed" in record.message
        and "jwt=redacted" in record.message
        and "super-secret-token" not in record.message
        for record in caplog.records
    )


def test_ffmpeg_rawvideo_capture_assembles_frame_from_pipe_chunks() -> None:
    frame = np.arange(2 * 4 * 3, dtype=np.uint8).reshape(2, 4, 3)
    payload = frame.tobytes()

    class _ChunkedStdout:
        def __init__(self) -> None:
            self._chunks = deque([payload[:5], payload[5:17], payload[17:]])

        def read(self, size: int) -> bytes:
            del size
            return b""

        def read1(self, size: int) -> bytes:
            if not self._chunks:
                return b""
            chunk = self._chunks.popleft()
            return chunk[:size]

    class _FakeProcess:
        stdout = _ChunkedStdout()
        stderr = io.BytesIO(b"")

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def kill(self) -> None:
            return None

    capture = camera_module._FFmpegRawVideoCapture(
        _process=_FakeProcess(),
        _width=4,
        _height=2,
        _source_uri="rtsp://camera.internal/live",
        _redacted_source_uri="rtsp://camera.internal/live",
    )

    capture._start_frame_pump()
    ok, decoded = capture.read()

    assert ok is True
    assert decoded is not None
    assert np.array_equal(decoded, frame)


def test_probe_video_dimensions_falls_back_to_ffmpeg_when_ffprobe_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When ffprobe reports valid JSON but width=0/height=0, fall back to the
    ffmpeg one-frame probe and parse dimensions out of stderr."""
    calls: list[str] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        if command[0] == "ffprobe":
            calls.append("ffprobe")
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout='{"streams":[{"width":0,"height":0}]}',
                stderr="",
            )
        if command[0] == "ffmpeg":
            calls.append("ffmpeg")
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="",
                stderr=(
                    "Input #0, rtsp, from 'rtsp://...':\n"
                    "  Stream #0:0: Audio: aac, 48000 Hz, mono, fltp\n"
                    "  Stream #0:1: Video: h264 (Main), yuv420p(progressive),"
                    " 960x540, 5 fps, 5 tbr\n"
                    "Output #0, null, to 'pipe:':\n"
                ),
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(camera_module.subprocess, "run", fake_run)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    width, height = camera_module._probe_video_dimensions("rtsp://relay/stream")

    assert (width, height) == (960, 540)
    assert calls == ["ffprobe", "ffmpeg"]
    assert any(
        "falling back to ffmpeg probe" in record.message for record in caplog.records
    )


def test_probe_video_dimensions_falls_back_to_ffmpeg_when_ffprobe_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    username = "user"
    password = "secret"
    source_uri = "rtsp" + "://" + f"{username}:{password}" + "@relay/stream"
    calls: list[str] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        if command[0] == "ffprobe":
            calls.append("ffprobe")
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=command,
                stderr=f"failed to open {source_uri}",
            )
        if command[0] == "ffmpeg":
            calls.append("ffmpeg")
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="",
                stderr=(
                    f"Input #0, rtsp, from '{source_uri}':\n"
                    "  Stream #0:0: Audio: aac, 16000 Hz, mono, fltp\n"
                    "  Stream #0:1: Video: h264 (Main), yuv420p(progressive),"
                    " 1280x720, 25 fps, 25 tbr\n"
                    "Output #0, null, to 'pipe:':\n"
                ),
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(camera_module.subprocess, "run", fake_run)
    caplog.set_level(logging.WARNING, logger="argus.vision.camera")

    width, height = camera_module._probe_video_dimensions(source_uri)

    assert (width, height) == (1280, 720)
    assert calls == ["ffprobe", "ffmpeg"]
    assert any(
        "falling back to ffmpeg probe" in record.message
        and password not in record.message
        for record in caplog.records
    )


def test_probe_via_ffmpeg_uses_rtsp_timeout_and_redacts_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_uri = "rtsp://relay/stream?jwt=super-secret-token"
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        raise subprocess.TimeoutExpired(cmd=command, timeout=float(kwargs["timeout"]))

    monkeypatch.setattr(camera_module.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="timed out"):
        camera_module._probe_via_ffmpeg(source_uri)

    command = captured["command"]
    assert isinstance(command, list)
    assert "-rw_timeout" not in command
    assert "-timeout" not in command
    assert "-stimeout" in command
    timeout_index = command.index("-stimeout")
    assert command[timeout_index + 1] == "20000000"
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["timeout"] == 20.0


def test_ffmpeg_rawvideo_capture_waits_20_seconds_for_first_frame() -> None:
    class _FakeEvent:
        def __init__(self) -> None:
            self.wait_calls: list[float] = []

        def wait(self, timeout: float | None = None) -> bool:
            self.wait_calls.append(float(timeout))
            return False

        def clear(self) -> None:
            return None

        def set(self) -> None:
            return None

    class _FakeProcess:
        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def kill(self) -> None:
            return None

    fake_event = _FakeEvent()
    capture = camera_module._FFmpegRawVideoCapture(
        _process=_FakeProcess(),
        _width=16,
        _height=12,
        _source_uri="rtsp://camera.internal/live",
        _redacted_source_uri="rtsp://camera.internal/live",
        _new_frame_event=fake_event,
    )

    ok, frame = capture.read()

    assert ok is False
    assert frame is None
    assert fake_event.wait_calls == [20.0]
