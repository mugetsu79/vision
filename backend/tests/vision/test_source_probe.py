from __future__ import annotations

import subprocess

from argus.vision import source_probe


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
