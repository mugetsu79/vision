from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import hypot

from argus.vision.track_lifecycle import LifecycleTrack
from argus.vision.types import BoundingBox, Detection


@dataclass(frozen=True, slots=True)
class CandidateQualityConfig:
    new_track_min_confidence: dict[str, float] = field(
        default_factory=lambda: {
            "person": 0.45,
            "car": 0.35,
            "truck": 0.35,
            "bus": 0.35,
            "forklift": 0.35,
            "default": 0.40,
        }
    )
    display_min_confidence: dict[str, float] = field(default_factory=dict)
    association_min_confidence: dict[str, float] = field(default_factory=dict)
    continuation_min_confidence: float = 0.10
    near_track_iou_threshold: float = 0.10
    near_track_center_distance_ratio: float = 0.65
    fragment_iou_or_ios_threshold: float = 0.55
    duplicate_suppression_enabled: bool = True

    def __post_init__(self) -> None:
        if not self.display_min_confidence:
            object.__setattr__(
                self,
                "display_min_confidence",
                dict(self.new_track_min_confidence),
            )
        if not self.association_min_confidence:
            object.__setattr__(
                self,
                "association_min_confidence",
                dict(self.new_track_min_confidence),
            )


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    detection: Detection
    accepted: bool
    reason: str
    display_eligible: bool = False


class CandidateQualityGate:
    def __init__(self, config: CandidateQualityConfig | None = None) -> None:
        self.config = config or CandidateQualityConfig()

    @classmethod
    def from_profile_candidate_quality(
        cls,
        candidate_quality: object,
    ) -> CandidateQualityGate:
        thresholds = dict(CandidateQualityConfig().new_track_min_confidence)
        profile_thresholds = getattr(candidate_quality, "new_track_min_confidence", None)
        if isinstance(profile_thresholds, Mapping):
            for class_name, value in profile_thresholds.items():
                if isinstance(class_name, str) and isinstance(value, int | float):
                    thresholds[class_name] = float(value)
        display_thresholds = dict(thresholds)
        profile_display_thresholds = getattr(
            candidate_quality,
            "display_min_confidence",
            None,
        )
        if isinstance(profile_display_thresholds, Mapping):
            for class_name, value in profile_display_thresholds.items():
                if isinstance(class_name, str) and isinstance(value, int | float):
                    display_thresholds[class_name] = float(value)
        association_thresholds = dict(thresholds)
        profile_association_thresholds = getattr(
            candidate_quality,
            "association_min_confidence",
            None,
        )
        if isinstance(profile_association_thresholds, Mapping):
            for class_name, value in profile_association_thresholds.items():
                if isinstance(class_name, str) and isinstance(value, int | float):
                    association_thresholds[class_name] = float(value)
        duplicate_suppression_enabled = getattr(
            candidate_quality,
            "duplicate_suppression_enabled",
            True,
        )
        return cls(
            CandidateQualityConfig(
                new_track_min_confidence=thresholds,
                display_min_confidence=display_thresholds,
                association_min_confidence=association_thresholds,
                duplicate_suppression_enabled=bool(duplicate_suppression_enabled),
            )
        )

    def filter_detections(
        self,
        detections: list[Detection],
        *,
        existing_tracks: list[LifecycleTrack],
        frame_shape: tuple[int, ...] | None = None,
    ) -> tuple[list[Detection], list[CandidateDecision]]:
        filtered: list[Detection] = []
        decisions: list[CandidateDecision] = []

        for detection in detections:
            decision = self._decide(detection, existing_tracks, frame_shape)
            decisions.append(decision)
            if decision.accepted:
                filtered.append(detection)

        return filtered, decisions

    def _decide(
        self,
        detection: Detection,
        existing_tracks: list[LifecycleTrack],
        frame_shape: tuple[int, ...] | None,
    ) -> CandidateDecision:
        same_class_tracks = [
            track
            for track in existing_tracks
            if track.state in {"tentative", "active", "coasting"}
            and track.detection.class_name == detection.class_name
        ]
        association_threshold = self._association_threshold(detection.class_name)
        display_eligible = (
            detection.confidence >= self._display_threshold(detection.class_name)
        )
        if (
            detection.confidence < association_threshold
            and detection.confidence >= self.config.continuation_min_confidence
            and self._is_near_existing_track(detection, same_class_tracks, frame_shape)
        ):
            return CandidateDecision(
                detection,
                accepted=True,
                reason="existing_track_continuation",
                display_eligible=display_eligible,
            )

        if (
            self.config.duplicate_suppression_enabled
            and self._is_duplicate_fragment(detection, same_class_tracks, frame_shape)
        ):
            return CandidateDecision(
                detection,
                accepted=False,
                reason="duplicate_fragment",
                display_eligible=False,
            )

        if (
            not display_eligible
            and detection.confidence >= association_threshold
            and self._is_near_existing_track(detection, same_class_tracks, frame_shape)
        ):
            return CandidateDecision(
                detection,
                accepted=True,
                reason="existing_track_association",
                display_eligible=display_eligible,
            )

        if display_eligible:
            return CandidateDecision(
                detection,
                accepted=True,
                reason="new_track_high_confidence",
                display_eligible=True,
            )

        return CandidateDecision(
            detection,
            accepted=False,
            reason="new_track_low_confidence",
            display_eligible=False,
        )

    def _new_track_threshold(self, class_name: str) -> float:
        return self._threshold_for_class(self.config.new_track_min_confidence, class_name)

    def _association_threshold(self, class_name: str) -> float:
        return self._threshold_for_class(self.config.association_min_confidence, class_name)

    def _display_threshold(self, class_name: str) -> float:
        return self._threshold_for_class(self.config.display_min_confidence, class_name)

    def _threshold_for_class(
        self,
        thresholds: Mapping[str, float],
        class_name: str,
    ) -> float:
        if (
            class_name in {"car", "truck", "bus", "forklift"}
            and class_name not in thresholds
            and "vehicle" in thresholds
        ):
            return thresholds["vehicle"]
        return thresholds.get(
            class_name,
            thresholds.get("default", 0.40),
        )

    def _is_near_existing_track(
        self,
        detection: Detection,
        tracks: list[LifecycleTrack],
        frame_shape: tuple[int, ...] | None,
    ) -> bool:
        bbox = _clamp_bbox(detection.bbox, frame_shape)
        return any(
            _iou(bbox, _clamp_bbox(track.detection.bbox, frame_shape))
            >= self.config.near_track_iou_threshold
            or _center_distance_ratio(bbox, _clamp_bbox(track.detection.bbox, frame_shape))
            <= self.config.near_track_center_distance_ratio
            for track in tracks
        )

    def _is_duplicate_fragment(
        self,
        detection: Detection,
        tracks: list[LifecycleTrack],
        frame_shape: tuple[int, ...] | None,
    ) -> bool:
        bbox = _clamp_bbox(detection.bbox, frame_shape)
        bbox_area = _area(bbox)
        if bbox_area <= 0:
            return False

        for track in tracks:
            existing_bbox = _clamp_bbox(track.detection.bbox, frame_shape)
            existing_area = _area(existing_bbox)
            if existing_area <= 0:
                continue
            smaller_area_ratio = min(bbox_area, existing_area) / max(bbox_area, existing_area)
            if smaller_area_ratio > 0.80:
                continue
            intersection = _intersection_area(bbox, existing_bbox)
            if intersection <= 0:
                continue
            iou = intersection / (bbox_area + existing_area - intersection)
            intersection_over_smaller = intersection / min(bbox_area, existing_area)
            if (
                iou >= self.config.fragment_iou_or_ios_threshold
                or intersection_over_smaller >= self.config.fragment_iou_or_ios_threshold
            ):
                return True
        return False


def _intersection_area(left: BoundingBox, right: BoundingBox) -> float:
    intersection_width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    intersection_height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return intersection_width * intersection_height


def _area(bbox: BoundingBox) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _iou(left: BoundingBox, right: BoundingBox) -> float:
    intersection = _intersection_area(left, right)
    if intersection <= 0:
        return 0.0
    union = _area(left) + _area(right) - intersection
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
