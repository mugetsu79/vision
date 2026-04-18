from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

BoundingBox = tuple[float, float, float, float]


@dataclass(slots=True)
class Detection:
    class_name: str
    confidence: float
    bbox: BoundingBox
    class_id: int | None = None
    track_id: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    zone_id: str | None = None
    speed_kph: float | None = None
    direction_deg: float | None = None

    @property
    def xyxy(self) -> BoundingBox:
        return self.bbox

    def with_updates(self, **changes: Any) -> Detection:
        return replace(self, **changes)
