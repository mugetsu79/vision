from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _contains_forbidden_command_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            key in {"argv", "args", "cmdline", "command_line", "command"}
            or _contains_forbidden_command_key(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_command_key(item) for item in value)
    return False


def test_worker_perf_probe_outputs_sanitized_json_for_current_process() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "worker_perf_probe.py"),
            "--origin",
            "central",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload: dict[str, Any] = json.loads(result.stdout)
    assert payload["origin"] == "central"
    assert payload["environment_thread_settings"].keys() >= {
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
    }
    assert payload["process_cpu_seconds"]["available"] in {True, False}
    assert any("Dockerized CPU only" in note for note in payload["notes"])
    assert not _contains_forbidden_command_key(payload)
