from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
from numpy.typing import NDArray

from argus.core.metrics import PRIVACY_FILTER_OPERATIONS_TOTAL


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
        self._applied_regions: dict[int, set[tuple[str, int, int, int, int]]] = {}

    def apply(self, frame: NDArray[np.uint8]) -> NDArray[np.uint8]:
        try:
            frame_key = id(frame)
            applied = self._applied_regions.setdefault(frame_key, set())
            if len(self._applied_regions) > 64:
                self._applied_regions.clear()
                self._applied_regions[frame_key] = applied

            if self.config.blur_faces and self.face_detector is not None:
                for bbox in self.face_detector.detect(frame):
                    self._apply_region(frame, bbox, "face", applied)

            if self.config.blur_plates and self.plate_detector is not None:
                for bbox in self.plate_detector.detect(frame):
                    self._apply_region(frame, bbox, "plate", applied)

            PRIVACY_FILTER_OPERATIONS_TOTAL.labels(result="success").inc()
            return frame
        except Exception:
            PRIVACY_FILTER_OPERATIONS_TOTAL.labels(result="error").inc()
            raise

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
    kernel_size = max(3, strength | 1)
    return np.asarray(
        cv2.GaussianBlur(roi, (kernel_size, kernel_size), sigmaX=0),
        dtype=np.uint8,
    )
