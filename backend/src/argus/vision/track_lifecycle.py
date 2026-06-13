from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import hypot
from typing import Literal, cast

from argus.vision.types import BoundingBox, Detection

TrackLifecycleState = Literal["tentative", "active", "coasting", "lost"]
PublishedTrackState = Literal["active", "coasting"]
CandidateContextTrackState = Literal["tentative", "active", "coasting"]
TrackLifecycleReason = Literal[
    "source_id_match",
    "spatial_reassociation",
    "new_track",
    "coasting",
    "forgotten",
    "duplicate_suppressed",
    "duplicate_replaced",
]
DEFAULT_TRACK_COAST_TTL_MS = 2_500


@dataclass(frozen=True, slots=True)
class TrackLifecycleConfig:
    coast_ttl_ms: int = DEFAULT_TRACK_COAST_TTL_MS
    tentative_hits: int = 2
    instant_activation_confidence: float = 0.75
    duplicate_iou_threshold: float = 0.60
    duplicate_replacement_confidence_delta: float = 0.25
    source_match_center_distance_ratio: float = 1.50
    reassociate_iou_threshold: float = 0.35
    reassociate_center_distance_ratio: float = 0.45
    velocity_damping: float = 0.70
    nominal_frame_interval_ms: float = 1000.0 / 25.0
    confidence_ema_alpha: float = 0.4


@dataclass(frozen=True, slots=True)
class LifecycleTrack:
    stable_track_id: int
    source_track_id: int | None
    state: CandidateContextTrackState
    last_seen_age_ms: int
    detection: Detection
    lifecycle_reason: TrackLifecycleReason | None = None


@dataclass(frozen=True, slots=True)
class TrackLifecycleDecision:
    stable_track_id: int
    source_track_id: int | None
    state: TrackLifecycleState
    reason: TrackLifecycleReason
    last_seen_age_ms: int
    detection: Detection


@dataclass(frozen=True, slots=True)
class _LifecycleMatch:
    stable_id: int
    reason: TrackLifecycleReason


@dataclass(slots=True)
class _MotionFilter:
    center_x: float
    center_y: float
    velocity_x_per_ms: float = 0.0
    velocity_y_per_ms: float = 0.0
    predicted_center_x: float | None = None
    predicted_center_y: float | None = None

    def update(self, bbox: BoundingBox, dt_ms: float) -> None:
        new_center_x, new_center_y, _, _ = _bbox_center_size(bbox)
        safe_dt = max(1.0, dt_ms)
        self.velocity_x_per_ms = (new_center_x - self.center_x) / safe_dt
        self.velocity_y_per_ms = (new_center_y - self.center_y) / safe_dt
        self.center_x = new_center_x
        self.center_y = new_center_y
        self.predicted_center_x = new_center_x
        self.predicted_center_y = new_center_y

    def predict(self, dt_ms: float, damping: float) -> tuple[float, float]:
        self.velocity_x_per_ms *= damping
        self.velocity_y_per_ms *= damping
        base_center_x = (
            self.predicted_center_x
            if self.predicted_center_x is not None
            else self.center_x
        )
        base_center_y = (
            self.predicted_center_y
            if self.predicted_center_y is not None
            else self.center_y
        )
        self.predicted_center_x = base_center_x + self.velocity_x_per_ms * dt_ms
        self.predicted_center_y = base_center_y + self.velocity_y_per_ms * dt_ms
        return self.predicted_center_x, self.predicted_center_y


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
    motion_filter: _MotionFilter | None = None
    last_width: float = 0.0
    last_height: float = 0.0
    confidence_ema: float | None = None
    class_votes: dict[str, int] = field(default_factory=dict)
    lifecycle_reason: TrackLifecycleReason | None = None


class TrackLifecycleManager:
    def __init__(self, config: TrackLifecycleConfig | None = None) -> None:
        self.config = config or TrackLifecycleConfig()
        self._next_stable_track_id = 1
        self._tracks: dict[int, _TrackMemory] = {}
        self._stable_id_by_source: dict[int, int] = {}
        self._last_visible_tracks: list[LifecycleTrack] = []
        self._last_candidate_context_tracks: list[LifecycleTrack] = []
        self._last_diagnostics: list[TrackLifecycleDecision] = []
        self._diagnostic_summary_window: dict[str, int] = {}

    def reset(self) -> None:
        self._next_stable_track_id = 1
        self._tracks.clear()
        self._stable_id_by_source.clear()
        self._last_visible_tracks.clear()
        self._last_candidate_context_tracks.clear()
        self._last_diagnostics.clear()
        self._diagnostic_summary_window.clear()

    def visible_tracks(self) -> list[LifecycleTrack]:
        return [_copy_lifecycle_track(track) for track in self._last_visible_tracks]

    def candidate_context_tracks(self) -> list[LifecycleTrack]:
        return [_copy_lifecycle_track(track) for track in self._last_candidate_context_tracks]

    def last_diagnostics(self) -> list[TrackLifecycleDecision]:
        return [_copy_lifecycle_decision(decision) for decision in self._last_diagnostics]

    def last_diagnostic_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for decision in self._last_diagnostics:
            summary[decision.reason] = summary.get(decision.reason, 0) + 1
        return summary

    def drain_diagnostic_summary(self) -> dict[str, int]:
        summary = dict(self._diagnostic_summary_window)
        self._diagnostic_summary_window.clear()
        return summary

    def update(
        self,
        *,
        detections: list[Detection],
        ts: datetime,
        frame_shape: tuple[int, ...] | None = None,
    ) -> list[LifecycleTrack]:
        self._last_diagnostics = []
        matched_stable_ids: set[int] = set()
        seen_this_frame: list[int] = []

        for detection in sorted(detections, key=self._detection_sort_key):
            match = self._match_existing_track(
                detection,
                matched_stable_ids,
                frame_shape,
            )
            if match is None:
                stable_id = self._create_track(detection, ts)
                lifecycle_reason: TrackLifecycleReason = "new_track"
            else:
                stable_id = match.stable_id
                lifecycle_reason = match.reason
            self._apply_detection(stable_id, detection, ts, frame_shape, lifecycle_reason)
            self._record_decision(
                self._tracks[stable_id],
                reason=lifecycle_reason,
                ts=ts,
                last_seen_age_ms=0,
            )
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
                    self._record_decision(
                        memory,
                        reason="coasting",
                        ts=ts,
                        last_seen_age_ms=age_ms,
                    )
                    visible.append(self._to_lifecycle_track(memory, last_seen_age_ms=age_ms))
                    continue
            forgotten = self._forget_track(stable_id)
            if forgotten is not None:
                self._record_decision(
                    forgotten,
                    reason="forgotten",
                    ts=ts,
                    state="lost",
                )

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
        )
        return (0 if has_source_match else 1, -detection.confidence)

    def _match_existing_track(
        self,
        detection: Detection,
        matched_stable_ids: set[int],
        frame_shape: tuple[int, ...] | None,
    ) -> _LifecycleMatch | None:
        bbox = _clamp_bbox(detection.bbox, frame_shape)
        source_track_id = detection.track_id
        if source_track_id is not None:
            stable_id = self._stable_id_by_source.get(source_track_id)
            memory = self._tracks.get(stable_id) if stable_id is not None else None
            if (
                memory is not None
                and stable_id not in matched_stable_ids
                and self._source_match_is_plausible(memory, bbox)
            ):
                return _LifecycleMatch(stable_id=stable_id, reason="source_id_match")

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
    ) -> _LifecycleMatch | None:
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
        if best_stable_id is None:
            return None
        return _LifecycleMatch(
            stable_id=best_stable_id,
            reason="spatial_reassociation",
        )

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
        lifecycle_reason: TrackLifecycleReason,
    ) -> None:
        memory = self._tracks[stable_id]
        old_source_track_id = memory.source_track_id
        source_track_id = detection.track_id
        if old_source_track_id is not None and old_source_track_id != source_track_id:
            self._forget_source_mapping(old_source_track_id, stable_id)
            if source_track_id is not None:
                self._record_diagnostic_window_count("source_id_switches")
        if source_track_id is not None:
            self._stable_id_by_source[source_track_id] = stable_id

        bbox = _clamp_bbox(detection.bbox, frame_shape)
        dt_ms = max(1, _elapsed_ms(memory.last_seen_ts, ts))
        center_x, center_y, width, height = _bbox_center_size(bbox)
        if memory.motion_filter is None:
            memory.motion_filter = _MotionFilter(center_x=center_x, center_y=center_y)
        else:
            memory.motion_filter.update(bbox, float(dt_ms))
        memory.last_width = width
        memory.last_height = height
        memory.confidence_ema = (
            detection.confidence
            if memory.confidence_ema is None
            else self.config.confidence_ema_alpha * detection.confidence
            + (1.0 - self.config.confidence_ema_alpha) * memory.confidence_ema
        )
        memory.class_votes[detection.class_name] = (
            memory.class_votes.get(detection.class_name, 0) + 1
        )
        published_class_name = _voted_class_name(
            memory.class_votes,
            detection.class_name,
        )
        memory.hits += 1
        memory.source_track_id = source_track_id
        memory.class_name = published_class_name
        memory.state = (
            "active"
            if memory.state in {"active", "coasting"}
            or memory.hits >= self.config.tentative_hits
            or detection.confidence >= self.config.instant_activation_confidence
            else "tentative"
        )
        memory.detection = _copy_detection(
            detection.with_updates(
                track_id=stable_id,
                bbox=bbox,
                confidence=memory.confidence_ema,
                class_name=published_class_name,
            )
        )
        memory.lifecycle_reason = lifecycle_reason
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
                memory.lifecycle_reason = "duplicate_suppressed"
                self._record_decision(
                    memory,
                    reason="duplicate_suppressed",
                    ts=ts,
                    last_seen_age_ms=0,
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
                    selected_memory.lifecycle_reason = "duplicate_replaced"
                    self._record_decision(
                        selected_memory,
                        reason="duplicate_replaced",
                        ts=ts,
                        last_seen_age_ms=0,
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
        for class_name, count in duplicate.class_votes.items():
            selected.class_votes[class_name] = selected.class_votes.get(class_name, 0) + count
        selected.class_name = _voted_class_name(
            selected.class_votes,
            duplicate.detection.class_name,
        )
        if duplicate.confidence_ema is not None:
            selected.confidence_ema = (
                duplicate.confidence_ema
                if selected.confidence_ema is None
                else max(selected.confidence_ema, duplicate.confidence_ema)
            )
        selected.motion_filter = _copy_motion_filter(duplicate.motion_filter)
        selected.last_width = duplicate.last_width
        selected.last_height = duplicate.last_height
        selected.detection = _copy_detection(
            duplicate.detection.with_updates(
                track_id=selected.stable_track_id,
                class_name=selected.class_name,
                confidence=(
                    selected.confidence_ema
                    if selected.confidence_ema is not None
                    else duplicate.detection.confidence
                ),
            )
        )
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
        memory.lifecycle_reason = "coasting"
        memory.missing_updates += 1
        dt_ms = max(1, _elapsed_ms(memory.updated_ts, ts))
        damping = self.config.velocity_damping ** (
            dt_ms / max(1.0, self.config.nominal_frame_interval_ms)
        )
        if memory.motion_filter is None:
            center_x, center_y, width, height = _bbox_center_size(memory.detection.bbox)
            memory.motion_filter = _MotionFilter(center_x=center_x, center_y=center_y)
            memory.last_width = width
            memory.last_height = height
        predicted_center_x, predicted_center_y = memory.motion_filter.predict(
            float(dt_ms),
            damping,
        )
        width = memory.last_width
        height = memory.last_height
        predicted_bbox = (
            predicted_center_x - width / 2.0,
            predicted_center_y - height / 2.0,
            predicted_center_x + width / 2.0,
            predicted_center_y + height / 2.0,
        )
        memory.detection = _copy_detection(
            memory.detection.with_updates(
                track_id=memory.stable_track_id,
                bbox=_clamp_bbox(predicted_bbox, frame_shape),
            )
        )
        memory.updated_ts = ts

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
            lifecycle_reason=memory.lifecycle_reason,
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
                    lifecycle_reason=memory.lifecycle_reason,
                )
            )
        return sorted(tracks, key=lambda track: track.stable_track_id)

    def _forget_track(self, stable_id: int) -> _TrackMemory | None:
        memory = self._tracks.pop(stable_id, None)
        if memory is not None and memory.source_track_id is not None:
            self._forget_source_mapping(memory.source_track_id, stable_id)
        return memory

    def _forget_source_mapping(self, source_track_id: int, stable_id: int) -> None:
        if self._stable_id_by_source.get(source_track_id) == stable_id:
            self._stable_id_by_source.pop(source_track_id, None)

    def _record_decision(
        self,
        memory: _TrackMemory,
        *,
        reason: TrackLifecycleReason,
        ts: datetime,
        last_seen_age_ms: int | None = None,
        state: TrackLifecycleState | None = None,
    ) -> None:
        self._last_diagnostics.append(
            TrackLifecycleDecision(
                stable_track_id=memory.stable_track_id,
                source_track_id=memory.source_track_id,
                state=state or memory.state,
                reason=reason,
                last_seen_age_ms=(
                    last_seen_age_ms
                    if last_seen_age_ms is not None
                    else _elapsed_ms(memory.last_seen_ts, ts)
                ),
                detection=_copy_detection(
                    memory.detection.with_updates(track_id=memory.stable_track_id)
                ),
            )
        )
        self._record_diagnostic_window_count(reason)

    def _record_diagnostic_window_count(self, key: str) -> None:
        self._diagnostic_summary_window[key] = (
            self._diagnostic_summary_window.get(key, 0) + 1
        )


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


def _bbox_center_size(bbox: BoundingBox) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    return (x1 + width / 2.0, y1 + height / 2.0, width, height)


def _voted_class_name(votes: dict[str, int], current_class_name: str) -> str:
    best_count = max(votes.values(), default=0)
    tied = [
        class_name
        for class_name, count in votes.items()
        if count == best_count
    ]
    if current_class_name in tied:
        return current_class_name
    return sorted(tied)[0] if tied else current_class_name


def _copy_motion_filter(motion_filter: _MotionFilter | None) -> _MotionFilter | None:
    if motion_filter is None:
        return None
    return _MotionFilter(
        center_x=motion_filter.center_x,
        center_y=motion_filter.center_y,
        velocity_x_per_ms=motion_filter.velocity_x_per_ms,
        velocity_y_per_ms=motion_filter.velocity_y_per_ms,
        predicted_center_x=motion_filter.predicted_center_x,
        predicted_center_y=motion_filter.predicted_center_y,
    )


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
    return detection.with_updates()


def _copy_lifecycle_track(track: LifecycleTrack) -> LifecycleTrack:
    return LifecycleTrack(
        stable_track_id=track.stable_track_id,
        source_track_id=track.source_track_id,
        state=track.state,
        last_seen_age_ms=track.last_seen_age_ms,
        detection=_copy_detection(track.detection),
        lifecycle_reason=track.lifecycle_reason,
    )


def _copy_lifecycle_decision(decision: TrackLifecycleDecision) -> TrackLifecycleDecision:
    return TrackLifecycleDecision(
        stable_track_id=decision.stable_track_id,
        source_track_id=decision.source_track_id,
        state=decision.state,
        reason=decision.reason,
        last_seen_age_ms=decision.last_seen_age_ms,
        detection=_copy_detection(decision.detection),
    )
