from __future__ import annotations

import subprocess

from argus.vision import source_probe


class _FakeUsbCapture:
    def __init__(self, source: str, backend: int) -> None:
        self.source = source
        self.backend = backend
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802
        return True

    def get(self, prop: int) -> float:
        if prop == source_probe.cv2.CAP_PROP_FRAME_WIDTH:
            return 1920
        if prop == source_probe.cv2.CAP_PROP_FRAME_HEIGHT:
            return 1080
        if prop == source_probe.cv2.CAP_PROP_FPS:
            return 30
        return 0

    def read(self):
        return False, None

    def release(self) -> None:
        self.released = True


def test_probe_rtsp_source_uses_client_socket_timeout(monkeypatch):
    captured_command: list[str] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        captured_command.extend(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=(
                '{"streams":[{"width":1280,"height":720,'
                '"codec_name":"h264","avg_frame_rate":"25/1","r_frame_rate":"25/1"}]}'
            ),
            stderr="",
        )

    monkeypatch.setattr(source_probe.subprocess, "run", fake_run)

    capability = source_probe.probe_rtsp_source("rtsp://camera.internal/live")

    assert capability.width == 1280
    assert capability.height == 720
    assert capability.fps == 25
    assert "-timeout" not in captured_command
    assert "-rw_timeout" in captured_command
    assert captured_command[captured_command.index("-rw_timeout") + 1] == "5000000"


def test_probe_usb_source_uses_v4l2_device(monkeypatch):
    captures: list[_FakeUsbCapture] = []

    def fake_video_capture(source: str, backend: int) -> _FakeUsbCapture:
        capture = _FakeUsbCapture(source, backend)
        captures.append(capture)
        return capture

    monkeypatch.setattr(source_probe.cv2, "VideoCapture", fake_video_capture)

    capability = source_probe.probe_usb_source("/dev/video0")

    assert captures[0].source == "/dev/video0"
    assert captures[0].backend == source_probe.cv2.CAP_V4L2
    assert captures[0].released is True
    assert capability.width == 1920
    assert capability.height == 1080
    assert capability.fps == 30
    assert capability.aspect_ratio == "16:9"
