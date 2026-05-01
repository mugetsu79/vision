from __future__ import annotations

import numpy as np

from argus.vision.open_vocab_detector import OpenVocabDetector, OpenVocabModelConfig
from argus.vision.runtime import (
    CpuVendor,
    ExecutionProfile,
    ExecutionProvider,
    HostClassification,
    RuntimeExecutionPolicy,
)


class _FakeBoxes:
    def __init__(self) -> None:
        self.xyxy = np.array([[10.0, 20.0, 50.0, 80.0]], dtype=np.float32)
        self.conf = np.array([0.91], dtype=np.float32)
        self.cls = np.array([0], dtype=np.float32)


class _FakeResult:
    names = {0: "forklift"}

    def __init__(self) -> None:
        self.boxes = _FakeBoxes()


class _FakeUltralyticsModel:
    def __init__(self, path: str) -> None:
        self.path = path
        self.classes: list[str] = []
        self.predict_calls: list[dict[str, object]] = []

    def set_classes(self, classes: list[str]) -> None:
        self.classes = list(classes)

    def predict(
        self,
        frame,  # noqa: ANN001
        verbose: bool = False,
        conf: float = 0.25,
        iou: float = 0.45,
    ):
        self.predict_calls.append(
            {"shape": frame.shape, "conf": conf, "iou": iou, "verbose": verbose}
        )
        return [_FakeResult()]


def _policy() -> RuntimeExecutionPolicy:
    return RuntimeExecutionPolicy(
        host=HostClassification(
            system="linux",
            machine="aarch64",
            cpu_vendor=CpuVendor.UNKNOWN,
            available_providers=(ExecutionProvider.CUDA.value,),
            profile=ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON,
        ),
        provider=ExecutionProvider.CUDA.value,
        available_providers=(ExecutionProvider.CUDA.value,),
        provider_overridden=False,
    )


def test_open_vocab_detector_sets_initial_vocabulary_and_normalizes_detections() -> None:
    loaded: list[_FakeUltralyticsModel] = []

    def loader(path: str, backend: str) -> _FakeUltralyticsModel:
        model = _FakeUltralyticsModel(path)
        loaded.append(model)
        return model

    detector = OpenVocabDetector(
        OpenVocabModelConfig(
            name="YOLOE-26N",
            path="/models/yoloe-26n-seg.pt",
            input_shape={"width": 640, "height": 640},
            capability_config={"runtime_backend": "ultralytics_yoloe"},
            default_vocabulary=["forklift", "pallet jack"],
            confidence_threshold=0.4,
            iou_threshold=0.5,
        ),
        runtime=None,
        runtime_policy=_policy(),
        model_loader=loader,
    )

    detections = detector.detect(np.zeros((100, 200, 3), dtype=np.uint8))

    assert loaded[0].classes == ["forklift", "pallet jack"]
    assert detections[0].class_name == "forklift"
    assert detections[0].confidence == 0.91
    assert detections[0].bbox == (10.0, 20.0, 50.0, 80.0)


def test_open_vocab_detector_hot_updates_runtime_vocabulary() -> None:
    model = _FakeUltralyticsModel("/models/yoloe-26n-seg.pt")

    detector = OpenVocabDetector(
        OpenVocabModelConfig(
            name="YOLOE-26N",
            path="/models/yoloe-26n-seg.pt",
            input_shape={"width": 640, "height": 640},
            capability_config={"runtime_backend": "ultralytics_yoloe"},
            default_vocabulary=["person"],
        ),
        runtime=None,
        runtime_policy=_policy(),
        model_loader=lambda path, backend: model,
    )

    detector.update_runtime_vocabulary(["forklift", "forklift", ""])

    assert model.classes == ["forklift"]
    assert detector.describe_runtime_state()["runtime_vocabulary"] == ["forklift"]
