from __future__ import annotations

import io
import logging
import os
import subprocess
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
    create_camera_source,
)


class _FakeCapture:
    def __init__(self, frames: list[np.ndarray | None]) -> None:
        self._frames = deque(frames)
        self.released = False
        self.properties: dict[int, float] = {}

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._frames:
            return False, None
        frame = self._frames.popleft()
        return (frame is not None, frame)

    def set(self, prop_id: int, value: float) -> bool:
        self.properties[prop_id] = value
        return True

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
        "rtsp_transport;tcp|analyzeduration;60000000|probesize;64000000"
    )
    assert capture.properties[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC] == 20000
    assert capture.properties[cv2.CAP_PROP_READ_TIMEOUT_MSEC] == 20000


def test_ffmpeg_rtsp_timeout_covers_worker_first_frame_wait() -> None:
    assert camera_module._FFMPEG_RTSP_TIMEOUT_US == str(
        int(camera_module._FFMPEG_FRAME_WAIT_TIMEOUT_S * 1_000_000)
    )


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
    assert "-timeout" in created_commands[0]
    timeout_index = created_commands[0].index("-timeout")
    assert created_commands[0][timeout_index + 1] == "20000000"
    assert "-rw_timeout" not in created_commands[0]
    assert "-analyzeduration" in created_commands[0]
    analyze_index = created_commands[0].index("-analyzeduration")
    assert created_commands[0][analyze_index + 1] == "60000000"
    assert "-probesize" in created_commands[0]
    probesize_index = created_commands[0].index("-probesize")
    assert created_commands[0][probesize_index + 1] == "64000000"
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

    assert capture is fallback_capture
    assert any(
        "FFmpeg rawvideo capture unavailable, falling back to OpenCV"
        in record.message
        and "ffprobe did not return a video stream." in record.message
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

    assert capture is fallback_capture
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
    assert "-timeout" in command
    timeout_index = command.index("-timeout")
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
