from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np

from argus.vision.types import Detection

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "tracking_replay_benchmark.py"
SPEC = importlib.util.spec_from_file_location("tracking_replay_benchmark", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
run_benchmark = cast(Any, MODULE).run_benchmark


class FakeDetector:
    def detect(self, frame: object, classes: list[str]) -> list[Detection]:
        return [
            Detection(
                class_name=classes[0],
                class_id=0,
                confidence=0.92,
                bbox=(4.0, 5.0, 24.0, 45.0),
                track_id=101,
            )
        ]


def test_run_benchmark_summarizes_one_stable_person_track(tmp_path: Path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    assert cv2.imwrite(str(frames_dir / "000001.jpg"), frame)

    summary = run_benchmark(
        frames_path=frames_dir,
        classes=["person"],
        output_json=False,
        detector=FakeDetector(),
    )

    assert summary["frames_processed"] == 1
    assert summary["stable_tracks"] == 1
    assert summary["id_switches"] == 0
