from __future__ import annotations

from traffic_monitor.models.enums import TrackerType
from traffic_monitor.vision.tracker import TrackerConfig, create_tracker
from traffic_monitor.vision.types import Detection


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
