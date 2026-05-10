from __future__ import annotations

from typing import Any

from argus.models.enums import DetectorCapability
from argus.vision.detector import DetectionModelConfig, RuntimeDetector, YoloDetector
from argus.vision.runtime import RuntimeExecutionPolicy


def build_detector(
    *,
    model: Any,
    runtime: Any,
    runtime_policy: RuntimeExecutionPolicy,
    runtime_selection: Any | None = None,
    yolo_detector_cls: type[YoloDetector] = YoloDetector,
) -> RuntimeDetector:
    if (
        runtime_selection is not None
        and getattr(runtime_selection, "selected_backend", None) == "tensorrt_engine"
        and getattr(runtime_selection, "artifact", None) is not None
    ):
        from argus.vision.ultralytics_engine_detector import UltralyticsEngineDetector

        return UltralyticsEngineDetector(runtime_selection.artifact)

    capability = _coerce_detector_capability(getattr(model, "capability", None))
    if capability is DetectorCapability.FIXED_VOCAB:
        return yolo_detector_cls(
            DetectionModelConfig(
                name=str(model.name),
                path=str(model.path),
                classes=list(model.classes),
                input_shape=dict(model.input_shape),
                confidence_threshold=float(getattr(model, "confidence_threshold", 0.25)),
                iou_threshold=float(getattr(model, "iou_threshold", 0.45)),
            ),
            runtime=runtime,
            runtime_policy=runtime_policy,
        )

    if capability is DetectorCapability.OPEN_VOCAB:
        from argus.vision.open_vocab_detector import OpenVocabDetector, OpenVocabModelConfig

        runtime_vocabulary = getattr(model, "runtime_vocabulary", None)
        default_vocabulary = (
            list(runtime_vocabulary.terms)
            if runtime_vocabulary is not None
            else list(model.classes)
        )
        return OpenVocabDetector(
            OpenVocabModelConfig(
                name=str(model.name),
                path=str(model.path),
                input_shape=dict(model.input_shape),
                capability_config=dict(getattr(model, "capability_config", {}) or {}),
                default_vocabulary=default_vocabulary,
                confidence_threshold=float(getattr(model, "confidence_threshold", 0.25)),
                iou_threshold=float(getattr(model, "iou_threshold", 0.45)),
            ),
            runtime=runtime,
            runtime_policy=runtime_policy,
        )

    raise ValueError(f"Unsupported detector capability: {capability}")


def _coerce_detector_capability(value: object) -> DetectorCapability:
    if value is None:
        return DetectorCapability.FIXED_VOCAB
    if isinstance(value, DetectorCapability):
        return value
    return DetectorCapability(str(value))
