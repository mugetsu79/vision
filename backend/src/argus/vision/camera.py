from __future__ import annotations

import platform
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from logging import getLogger
from typing import Protocol, cast

import cv2
import numpy as np
from numpy.typing import NDArray

LOGGER = getLogger(__name__)

type Frame = NDArray[np.uint8]
type CaptureFactory = Callable[[str | int, int | None], CaptureHandle]
type MonotonicClock = Callable[[], float]
type SleepFunction = Callable[[float], None]


class CaptureHandle(Protocol):
    def read(self) -> tuple[bool, Frame | None]: ...

    def release(self) -> None: ...


class CameraSourceMode(StrEnum):
    X86_RTSP = "x86-rtsp"
    JETSON_RTSP = "jetson-rtsp"
    JETSON_CSI = "jetson-csi"


@dataclass(slots=True, frozen=True)
class PlatformInfo:
    machine: str
    jetson: bool = False


@dataclass(slots=True, frozen=True)
class CameraSourceConfig:
    source_uri: str
    frame_skip: int = 1
    fps_cap: int = 25
    reconnect_backoff_base: float = 1.0
    reconnect_backoff_max: float = 60.0


class CameraSource:
    def __init__(
        self,
        *,
        config: CameraSourceConfig,
        mode: CameraSourceMode,
        source: str | int,
        backend: int | None,
        capture_factory: CaptureFactory,
        monotonic: MonotonicClock,
        sleep: SleepFunction,
    ) -> None:
        self.config = config
        self.mode = mode
        self._source = source
        self._backend = backend
        self._capture_factory = capture_factory
        self._monotonic = monotonic
        self._sleep = sleep
        self._capture = self._open_capture()
        self._raw_frame_index = 0
        self._last_yield_at: float | None = None
        self._reconnect_attempts = 0

    @property
    def reconnect_attempts(self) -> int:
        return self._reconnect_attempts

    def next_frame(self) -> Frame:
        self._throttle()
        while True:
            success, frame = self._capture.read()
            if not success or frame is None:
                self._reconnect()
                continue

            current_index = self._raw_frame_index
            self._raw_frame_index += 1
            if current_index % max(1, self.config.frame_skip) != 0:
                continue

            if self._last_yield_at is None:
                self._last_yield_at = self._monotonic()
            self._reconnect_attempts = 0
            return frame

    def close(self) -> None:
        self._capture.release()

    def _open_capture(self) -> CaptureHandle:
        return self._capture_factory(self._source, self._backend)

    def _throttle(self) -> None:
        if self._last_yield_at is None or self.config.fps_cap <= 0:
            return
        interval = 1.0 / float(self.config.fps_cap)
        now = self._monotonic()
        target = self._last_yield_at + interval
        if now < target:
            self._sleep(target - now)
            self._last_yield_at = target
        else:
            self._last_yield_at = now

    def _reconnect(self) -> None:
        self._capture.release()
        delay = min(
            self.config.reconnect_backoff_base * (2**self._reconnect_attempts),
            self.config.reconnect_backoff_max,
        )
        LOGGER.warning(
            "Camera capture lost, reconnecting",
            extra={
                "source_uri": self.config.source_uri,
                "mode": self.mode.value,
                "reconnect_delay_seconds": delay,
            },
        )
        self._sleep(delay)
        self._capture = self._open_capture()
        self._reconnect_attempts += 1


def create_camera_source(
    config: CameraSourceConfig,
    *,
    platform_info: PlatformInfo | None = None,
    capture_factory: CaptureFactory | None = None,
    monotonic: MonotonicClock = time.monotonic,
    sleep: SleepFunction = time.sleep,
) -> CameraSource:
    resolved_platform = platform_info or detect_platform()
    mode, source, backend = _resolve_capture_spec(config.source_uri, resolved_platform)
    return CameraSource(
        config=config,
        mode=mode,
        source=source,
        backend=backend,
        capture_factory=capture_factory or _default_capture_factory,
        monotonic=monotonic,
        sleep=sleep,
    )


def detect_platform() -> PlatformInfo:
    machine = platform.machine().lower()
    jetson = machine in {"aarch64", "arm64"} and _is_jetson_device()
    return PlatformInfo(machine=machine, jetson=jetson)


def _is_jetson_device() -> bool:
    try:
        with open("/etc/nv_tegra_release", encoding="utf-8"):
            return True
    except OSError:
        return False


def _resolve_capture_spec(
    source_uri: str,
    platform_info: PlatformInfo,
) -> tuple[CameraSourceMode, str | int, int | None]:
    if platform_info.jetson and source_uri.startswith("csi://"):
        sensor_id = source_uri.removeprefix("csi://") or "0"
        pipeline = (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            "video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1 ! "
            "nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! appsink"
        )
        return CameraSourceMode.JETSON_CSI, pipeline, cv2.CAP_GSTREAMER

    if platform_info.jetson:
        pipeline = (
            f"rtspsrc location={source_uri} latency=0 ! "
            "rtph264depay ! h264parse ! nvv4l2decoder ! nvvidconv ! "
            "video/x-raw,format=BGRx ! videoconvert ! appsink"
        )
        return CameraSourceMode.JETSON_RTSP, pipeline, cv2.CAP_GSTREAMER

    return CameraSourceMode.X86_RTSP, source_uri, cv2.CAP_FFMPEG


def _default_capture_factory(source: str | int, backend: int | None) -> CaptureHandle:
    capture = cv2.VideoCapture(source, backend) if backend is not None else cv2.VideoCapture(source)
    return cast(CaptureHandle, capture)
