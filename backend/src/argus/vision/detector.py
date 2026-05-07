from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from logging import getLogger
from time import perf_counter
from typing import Any, Protocol

import cv2
import numpy as np
from numpy.typing import NDArray

from argus.models.enums import DetectorCapability
from argus.vision.runtime import (
    RuntimeExecutionPolicy,
    create_session_options,
    import_onnxruntime,
    resolve_execution_policy,
)
from argus.vision.types import Detection

LOGGER = getLogger(__name__)


@dataclass(slots=True)
class DetectionModelConfig:
    name: str
    path: str
    classes: list[str]
    input_shape: dict[str, int]
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45


class RuntimeDetector(Protocol):
    capability: DetectorCapability

    def detect(
        self,
        frame: NDArray[np.uint8],
        allowed_classes: Iterable[str] | None = None,
    ) -> list[Detection]: ...

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None: ...

    def describe_runtime_state(self) -> dict[str, object]: ...


class YoloDetector:
    capability = DetectorCapability.FIXED_VOCAB

    def __init__(
        self,
        model_config: DetectionModelConfig,
        runtime: Any | None = None,
        runtime_policy: RuntimeExecutionPolicy | None = None,
    ) -> None:
        self.model_config = model_config
        self.runtime = runtime or import_onnxruntime()
        self.runtime_policy = runtime_policy or resolve_execution_policy(self.runtime)
        session_options = create_session_options(self.runtime, policy=self.runtime_policy)
        self.session = self.runtime.InferenceSession(
            model_config.path,
            providers=[self.runtime_policy.provider],
            sess_options=session_options,
        )
        self.selected_provider = self.runtime_policy.provider
        self.input_name = self.session.get_inputs()[0].name
        self._last_stage_timings: dict[str, float] = {}
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
        allowed_class_ids = {
            index
            for index, class_name in enumerate(self.model_config.classes)
            if class_name in allowed
        }
        started_at = perf_counter()
        tensor = self._prepare_tensor(frame)
        prepared_at = perf_counter()
        outputs = self.session.run(None, {self.input_name: tensor})
        inferred_at = perf_counter()
        predictions = self._parse_predictions(
            outputs[0],
            frame.shape[1],
            frame.shape[0],
            allowed_class_ids=allowed_class_ids,
        )
        parsed_at = perf_counter()
        detections = _apply_nms(predictions, self.model_config.iou_threshold)
        completed_at = perf_counter()
        self._last_stage_timings = {
            "prepare": max(0.0, prepared_at - started_at),
            "session": max(0.0, inferred_at - prepared_at),
            "parse": max(0.0, parsed_at - inferred_at),
            "nms": max(0.0, completed_at - parsed_at),
        }
        return detections

    def last_stage_timings(self) -> dict[str, float]:
        return dict(self._last_stage_timings)

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None:
        return None

    def describe_runtime_state(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "classes": list(self.model_config.classes),
            "selected_provider": self.selected_provider,
        }

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
        *,
        allowed_class_ids: set[int],
    ) -> list[Detection]:
        squeezed = np.asarray(predictions, dtype=np.float32)
        transposed_channel_first = False
        if squeezed.ndim == 3:
            squeezed = np.squeeze(squeezed, axis=0)

        if squeezed.ndim != 2:
            raise ValueError("Unexpected detector output shape.")

        if _looks_like_channel_first_layout(
            squeezed,
            configured_class_count=len(self.model_config.classes),
        ):
            squeezed = squeezed.T
            transposed_channel_first = True

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
                if int(row[5]) in allowed_class_ids
                and float(row[4]) >= self.model_config.confidence_threshold
            ]

        if transposed_channel_first:
            return self._parse_dense_predictions(
                squeezed,
                frame_width=frame_width,
                frame_height=frame_height,
                has_objectness=False,
                allowed_class_ids=allowed_class_ids,
            )

        if squeezed.shape[1] == 4 + len(self.model_config.classes):
            return self._parse_dense_predictions(
                squeezed,
                frame_width=frame_width,
                frame_height=frame_height,
                has_objectness=False,
                allowed_class_ids=allowed_class_ids,
            )

        if squeezed.shape[1] >= 5 + len(self.model_config.classes):
            return self._parse_dense_predictions(
                squeezed,
                frame_width=frame_width,
                frame_height=frame_height,
                has_objectness=True,
                allowed_class_ids=allowed_class_ids,
            )

        if squeezed.shape[1] < 6:
            raise ValueError("Unexpected detector output columns.")
        raise ValueError("Unexpected detector output columns.")

    def _parse_dense_predictions(
        self,
        predictions: NDArray[np.float32],
        *,
        frame_width: int,
        frame_height: int,
        has_objectness: bool,
        allowed_class_ids: set[int],
    ) -> list[Detection]:
        detections: list[Detection] = []
        class_offset = 5 if has_objectness else 4
        class_scores = predictions[:, class_offset:]
        if class_scores.size == 0 or not allowed_class_ids:
            return detections
        allowed_indices = np.fromiter(
            sorted(allowed_class_ids),
            dtype=np.int64,
            count=len(allowed_class_ids),
        )
        allowed_indices = allowed_indices[allowed_indices < class_scores.shape[1]]
        if allowed_indices.size == 0:
            return detections
        allowed_mask = np.zeros(class_scores.shape[1], dtype=np.bool_)
        allowed_mask[allowed_indices] = True
        class_ids = np.argmax(class_scores, axis=1)
        class_confidences = class_scores[np.arange(len(class_ids)), class_ids]
        if has_objectness:
            confidences = predictions[:, 4] * class_confidences
        else:
            confidences = class_confidences
        keep_indices = np.flatnonzero(
            (confidences >= self.model_config.confidence_threshold)
            & allowed_mask[class_ids]
        )
        for row, class_id, confidence in zip(
            predictions[keep_indices],
            class_ids[keep_indices].tolist(),
            confidences[keep_indices].tolist(),
            strict=False,
        ):
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
        if (
            input_width <= 0.0
            or input_height <= 0.0
            or frame_width <= 0
            or frame_height <= 0
        ):
            LOGGER.warning(
                "Invalid input/frame dimensions, returning bbox unchanged: "
                "input=%sx%s frame=%sx%s",
                input_width,
                input_height,
                frame_width,
                frame_height,
            )
            x1, y1, x2, y2 = bbox
            return (float(x1), float(y1), float(x2), float(y2))
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


def _looks_like_channel_first_layout(
    predictions: NDArray[np.float32],
    *,
    configured_class_count: int,
) -> bool:
    rows, columns = predictions.shape
    if rows <= 4 or columns <= rows:
        return False
    return (rows - 4 >= configured_class_count) or (rows - 5 >= configured_class_count)


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
