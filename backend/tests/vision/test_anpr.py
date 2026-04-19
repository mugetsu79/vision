from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from argus.vision.anpr import LineCrossingAnprProcessor
from argus.vision.types import Detection


def test_anpr_processor_emits_incident_when_vehicle_crosses_virtual_line() -> None:
    camera_id = uuid4()
    processor = LineCrossingAnprProcessor(
        line_definitions=[
            {
                "id": "gate-northbound",
                "type": "line",
                "points": [[0, 40], [120, 40]],
                "class_names": ["car", "truck"],
            }
        ]
    )

    before_crossing = processor.process(
        camera_id=camera_id,
        ts=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
        detections=[
            Detection(
                class_name="car",
                confidence=0.98,
                bbox=(12.0, 52.0, 36.0, 72.0),
                track_id=7,
                attributes={"plate_text": "ZH123456"},
            )
        ],
    )
    after_crossing = processor.process(
        camera_id=camera_id,
        ts=datetime(2026, 4, 19, 12, 0, 1, tzinfo=UTC),
        detections=[
            Detection(
                class_name="car",
                confidence=0.98,
                bbox=(12.0, 8.0, 36.0, 28.0),
                track_id=7,
                attributes={"plate_text": "ZH123456"},
            )
        ],
    )

    assert before_crossing == []
    assert len(after_crossing) == 1
    payload = after_crossing[0].payload
    assert after_crossing[0].type == "anpr.line_crossed"
    assert payload["line_id"] == "gate-northbound"
    assert payload["track_id"] == 7
    assert payload["plate_text"] == "ZH123456"
    assert payload["plate_hash"] == sha256(b"ZH123456").hexdigest()


def test_anpr_processor_ignores_non_vehicle_or_missing_plate_text() -> None:
    camera_id = uuid4()
    processor = LineCrossingAnprProcessor(
        line_definitions=[
            {
                "id": "gate-northbound",
                "type": "line",
                "points": [[0, 40], [120, 40]],
                "class_names": ["car", "truck"],
            }
        ]
    )

    incidents = processor.process(
        camera_id=camera_id,
        ts=datetime(2026, 4, 19, 12, 5, tzinfo=UTC),
        detections=[
            Detection(
                class_name="person",
                confidence=0.94,
                bbox=(30.0, 10.0, 50.0, 60.0),
                track_id=12,
                attributes={},
            )
        ],
    )

    assert incidents == []
