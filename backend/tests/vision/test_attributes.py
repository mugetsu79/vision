from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from traffic_monitor.vision.attributes import AttributeClassifier, AttributeModelConfig
from traffic_monitor.vision.types import Detection


@dataclass(slots=True)
class _FakeInput:
    name: str


class _FakeSession:
    def __init__(self, outputs: list[np.ndarray]) -> None:
        self.outputs = outputs
        self.last_batch_shape: tuple[int, ...] | None = None

    def get_inputs(self) -> list[_FakeInput]:
        return [_FakeInput(name="images")]

    def run(self, output_names: object, inputs: dict[str, np.ndarray]) -> list[np.ndarray]:
        self.last_batch_shape = inputs["images"].shape
        return self.outputs


class _FakeRuntime:
    def __init__(self, outputs: list[np.ndarray]) -> None:
        self.outputs = outputs
        self.session: _FakeSession | None = None

    def get_available_providers(self) -> list[str]:
        return ["CPUExecutionProvider"]

    def InferenceSession(
        self,
        model_path: str,
        providers: list[str],
        sess_options: object | None = None,
    ) -> _FakeSession:
        self.session = _FakeSession(self.outputs)
        return self.session


def test_attribute_classifier_batches_relevant_detections_and_maps_outputs(ppe_frame) -> None:
    runtime = _FakeRuntime(
        outputs=[np.array([[0.91, 0.12]], dtype=np.float32)]
    )
    classifier = AttributeClassifier(
        AttributeModelConfig(
            name="ppe-attributes",
            path="tests/fixtures/fake-attributes.onnx",
            classes=["hi_vis", "hard_hat"],
            input_shape={"width": 64, "height": 64},
            target_classes={"person", "hi_vis_worker"},
            threshold=0.5,
            batch_size=4,
        ),
        runtime=runtime,
    )

    attributes = classifier.classify(
        ppe_frame,
        [
            Detection(
                class_name="hi_vis_worker",
                confidence=0.97,
                bbox=(36.0, 16.0, 92.0, 116.0),
                class_id=3,
            ),
            Detection(class_name="car", confidence=0.92, bbox=(0.0, 0.0, 32.0, 32.0), class_id=0),
        ],
    )

    assert runtime.session is not None
    assert runtime.session.last_batch_shape == (1, 3, 64, 64)
    assert attributes == [{"hi_vis": True, "hard_hat": False}, {}]
