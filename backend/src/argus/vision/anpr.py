from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import UUID

from argus.services.incident_capture import IncidentTriggeredEvent
from argus.vision.types import Detection

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}


@dataclass(slots=True, frozen=True)
class _LineDefinition:
    line_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    class_names: frozenset[str]


class LineCrossingAnprProcessor:
    def __init__(self, line_definitions: list[dict[str, Any]]) -> None:
        self._lines = [_parse_line_definition(definition) for definition in line_definitions]
        self._last_side: dict[tuple[str, int], float] = {}

    def process(
        self,
        *,
        camera_id: UUID,
        ts: datetime,
        detections: list[Detection],
    ) -> list[IncidentTriggeredEvent]:
        incidents: list[IncidentTriggeredEvent] = []
        for detection in detections:
            if detection.track_id is None or detection.class_name not in VEHICLE_CLASSES:
                continue
            plate_text = detection.attributes.get("plate_text")
            if not isinstance(plate_text, str) or not plate_text.strip():
                continue

            x1, y1, x2, y2 = detection.bbox
            bottom_center = ((x1 + x2) / 2.0, y2)
            for line in self._lines:
                if line.class_names and detection.class_name not in line.class_names:
                    continue
                side = _point_side(bottom_center, line)
                key = (line.line_id, detection.track_id)
                previous_side = self._last_side.get(key)
                self._last_side[key] = side
                if previous_side is None or previous_side == 0 or side == 0:
                    continue
                if previous_side * side > 0:
                    continue

                incidents.append(
                    IncidentTriggeredEvent(
                        camera_id=camera_id,
                        ts=ts,
                        type="anpr.line_crossed",
                        payload={
                            "line_id": line.line_id,
                            "track_id": detection.track_id,
                            "class_name": detection.class_name,
                            "plate_text": plate_text,
                            "plate_hash": sha256(plate_text.encode("utf-8")).hexdigest(),
                            "direction": _direction(previous_side, side),
                        },
                    )
                )
        return incidents


def _parse_line_definition(definition: dict[str, Any]) -> _LineDefinition:
    if str(definition.get("type", "line")) != "line":
        raise ValueError("ANPR line definitions must use type='line'.")
    points = definition.get("points")
    if not isinstance(points, list) or len(points) != 2:
        raise ValueError("Line definitions require exactly two points.")
    start = (float(points[0][0]), float(points[0][1]))
    end = (float(points[1][0]), float(points[1][1]))
    class_names = definition.get("class_names") or list(VEHICLE_CLASSES)
    return _LineDefinition(
        line_id=str(definition["id"]),
        start=start,
        end=end,
        class_names=frozenset(str(name) for name in class_names),
    )


def _point_side(point: tuple[float, float], line: _LineDefinition) -> float:
    px, py = point
    x1, y1 = line.start
    x2, y2 = line.end
    return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)


def _direction(previous_side: float, side: float) -> str:
    if previous_side > 0 and side < 0:
        return "positive-to-negative"
    return "negative-to-positive"
