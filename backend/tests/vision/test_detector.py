from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from argus.vision.detector import DetectionModelConfig, YoloDetector


@dataclass(slots=True)
class _FakeInput:
    name: str


class _FakeSession:
    def __init__(self, providers: list[str], outputs: list[np.ndarray]) -> None:
        self._providers = providers
        self._outputs = outputs
        self.run_calls = 0

    def get_inputs(self) -> list[_FakeInput]:
        return [_FakeInput(name="images")]

    def get_providers(self) -> list[str]:
        return self._providers

    def run(self, output_names: object, inputs: dict[str, np.ndarray]) -> list[np.ndarray]:
        self.run_calls += 1
        assert "images" in inputs
        return self._outputs


class _FakeRuntime:
    def __init__(self, providers: list[str], outputs: list[np.ndarray]) -> None:
        self._providers = providers
        self._outputs = outputs

    def get_available_providers(self) -> list[str]:
        return self._providers

    def InferenceSession(
        self,
        model_path: str,
        providers: list[str],
        sess_options: object | None = None,
    ) -> _FakeSession:
        assert model_path.endswith(".onnx")
        assert providers
        return _FakeSession(providers=providers, outputs=self._outputs)


def test_detector_selects_best_provider_and_filters_allowed_classes(vehicle_frame) -> None:
    model_config = DetectionModelConfig(
        name="detector",
        path="tests/fixtures/fake-detector.onnx",
        classes=["car", "truck", "person", "hi_vis_worker"],
        input_shape={"width": 640, "height": 640},
        confidence_threshold=0.2,
        iou_threshold=0.5,
    )
    runtime = _FakeRuntime(
        providers=["CPUExecutionProvider", "CUDAExecutionProvider"],
        outputs=[
            np.array(
                [
                    [18.0, 48.0, 58.0, 74.0, 0.94, 0.0],
                    [82.0, 38.0, 146.0, 78.0, 0.91, 1.0],
                    [40.0, 20.0, 80.0, 80.0, 0.88, 2.0],
                ],
                dtype=np.float32,
            )
        ],
    )

    detector = YoloDetector(model_config, runtime=runtime)

    detections = detector.detect(vehicle_frame, allowed_classes={"truck"})

    assert detector.selected_provider == "CUDAExecutionProvider"
    assert [detection.class_name for detection in detections] == ["truck"]
    assert detections[0].bbox == (82.0, 38.0, 146.0, 78.0)


def test_detector_supports_vehicle_person_and_custom_ppe_classes(
    vehicle_frame,
    pedestrian_frame,
    ppe_frame,
) -> None:
    model_config = DetectionModelConfig(
        name="detector",
        path="tests/fixtures/fake-detector.onnx",
        classes=["car", "truck", "person", "hi_vis_worker"],
        input_shape={"width": 640, "height": 640},
    )
    runtime = _FakeRuntime(
        providers=["CoreMLExecutionProvider", "CPUExecutionProvider"],
        outputs=[
            np.array(
                [
                    [18.0, 48.0, 58.0, 74.0, 0.94, 0.0],
                    [42.0, 18.0, 86.0, 112.0, 0.98, 2.0],
                    [36.0, 16.0, 92.0, 116.0, 0.96, 3.0],
                ],
                dtype=np.float32,
            )
        ],
    )
    detector = YoloDetector(model_config, runtime=runtime)

    vehicle_detections = detector.detect(vehicle_frame, allowed_classes={"car"})
    pedestrian_detections = detector.detect(pedestrian_frame, allowed_classes={"person"})
    ppe_detections = detector.detect(ppe_frame, allowed_classes={"hi_vis_worker"})

    assert [d.class_name for d in vehicle_detections] == ["car"]
    assert [d.class_name for d in pedestrian_detections] == ["person"]
    assert [d.class_name for d in ppe_detections] == ["hi_vis_worker"]
