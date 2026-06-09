from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from argus.supervisor.tensorrt_builder import TrtExecTensorRTEngineBuilder


def test_trtexec_builder_writes_engine_with_fp16(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "yolo26n.onnx"
    source.write_bytes(b"onnx")
    output = tmp_path / "yolo26n.engine"
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check):  # noqa: ANN001
        calls.append(list(command))
        output.write_bytes(b"engine")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="&&&& PASSED TensorRT.trtexec",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    builder = TrtExecTensorRTEngineBuilder(executable="trtexec")

    result = builder.build(
        source,
        output,
        {"batch": 1, "channels": 3, "height": 640, "width": 640},
        "fp16",
    )

    assert result == output
    assert output.read_bytes() == b"engine"
    assert f"--onnx={source}" in calls[0]
    assert f"--saveEngine={output}" in calls[0]
    assert str(source) not in calls[0]
    assert str(output) not in calls[0]
    assert "--fp16" in calls[0]


def test_trtexec_builder_raises_clear_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "bad.onnx"
    source.write_bytes(b"onnx")
    output = tmp_path / "bad.engine"

    def fake_run(command, capture_output, text, check):  # noqa: ANN001
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="parser failed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    builder = TrtExecTensorRTEngineBuilder(executable="trtexec")

    with pytest.raises(RuntimeError, match="parser failed"):
        builder.build(
            source,
            output,
            {"batch": 1, "channels": 3, "height": 640, "width": 640},
            "fp16",
        )
