from __future__ import annotations

import json
import os
import platform
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from logging import getLogger
from typing import Protocol, cast

import cv2
import numpy as np
from numpy.typing import NDArray

LOGGER = getLogger(__name__)

_FFMPEG_RTSP_TIMEOUT_US = "5000000"

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
    if _should_use_ffmpeg_rawvideo_capture(source=source, backend=backend):
        try:
            return _FFmpegRawVideoCapture.create(cast(str, source))
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            LOGGER.warning(
                "FFmpeg rawvideo capture unavailable, falling back to OpenCV: %s",
                exc,
                extra={"source_uri": source},
            )
    if (
        backend == cv2.CAP_FFMPEG
        and isinstance(source, str)
        and source.startswith(("rtsp://", "rtsps://"))
        and "OPENCV_FFMPEG_CAPTURE_OPTIONS" not in os.environ
    ):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    capture = cv2.VideoCapture(source, backend) if backend is not None else cv2.VideoCapture(source)
    return cast(CaptureHandle, capture)


_FFMPEG_FRAME_WAIT_TIMEOUT_S = 10.0


@dataclass(slots=True)
class _FFmpegRawVideoCapture:
    _process: subprocess.Popen[bytes]
    _width: int
    _height: int
    _stderr_tail: deque[str] = field(default_factory=lambda: deque(maxlen=20))
    _stderr_reported: bool = False
    _latest_frame: deque[Frame] = field(default_factory=lambda: deque(maxlen=1))
    _new_frame_event: threading.Event = field(default_factory=threading.Event)
    _frame_pump_done: bool = False

    @classmethod
    def create(cls, source_uri: str) -> _FFmpegRawVideoCapture:
        width, height = _probe_video_dimensions(source_uri)
        command = [
            "ffmpeg",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-timeout",
            _FFMPEG_RTSP_TIMEOUT_US,
            "-i",
            source_uri,
            "-map",
            "0:v:0",
            "-an",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "pipe:1",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=max(1, width * height * 3 * 2),
        )
        instance = cls(_process=process, _width=width, _height=height)
        instance._start_stderr_pump()
        instance._start_frame_pump()
        return instance

    def _start_stderr_pump(self) -> None:
        stderr = self._process.stderr
        if stderr is None:
            return

        def pump() -> None:
            try:
                for raw_line in stderr:
                    line = raw_line.decode("utf-8", errors="replace").rstrip()
                    if line:
                        self._stderr_tail.append(line)
            except (OSError, ValueError):
                return

        threading.Thread(target=pump, daemon=True).start()

    def _start_frame_pump(self) -> None:
        stdout = self._process.stdout
        if stdout is None:
            self._frame_pump_done = True
            self._new_frame_event.set()
            return

        frame_size = self._width * self._height * 3
        width = self._width
        height = self._height

        def pump() -> None:
            try:
                while True:
                    payload = stdout.read(frame_size)
                    if len(payload) != frame_size:
                        return
                    frame = np.frombuffer(payload, dtype=np.uint8).reshape(
                        (height, width, 3)
                    ).copy()
                    self._latest_frame.append(frame)
                    self._new_frame_event.set()
            except (OSError, ValueError):
                return
            finally:
                self._frame_pump_done = True
                self._new_frame_event.set()

        threading.Thread(target=pump, daemon=True).start()

    def read(self) -> tuple[bool, Frame | None]:
        if not self._new_frame_event.wait(timeout=_FFMPEG_FRAME_WAIT_TIMEOUT_S):
            self._report_stderr(
                f"no frame produced within {_FFMPEG_FRAME_WAIT_TIMEOUT_S:.0f}s"
            )
            return False, None
        self._new_frame_event.clear()
        try:
            frame = self._latest_frame[0]
        except IndexError:
            if self._frame_pump_done:
                self._report_stderr("ffmpeg frame pump exited")
            return False, None
        if self._frame_pump_done and len(self._latest_frame) == 0:
            self._report_stderr("ffmpeg frame pump exited")
            return False, None
        return True, frame

    def _report_stderr(self, reason: str) -> None:
        if self._stderr_reported:
            return
        self._stderr_reported = True
        tail = list(self._stderr_tail)
        if tail:
            LOGGER.warning(
                "ffmpeg rawvideo capture failed (%s); last stderr: %s",
                reason,
                " | ".join(tail),
            )
        else:
            LOGGER.warning(
                "ffmpeg rawvideo capture failed (%s); no stderr captured",
                reason,
            )

    def release(self) -> None:
        if self._process.poll() is not None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=2.0)


def _should_use_ffmpeg_rawvideo_capture(*, source: str | int, backend: int | None) -> bool:
    return (
        backend == cv2.CAP_FFMPEG
        and isinstance(source, str)
        and source.startswith(("rtsp://", "rtsps://"))
        and platform.system() == "Darwin"
        and platform.machine().lower() == "x86_64"
    )


def _probe_video_dimensions(source_uri: str) -> tuple[int, int]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-rtsp_transport",
        "tcp",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        source_uri,
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    if not streams:
        raise RuntimeError("ffprobe did not return a video stream.")
    width = int(streams[0]["width"])
    height = int(streams[0]["height"])
    if width <= 0 or height <= 0:
        raise RuntimeError("ffprobe returned invalid video dimensions.")
    return width, height
