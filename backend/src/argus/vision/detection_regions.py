from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.geometry import Point, Polygon  # type: ignore[import-untyped]
from shapely.prepared import PreparedGeometry, prep  # type: ignore[import-untyped]

from argus.api.contracts import DetectionRegion
from argus.vision.types import Detection

_BOTTOM_CENTER_ANCHOR_CLASSES = {
    "person",
    "car",
    "truck",
    "bus",
    "motorcycle",
    "bicycle",
    "forklift",
}


@dataclass(frozen=True, slots=True)
class DetectionRegionDecision:
    detection: Detection
    allowed: bool
    anchor: tuple[float, float]
    reason: str
    include_region_ids: list[str]
    exclude_region_ids: list[str]


@dataclass(frozen=True, slots=True)
class _PreparedDetectionRegion:
    region_id: str
    mode: str
    class_names: frozenset[str]
    polygon: PreparedGeometry

    def applies_to(self, class_name: str) -> bool:
        return not self.class_names or _normalize_class_name(class_name) in self.class_names

    def covers(self, anchor: tuple[float, float]) -> bool:
        return bool(self.polygon.covers(Point(anchor)))


class DetectionRegionPolicy:
    def __init__(self, regions: list[DetectionRegion | dict[str, Any]]) -> None:
        self._regions = [_prepare_region(region) for region in regions]

    def filter_detections(
        self,
        detections: list[Detection],
    ) -> tuple[list[Detection], list[DetectionRegionDecision]]:
        allowed: list[Detection] = []
        decisions: list[DetectionRegionDecision] = []
        for detection in detections:
            decision = self._decide(detection)
            decisions.append(decision)
            if decision.allowed:
                allowed.append(detection)
        return allowed, decisions

    def _decide(self, detection: Detection) -> DetectionRegionDecision:
        anchor = _anchor_for_detection(detection)
        matching_regions = [
            region for region in self._regions if region.applies_to(detection.class_name)
        ]
        include_regions = [region for region in matching_regions if region.mode == "include"]
        include_region_ids = [
            region.region_id for region in include_regions if region.covers(anchor)
        ]
        if include_regions and not include_region_ids:
            return DetectionRegionDecision(
                detection=detection,
                allowed=False,
                anchor=anchor,
                reason="outside_include_region",
                include_region_ids=[],
                exclude_region_ids=[],
            )

        exclude_region_ids = [
            region.region_id
            for region in matching_regions
            if region.mode == "exclude" and region.covers(anchor)
        ]
        if exclude_region_ids:
            return DetectionRegionDecision(
                detection=detection,
                allowed=False,
                anchor=anchor,
                reason="inside_exclusion_region",
                include_region_ids=include_region_ids,
                exclude_region_ids=exclude_region_ids,
            )

        return DetectionRegionDecision(
            detection=detection,
            allowed=True,
            anchor=anchor,
            reason="allowed",
            include_region_ids=include_region_ids,
            exclude_region_ids=[],
        )


def filter_detections(
    detections: list[Detection],
) -> tuple[list[Detection], list[DetectionRegionDecision]]:
    return DetectionRegionPolicy([]).filter_detections(detections)


def _prepare_region(region: DetectionRegion | dict[str, Any]) -> _PreparedDetectionRegion:
    definition = (
        region if isinstance(region, DetectionRegion) else DetectionRegion.model_validate(region)
    )
    return _PreparedDetectionRegion(
        region_id=definition.id,
        mode=definition.mode,
        class_names=frozenset(_normalize_class_name(name) for name in definition.class_names),
        polygon=prep(Polygon(definition.polygon)),
    )


def _anchor_for_detection(detection: Detection) -> tuple[float, float]:
    x1, y1, x2, y2 = detection.bbox
    center_x = (x1 + x2) / 2.0
    if _normalize_class_name(detection.class_name) in _BOTTOM_CENTER_ANCHOR_CLASSES:
        return (center_x, y2)
    return (center_x, (y1 + y2) / 2.0)


def _normalize_class_name(class_name: str) -> str:
    return class_name.strip().lower()
