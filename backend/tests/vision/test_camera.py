from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass

import numpy as np
import cv2

from argus.vision.camera import (
    CameraSourceConfig,
    PlatformInfo,
    _default_capture_factory,
    create_camera_source,
)


class _FakeCapture:
    def __init__(self, frames: list[np.ndarray | None]) -> None:
        self._frames = deque(frames)
        self.released = False

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._frames:
            return False, None
        frame = self._frames.popleft()
        return (frame is not None, frame)

    def release(self) -> None:
        self.released = True


@dataclass(slots=True)
class _CaptureCall:
    source: str | int
    backend: int | None


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
    assert "rtspsrc location=rtsp://camera.internal/live" in str(calls[0].source)
    assert "nvv4l2decoder" in str(calls[0].source)
    assert source.mode.value == "jetson-rtsp"


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
    clock_values = iter([0.0, 0.0, 0.1, 0.1, 0.55, 0.55])

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
        monotonic=lambda: next(clock_values),
        sleep=sleep_calls.append,
    )

    first = source.next_frame()
    second = source.next_frame()

    assert int(first[0, 0, 0]) == 1
    assert int(second[0, 0, 0]) == 3
    assert sleep_calls == [0.5, 1.0]
    assert source.reconnect_attempts == 0


def test_default_capture_factory_prefers_tcp_for_x86_rtsp(monkeypatch: object) -> None:
    calls: list[_CaptureCall] = []

    def fake_video_capture(source: str | int, backend: int | None = None) -> _FakeCapture:
        calls.append(_CaptureCall(source=source, backend=backend))
        return _FakeCapture([])

    monkeypatch.setattr(cv2, "VideoCapture", fake_video_capture)
    monkeypatch.delenv("OPENCV_FFMPEG_CAPTURE_OPTIONS", raising=False)

    _default_capture_factory("rtsp://camera.internal/live", cv2.CAP_FFMPEG)

    assert calls[0].source == "rtsp://camera.internal/live"
    assert calls[0].backend == cv2.CAP_FFMPEG
    assert os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] == "rtsp_transport;tcp"
