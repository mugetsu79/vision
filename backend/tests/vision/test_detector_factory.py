from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from argus.inference.engine import RuntimeArtifactSettings
from argus.models.enums import (
    DetectorCapability,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
)
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


def test_factory_builds_engine_detector_for_tensorrt_selection(monkeypatch) -> None:  # noqa: ANN001
    import argus.vision.ultralytics_engine_detector as engine_module

    class _FakeEngineDetector:
        def __init__(self, artifact) -> None:  # noqa: ANN001
            self.artifact = artifact

    monkeypatch.setattr(engine_module, "UltralyticsEngineDetector", _FakeEngineDetector)
    artifact = RuntimeArtifactSettings(
        id=uuid4(),
        scope=RuntimeArtifactScope.MODEL,
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.FIXED_VOCAB,
        runtime_backend="tensorrt_engine",
        path="/models/yolo26n.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "car"],
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=1234,
    )
    selection = SimpleNamespace(selected_backend="tensorrt_engine", artifact=artifact)
    model = SimpleNamespace(
        name="YOLO26n",
        path="/models/yolo26n.onnx",
        capability=DetectorCapability.FIXED_VOCAB,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        confidence_threshold=0.25,
        iou_threshold=0.45,
    )

    detector = build_detector(
        model=model,
        runtime=object(),
        runtime_policy=object(),
        runtime_selection=selection,
        yolo_detector_cls=_FakeFixedDetector,
    )

    assert isinstance(detector, _FakeEngineDetector)
    assert detector.artifact == artifact
