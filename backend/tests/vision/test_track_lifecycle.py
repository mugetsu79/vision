from __future__ import annotations

from datetime import UTC, datetime, timedelta

from argus.vision.track_lifecycle import TrackLifecycleConfig, TrackLifecycleManager
from argus.vision.types import Detection

BASE_TS = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
FRAME_SHAPE = (720, 1280, 3)


def _ts(milliseconds: int) -> datetime:
    return BASE_TS + timedelta(milliseconds=milliseconds)


def _person(
    *,
    track_id: int,
    bbox: tuple[float, float, float, float] = (10.0, 10.0, 60.0, 120.0),
    confidence: float = 0.91,
) -> Detection:
    return Detection(
        class_name="person",
        class_id=0,
        confidence=confidence,
        bbox=bbox,
        track_id=track_id,
    )


def test_missing_track_coasts_until_ttl() -> None:
    manager = TrackLifecycleManager(TrackLifecycleConfig(coast_ttl_ms=2_500))

    first = manager.update(
        detections=[_person(track_id=4)],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    coasting = manager.update(
        detections=[],
        ts=_ts(2_499),
        frame_shape=FRAME_SHAPE,
    )

    assert [track.stable_track_id for track in first] == [1]
    assert len(coasting) == 1
    assert coasting[0].stable_track_id == 1
    assert coasting[0].source_track_id == 4
    assert coasting[0].state == "coasting"
    assert coasting[0].last_seen_age_ms == 2_499


def test_coasting_track_expires_after_ttl() -> None:
    manager = TrackLifecycleManager(TrackLifecycleConfig(coast_ttl_ms=2_500))

    manager.update(
        detections=[_person(track_id=4)],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    expired = manager.update(
        detections=[],
        ts=_ts(2_501),
        frame_shape=FRAME_SHAPE,
    )

    assert expired == []


def test_tracker_id_switch_reuses_stable_id_by_overlap() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(reassociate_iou_threshold=0.35),
    )

    first = manager.update(
        detections=[_person(track_id=4, bbox=(10.0, 10.0, 60.0, 120.0))],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    switched = manager.update(
        detections=[_person(track_id=99, bbox=(12.0, 12.0, 62.0, 122.0))],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )

    assert first[0].stable_track_id == 1
    assert len(switched) == 1
    assert switched[0].stable_track_id == 1
    assert switched[0].source_track_id == 99
    assert switched[0].state == "active"


def test_tracker_id_switch_requires_overlap_and_center_proximity() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(
            reassociate_iou_threshold=0.35,
            reassociate_center_distance_ratio=0.45,
        ),
    )

    manager.update(
        detections=[_person(track_id=4, bbox=(100.0, 100.0, 200.0, 400.0))],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    visible = manager.update(
        detections=[_person(track_id=99, bbox=(201.0, 100.0, 301.0, 400.0))],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )

    assert [(track.stable_track_id, track.source_track_id, track.state) for track in visible] == [
        (1, 4, "coasting"),
        (2, 99, "active"),
    ]


def test_source_track_id_reuse_far_away_does_not_teleport_stable_track() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(source_match_center_distance_ratio=1.5),
    )

    manager.update(
        detections=[_person(track_id=4, bbox=(10.0, 10.0, 60.0, 120.0))],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    visible = manager.update(
        detections=[_person(track_id=4, bbox=(700.0, 500.0, 760.0, 640.0))],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )

    assert [(track.stable_track_id, track.source_track_id, track.state) for track in visible] == [
        (1, 4, "coasting"),
        (2, 4, "active"),
    ]


def test_expiring_old_track_does_not_delete_reused_source_mapping() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(coast_ttl_ms=2_500, source_match_center_distance_ratio=1.5),
    )

    manager.update(
        detections=[_person(track_id=4, bbox=(10.0, 10.0, 60.0, 120.0))],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    manager.update(
        detections=[_person(track_id=4, bbox=(700.0, 500.0, 760.0, 640.0))],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )
    manager.update(
        detections=[_person(track_id=4, bbox=(761.0, 500.0, 821.0, 640.0))],
        ts=_ts(2_601),
        frame_shape=FRAME_SHAPE,
    )
    visible = manager.update(
        detections=[_person(track_id=4, bbox=(822.0, 500.0, 882.0, 640.0))],
        ts=_ts(2_700),
        frame_shape=FRAME_SHAPE,
    )

    assert [(track.stable_track_id, track.source_track_id, track.state) for track in visible] == [
        (2, 4, "active"),
    ]


def test_duplicate_same_class_track_is_suppressed() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(duplicate_iou_threshold=0.60),
    )

    manager.update(
        detections=[_person(track_id=4, bbox=(10.0, 10.0, 60.0, 120.0))],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    visible = manager.update(
        detections=[
            _person(track_id=4, bbox=(11.0, 11.0, 61.0, 121.0), confidence=0.90),
            _person(track_id=5, bbox=(12.0, 12.0, 62.0, 122.0), confidence=0.88),
        ],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )

    assert len(visible) == 1
    assert visible[0].stable_track_id == 1
    assert visible[0].source_track_id == 4


def test_clearly_better_duplicate_refreshes_stable_track() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(
            duplicate_iou_threshold=0.60,
            duplicate_replacement_confidence_delta=0.25,
        ),
    )

    manager.update(
        detections=[_person(track_id=4, bbox=(10.0, 10.0, 60.0, 120.0), confidence=0.76)],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    visible = manager.update(
        detections=[
            _person(track_id=4, bbox=(11.0, 11.0, 61.0, 121.0), confidence=0.40),
            _person(track_id=5, bbox=(12.0, 12.0, 62.0, 122.0), confidence=0.92),
        ],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )

    assert len(visible) == 1
    assert visible[0].stable_track_id == 1
    assert visible[0].source_track_id == 5
    assert visible[0].detection.confidence == 0.92


def test_overlapping_crossing_tracks_keep_one_stable_identity_for_one_object() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(duplicate_iou_threshold=0.60),
    )

    manager.update(
        detections=[_person(track_id=7, bbox=(400.0, 100.0, 500.0, 360.0))],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    crossing = manager.update(
        detections=[
            _person(track_id=7, bbox=(405.0, 100.0, 505.0, 360.0), confidence=0.89),
            _person(track_id=22, bbox=(408.0, 102.0, 508.0, 362.0), confidence=0.83),
        ],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )

    assert [(track.stable_track_id, track.source_track_id) for track in crossing] == [(1, 7)]


def test_established_overlapping_tracks_are_not_collapsed() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(duplicate_iou_threshold=0.60),
    )

    manager.update(
        detections=[
            _person(track_id=7, bbox=(100.0, 100.0, 200.0, 360.0)),
            _person(track_id=8, bbox=(400.0, 100.0, 500.0, 360.0)),
        ],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    manager.update(
        detections=[
            _person(track_id=7, bbox=(105.0, 100.0, 205.0, 360.0)),
            _person(track_id=8, bbox=(405.0, 100.0, 505.0, 360.0)),
        ],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )
    overlapping = manager.update(
        detections=[
            _person(track_id=7, bbox=(300.0, 100.0, 400.0, 360.0)),
            _person(track_id=8, bbox=(305.0, 102.0, 405.0, 362.0)),
        ],
        ts=_ts(200),
        frame_shape=FRAME_SHAPE,
    )

    assert [(track.stable_track_id, track.source_track_id) for track in overlapping] == [
        (1, 7),
        (2, 8),
    ]


def test_single_low_confidence_candidate_stays_tentative() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(tentative_hits=2, instant_activation_confidence=0.75),
    )

    first = manager.update(
        detections=[_person(track_id=31, confidence=0.42)],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    second = manager.update(
        detections=[_person(track_id=31, confidence=0.44)],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )

    assert first == []
    assert len(second) == 1
    assert second[0].stable_track_id == 1
    assert second[0].state == "active"


def test_low_confidence_candidate_can_promote_after_source_id_switch() -> None:
    manager = TrackLifecycleManager(
        TrackLifecycleConfig(tentative_hits=2, instant_activation_confidence=0.75),
    )

    first = manager.update(
        detections=[_person(track_id=31, confidence=0.42)],
        ts=_ts(0),
        frame_shape=FRAME_SHAPE,
    )
    second = manager.update(
        detections=[_person(track_id=32, bbox=(11.0, 11.0, 61.0, 121.0), confidence=0.44)],
        ts=_ts(100),
        frame_shape=FRAME_SHAPE,
    )

    assert first == []
    assert len(second) == 1
    assert second[0].stable_track_id == 1
    assert second[0].source_track_id == 32
    assert second[0].state == "active"
