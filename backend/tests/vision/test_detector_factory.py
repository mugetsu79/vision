from __future__ import annotations

from types import SimpleNamespace

from argus.models.enums import DetectorCapability
from argus.vision.detector_factory import build_detector


class _FakeFixedDetector:
    def __init__(self, config, runtime, runtime_policy) -> None:  # noqa: ANN001
        self.config = config


class _FakeOpenDetector:
    def __init__(self, config, runtime, runtime_policy) -> None:  # noqa: ANN001
        self.config = config


def test_factory_builds_open_vocab_detector_with_runtime_backend(monkeypatch) -> None:  # noqa: ANN001
    import argus.vision.open_vocab_detector as open_vocab_module

    monkeypatch.setattr(open_vocab_module, "OpenVocabDetector", _FakeOpenDetector)
    model = SimpleNamespace(
        name="YOLOE-26N",
        path="/models/yoloe-26n-seg.pt",
        capability=DetectorCapability.OPEN_VOCAB,
        capability_config={"runtime_backend": "ultralytics_yoloe"},
        classes=[],
        input_shape={"width": 640, "height": 640},
        runtime_vocabulary=SimpleNamespace(terms=["forklift"]),
        confidence_threshold=0.25,
        iou_threshold=0.45,
    )

    detector = build_detector(
        model=model,
        runtime=object(),
        runtime_policy=object(),
        yolo_detector_cls=_FakeFixedDetector,
    )

    assert isinstance(detector, _FakeOpenDetector)
    assert detector.config.default_vocabulary == ["forklift"]
    assert detector.config.capability_config["runtime_backend"] == "ultralytics_yoloe"
