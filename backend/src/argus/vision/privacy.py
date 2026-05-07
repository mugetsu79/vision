from __future__ import annotations

import weakref
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
from numpy.typing import NDArray

from argus.core.metrics import PRIVACY_FILTER_OPERATIONS_TOTAL
from argus.vision.types import Detection


class RegionDetector(Protocol):
    def detect(self, frame: NDArray[np.uint8]) -> list[tuple[int, int, int, int]]: ...


@dataclass(slots=True)
class PrivacyConfig:
    blur_faces: bool = True
    blur_plates: bool = True
    method: str = "gaussian"
    strength: int = 9


class PrivacyFilter:
    def __init__(
        self,
        *,
        config: PrivacyConfig,
        face_detector: RegionDetector | None = None,
        plate_detector: RegionDetector | None = None,
    ) -> None:
        self.config = config
        self.face_detector = face_detector
        self.plate_detector = plate_detector
        self._applied_regions: dict[
            int,
            tuple[weakref.ReferenceType[NDArray[np.uint8]], set[tuple[str, int, int, int, int]]],
        ] = {}

    def apply(
        self,
        frame: NDArray[np.uint8],
        *,
        detections: list[Detection] | None = None,
    ) -> NDArray[np.uint8]:
        try:
            applied = self._applied_regions_for(frame)

            if self.config.blur_faces and self.face_detector is not None:
                for bbox in self.face_detector.detect(frame):
                    self._apply_region(frame, bbox, "face", applied)

            if self.config.blur_faces and detections is not None:
                for bbox in _person_head_bboxes(detections):
                    self._apply_region(frame, bbox, "person_face", applied)

            if self.config.blur_plates and self.plate_detector is not None:
                for bbox in self.plate_detector.detect(frame):
                    self._apply_region(frame, bbox, "plate", applied)

            PRIVACY_FILTER_OPERATIONS_TOTAL.labels(result="success").inc()
            return frame
        except Exception:
            PRIVACY_FILTER_OPERATIONS_TOTAL.labels(result="error").inc()
            raise

    def _applied_regions_for(
        self,
        frame: NDArray[np.uint8],
    ) -> set[tuple[str, int, int, int, int]]:
        frame_key = id(frame)
        entry = self._applied_regions.get(frame_key)
        if entry is not None:
            cached_frame_ref, cached_applied = entry
            if cached_frame_ref() is frame:
                return cached_applied

        applied: set[tuple[str, int, int, int, int]] = set()

        def remove_stale_entry(_: weakref.ReferenceType[NDArray[np.uint8]]) -> None:
            current = self._applied_regions.get(frame_key)
            if current is not None and current[0] is frame_ref:
                self._applied_regions.pop(frame_key, None)

        frame_ref = weakref.ref(frame, remove_stale_entry)
        self._applied_regions[frame_key] = (frame_ref, applied)
        return applied

    def _apply_region(
        self,
        frame: NDArray[np.uint8],
        bbox: tuple[int, int, int, int],
        region_kind: str,
        applied: set[tuple[str, int, int, int, int]],
    ) -> None:
        x1, y1, x2, y2 = _clip_bbox(bbox, frame.shape[1], frame.shape[0])
        if x2 <= x1 or y2 <= y1:
            return

        signature = (region_kind, x1, y1, x2, y2)
        if signature in applied:
            return

        roi = frame[y1:y2, x1:x2]
        if self.config.method == "pixelate":
            frame[y1:y2, x1:x2] = _pixelate_roi(roi, self.config.strength)
        else:
            frame[y1:y2, x1:x2] = _gaussian_blur_roi(roi, self.config.strength)
        applied.add(signature)


def _person_head_bboxes(
    detections: list[Detection],
) -> list[tuple[int, int, int, int]]:
    bboxes: list[tuple[int, int, int, int]] = []
    for detection in detections:
        if detection.class_name.strip().lower() not in {"person", "pedestrian"}:
            continue
        x1, y1, x2, y2 = detection.bbox
        width = x2 - x1
        height = y2 - y1
        if width <= 2 or height <= 4:
            continue
        head_height = max(2.0, height * 0.42)
        head_width = max(2.0, width * 0.9)
        center_x = x1 + width / 2.0
        bboxes.append(
            (
                int(round(center_x - head_width / 2.0)),
                int(round(y1)),
                int(round(center_x + head_width / 2.0)),
                int(round(y1 + head_height)),
            )
        )
    return bboxes


def _clip_bbox(
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    return (
        int(np.clip(x1, 0, width)),
        int(np.clip(y1, 0, height)),
        int(np.clip(x2, 0, width)),
        int(np.clip(y2, 0, height)),
    )


def _pixelate_roi(roi: NDArray[np.uint8], strength: int) -> NDArray[np.uint8]:
    pixel_size = max(1, strength)
    width = max(1, roi.shape[1] // pixel_size)
    height = max(1, roi.shape[0] // pixel_size)
    reduced = cv2.resize(roi, (width, height), interpolation=cv2.INTER_LINEAR)
    return np.asarray(
        cv2.resize(reduced, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_NEAREST),
        dtype=np.uint8,
    )


def _gaussian_blur_roi(roi: NDArray[np.uint8], strength: int) -> NDArray[np.uint8]:
    kernel_size = max(3, (max(1, strength) * 2 + 1) | 1)
    return np.asarray(
        cv2.GaussianBlur(roi, (kernel_size, kernel_size), sigmaX=0),
        dtype=np.uint8,
    )
