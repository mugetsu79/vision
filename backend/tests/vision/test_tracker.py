from __future__ import annotations

import numpy as np
import pytest

from argus.models.enums import TrackerType
from argus.vision.tracker import TrackerConfig, create_tracker
from argus.vision.types import Detection


class _FakeTrackerBackend:
    def __init__(self, tracker_name: str) -> None:
        self.tracker_name = tracker_name

    def update(self, results, img=None, feats=None):  # noqa: ANN001
        rows = []
        for index, bbox in enumerate(results.xyxy):
            rows.append(
                [
                    bbox[0],
                    bbox[1],
                    bbox[2],
                    bbox[3],
                    100 + index,
                    results.conf[index],
                    results.cls[index],
                    index,
                ]
            )
        return rows


def test_tracker_factory_wraps_backend_and_assigns_track_ids() -> None:
    config = TrackerConfig(tracker_type=TrackerType.BYTETRACK, frame_rate=15)
    tracker = create_tracker(
        config,
        backend_factory=lambda tracker_name, tracker_config: _FakeTrackerBackend(tracker_name),
    )

    tracked = tracker.update(
        [
            Detection(
                class_name="person",
                confidence=0.95,
                bbox=(10.0, 10.0, 40.0, 80.0),
                class_id=2,
            ),
            Detection(
                class_name="hi_vis_worker",
                confidence=0.97,
                bbox=(45.0, 12.0, 90.0, 84.0),
                class_id=3,
            ),
        ]
    )

    assert tracker.name == "bytetrack"
    assert [detection.track_id for detection in tracked] == [100, 101]
    assert [detection.class_name for detection in tracked] == ["person", "hi_vis_worker"]


def test_tracker_supports_botsort_selection() -> None:
    config = TrackerConfig(tracker_type=TrackerType.BOTSORT, frame_rate=30)
    tracker = create_tracker(
        config,
        backend_factory=lambda tracker_name, tracker_config: _FakeTrackerBackend(tracker_name),
    )

    assert tracker.name == "botsort"


def test_real_botsort_backend_accepts_default_tracker_config() -> None:
    tracker = create_tracker(TrackerConfig(tracker_type=TrackerType.BOTSORT, frame_rate=30))

    tracked = tracker.update(
        [
            Detection(
                class_name="car",
                confidence=0.93,
                bbox=(10.0, 12.0, 60.0, 42.0),
                class_id=2,
            )
        ],
        frame=np.zeros((96, 96, 3), dtype=np.uint8),
    )

    assert len(tracked) == 1
    assert tracked[0].class_name == "car"


def test_botsort_default_disables_global_motion_compensation_for_fixed_cameras() -> None:
    tracker = create_tracker(TrackerConfig(tracker_type=TrackerType.BOTSORT, frame_rate=30))

    assert tracker.backend.gmc.method is None


def test_tracker_defaults_are_tolerant_for_low_fps_live_telemetry() -> None:
    captured: dict[str, TrackerConfig] = {}

    def backend_factory(tracker_name: str, tracker_config: TrackerConfig) -> _FakeTrackerBackend:
        captured["config"] = tracker_config
        return _FakeTrackerBackend(tracker_name)

    create_tracker(
        TrackerConfig(tracker_type=TrackerType.BOTSORT, frame_rate=10),
        backend_factory=backend_factory,
    )

    namespace = captured["config"].to_namespace()

    assert namespace.track_high_thresh == 0.25
    assert namespace.new_track_thresh == 0.35
    assert namespace.track_buffer == 90
    assert namespace.gmc_method == "none"


def test_tracker_efficient_profile_preserves_low_score_association_defaults() -> None:
    config = TrackerConfig.for_scene_profile(
        "efficient",
        tracker_type=TrackerType.BYTETRACK,
        frame_rate=10,
    )

    namespace = config.to_namespace()

    assert config.scene_profile == "efficient"
    assert config.tracker_type is TrackerType.BYTETRACK
    assert config.frame_rate == 10
    assert namespace.track_high_thresh == 0.25
    assert namespace.track_low_thresh == 0.1
    assert namespace.new_track_thresh == 0.35
    assert namespace.match_thresh == 0.8
    assert namespace.track_buffer == 90
    assert namespace.fuse_score is True


def test_tracker_difficult_scene_profile_enables_appearance_ready_knobs() -> None:
    config = TrackerConfig.for_scene_profile("difficult", frame_rate=12)

    namespace = config.to_namespace()

    assert config.scene_profile == "difficult"
    assert config.tracker_type is TrackerType.BOTSORT
    assert config.frame_rate == 12
    assert namespace.track_buffer > 90
    assert namespace.match_thresh >= 0.85
    assert namespace.with_reid is False
    assert namespace.appearance_thresh == 0.8
    assert namespace.proximity_thresh == 0.5
    assert namespace.model == "auto"


def test_tracker_difficult_scene_profile_rejects_bytetrack_override() -> None:
    with pytest.raises(ValueError, match="difficult scene profile requires botsort"):
        TrackerConfig.for_scene_profile("difficult", tracker_type=TrackerType.BYTETRACK)


def test_tracker_efficient_profile_does_not_enable_reid_by_default() -> None:
    config = TrackerConfig.for_scene_profile("efficient")
    namespace = config.to_namespace()

    assert namespace.with_reid is False
    assert namespace.appearance_thresh == 0.25


def test_real_tracker_ages_state_on_empty_detection_frames() -> None:
    tracker = create_tracker(TrackerConfig(tracker_type=TrackerType.BYTETRACK, frame_rate=30))

    tracked = tracker.update(
        [
            Detection(
                class_name="car",
                confidence=0.93,
                bbox=(10.0, 12.0, 60.0, 42.0),
                class_id=2,
            )
        ],
        frame=np.zeros((96, 96, 3), dtype=np.uint8),
    )
    assert len(tracked) == 1

    tracker.update([], frame=np.zeros((96, 96, 3), dtype=np.uint8))

    assert tracker.backend.frame_id == 2


def test_real_botsort_difficult_profile_without_reid_handles_update() -> None:
    tracker = create_tracker(TrackerConfig.for_scene_profile("difficult", frame_rate=30))

    tracked = tracker.update(
        [
            Detection(
                class_name="person",
                confidence=0.93,
                bbox=(10.0, 12.0, 60.0, 82.0),
                class_id=0,
            )
        ],
        frame=np.zeros((96, 96, 3), dtype=np.uint8),
    )

    assert len(tracked) == 1
    assert tracked[0].class_name == "person"
