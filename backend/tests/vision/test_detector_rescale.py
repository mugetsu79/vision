from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from argus.vision.detector import YoloDetector


def _make_detector(model_input: tuple[int, int]) -> YoloDetector:
    detector = YoloDetector.__new__(YoloDetector)
    detector.model_config = MagicMock()
    detector.model_config.input_shape = {"width": model_input[0], "height": model_input[1]}
    return detector


def test_rescale_bbox_scales_model_input_to_frame() -> None:
    detector = _make_detector((640, 640))
    bbox = (100.0, 100.0, 500.0, 500.0)
    result = detector._rescale_bbox(bbox, frame_width=1280, frame_height=720)
    assert result == pytest.approx((200.0, 112.5, 1000.0, 562.5), rel=1e-6)


def test_rescale_bbox_clips_to_frame_bounds() -> None:
    detector = _make_detector((640, 640))
    bbox = (-50.0, -50.0, 700.0, 700.0)
    x1, y1, x2, y2 = detector._rescale_bbox(bbox, frame_width=1280, frame_height=720)
    assert x1 == 0.0
    assert y1 == 0.0
    assert x2 == pytest.approx(1280.0)
    assert y2 == pytest.approx(720.0)


def test_rescale_bbox_returns_unchanged_on_invalid_dimensions() -> None:
    detector = _make_detector((0, 640))
    bbox = (10.0, 20.0, 30.0, 40.0)
    result = detector._rescale_bbox(bbox, frame_width=1280, frame_height=720)
    assert result == (10.0, 20.0, 30.0, 40.0)
