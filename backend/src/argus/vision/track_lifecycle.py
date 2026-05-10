from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import hypot
from typing import Literal, cast

from argus.vision.types import BoundingBox, Detection

TrackLifecycleState = Literal["tentative", "active", "coasting", "lost"]
PublishedTrackState = Literal["active", "coasting"]
CandidateContextTrackState = Literal["tentative", "active", "coasting"]


@dataclass(frozen=True, slots=True)
class TrackLifecycleConfig:
    coast_ttl_ms: int = 2_500
    tentative_hits: int = 2
    instant_activation_confidence: float = 0.75
    duplicate_iou_threshold: float = 0.60
    duplicate_replacement_confidence_delta: float = 0.25
    source_match_center_distance_ratio: float = 1.50
    reassociate_iou_threshold: float = 0.35
    reassociate_center_distance_ratio: float = 0.45
    velocity_damping: float = 0.70


@dataclass(frozen=True, slots=True)
class LifecycleTrack:
    stable_track_id: int
    source_track_id: int | None
    state: CandidateContextTrackState
    last_seen_age_ms: int
    detection: Detection


@dataclass(slots=True)
class _TrackMemory:
    stable_track_id: int
    class_name: str
    source_track_id: int | None
    state: TrackLifecycleState
    detection: Detection
    first_seen_ts: datetime
    last_seen_ts: datetime
    updated_ts: datetime
    hits: int = 0
    missing_updates: int = 0
    velocity: BoundingBox = (0.0, 0.0, 0.0, 0.0)


class TrackLifecycleManager:
    def __init__(self, config: TrackLifecycleConfig | None = None) -> None:
        self.config = config or TrackLifecycleConfig()
        self._next_stable_track_id = 1
        self._tracks: dict[int, _TrackMemory] = {}
        self._stable_id_by_source: dict[int, int] = {}
        self._last_visible_tracks: list[LifecycleTrack] = []
        self._last_candidate_context_tracks: list[LifecycleTrack] = []

    def reset(self) -> None:
        self._next_stable_track_id = 1
        self._tracks.clear()
        self._stable_id_by_source.clear()
        self._last_visible_tracks.clear()
        self._last_candidate_context_tracks.clear()

    def visible_tracks(self) -> list[LifecycleTrack]:
        return [_copy_lifecycle_track(track) for track in self._last_visible_tracks]

    def candidate_context_tracks(self) -> list[LifecycleTrack]:
        return [_copy_lifecycle_track(track) for track in self._last_candidate_context_tracks]

    def update(
        self,
        *,
        detections: list[Detection],
        ts: datetime,
        frame_shape: tuple[int, ...] | None = None,
    ) -> list[LifecycleTrack]:
        matched_stable_ids: set[int] = set()
        seen_this_frame: list[int] = []

        for detection in sorted(detections, key=self._detection_sort_key):
            stable_id = self._match_existing_track(
                detection,
                matched_stable_ids,
                frame_shape,
            )
            if stable_id is None:
                stable_id = self._create_track(detection, ts)
            self._apply_detection(stable_id, detection, ts, frame_shape)
            matched_stable_ids.add(stable_id)
            seen_this_frame.append(stable_id)

        suppressed = self._suppress_duplicate_detections(seen_this_frame, ts)
        visible: list[LifecycleTrack] = []

        for stable_id in seen_this_frame:
            if stable_id in suppressed:
                continue
            memory = self._tracks.get(stable_id)
            if memory is not None and memory.state == "active":
                visible.append(self._to_lifecycle_track(memory, last_seen_age_ms=0))

        for stable_id, memory in list(self._tracks.items()):
            if stable_id in matched_stable_ids or stable_id in suppressed:
                continue
            if memory.state in {"active", "coasting"}:
                age_ms = _elapsed_ms(memory.last_seen_ts, ts)
                if age_ms <= self.config.coast_ttl_ms:
                    self._coast_track(memory, ts, frame_shape)
                    visible.append(self._to_lifecycle_track(memory, last_seen_age_ms=age_ms))
                    continue
            self._forget_track(stable_id)

        self._last_visible_tracks = sorted(visible, key=lambda track: track.stable_track_id)
        self._last_candidate_context_tracks = self._candidate_context_snapshot(ts)
        return self.visible_tracks()

    def _detection_sort_key(self, detection: Detection) -> tuple[int, float]:
        source_track_id = detection.track_id
        source_stable_id = (
            self._stable_id_by_source.get(source_track_id)
            if source_track_id is not None
            else None
        )
        has_source_match = (
            source_stable_id is not None
            and source_stable_id in self._tracks
            and self._tracks[source_stable_id].class_name == detection.class_name
        )
        return (0 if has_source_match else 1, -detection.confidence)

    def _match_existing_track(
        self,
        detection: Detection,
        matched_stable_ids: set[int],
        frame_shape: tuple[int, ...] | None,
    ) -> int | None:
        bbox = _clamp_bbox(detection.bbox, frame_shape)
        source_track_id = detection.track_id
        if source_track_id is not None:
            stable_id = self._stable_id_by_source.get(source_track_id)
            memory = self._tracks.get(stable_id) if stable_id is not None else None
            if (
                memory is not None
                and memory.class_name == detection.class_name
                and stable_id not in matched_stable_ids
                and self._source_match_is_plausible(memory, bbox)
            ):
                return stable_id

        return self._find_spatial_reassociation(detection, bbox, matched_stable_ids)

    def _source_match_is_plausible(
        self,
        memory: _TrackMemory,
        bbox: BoundingBox,
    ) -> bool:
        return (
            _iou(memory.detection.bbox, bbox) > 0.0
            or _center_distance_ratio(memory.detection.bbox, bbox)
            <= self.config.source_match_center_distance_ratio
        )

    def _find_spatial_reassociation(
        self,
        detection: Detection,
        bbox: BoundingBox,
        matched_stable_ids: set[int],
    ) -> int | None:
        best_stable_id: int | None = None
        best_score = float("-inf")
        for stable_id, memory in self._tracks.items():
            if (
                stable_id in matched_stable_ids
                or memory.class_name != detection.class_name
                or memory.state not in {"tentative", "active", "coasting"}
            ):
                continue
            overlap = _iou(memory.detection.bbox, bbox)
            center_ratio = _center_distance_ratio(memory.detection.bbox, bbox)
            if overlap < self.config.reassociate_iou_threshold:
                continue
            if center_ratio > self.config.reassociate_center_distance_ratio:
                continue
            score = overlap - center_ratio
            if score > best_score:
                best_score = score
                best_stable_id = stable_id
        return best_stable_id

    def _create_track(self, detection: Detection, ts: datetime) -> int:
        stable_id = self._next_stable_track_id
        self._next_stable_track_id += 1
        source_track_id = detection.track_id
        self._tracks[stable_id] = _TrackMemory(
            stable_track_id=stable_id,
            class_name=detection.class_name,
            source_track_id=source_track_id,
            state="tentative",
            detection=detection.with_updates(track_id=stable_id),
            first_seen_ts=ts,
            last_seen_ts=ts,
            updated_ts=ts,
        )
        if source_track_id is not None:
            self._stable_id_by_source[source_track_id] = stable_id
        return stable_id

    def _apply_detection(
        self,
        stable_id: int,
        detection: Detection,
        ts: datetime,
        frame_shape: tuple[int, ...] | None,
    ) -> None:
        memory = self._tracks[stable_id]
        old_source_track_id = memory.source_track_id
        source_track_id = detection.track_id
        if old_source_track_id is not None and old_source_track_id != source_track_id:
            self._forget_source_mapping(old_source_track_id, stable_id)
        if source_track_id is not None:
            self._stable_id_by_source[source_track_id] = stable_id

        previous_bbox = memory.detection.bbox
        bbox = _clamp_bbox(detection.bbox, frame_shape)
        memory.velocity = cast(BoundingBox, tuple(
            bbox[index] - previous_bbox[index]
            for index in range(4)
        ))
        memory.hits += 1
        memory.source_track_id = source_track_id
        memory.class_name = detection.class_name
        memory.state = (
            "active"
            if memory.state in {"active", "coasting"}
            or memory.hits >= self.config.tentative_hits
            or detection.confidence >= self.config.instant_activation_confidence
            else "tentative"
        )
        memory.detection = _copy_detection(
            detection.with_updates(track_id=stable_id, bbox=bbox)
        )
        memory.last_seen_ts = ts
        memory.updated_ts = ts
        memory.missing_updates = 0

    def _suppress_duplicate_detections(self, stable_ids: list[int], ts: datetime) -> set[int]:
        selected: list[int] = []
        suppressed: set[int] = set()

        for stable_id in sorted(stable_ids, key=self._duplicate_rank):
            memory = self._tracks.get(stable_id)
            if memory is None:
                continue
            duplicate_of = next(
                (
                    selected_id
                    for selected_id in selected
                    if self._is_suppressible_duplicate(
                        candidate=memory,
                        selected=self._tracks[selected_id],
                        ts=ts,
                    )
                ),
                None,
            )
            if duplicate_of is not None:
                selected_memory = self._tracks[duplicate_of]
                replace_selected = self._candidate_is_clearly_better(
                    candidate=memory,
                    selected=selected_memory,
                )
                suppressed.add(stable_id)
                self._forget_track(stable_id)
                if replace_selected:
                    # Keep the stable identity while adopting the better raw detection.
                    # This avoids both duplicate overlays and unnecessary ID churn.
                    self._replace_with_duplicate(
                        selected=selected_memory,
                        duplicate=memory,
                    )
                continue
            selected.append(stable_id)

        return suppressed

    def _duplicate_rank(self, stable_id: int) -> tuple[int, datetime, int, float]:
        memory = self._tracks[stable_id]
        state_rank = 0 if memory.state == "active" else 1
        return (state_rank, memory.first_seen_ts, -memory.hits, -memory.detection.confidence)

    def _is_suppressible_duplicate(
        self,
        *,
        candidate: _TrackMemory,
        selected: _TrackMemory,
        ts: datetime,
    ) -> bool:
        if candidate.class_name != selected.class_name:
            return False
        overlap = _iou(candidate.detection.bbox, selected.detection.bbox)
        if overlap < self.config.duplicate_iou_threshold:
            return False

        candidate_established = (
            candidate.first_seen_ts < ts
            and candidate.hits >= self.config.tentative_hits
        )
        selected_established = (
            selected.first_seen_ts < ts
            and selected.hits >= self.config.tentative_hits
        )
        return not (candidate_established and selected_established)

    def _candidate_is_clearly_better(
        self,
        *,
        candidate: _TrackMemory,
        selected: _TrackMemory,
    ) -> bool:
        return (
            candidate.detection.confidence
            >= selected.detection.confidence
            + self.config.duplicate_replacement_confidence_delta
        )

    def _replace_with_duplicate(
        self,
        *,
        selected: _TrackMemory,
        duplicate: _TrackMemory,
    ) -> None:
        if selected.source_track_id is not None:
            self._stable_id_by_source.pop(selected.source_track_id, None)
        selected.source_track_id = duplicate.source_track_id
        if duplicate.source_track_id is not None:
            self._stable_id_by_source[duplicate.source_track_id] = selected.stable_track_id
        selected.detection = _copy_detection(
            duplicate.detection.with_updates(
                track_id=selected.stable_track_id,
            )
        )
        selected.velocity = duplicate.velocity
        selected.last_seen_ts = duplicate.last_seen_ts
        selected.updated_ts = duplicate.updated_ts
        selected.missing_updates = 0
        selected.state = "active"

    def _coast_track(
        self,
        memory: _TrackMemory,
        ts: datetime,
        frame_shape: tuple[int, ...] | None,
    ) -> None:
        memory.state = "coasting"
        memory.updated_ts = ts
        memory.missing_updates += 1
        damping = self.config.velocity_damping ** memory.missing_updates
        predicted_bbox = cast(BoundingBox, tuple(
            memory.detection.bbox[index] + memory.velocity[index] * damping
            for index in range(4)
        ))
        memory.detection = _copy_detection(
            memory.detection.with_updates(
                track_id=memory.stable_track_id,
                bbox=_clamp_bbox(predicted_bbox, frame_shape),
            )
        )

    def _to_lifecycle_track(
        self,
        memory: _TrackMemory,
        *,
        last_seen_age_ms: int,
    ) -> LifecycleTrack:
        state: PublishedTrackState = "coasting" if memory.state == "coasting" else "active"
        return LifecycleTrack(
            stable_track_id=memory.stable_track_id,
            source_track_id=memory.source_track_id,
            state=state,
            last_seen_age_ms=last_seen_age_ms,
            detection=_copy_detection(
                memory.detection.with_updates(track_id=memory.stable_track_id)
            ),
        )

    def _candidate_context_snapshot(self, ts: datetime) -> list[LifecycleTrack]:
        tracks: list[LifecycleTrack] = []
        for memory in self._tracks.values():
            if memory.state not in {"tentative", "active", "coasting"}:
                continue
            state: CandidateContextTrackState = cast(CandidateContextTrackState, memory.state)
            tracks.append(
                LifecycleTrack(
                    stable_track_id=memory.stable_track_id,
                    source_track_id=memory.source_track_id,
                    state=state,
                    last_seen_age_ms=_elapsed_ms(memory.last_seen_ts, ts),
                    detection=_copy_detection(
                        memory.detection.with_updates(track_id=memory.stable_track_id)
                    ),
                )
            )
        return sorted(tracks, key=lambda track: track.stable_track_id)

    def _forget_track(self, stable_id: int) -> None:
        memory = self._tracks.pop(stable_id, None)
        if memory is not None and memory.source_track_id is not None:
            self._forget_source_mapping(memory.source_track_id, stable_id)

    def _forget_source_mapping(self, source_track_id: int, stable_id: int) -> None:
        if self._stable_id_by_source.get(source_track_id) == stable_id:
            self._stable_id_by_source.pop(source_track_id, None)


def _elapsed_ms(start: datetime, end: datetime) -> int:
    return max(0, round((end - start).total_seconds() * 1000))


def _iou(left: BoundingBox, right: BoundingBox) -> float:
    left_x1, left_y1, left_x2, left_y2 = left
    right_x1, right_y1, right_x2, right_y2 = right

    intersection_width = max(0.0, min(left_x2, right_x2) - max(left_x1, right_x1))
    intersection_height = max(0.0, min(left_y2, right_y2) - max(left_y1, right_y1))
    intersection = intersection_width * intersection_height
    if intersection <= 0:
        return 0.0

    left_area = max(0.0, left_x2 - left_x1) * max(0.0, left_y2 - left_y1)
    right_area = max(0.0, right_x2 - right_x1) * max(0.0, right_y2 - right_y1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def _center_distance_ratio(left: BoundingBox, right: BoundingBox) -> float:
    left_width = max(1.0, left[2] - left[0])
    left_height = max(1.0, left[3] - left[1])
    right_width = max(1.0, right[2] - right[0])
    right_height = max(1.0, right[3] - right[1])
    left_center = (left[0] + left_width / 2.0, left[1] + left_height / 2.0)
    right_center = (right[0] + right_width / 2.0, right[1] + right_height / 2.0)
    distance = hypot(left_center[0] - right_center[0], left_center[1] - right_center[1])
    reference = max(left_width, left_height, right_width, right_height, 1.0)
    return distance / reference


def _clamp_bbox(
    bbox: BoundingBox,
    frame_shape: tuple[int, ...] | None,
) -> BoundingBox:
    x1, y1, x2, y2 = bbox
    if frame_shape and len(frame_shape) >= 2:
        height = float(max(1, frame_shape[0]))
        width = float(max(1, frame_shape[1]))
        x1 = min(max(0.0, x1), width)
        x2 = min(max(0.0, x2), width)
        y1 = min(max(0.0, y1), height)
        y2 = min(max(0.0, y2), height)

    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return (x1, y1, x2, y2)


def _copy_detection(detection: Detection) -> Detection:
    return detection.with_updates(attributes=dict(detection.attributes))


def _copy_lifecycle_track(track: LifecycleTrack) -> LifecycleTrack:
    return LifecycleTrack(
        stable_track_id=track.stable_track_id,
        source_track_id=track.source_track_id,
        state=track.state,
        last_seen_age_ms=track.last_seen_age_ms,
        detection=_copy_detection(track.detection),
    )
