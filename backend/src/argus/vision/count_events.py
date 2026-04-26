from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from argus.models.enums import CountEventType
from argus.vision.anpr import line_cross_direction, point_side
from argus.vision.types import Detection
from argus.vision.zones import Zones


@dataclass(slots=True, frozen=True)
class _LineBoundary:
    boundary_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    class_names: frozenset[str]


@dataclass(slots=True, frozen=True)
class _SpatialSignature:
    x: int
    y: int


@dataclass(slots=True, frozen=True)
class CountEventRecord:
    ts: datetime
    class_name: str
    track_id: int | None
    event_type: CountEventType
    boundary_id: str
    direction: str | None = None
    from_zone_id: str | None = None
    to_zone_id: str | None = None
    speed_kph: float | None = None
    confidence: float | None = None
    attributes: dict[str, Any] | None = None
    payload: dict[str, object] = field(default_factory=dict)

    def __getitem__(self, key: str) -> object:
        if key == "ts":
            return self.ts
        if key == "class_name":
            return self.class_name
        if key == "track_id":
            return self.track_id
        if key == "event_type":
            return self.event_type
        if key == "boundary_id":
            return self.boundary_id
        if key == "direction":
            return self.direction
        if key == "from_zone_id":
            return self.from_zone_id
        if key == "to_zone_id":
            return self.to_zone_id
        if key == "speed_kph":
            return self.speed_kph
        if key == "confidence":
            return self.confidence
        if key == "attributes":
            return self.attributes
        if key == "payload":
            return self.payload
        raise KeyError(key)


class CountEventProcessor:
    def __init__(
        self,
        definitions: list[dict[str, Any]],
        *,
        dedupe_seconds: float = 1.5,
        stale_state_ttl_seconds: float = 5.0,
    ) -> None:
        self._lines: list[_LineBoundary] = []
        zone_definitions: list[dict[str, Any]] = []
        self._last_line_side: dict[tuple[str, int], float] = {}
        self._last_zone_by_track: dict[int, str | None] = {}
        self._track_last_seen: dict[int, datetime] = {}
        self._recent_boundary_hits: dict[tuple[str, str, str, str | None, _SpatialSignature], datetime] = {}
        self._dedupe_seconds = dedupe_seconds
        self._stale_state_ttl_seconds = stale_state_ttl_seconds

        for definition in definitions:
            boundary_type = str(definition.get("type", "polygon")).lower()
            if boundary_type == "line":
                if "polygon" in definition:
                    raise ValueError("Line definitions must not include a polygon field.")
                points = definition.get("points")
                if not isinstance(points, list) or len(points) != 2:
                    raise ValueError("Line definitions require type='line' and exactly two points.")
                self._lines.append(
                    _LineBoundary(
                        boundary_id=str(definition["id"]),
                        start=(float(points[0][0]), float(points[0][1])),
                        end=(float(points[1][0]), float(points[1][1])),
                        class_names=frozenset(str(name) for name in definition.get("class_names", [])),
                    )
                )
                continue

            if "points" in definition:
                raise ValueError("Line definitions must declare type='line'; polygon definitions must use 'polygon'.")

            if "polygon" not in definition:
                raise ValueError("Polygon definitions require a polygon field.")
            zone_definitions.append(definition)

        self._zones = Zones(zone_definitions) if zone_definitions else None

    def process(self, *, ts: datetime, detections: list[Detection]) -> list[CountEventRecord]:
        events: list[CountEventRecord] = []
        self._prune_expired_state(ts)
        for detection in detections:
            if detection.track_id is None:
                continue

            self._prune_stale_track_state(detection.track_id, ts)
            bottom_center = self._bottom_center(detection.bbox)
            current_zone = self._current_zone(bottom_center, detection)
            spatial_signature = self._spatial_signature(bottom_center)
            events.extend(
                self._process_lines(
                    ts=ts,
                    detection=detection,
                    bottom_center=bottom_center,
                    spatial_signature=spatial_signature,
                    current_zone=current_zone,
                )
            )
            events.extend(
                self._process_zones(
                    ts=ts,
                    detection=detection,
                    current_zone=current_zone,
                    spatial_signature=spatial_signature,
                )
            )
        return events

    def _prune_stale_track_state(self, track_id: int, ts: datetime) -> None:
        self._track_last_seen[track_id] = ts

    def _prune_expired_state(self, ts: datetime) -> None:
        expired_tracks = [
            track_id
            for track_id, last_seen in self._track_last_seen.items()
            if (ts - last_seen).total_seconds() > self._stale_state_ttl_seconds
        ]
        for track_id in expired_tracks:
            self._track_last_seen.pop(track_id, None)
            self._last_zone_by_track.pop(track_id, None)
            stale_line_keys = [key for key in self._last_line_side if key[1] == track_id]
            for key in stale_line_keys:
                self._last_line_side.pop(key, None)

        expired_boundary_hits = [
            key
            for key, previous_hit in self._recent_boundary_hits.items()
            if (ts - previous_hit).total_seconds() > self._dedupe_seconds
        ]
        for key in expired_boundary_hits:
            self._recent_boundary_hits.pop(key, None)

    def _process_lines(
        self,
        *,
        ts: datetime,
        detection: Detection,
        bottom_center: tuple[float, float],
        spatial_signature: _SpatialSignature,
        current_zone: str | None,
    ) -> list[CountEventRecord]:
        emitted: list[CountEventRecord] = []
        for boundary in self._lines:
            if boundary.class_names and detection.class_name not in boundary.class_names:
                continue

            side = point_side(bottom_center, boundary.start, boundary.end)
            key = (boundary.boundary_id, detection.track_id)
            previous_side = self._last_line_side.get(key)
            self._last_line_side[key] = side
            if previous_side is None or previous_side == 0 or side == 0 or previous_side * side > 0:
                continue

            direction = line_cross_direction(previous_side, side)
            if self._is_recent(
                boundary_id=boundary.boundary_id,
                event_type=CountEventType.LINE_CROSS,
                class_name=detection.class_name,
                transition=direction,
                spatial_signature=spatial_signature,
                ts=ts,
            ):
                continue

            emitted.append(
                build_count_event(
                    ts=ts,
                    detection=detection,
                    event_type=CountEventType.LINE_CROSS,
                    boundary_id=boundary.boundary_id,
                    direction=direction,
                    zone_id=current_zone,
                )
            )
        return emitted

    def _process_zones(
        self,
        *,
        ts: datetime,
        detection: Detection,
        current_zone: str | None,
        spatial_signature: _SpatialSignature,
    ) -> list[CountEventRecord]:
        previous_zone = self._last_zone_by_track.get(detection.track_id)
        self._last_zone_by_track[detection.track_id] = current_zone

        if previous_zone == current_zone:
            return []

        if previous_zone is None and current_zone is not None:
            if self._is_recent(
                boundary_id=current_zone,
                event_type=CountEventType.ZONE_ENTER,
                class_name=detection.class_name,
                transition=current_zone,
                spatial_signature=spatial_signature,
                ts=ts,
            ):
                return []
            return [
                build_count_event(
                    ts=ts,
                    detection=detection,
                    event_type=CountEventType.ZONE_ENTER,
                    boundary_id=current_zone,
                    to_zone_id=current_zone,
                    zone_id=current_zone,
                )
            ]

        if previous_zone is not None and current_zone is None:
            if self._is_recent(
                boundary_id=previous_zone,
                event_type=CountEventType.ZONE_EXIT,
                class_name=detection.class_name,
                transition=previous_zone,
                spatial_signature=spatial_signature,
                ts=ts,
            ):
                return []
            return [
                build_count_event(
                    ts=ts,
                    detection=detection,
                    event_type=CountEventType.ZONE_EXIT,
                    boundary_id=previous_zone,
                    from_zone_id=previous_zone,
                    zone_id=None,
                )
            ]

        if previous_zone is not None and current_zone is not None:
            spatial_signature = self._spatial_signature(self._bottom_center(detection.bbox))
            events: list[CountEventRecord] = []
            if not self._is_recent(
                boundary_id=previous_zone,
                event_type=CountEventType.ZONE_EXIT,
                class_name=detection.class_name,
                transition=previous_zone,
                spatial_signature=spatial_signature,
                ts=ts,
            ):
                events.append(
                    build_count_event(
                        ts=ts,
                        detection=detection,
                        event_type=CountEventType.ZONE_EXIT,
                        boundary_id=previous_zone,
                        from_zone_id=previous_zone,
                        zone_id=previous_zone,
                    )
                )
            if not self._is_recent(
                boundary_id=current_zone,
                event_type=CountEventType.ZONE_ENTER,
                class_name=detection.class_name,
                transition=current_zone,
                spatial_signature=spatial_signature,
                ts=ts,
            ):
                events.append(
                    build_count_event(
                        ts=ts,
                        detection=detection,
                        event_type=CountEventType.ZONE_ENTER,
                        boundary_id=current_zone,
                        to_zone_id=current_zone,
                        zone_id=current_zone,
                    )
                )
            return events

        return []

    def _current_zone(
        self,
        bottom_center: tuple[float, float],
        detection: Detection,
    ) -> str | None:
        if self._zones is None:
            return detection.zone_id
        return self._zones.zone_for_point(bottom_center[0], bottom_center[1]) or detection.zone_id

    def _is_recent(
        self,
        boundary_id: str,
        event_type: CountEventType,
        class_name: str,
        transition: str | None,
        spatial_signature: _SpatialSignature,
        ts: datetime,
    ) -> bool:
        key = (boundary_id, event_type.value, class_name, transition, spatial_signature)
        previous_hit = self._recent_boundary_hits.get(key)
        if previous_hit is not None and (ts - previous_hit).total_seconds() < self._dedupe_seconds:
            return True
        self._recent_boundary_hits[key] = ts
        return False

    @staticmethod
    def _bottom_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, y2)

    @staticmethod
    def _spatial_signature(point: tuple[float, float]) -> _SpatialSignature:
        quantum = 1.0
        return _SpatialSignature(
            x=int(round(point[0] / quantum)),
            y=int(round(point[1] / quantum)),
        )


def build_count_event(
    *,
    ts: datetime,
    detection: Detection,
    event_type: CountEventType,
    boundary_id: str,
    direction: str | None = None,
    from_zone_id: str | None = None,
    to_zone_id: str | None = None,
    zone_id: str | None = None,
) -> CountEventRecord:
    return CountEventRecord(
        ts=ts,
        class_name=detection.class_name,
        track_id=detection.track_id,
        event_type=event_type,
        boundary_id=boundary_id,
        direction=direction,
        from_zone_id=from_zone_id,
        to_zone_id=to_zone_id,
        speed_kph=detection.speed_kph,
        confidence=detection.confidence,
        attributes=dict(detection.attributes),
        payload={"zone_id": zone_id},
    )
