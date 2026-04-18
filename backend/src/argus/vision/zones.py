from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from shapely.geometry import Point, Polygon  # type: ignore[import-untyped]
from shapely.prepared import prep  # type: ignore[import-untyped]


class Zones:
    def __init__(self, zone_definitions: Sequence[dict[str, Any]]) -> None:
        self._zones = []
        for definition in zone_definitions:
            zone_id = str(definition["id"])
            polygon = Polygon(definition["polygon"])
            self._zones.append((zone_id, prep(polygon)))

    def zone_for_point(self, x: float, y: float) -> str | None:
        point = Point(x, y)
        for zone_id, polygon in reversed(self._zones):
            if polygon.covers(point):
                return zone_id
        return None
