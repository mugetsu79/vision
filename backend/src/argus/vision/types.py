from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any

BoundingBox = tuple[float, float, float, float]


@dataclass(slots=True)
class Detection:
    class_name: str
    confidence: float
    bbox: BoundingBox
    class_id: int | None = None
    track_id: int | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)
    zone_id: str | None = None
    speed_kph: float | None = None
    direction_deg: float | None = None

    @property
    def xyxy(self) -> BoundingBox:
        return self.bbox

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _freeze_attributes(self.attributes))

    def with_updates(self, **changes: Any) -> Detection:
        if "attributes" in changes:
            changes["attributes"] = _freeze_attributes(changes["attributes"])
        return replace(self, **changes)


def _freeze_attributes(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if isinstance(value, MappingProxyType):
        return value
    return MappingProxyType(dict(value or {}))
