from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from argus.vision.attributes import AttributeClassifier, AttributeModelConfig
from argus.vision.runtime import (
    CpuVendor,
    ExecutionProfile,
    ExecutionProvider,
    HostClassification,
    RuntimeExecutionPolicy,
)
from argus.vision.types import Detection


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
    class SessionOptions:
        def __init__(self) -> None:
            self.inter_op_num_threads: int | None = None
            self.intra_op_num_threads: int | None = None

    def __init__(self, outputs: list[np.ndarray]) -> None:
        self.outputs = outputs
        self.session: _FakeSession | None = None
        self.last_providers: list[str] | None = None
        self.last_sess_options: _FakeRuntime.SessionOptions | None = None

    def get_available_providers(self) -> list[str]:
        return ["CPUExecutionProvider"]

    def InferenceSession(
        self,
        model_path: str,
        providers: list[str],
        sess_options: object | None = None,
    ) -> _FakeSession:
        self.last_providers = list(providers)
        self.last_sess_options = sess_options  # type: ignore[assignment]
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


def test_attribute_classifier_uses_explicit_runtime_policy_and_thread_overrides(ppe_frame) -> None:
    runtime = _FakeRuntime(outputs=[np.array([[0.91, 0.12]], dtype=np.float32)])
    runtime_policy = RuntimeExecutionPolicy(
        host=HostClassification(
            system="linux",
            machine="x86_64",
            cpu_vendor=CpuVendor.INTEL,
            available_providers=(ExecutionProvider.CPU.value,),
            profile=ExecutionProfile.LINUX_X86_64_INTEL,
            profile_overridden=False,
        ),
        provider=ExecutionProvider.CPU.value,
        available_providers=(ExecutionProvider.CPU.value,),
        provider_overridden=False,
        inter_op_threads=1,
        intra_op_threads=3,
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
        runtime_policy=runtime_policy,
    )

    attributes = classifier.classify(
        ppe_frame,
        [
            Detection(
                class_name="hi_vis_worker",
                confidence=0.97,
                bbox=(36.0, 16.0, 92.0, 116.0),
                class_id=3,
            )
        ],
    )

    assert runtime.last_providers == [ExecutionProvider.CPU.value]
    assert runtime.last_sess_options is not None
    assert runtime.last_sess_options.inter_op_num_threads == 1
    assert runtime.last_sess_options.intra_op_num_threads == 3
    assert attributes == [{"hi_vis": True, "hard_hat": False}]
