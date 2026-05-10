from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import numpy as np

from argus.inference.engine import RuntimeArtifactSettings
from argus.models.enums import (
    DetectorCapability,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
)
from argus.vision.ultralytics_engine_detector import UltralyticsEngineDetector


class _FakeModel:
    def __init__(self, results: list[object]) -> None:
        self.results = results
        self.calls: list[dict[str, object]] = []

    def predict(self, frame, **kwargs):  # noqa: ANN001
        self.calls.append({"frame": frame, **kwargs})
        return self.results


def _artifact(classes: list[str] | None = None) -> RuntimeArtifactSettings:
    return RuntimeArtifactSettings(
        id=uuid4(),
        scope=RuntimeArtifactScope.MODEL,
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.FIXED_VOCAB,
        runtime_backend="tensorrt_engine",
        path="/models/yolo26n.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=classes or ["person", "car"],
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=1234,
    )


def _result(
    *,
    xyxy: list[list[float]],
    conf: list[float],
    cls: list[float],
    names: dict[int, str] | None = None,
) -> object:
    return SimpleNamespace(
        names=names or {},
        boxes=SimpleNamespace(
            xyxy=np.asarray(xyxy, dtype=np.float32),
            conf=np.asarray(conf, dtype=np.float32),
            cls=np.asarray(cls, dtype=np.float32),
        ),
    )


def test_engine_detector_maps_ultralytics_boxes_to_detections() -> None:
    model = _FakeModel(
        [
            _result(
                xyxy=[[1, 2, 3, 4]],
                conf=[0.91],
                cls=[1],
                names={1: "car"},
            )
        ]
    )
    detector = UltralyticsEngineDetector(_artifact(), model_loader=lambda path: model)

    detections = detector.detect(np.zeros((8, 8, 3), dtype=np.uint8))

    assert len(detections) == 1
    assert detections[0].class_name == "car"
    assert detections[0].class_id == 1
    assert detections[0].confidence == 0.91
    assert detections[0].bbox == (1.0, 2.0, 3.0, 4.0)
    assert model.calls[0]["verbose"] is False


def test_engine_detector_uses_artifact_classes_when_result_names_are_missing() -> None:
    model = _FakeModel(
        [
            _result(
                xyxy=[[1, 2, 3, 4]],
                conf=[0.8],
                cls=[0],
            )
        ]
    )
    detector = UltralyticsEngineDetector(
        _artifact(classes=["forklift"]),
        model_loader=lambda path: model,
    )

    detections = detector.detect(np.zeros((8, 8, 3), dtype=np.uint8))

    assert detections[0].class_name == "forklift"


def test_engine_detector_empty_results_return_empty_list() -> None:
    detector = UltralyticsEngineDetector(_artifact(), model_loader=lambda path: _FakeModel([]))

    detections = detector.detect(np.zeros((8, 8, 3), dtype=np.uint8))

    assert detections == []


def test_engine_detector_describes_runtime_artifact_state() -> None:
    artifact = _artifact()
    detector = UltralyticsEngineDetector(artifact, model_loader=lambda path: _FakeModel([]))

    state = detector.describe_runtime_state()

    assert state["capability"] is DetectorCapability.FIXED_VOCAB
    assert state["runtime_backend"] == "tensorrt_engine"
    assert state["artifact_id"] == str(artifact.id)
    assert state["artifact_path"] == artifact.path
