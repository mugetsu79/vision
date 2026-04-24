from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from argus.vision.detector import DetectionModelConfig, YoloDetector
from argus.vision.runtime import (
    CpuVendor,
    ExecutionProfile,
    ExecutionProvider,
    HostClassification,
    RuntimeExecutionPolicy,
)


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
    class SessionOptions:
        def __init__(self) -> None:
            self.inter_op_num_threads: int | None = None
            self.intra_op_num_threads: int | None = None

    def __init__(self, providers: list[str], outputs: list[np.ndarray]) -> None:
        self._providers = providers
        self._outputs = outputs
        self.last_providers: list[str] | None = None
        self.last_sess_options: _FakeRuntime.SessionOptions | None = None

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
        self.last_providers = list(providers)
        self.last_sess_options = sess_options  # type: ignore[assignment]
        return _FakeSession(providers=providers, outputs=self._outputs)


def _runtime_policy(
    *,
    system: str,
    machine: str,
    cpu_vendor: CpuVendor,
    profile: ExecutionProfile,
    provider: ExecutionProvider,
    available_providers: tuple[str, ...],
    inter_op_threads: int | None = None,
    intra_op_threads: int | None = None,
    provider_overridden: bool = False,
) -> RuntimeExecutionPolicy:
    return RuntimeExecutionPolicy(
        host=HostClassification(
            system=system,
            machine=machine,
            cpu_vendor=cpu_vendor,
            available_providers=available_providers,
            profile=profile,
            profile_overridden=False,
        ),
        provider=provider.value,
        available_providers=available_providers,
        provider_overridden=provider_overridden,
        inter_op_threads=inter_op_threads,
        intra_op_threads=intra_op_threads,
    )


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

    detector = YoloDetector(
        model_config,
        runtime=runtime,
        runtime_policy=_runtime_policy(
            system="linux",
            machine="x86_64",
            cpu_vendor=CpuVendor.INTEL,
            profile=ExecutionProfile.NVIDIA_LINUX_X86_64,
            provider=ExecutionProvider.CUDA,
            available_providers=(
                ExecutionProvider.CPU.value,
                ExecutionProvider.CUDA.value,
            ),
        ),
    )

    detections = detector.detect(vehicle_frame, allowed_classes={"truck"})

    assert detector.selected_provider == "CUDAExecutionProvider"
    assert [detection.class_name for detection in detections] == ["truck"]
    assert detections[0].bbox == pytest.approx((20.5, 5.7, 36.5, 11.7), rel=1e-6)


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
    detector = YoloDetector(
        model_config,
        runtime=runtime,
        runtime_policy=_runtime_policy(
            system="darwin",
            machine="arm64",
            cpu_vendor=CpuVendor.APPLE,
            profile=ExecutionProfile.MACOS_APPLE_SILICON,
            provider=ExecutionProvider.COREML,
            available_providers=(
                ExecutionProvider.COREML.value,
                ExecutionProvider.CPU.value,
            ),
        ),
    )

    vehicle_detections = detector.detect(vehicle_frame, allowed_classes={"car"})
    pedestrian_detections = detector.detect(pedestrian_frame, allowed_classes={"person"})
    ppe_detections = detector.detect(ppe_frame, allowed_classes={"hi_vis_worker"})

    assert [d.class_name for d in vehicle_detections] == ["car"]
    assert [d.class_name for d in pedestrian_detections] == ["person"]
    assert [d.class_name for d in ppe_detections] == ["hi_vis_worker"]


def test_detector_supports_channel_first_yolo_outputs(vehicle_frame) -> None:
    model_config = DetectionModelConfig(
        name="detector",
        path="tests/fixtures/fake-detector.onnx",
        classes=["car", "truck", "person", "hi_vis_worker"],
        input_shape={"width": 640, "height": 640},
    )
    runtime = _FakeRuntime(
        providers=["CPUExecutionProvider"],
        outputs=[
            _channel_first_output(
                [
                    [38.0, 61.0, 40.0, 26.0, 0.94, 0.03, 0.02, 0.01],
                    [96.0, 58.0, 64.0, 40.0, 0.02, 0.04, 0.93, 0.01],
                ],
                feature_count=8,
                detection_count=16,
            )
        ],
    )

    detector = YoloDetector(
        model_config,
        runtime=runtime,
        runtime_policy=_runtime_policy(
            system="darwin",
            machine="x86_64",
            cpu_vendor=CpuVendor.INTEL,
            profile=ExecutionProfile.MACOS_X86_64_INTEL,
            provider=ExecutionProvider.CPU,
            available_providers=(ExecutionProvider.CPU.value,),
        ),
    )

    detections = detector.detect(vehicle_frame, allowed_classes={"car", "person"})

    assert [detection.class_name for detection in detections] == ["car", "person"]
    assert detections[0].confidence == pytest.approx(0.94)
    assert detections[0].bbox == pytest.approx((4.5, 7.2, 14.5, 11.1), rel=1e-6)
    assert detections[1].confidence == pytest.approx(0.93)
    assert detections[1].bbox == pytest.approx((16.0, 5.7, 32.0, 11.7), rel=1e-6)


def test_detector_uses_resolved_runtime_policy_provider_and_thread_overrides(vehicle_frame) -> None:
    model_config = DetectionModelConfig(
        name="detector",
        path="tests/fixtures/fake-detector.onnx",
        classes=["car", "truck"],
        input_shape={"width": 640, "height": 640},
    )
    runtime = _FakeRuntime(
        providers=[ExecutionProvider.CPU.value, ExecutionProvider.COREML.value],
        outputs=[
            np.array(
                [[18.0, 48.0, 58.0, 74.0, 0.94, 0.0]],
                dtype=np.float32,
            )
        ],
    )
    runtime_policy = _runtime_policy(
        system="darwin",
        machine="arm64",
        cpu_vendor=CpuVendor.APPLE,
        profile=ExecutionProfile.MACOS_APPLE_SILICON,
        provider=ExecutionProvider.CPU,
        available_providers=(
            ExecutionProvider.CPU.value,
            ExecutionProvider.COREML.value,
        ),
        inter_op_threads=2,
        intra_op_threads=4,
        provider_overridden=True,
    )

    detector = YoloDetector(model_config, runtime=runtime, runtime_policy=runtime_policy)

    detections = detector.detect(vehicle_frame, allowed_classes={"car"})

    assert detector.selected_provider == ExecutionProvider.CPU.value
    assert runtime.last_providers == [ExecutionProvider.CPU.value]
    assert runtime.last_sess_options is not None
    assert runtime.last_sess_options.inter_op_num_threads == 2
    assert runtime.last_sess_options.intra_op_num_threads == 4
    assert [detection.class_name for detection in detections] == ["car"]


def _channel_first_output(
    rows: list[list[float]],
    *,
    feature_count: int,
    detection_count: int,
) -> np.ndarray:
    output = np.zeros((1, feature_count, detection_count), dtype=np.float32)
    for detection_index, values in enumerate(rows):
        for feature_index, value in enumerate(values):
            output[0, feature_index, detection_index] = value
    return output
