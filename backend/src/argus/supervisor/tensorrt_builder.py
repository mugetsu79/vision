from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class TrtExecTensorRTEngineBuilder:
    def __init__(self, executable: str | None = None, workspace_mib: int = 2048) -> None:
        self.executable = executable or shutil.which("trtexec") or "/usr/src/tensorrt/bin/trtexec"
        self.workspace_mib = workspace_mib

    def available(self) -> bool:
        return Path(self.executable).exists() or shutil.which(self.executable) is not None

    def build(
        self,
        source_path: Path,
        output_path: Path,
        input_shape: dict[str, int],
        precision: str,
    ) -> Path:
        if not source_path.is_file():
            raise FileNotFoundError(f"TensorRT source model does not exist: {source_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.executable,
            f"--onnx={source_path}",
            f"--saveEngine={output_path}",
            f"--memPoolSize=workspace:{self.workspace_mib}",
        ]
        if precision.lower() == "fp16":
            command.append("--fp16")
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        if completed.returncode != 0:
            raise RuntimeError(f"TensorRT trtexec failed: {combined.strip()}")
        if not output_path.is_file() or output_path.stat().st_size <= 0:
            raise RuntimeError("TensorRT trtexec succeeded but did not write an engine file.")
        return output_path
