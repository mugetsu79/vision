from __future__ import annotations

import numpy as np

from argus.vision.privacy import PrivacyConfig, PrivacyFilter
from argus.vision.types import Detection


class _StaticDetector:
    def __init__(self, boxes: list[tuple[int, int, int, int]]) -> None:
        self.boxes = boxes

    def detect(self, frame):  # noqa: ANN001
        return self.boxes


def test_privacy_filter_pixelates_sensitive_regions_idempotently(pedestrian_frame) -> None:
    face_detector = _StaticDetector([(54, 26, 74, 44)])
    plate_detector = _StaticDetector([(24, 64, 40, 70)])
    filter_config = PrivacyConfig(
        blur_faces=True,
        blur_plates=True,
        method="pixelate",
        strength=8,
    )
    privacy_filter = PrivacyFilter(
        config=filter_config,
        face_detector=face_detector,
        plate_detector=plate_detector,
    )

    frame = pedestrian_frame.copy()
    first_pass = privacy_filter.apply(frame)
    second_pass = privacy_filter.apply(frame)

    assert first_pass is frame
    assert second_pass is frame
    assert np.array_equal(first_pass, second_pass)
    assert not np.array_equal(first_pass[26:44, 54:74], pedestrian_frame[26:44, 54:74])
    assert np.array_equal(first_pass[0:8, 0:8], pedestrian_frame[0:8, 0:8])


def test_privacy_filter_supports_gaussian_mode(vehicle_frame) -> None:
    face_detector = _StaticDetector([])
    plate_detector = _StaticDetector([(108, 64, 128, 70)])
    privacy_filter = PrivacyFilter(
        config=PrivacyConfig(
            blur_faces=False,
            blur_plates=True,
            method="gaussian",
            strength=9,
        ),
        face_detector=face_detector,
        plate_detector=plate_detector,
    )

    frame = vehicle_frame.copy()
    privacy_filter.apply(frame)

    assert not np.array_equal(frame[64:70, 108:128], vehicle_frame[64:70, 108:128])


def test_privacy_filter_blurs_person_head_regions_without_face_detector() -> None:
    privacy_filter = PrivacyFilter(
        config=PrivacyConfig(
            blur_faces=True,
            blur_plates=False,
            method="gaussian",
            strength=9,
        ),
    )
    detections = [
        Detection(
            class_name="person",
            confidence=0.95,
            bbox=(40.0, 20.0, 88.0, 116.0),
            class_id=0,
        )
    ]

    y_index, x_index = np.indices((128, 128))
    original = np.dstack(
        (
            (x_index * 3 + y_index * 5) % 256,
            (x_index * 7 + y_index * 2) % 256,
            (x_index * 11 + y_index * 13) % 256,
        )
    ).astype(np.uint8)
    frame = original.copy()
    privacy_filter.apply(frame, detections=detections)

    assert not np.array_equal(frame[20:46, 48:80], original[20:46, 48:80])
    assert not np.array_equal(frame[52:58, 44:84], original[52:58, 44:84])
    assert np.array_equal(frame[80:104, 48:80], original[80:104, 48:80])
