from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from logging import getLogger
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from traffic_monitor.vision.runtime import import_onnxruntime, select_execution_provider
from traffic_monitor.vision.types import Detection

LOGGER = getLogger(__name__)


@dataclass(slots=True)
class DetectionModelConfig:
    name: str
    path: str
    classes: list[str]
    input_shape: dict[str, int]
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45


class YoloDetector:
    def __init__(self, model_config: DetectionModelConfig, runtime: Any | None = None) -> None:
        self.model_config = model_config
        self.runtime = runtime or import_onnxruntime()
        provider = select_execution_provider(self.runtime)
        self.session = self.runtime.InferenceSession(model_config.path, providers=[provider])
        self.selected_provider = provider
        self.input_name = self.session.get_inputs()[0].name
        LOGGER.info(
            "Loaded detection model %s with provider %s",
            self.model_config.name,
            self.selected_provider,
        )

    def detect(
        self,
        frame: NDArray[np.uint8],
        allowed_classes: Iterable[str] | None = None,
    ) -> list[Detection]:
        allowed = set(allowed_classes or self.model_config.classes)
        tensor = self._prepare_tensor(frame)
        outputs = self.session.run(None, {self.input_name: tensor})
        predictions = self._parse_predictions(outputs[0], frame.shape[1], frame.shape[0])
        filtered = [
            prediction
            for prediction in predictions
            if prediction.confidence >= self.model_config.confidence_threshold
            and prediction.class_name in allowed
        ]
        return _apply_nms(filtered, self.model_config.iou_threshold)

    def _prepare_tensor(self, frame: NDArray[np.uint8]) -> NDArray[np.float32]:
        target_width = int(self.model_config.input_shape["width"])
        target_height = int(self.model_config.input_shape["height"])
        resized = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        return np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]

    def _parse_predictions(
        self,
        predictions: NDArray[np.float32],
        frame_width: int,
        frame_height: int,
    ) -> list[Detection]:
        squeezed = np.asarray(predictions, dtype=np.float32)
        if squeezed.ndim == 3:
            squeezed = np.squeeze(squeezed, axis=0)

        if squeezed.ndim != 2:
            raise ValueError("Unexpected detector output shape.")

        if squeezed.shape[1] >= 6 and np.all(squeezed[:, 5] == np.floor(squeezed[:, 5])):
            return [
                Detection(
                    class_name=self.model_config.classes[int(row[5])],
                    class_id=int(row[5]),
                    confidence=float(row[4]),
                    bbox=self._rescale_bbox(
                        (
                            float(row[0]),
                            float(row[1]),
                            float(row[2]),
                            float(row[3]),
                        ),
                        frame_width,
                        frame_height,
                    ),
                )
                for row in squeezed
                if int(row[5]) < len(self.model_config.classes)
            ]

        if squeezed.shape[1] < 6:
            raise ValueError("Unexpected detector output columns.")

        detections: list[Detection] = []
        class_scores = squeezed[:, 5:]
        class_ids = np.argmax(class_scores, axis=1)
        confidences = squeezed[:, 4] * class_scores[np.arange(len(class_ids)), class_ids]
        for row, class_id, confidence in zip(
            squeezed,
            class_ids.tolist(),
            confidences.tolist(),
            strict=False,
        ):
            if class_id >= len(self.model_config.classes):
                continue
            x_center, y_center, width, height = [float(value) for value in row[:4]]
            bbox = (
                x_center - width / 2.0,
                y_center - height / 2.0,
                x_center + width / 2.0,
                y_center + height / 2.0,
            )
            detections.append(
                Detection(
                    class_name=self.model_config.classes[class_id],
                    class_id=class_id,
                    confidence=float(confidence),
                    bbox=self._rescale_bbox(bbox, frame_width, frame_height),
                )
            )
        return detections

    def _rescale_bbox(
        self,
        bbox: tuple[float, float, float, float],
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float, float, float]:
        input_width = float(self.model_config.input_shape["width"])
        input_height = float(self.model_config.input_shape["height"])
        max_coordinate = max(bbox)
        if max_coordinate <= max(frame_width, frame_height):
            scale_x = 1.0
            scale_y = 1.0
        else:
            scale_x = frame_width / input_width
            scale_y = frame_height / input_height

        x1, y1, x2, y2 = bbox
        return (
            float(np.clip(x1 * scale_x, 0.0, frame_width)),
            float(np.clip(y1 * scale_y, 0.0, frame_height)),
            float(np.clip(x2 * scale_x, 0.0, frame_width)),
            float(np.clip(y2 * scale_y, 0.0, frame_height)),
        )


def _apply_nms(detections: list[Detection], iou_threshold: float) -> list[Detection]:
    kept: list[Detection] = []
    for class_name in sorted({detection.class_name for detection in detections}):
        class_detections = sorted(
            (detection for detection in detections if detection.class_name == class_name),
            key=lambda detection: detection.confidence,
            reverse=True,
        )
        while class_detections:
            current = class_detections.pop(0)
            kept.append(current)
            class_detections = [
                candidate
                for candidate in class_detections
                if _bbox_iou(current.bbox, candidate.bbox) < iou_threshold
            ]
    return kept


def _bbox_iou(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    left_x1, left_y1, left_x2, left_y2 = left
    right_x1, right_y1, right_x2, right_y2 = right

    intersection_x1 = max(left_x1, right_x1)
    intersection_y1 = max(left_y1, right_y1)
    intersection_x2 = min(left_x2, right_x2)
    intersection_y2 = min(left_y2, right_y2)

    intersection_width = max(0.0, intersection_x2 - intersection_x1)
    intersection_height = max(0.0, intersection_y2 - intersection_y1)
    intersection_area = intersection_width * intersection_height

    left_area = max(0.0, left_x2 - left_x1) * max(0.0, left_y2 - left_y1)
    right_area = max(0.0, right_x2 - right_x1) * max(0.0, right_y2 - right_y1)
    union_area = left_area + right_area - intersection_area
    if union_area <= 0.0:
        return 0.0
    return intersection_area / union_area
