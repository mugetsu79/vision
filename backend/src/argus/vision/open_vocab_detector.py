from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from argus.models.enums import DetectorCapability
from argus.vision.detector import DetectionModelConfig, YoloDetector
from argus.vision.runtime import RuntimeExecutionPolicy
from argus.vision.types import Detection


@dataclass(slots=True)
class OpenVocabModelConfig:
    name: str
    path: str
    input_shape: dict[str, int]
    capability_config: dict[str, object]
    default_vocabulary: list[str]
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45


class OpenVocabDetector:
    capability = DetectorCapability.OPEN_VOCAB

    def __init__(
        self,
        model_config: OpenVocabModelConfig,
        runtime: Any,
        runtime_policy: RuntimeExecutionPolicy,
    ) -> None:
        self.model_config = model_config
        self.runtime = runtime
        self.runtime_policy = runtime_policy
        self._runtime_vocabulary = _normalize_vocabulary(model_config.default_vocabulary)
        self._detector = YoloDetector(
            DetectionModelConfig(
                name=model_config.name,
                path=model_config.path,
                classes=list(self._runtime_vocabulary),
                input_shape=dict(model_config.input_shape),
                confidence_threshold=model_config.confidence_threshold,
                iou_threshold=model_config.iou_threshold,
            ),
            runtime=runtime,
            runtime_policy=runtime_policy,
        )

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None:
        self._runtime_vocabulary = _normalize_vocabulary(vocabulary)
        self._detector.model_config = replace(
            self._detector.model_config,
            classes=list(self._runtime_vocabulary),
        )

    def detect(
        self,
        frame: NDArray[np.uint8],
        allowed_classes: Iterable[str] | None = None,
    ) -> list[Detection]:
        visible_classes = (
            _normalize_vocabulary(allowed_classes)
            if allowed_classes is not None
            else list(self._runtime_vocabulary)
        )
        if not visible_classes:
            return []
        return self._detector.detect(frame, visible_classes)

    def describe_runtime_state(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "runtime_vocabulary": list(self._runtime_vocabulary),
            "selected_provider": self._detector.selected_provider,
        }


def _normalize_vocabulary(vocabulary: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for term in vocabulary:
        value = str(term).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized
