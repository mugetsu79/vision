from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from argus.vision.runtime import import_onnxruntime, select_execution_provider
from argus.vision.types import Detection


@dataclass(slots=True)
class AttributeModelConfig:
    name: str
    path: str
    classes: list[str]
    input_shape: dict[str, int]
    target_classes: set[str] = field(default_factory=set)
    threshold: float = 0.5
    batch_size: int = 8


class AttributeClassifier:
    def __init__(self, model_config: AttributeModelConfig, runtime: Any | None = None) -> None:
        self.model_config = model_config
        self.runtime = runtime or import_onnxruntime()
        provider = select_execution_provider(self.runtime)
        self.session = self.runtime.InferenceSession(model_config.path, providers=[provider])
        self.selected_provider = provider
        self.input_name = self.session.get_inputs()[0].name

    def classify(
        self,
        frame: NDArray[np.uint8],
        detections: list[Detection],
    ) -> list[dict[str, Any]]:
        relevant_indices = [
            index
            for index, detection in enumerate(detections)
            if detection.class_name in self.model_config.target_classes
        ]
        if not relevant_indices:
            return [{} for _ in detections]

        crops = [self._extract_crop(frame, detections[index]) for index in relevant_indices]
        batch = np.stack(crops, axis=0)
        outputs = self.session.run(None, {self.input_name: batch})[0]
        probabilities = _normalize_scores(np.asarray(outputs, dtype=np.float32))

        attributes: list[dict[str, Any]] = [{} for _ in detections]
        for output_index, detection_index in enumerate(relevant_indices):
            attributes[detection_index] = {
                class_name: bool(
                    probabilities[output_index, class_index] >= self.model_config.threshold
                )
                for class_index, class_name in enumerate(self.model_config.classes)
            }
        return attributes

    def _extract_crop(self, frame: NDArray[np.uint8], detection: Detection) -> NDArray[np.float32]:
        x1, y1, x2, y2 = detection.bbox
        x1_int = int(np.clip(np.floor(x1), 0, frame.shape[1] - 1))
        y1_int = int(np.clip(np.floor(y1), 0, frame.shape[0] - 1))
        x2_int = int(np.clip(np.ceil(x2), x1_int + 1, frame.shape[1]))
        y2_int = int(np.clip(np.ceil(y2), y1_int + 1, frame.shape[0]))
        crop = frame[y1_int:y2_int, x1_int:x2_int]
        target_width = int(self.model_config.input_shape["width"])
        target_height = int(self.model_config.input_shape["height"])
        resized = cv2.resize(crop, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        return np.transpose(normalized, (2, 0, 1))


def _normalize_scores(scores: NDArray[np.float32]) -> NDArray[np.float32]:
    if scores.ndim == 1:
        scores = scores[np.newaxis, :]
    if scores.min() < 0.0 or scores.max() > 1.0:
        return 1.0 / (1.0 + np.exp(-scores))
    return scores
