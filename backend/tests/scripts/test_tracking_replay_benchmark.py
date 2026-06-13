from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np
import pytest

from argus.vision.types import Detection

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "tracking_replay_benchmark.py"
SPEC = importlib.util.spec_from_file_location("tracking_replay_benchmark", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
run_benchmark = cast(Any, MODULE).run_benchmark
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GATE_METADATA = {
    "effective_processing_fps": 15,
    "fixture_id": "tracker_continuity_people_001",
    "fixture_sha256": "a" * 64,
    "tracker_scene_profile": "difficult",
}


def _current_gate_summary(metrics: dict[str, object]) -> dict[str, object]:
    return GATE_METADATA | metrics


def _baseline_gate(metrics: dict[str, object]) -> dict[str, object]:
    return GATE_METADATA | {"metrics": metrics}


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


def _write_two_frame_fixture(tmp_path: Path) -> Path:
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    (fixture_dir / "manifest.json").write_text(
        json.dumps(
            {
                "fixture_id": "two_frame",
                "fps": 10,
                "frame_count": 2,
                "classes": ["person"],
                "tracker_scene_profile": "difficult",
                "iou_match_threshold": 0.5,
                "redacted": True,
            }
        ),
        encoding="utf-8",
    )
    detections = [
        {
            "frame_id": 1,
            "detections": [
                {
                    "class_name": "person",
                    "class_id": 0,
                    "confidence": 0.92,
                    "bbox": [0.0, 0.0, 10.0, 10.0],
                }
            ],
        },
        {
            "frame_id": 2,
            "detections": [
                {
                    "class_name": "person",
                    "class_id": 0,
                    "confidence": 0.94,
                    "bbox": [1.0, 0.0, 11.0, 10.0],
                }
            ],
        },
    ]
    (fixture_dir / "detections.jsonl").write_text(
        "\n".join(json.dumps(row) for row in detections) + "\n",
        encoding="utf-8",
    )
    ground_truth = [
        {
            "frame_id": 1,
            "gt_id": "person_1",
            "class_name": "person",
            "bbox": [0.0, 0.0, 10.0, 10.0],
            "visibility": 1.0,
            "ignore": False,
        },
        {
            "frame_id": 1,
            "gt_id": "person_2",
            "class_name": "person",
            "bbox": [40.0, 0.0, 50.0, 10.0],
            "visibility": 1.0,
            "ignore": False,
        },
        {
            "frame_id": 2,
            "gt_id": "person_1",
            "class_name": "person",
            "bbox": [1.0, 0.0, 11.0, 10.0],
            "visibility": 1.0,
            "ignore": False,
        },
        {
            "frame_id": 2,
            "gt_id": "person_2",
            "class_name": "person",
            "bbox": [41.0, 0.0, 51.0, 10.0],
            "visibility": 1.0,
            "ignore": False,
        },
    ]
    (fixture_dir / "ground_truth.jsonl").write_text(
        "\n".join(json.dumps(row) for row in ground_truth) + "\n",
        encoding="utf-8",
    )
    return fixture_dir


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


def test_run_fixture_benchmark_uses_ground_truth_metrics(tmp_path: Path) -> None:
    fixture = _write_two_frame_fixture(tmp_path)

    summary = MODULE.run_fixture_benchmark(
        fixture_dir=fixture,
        output_json=False,
        track_runner=lambda frame: [
            MODULE.ReplayTrack(
                stable_track_id=frame.frame_id,
                class_name="person",
                bbox=frame.ground_truth[0].bbox,
            )
        ],
    )

    assert summary["id_switches"] == 1
    assert summary["track_fragmentation_sum"] == 1


def test_run_fixture_benchmark_reports_fixture_hash_and_runtime_metric(
    tmp_path: Path,
) -> None:
    fixture = _write_two_frame_fixture(tmp_path)

    summary = MODULE.run_fixture_benchmark(
        fixture_dir=fixture,
        output_json=False,
        track_runner=lambda frame: [
            MODULE.ReplayTrack(
                stable_track_id=1,
                class_name="person",
                bbox=frame.ground_truth[0].bbox,
            )
        ],
    )

    assert len(summary["fixture_sha256"]) == 64
    assert float(summary["median_tracker_lifecycle_ms"]) >= 0.0


def test_fixture_cli_accepts_assert_improvement_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tracking_replay_benchmark.py",
            "--fixture",
            "fixture",
            "--baseline",
            "baseline.json",
            "--assert-improvement",
        ],
    )

    args = MODULE._parse_args()

    assert args.assert_improvement is True


def test_fixture_cli_requires_baseline_when_asserting_improvement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tracking_replay_benchmark.py",
            "--fixture",
            "fixture",
            "--assert-improvement",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        MODULE._parse_args()

    assert exc_info.value.code == 2


def test_replay_fixture_requires_ground_truth_identities(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    (fixture_dir / "manifest.json").write_text(
        json.dumps(
            {
                "fixture_id": "empty",
                "fps": 15,
                "frame_count": 1,
                "classes": ["person"],
                "iou_match_threshold": 0.5,
                "redacted": True,
            }
        ),
        encoding="utf-8",
    )
    (fixture_dir / "detections.jsonl").write_text(
        json.dumps({"frame_id": 1, "image": "frames/000001.jpg", "detections": []}) + "\n",
        encoding="utf-8",
    )
    (fixture_dir / "ground_truth.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="at least two distinct"):
        MODULE.load_replay_fixture(fixture_dir)


def test_evaluator_counts_id_switches_against_ground_truth() -> None:
    frames = [
        MODULE.ReplayFrame(
            frame_id=1,
            image_path=None,
            detections=[],
            ground_truth=[
                MODULE.GroundTruthObject(
                    frame_id=1,
                    gt_id="person_1",
                    class_name="person",
                    bbox=(0.0, 0.0, 10.0, 10.0),
                    visibility=1.0,
                    ignore=False,
                )
            ],
        ),
        MODULE.ReplayFrame(
            frame_id=2,
            image_path=None,
            detections=[],
            ground_truth=[
                MODULE.GroundTruthObject(
                    frame_id=2,
                    gt_id="person_1",
                    class_name="person",
                    bbox=(1.0, 0.0, 11.0, 10.0),
                    visibility=1.0,
                    ignore=False,
                )
            ],
        ),
    ]
    outputs = {
        1: [
            MODULE.ReplayTrack(
                stable_track_id=10,
                class_name="person",
                bbox=(0.0, 0.0, 10.0, 10.0),
            )
        ],
        2: [
            MODULE.ReplayTrack(
                stable_track_id=11,
                class_name="person",
                bbox=(1.0, 0.0, 11.0, 10.0),
            )
        ],
    }

    metrics = MODULE.evaluate_tracks(
        frames,
        track_outputs_by_frame=outputs,
        iou_match_threshold=0.5,
    )

    assert metrics["id_switches"] == 1
    assert metrics["track_fragmentation_sum"] == 1
    assert metrics["coverage_ratio"] == 1.0


def test_committed_replay_fixture_and_baseline_are_well_formed() -> None:
    manifest, frames = MODULE.load_replay_fixture(
        FIXTURES_DIR / "tracker_continuity_people_001"
    )
    assert manifest["fixture_id"] == "tracker_continuity_people_001"
    assert manifest["tracker_scene_profile"] == "difficult"
    assert manifest["redacted"] is True
    assert len(frames) == 220

    ground_truth = [
        gt for frame in frames for gt in frame.ground_truth if not gt.ignore
    ]
    assert len(ground_truth) == 440
    assert {gt.gt_id for gt in ground_truth} == {"person_1", "person_2"}
    assert all(frame.image_path is not None and frame.image_path.exists() for frame in frames)

    baseline = json.loads(
        (FIXTURES_DIR / "tracking_replay_baseline.json").read_text(encoding="utf-8")
    )
    assert baseline["fixture_sha256"]
    assert len(baseline["fixture_sha256"]) == 64
    metrics = baseline["metrics"]
    required_metric_keys = {
        "id_switches",
        "track_fragmentation_sum",
        "coverage_ratio",
        "median_track_lifetime_frames",
        "median_tracker_lifecycle_ms",
        "duplicate_active_track_frames",
    }
    assert required_metric_keys <= set(metrics)
    assert int(metrics["id_switches"]) + int(metrics["track_fragmentation_sum"]) >= 5


def test_committed_replay_fixture_meets_baseline_gate() -> None:
    baseline = json.loads(
        (FIXTURES_DIR / "tracking_replay_baseline.json").read_text(encoding="utf-8")
    )

    current = MODULE.run_fixture_benchmark(
        fixture_dir=FIXTURES_DIR / "tracker_continuity_people_001",
        output_json=False,
    )

    assert MODULE.compare_to_baseline(current, baseline) == []


def test_compare_to_baseline_rejects_weak_baseline() -> None:
    failures = MODULE.compare_to_baseline(
        _current_gate_summary({
            "id_switches": 0,
            "track_fragmentation_sum": 0,
            "coverage_ratio": 1.0,
            "median_track_lifetime_frames": 10,
            "duplicate_active_track_frames": 0,
            "median_tracker_lifecycle_ms": 9.0,
        }),
        _baseline_gate({
            "id_switches": 1,
            "track_fragmentation_sum": 1,
            "coverage_ratio": 1.0,
            "median_track_lifetime_frames": 10,
            "duplicate_active_track_frames": 0,
            "median_tracker_lifecycle_ms": 10.0,
        }),
    )

    assert failures == [
        "baseline continuity defects are below the required floor of 5"
    ]


def test_compare_to_baseline_rejects_fixture_digest_mismatch() -> None:
    current = _current_gate_summary({
        "id_switches": 0,
        "track_fragmentation_sum": 0,
        "coverage_ratio": 1.0,
        "median_track_lifetime_frames": 12,
        "duplicate_active_track_frames": 0,
        "median_tracker_lifecycle_ms": 9.0,
    })
    baseline = _baseline_gate({
        "id_switches": 4,
        "track_fragmentation_sum": 4,
        "coverage_ratio": 1.0,
        "median_track_lifetime_frames": 10,
        "duplicate_active_track_frames": 0,
        "median_tracker_lifecycle_ms": 10.0,
    }) | {"fixture_sha256": "b" * 64}

    assert MODULE.compare_to_baseline(current, baseline) == [
        "fixture_sha256 does not match baseline"
    ]


def test_compare_to_baseline_requires_fixture_metadata() -> None:
    current = {
        "effective_processing_fps": 15,
        "fixture_id": "tracker_continuity_people_001",
        "fixture_sha256": "a" * 64,
        "tracker_scene_profile": "difficult",
        "id_switches": 0,
        "track_fragmentation_sum": 0,
        "coverage_ratio": 1.0,
        "median_track_lifetime_frames": 12,
        "duplicate_active_track_frames": 0,
        "median_tracker_lifecycle_ms": 9.0,
    }
    baseline = {
        "metrics": {
            "id_switches": 4,
            "track_fragmentation_sum": 4,
            "coverage_ratio": 1.0,
            "median_track_lifetime_frames": 10,
            "duplicate_active_track_frames": 0,
            "median_tracker_lifecycle_ms": 10.0,
        },
    }

    assert MODULE.compare_to_baseline(current, baseline) == [
        "baseline missing fixture_id",
        "baseline missing fixture_sha256",
        "baseline missing tracker_scene_profile",
        "baseline missing effective_processing_fps",
    ]


def test_compare_to_baseline_rejects_fixture_metadata_mismatch() -> None:
    current = {
        "fixture_id": "current_fixture",
        "fixture_sha256": "a" * 64,
        "tracker_scene_profile": "difficult",
        "effective_processing_fps": 15,
        "id_switches": 0,
        "track_fragmentation_sum": 0,
        "coverage_ratio": 1.0,
        "median_track_lifetime_frames": 12,
        "duplicate_active_track_frames": 0,
        "median_tracker_lifecycle_ms": 9.0,
    }
    baseline = {
        "fixture_id": "baseline_fixture",
        "fixture_sha256": "a" * 64,
        "tracker_scene_profile": "efficient",
        "effective_processing_fps": 30,
        "metrics": {
            "id_switches": 4,
            "track_fragmentation_sum": 4,
            "coverage_ratio": 1.0,
            "median_track_lifetime_frames": 10,
            "duplicate_active_track_frames": 0,
            "median_tracker_lifecycle_ms": 10.0,
        },
    }

    assert MODULE.compare_to_baseline(current, baseline) == [
        "fixture_id does not match baseline",
        "tracker_scene_profile does not match baseline",
        "effective_processing_fps does not match baseline",
    ]


def test_compare_to_baseline_rejects_runtime_regression() -> None:
    current = _current_gate_summary({
        "id_switches": 0,
        "track_fragmentation_sum": 0,
        "coverage_ratio": 1.0,
        "median_track_lifetime_frames": 12,
        "duplicate_active_track_frames": 0,
        "median_tracker_lifecycle_ms": 11.1,
    })
    baseline = _baseline_gate({
        "id_switches": 4,
        "track_fragmentation_sum": 4,
        "coverage_ratio": 1.0,
        "median_track_lifetime_frames": 10,
        "duplicate_active_track_frames": 0,
        "median_tracker_lifecycle_ms": 10.0,
    })

    assert MODULE.compare_to_baseline(current, baseline) == [
        "median_tracker_lifecycle_ms regressed by more than 10 percent"
    ]


def test_compare_to_baseline_requires_runtime_metric() -> None:
    current = {
        "effective_processing_fps": 15,
        "fixture_id": "tracker_continuity_people_001",
        "fixture_sha256": "a" * 64,
        "tracker_scene_profile": "difficult",
        "id_switches": 0,
        "track_fragmentation_sum": 0,
        "coverage_ratio": 1.0,
        "median_track_lifetime_frames": 12,
        "duplicate_active_track_frames": 0,
        "median_tracker_lifecycle_ms": 9.0,
    }
    baseline = {
        "effective_processing_fps": 15,
        "fixture_id": "tracker_continuity_people_001",
        "fixture_sha256": "a" * 64,
        "tracker_scene_profile": "difficult",
        "metrics": {
            "id_switches": 4,
            "track_fragmentation_sum": 4,
            "coverage_ratio": 1.0,
            "median_track_lifetime_frames": 10,
            "duplicate_active_track_frames": 0,
        },
    }

    assert MODULE.compare_to_baseline(current, baseline) == [
        "baseline missing median_tracker_lifecycle_ms"
    ]
