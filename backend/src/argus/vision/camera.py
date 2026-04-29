from __future__ import annotations

import json
import os
import platform
import re
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

from argus.core.logging import redact_url_secrets

LOGGER = getLogger(__name__)

# Analyze long enough to catch the first H.264 SPS + keyframe even on slow
# streams (e.g. 5 fps with a 60-frame GOP = 12 s between keyframes), plus
# allowance for MediaMTX UDP→TCP renegotiation when first connecting upstream.
# ffmpeg's default 5 s analyzeduration was tripping on such streams and
# returning zero dimensions / empty media-info.
_FFMPEG_ANALYZE_DURATION_US = "60000000"  # 60 seconds
_FFMPEG_PROBE_SIZE = "64000000"  # 64 MB
_FFMPEG_DIMENSION_PROBE_TIMEOUT_S = 20.0
_FFMPEG_FRAME_WAIT_TIMEOUT_S = 20.0
_FFMPEG_RTSP_TIMEOUT_US = str(int(_FFMPEG_FRAME_WAIT_TIMEOUT_S * 1_000_000))
_OPENCV_CAPTURE_OPEN_TIMEOUT_MS = int(_FFMPEG_DIMENSION_PROBE_TIMEOUT_S * 1000)
_OPENCV_CAPTURE_READ_TIMEOUT_MS = int(_FFMPEG_FRAME_WAIT_TIMEOUT_S * 1000)
_OPENCV_FFMPEG_CAPTURE_OPTIONS = (
    f"rtsp_transport;tcp|analyzeduration;{_FFMPEG_ANALYZE_DURATION_US}"
    f"|probesize;{_FFMPEG_PROBE_SIZE}"
)

type Frame = NDArray[np.uint8]
type CaptureFactory = Callable[[str | int, int | None], CaptureHandle]
type MonotonicClock = Callable[[], float]
type SleepFunction = Callable[[float], None]
type SourceUriFactory = Callable[[], str]


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
    source_uri_factory: SourceUriFactory | None = None
    frame_skip: int = 1
    fps_cap: int = 25
    reconnect_backoff_base: float = 1.0
    reconnect_backoff_max: float = 60.0


class CameraSource:
    def __init__(
        self,
        *,
        config: CameraSourceConfig,
        platform_info: PlatformInfo,
        capture_factory: CaptureFactory,
        monotonic: MonotonicClock,
        sleep: SleepFunction,
    ) -> None:
        self.config = config
        self._platform_info = platform_info
        self.mode = CameraSourceMode.X86_RTSP
        self._source: str | int = config.source_uri
        self._backend: int | None = None
        self._current_source_uri = config.source_uri
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
        source_uri = self._resolve_source_uri()
        mode, source, backend = _resolve_capture_spec(source_uri, self._platform_info)
        self.mode = mode
        self._source = source
        self._backend = backend
        self._current_source_uri = source_uri
        return self._capture_factory(self._source, self._backend)

    def _resolve_source_uri(self) -> str:
        if self.config.source_uri_factory is None:
            return self.config.source_uri
        return self.config.source_uri_factory()

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
                "source_uri": redact_url_secrets(self._current_source_uri),
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
    return CameraSource(
        config=config,
        platform_info=resolved_platform,
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
            redacted_source = redact_url_secrets(source) if isinstance(source, str) else source
            LOGGER.warning(
                "FFmpeg rawvideo capture unavailable, falling back to OpenCV: %s",
                _redact_capture_exception_message(exc, source=source),
                extra={"source_uri": redacted_source},
            )
    if (
        backend == cv2.CAP_FFMPEG
        and isinstance(source, str)
        and source.startswith(("rtsp://", "rtsps://"))
        and "OPENCV_FFMPEG_CAPTURE_OPTIONS" not in os.environ
    ):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = _OPENCV_FFMPEG_CAPTURE_OPTIONS
    capture = _open_opencv_capture(source, backend)
    return cast(CaptureHandle, capture)


def _open_opencv_capture(source: str | int, backend: int | None) -> cv2.VideoCapture:
    if backend is not None:
        capture = cv2.VideoCapture(source, backend)
    else:
        capture = cv2.VideoCapture(source)
    _configure_opencv_capture(capture)
    return capture


def _configure_opencv_capture(capture: cv2.VideoCapture) -> None:
    setter = getattr(capture, "set", None)
    if not callable(setter):
        return

    for prop_id, value in (
        (getattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC", None), _OPENCV_CAPTURE_OPEN_TIMEOUT_MS),
        (getattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC", None), _OPENCV_CAPTURE_READ_TIMEOUT_MS),
    ):
        if prop_id is None:
            continue
        try:
            setter(prop_id, value)
        except Exception:  # pragma: no cover - backend-specific OpenCV failure
            continue

@dataclass(slots=True)
class _FFmpegRawVideoCapture:
    _process: subprocess.Popen[bytes]
    _width: int
    _height: int
    _source_uri: str
    _redacted_source_uri: str
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
            "-analyzeduration",
            _FFMPEG_ANALYZE_DURATION_US,
            "-probesize",
            _FFMPEG_PROBE_SIZE,
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
        instance = cls(
            _process=process,
            _width=width,
            _height=height,
            _source_uri=source_uri,
            _redacted_source_uri=redact_url_secrets(source_uri),
        )
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
                        self._stderr_tail.append(self._sanitize_stderr_line(line))
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

    def _sanitize_stderr_line(self, line: str) -> str:
        if self._redacted_source_uri == self._source_uri:
            return line
        return line.replace(self._source_uri, self._redacted_source_uri)

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


_FFMPEG_VIDEO_LINE_PATTERN = re.compile(
    r"Stream #\d+:\d+.*?Video:.*?\b(\d{2,5})x(\d{2,5})\b",
    re.DOTALL,
)


def _probe_video_dimensions(source_uri: str) -> tuple[int, int]:
    """Resolve the stream's frame size, with fallback to an ffmpeg one-frame probe.

    ffprobe is the cheap, fast first try. On RTSP relays that don't surface
    SPS dimensions in the SDP (observed with MediaMTX-fronted on-demand
    sources at low FPS), ffprobe returns a clean JSON payload but with
    width=0 / height=0. In that case we fall back to ffmpeg, which actually
    decodes a keyframe and prints the stream layout to stderr.
    """
    try:
        return _probe_via_ffprobe(source_uri)
    except RuntimeError as exc:
        LOGGER.warning(
            "ffprobe could not determine video dimensions; falling back to ffmpeg probe: %s",
            exc,
        )
    return _probe_via_ffmpeg(source_uri)


def _probe_via_ffprobe(source_uri: str) -> tuple[int, int]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-rtsp_transport",
        "tcp",
        "-timeout",
        _FFMPEG_RTSP_TIMEOUT_US,
        "-analyzeduration",
        _FFMPEG_ANALYZE_DURATION_US,
        "-probesize",
        _FFMPEG_PROBE_SIZE,
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        source_uri,
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=_FFMPEG_DIMENSION_PROBE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "ffprobe timed out while probing video dimensions "
            f"after {_FFMPEG_DIMENSION_PROBE_TIMEOUT_S:.0f}s."
        ) from exc
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    if not streams:
        raise RuntimeError(
            "ffprobe did not return a video stream. "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    raw_width = streams[0].get("width")
    raw_height = streams[0].get("height")
    try:
        width = int(raw_width) if raw_width is not None else 0
        height = int(raw_height) if raw_height is not None else 0
    except (TypeError, ValueError):
        raise RuntimeError(
            "ffprobe returned non-numeric video dimensions: "
            f"width={raw_width!r} height={raw_height!r} "
            f"stderr={completed.stderr!r}"
        ) from None
    if width <= 0 or height <= 0:
        raise RuntimeError(
            "ffprobe returned invalid video dimensions: "
            f"width={width} height={height} payload={payload!r} "
            f"stderr={completed.stderr!r}"
        )
    return width, height


def _probe_via_ffmpeg(source_uri: str) -> tuple[int, int]:
    """Fall-back probe: decode one frame with ffmpeg and parse stderr.

    ffmpeg prints `Stream #0:N: Video: h264 (...), yuv420p(...), 960x540, ...`
    once it has decoded the SPS for a keyframe. We regex the WxH out.
    """
    command = [
        "ffmpeg",
        "-v",
        "info",
        "-rtsp_transport",
        "tcp",
        "-timeout",
        _FFMPEG_RTSP_TIMEOUT_US,
        "-analyzeduration",
        _FFMPEG_ANALYZE_DURATION_US,
        "-probesize",
        _FFMPEG_PROBE_SIZE,
        "-i",
        source_uri,
        "-map",
        "0:v:0",
        "-frames:v",
        "1",
        "-f",
        "null",
        "-",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=_FFMPEG_DIMENSION_PROBE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "ffmpeg fallback probe timed out while probing video dimensions "
            f"after {_FFMPEG_DIMENSION_PROBE_TIMEOUT_S:.0f}s."
        ) from exc
    match = _FFMPEG_VIDEO_LINE_PATTERN.search(completed.stderr)
    if match is None:
        raise RuntimeError(
            "ffmpeg fallback probe did not report video dimensions. "
            f"returncode={completed.returncode} "
            f"stderr={completed.stderr[-2000:]!r}"
        )
    width = int(match.group(1))
    height = int(match.group(2))
    if width <= 0 or height <= 0:
        raise RuntimeError(
            f"ffmpeg fallback probe returned non-positive dimensions: "
            f"width={width} height={height}"
        )
    LOGGER.info(
        "ffmpeg fallback probe resolved video dimensions: %sx%s",
        width,
        height,
    )
    return width, height


def _redact_capture_exception_message(
    exc: BaseException,
    *,
    source: str | int,
) -> str:
    message = str(exc)
    if not isinstance(source, str):
        return message
    redacted_source = redact_url_secrets(source)
    if redacted_source == source:
        return message
    return message.replace(source, redacted_source)


def capture_still_image(source_uri: str) -> tuple[bytes, int, int]:
    capture = _default_capture_factory(source_uri, cv2.CAP_FFMPEG)
    deadline = time.monotonic() + _FFMPEG_FRAME_WAIT_TIMEOUT_S

    try:
        while time.monotonic() < deadline:
            success, frame = capture.read()
            if not success or frame is None or frame.size == 0:
                continue

            height, width = frame.shape[:2]
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                raise RuntimeError("OpenCV failed to encode setup preview frame as JPEG.")
            return encoded.tobytes(), int(width), int(height)
    finally:
        capture.release()

    raise RuntimeError(
        "Timed out while capturing a setup preview frame "
        f"after {_FFMPEG_FRAME_WAIT_TIMEOUT_S:.0f}s."
    )
