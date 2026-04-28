from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from argus.models.enums import CountEventType
from argus.vision.anpr import LineCrossingAnprProcessor
from argus.vision.count_events import CountEventProcessor
from argus.vision.types import Detection


def _car(
    track_id: int,
    bbox: tuple[float, float, float, float],
    *,
    zone_id: str | None = None,
) -> Detection:
    return Detection(
        class_name="car",
        confidence=0.95,
        bbox=bbox,
        track_id=track_id,
        zone_id=zone_id,
        speed_kph=32.0,
        attributes={},
    )


def test_line_cross_emits_direction_once() -> None:
    processor = CountEventProcessor(
        definitions=[
            {
                "id": "driveway",
                "type": "line",
                "points": [[50, 0], [50, 100]],
                "class_names": ["car"],
            }
        ]
    )
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    assert processor.process(ts=ts, detections=[_car(1, (10, 10, 30, 30))]) == []
    events = processor.process(ts=ts + timedelta(seconds=1), detections=[_car(1, (60, 10, 80, 30))])

    assert len(events) == 1
    assert events[0]["event_type"] == CountEventType.LINE_CROSS
    assert events[0]["boundary_id"] == "driveway"
    assert events[0]["direction"] == "positive-to-negative"


def test_close_in_time_different_tracks_both_count() -> None:
    processor = CountEventProcessor(
        definitions=[
            {
                "id": "driveway",
                "type": "line",
                "points": [[50, 0], [50, 100]],
                "class_names": ["car"],
            }
        ]
    )
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    assert processor.process(ts=ts, detections=[_car(1, (10, 10, 30, 30))]) == []
    first = processor.process(
        ts=ts + timedelta(milliseconds=500), detections=[_car(1, (60, 10, 80, 30))]
    )
    assert len(first) == 1

    assert (
        processor.process(
            ts=ts + timedelta(milliseconds=750), detections=[_car(2, (10, 50, 30, 70))]
        )
        == []
    )
    second = processor.process(ts=ts + timedelta(seconds=1), detections=[_car(2, (60, 50, 80, 70))])

    assert len(second) == 1
    assert second[0]["event_type"] == CountEventType.LINE_CROSS
    assert second[0]["boundary_id"] == "driveway"
    assert second[0]["direction"] == "positive-to-negative"


def test_zone_transition_emits_exit_and_enter() -> None:
    processor = CountEventProcessor(
        definitions=[
            {"id": "zone-a", "polygon": [[0, 0], [50, 0], [50, 100], [0, 100]]},
            {"id": "zone-b", "polygon": [[50, 0], [100, 0], [100, 100], [50, 100]]},
        ]
    )
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    processor.process(ts=ts, detections=[_car(7, (10, 20, 30, 40))])
    transitioned = processor.process(
        ts=ts + timedelta(seconds=1), detections=[_car(7, (60, 20, 80, 40))]
    )

    assert [event["event_type"] for event in transitioned] == [
        CountEventType.ZONE_EXIT,
        CountEventType.ZONE_ENTER,
    ]
    assert transitioned[0]["from_zone_id"] == "zone-a"
    assert transitioned[0]["boundary_id"] == "zone-a"
    assert transitioned[1]["to_zone_id"] == "zone-b"
    assert transitioned[1]["boundary_id"] == "zone-b"


def test_short_boundary_dedupe_suppresses_track_churn() -> None:
    processor = CountEventProcessor(
        definitions=[
            {
                "id": "driveway",
                "type": "line",
                "points": [[50, 0], [50, 100]],
                "class_names": ["car"],
            }
        ],
        dedupe_seconds=2.0,
    )
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    assert processor.process(ts=ts, detections=[_car(10, (10, 10, 30, 30))]) == []
    first = processor.process(ts=ts + timedelta(seconds=1), detections=[_car(10, (60, 10, 80, 30))])
    assert len(first) == 1

    assert (
        processor.process(
            ts=ts + timedelta(seconds=1, milliseconds=500), detections=[_car(11, (10, 10, 30, 30))]
        )
        == []
    )
    second = processor.process(
        ts=ts + timedelta(seconds=2), detections=[_car(11, (60, 10, 80, 30))]
    )

    assert second == []


def test_stale_track_state_ttl_clears_reused_track_ids() -> None:
    processor = CountEventProcessor(
        definitions=[
            {
                "id": "driveway",
                "type": "line",
                "points": [[50, 0], [50, 100]],
                "class_names": ["car"],
            }
        ],
        stale_state_ttl_seconds=1.0,
    )
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    assert processor.process(ts=ts, detections=[_car(3, (10, 10, 30, 30))]) == []
    first = processor.process(
        ts=ts + timedelta(milliseconds=500), detections=[_car(3, (60, 10, 80, 30))]
    )
    assert len(first) == 1

    assert (
        processor.process(ts=ts + timedelta(seconds=2), detections=[_car(3, (10, 10, 30, 30))])
        == []
    )
    second = processor.process(
        ts=ts + timedelta(seconds=2, milliseconds=500), detections=[_car(3, (60, 10, 80, 30))]
    )

    assert len(second) == 1
    assert second[0]["event_type"] == CountEventType.LINE_CROSS
    assert second[0]["boundary_id"] == "driveway"


def test_expired_processor_state_is_pruned_without_track_reuse() -> None:
    processor = CountEventProcessor(
        definitions=[
            {
                "id": "driveway",
                "type": "line",
                "points": [[50, 0], [50, 100]],
                "class_names": ["car"],
            }
        ],
        dedupe_seconds=1.0,
        stale_state_ttl_seconds=1.0,
    )
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    assert processor.process(ts=ts, detections=[_car(3, (10, 10, 30, 30))]) == []
    crossed = processor.process(
        ts=ts + timedelta(milliseconds=500), detections=[_car(3, (60, 10, 80, 30))]
    )
    assert len(crossed) == 1

    assert (
        processor.process(ts=ts + timedelta(seconds=2), detections=[_car(9, (10, 60, 30, 80))])
        == []
    )
    assert 3 not in processor._track_last_seen
    assert all(key[1] != 3 for key in processor._last_line_side)
    assert processor._recent_boundary_hits == {}


def test_malformed_mixed_definition_shape_is_rejected() -> None:
    with pytest.raises(ValueError, match="type='line'|polygon"):
        CountEventProcessor(definitions=[{"id": "broken", "points": [[0, 0], [10, 10]]}])

    with pytest.raises(ValueError, match="polygon field"):
        CountEventProcessor(
            definitions=[
                {
                    "id": "broken-line",
                    "type": "line",
                    "points": [[0, 0], [10, 10]],
                    "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
                }
            ]
        )

    with pytest.raises(ValueError, match="polygon field"):
        CountEventProcessor(
            definitions=[
                {
                    "id": "broken-anpr",
                    "type": "line",
                    "points": [[0, 0], [10, 10]],
                    "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
                }
            ]
        )

    with pytest.raises(ValueError, match="polygon field"):
        LineCrossingAnprProcessor(
            line_definitions=[
                {
                    "id": "broken-anpr",
                    "type": "line",
                    "points": [[0, 0], [10, 10]],
                    "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
                }
            ]
        )
