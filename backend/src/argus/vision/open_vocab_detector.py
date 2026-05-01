from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

from argus.models.enums import DetectorCapability
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
        model_loader: Callable[[str, str], Any] | None = None,
    ) -> None:
        self.model_config = model_config
        self.runtime = runtime
        self.runtime_policy = runtime_policy
        self._runtime_backend = str(
            model_config.capability_config.get("runtime_backend") or "ultralytics_yoloe"
        )
        self._runtime_vocabulary = _normalize_vocabulary(model_config.default_vocabulary)
        self._model = (model_loader or _load_ultralytics_model)(
            model_config.path,
            self._runtime_backend,
        )
        self._apply_vocabulary()

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None:
        self._runtime_vocabulary = _normalize_vocabulary(vocabulary)
        self._apply_vocabulary()

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
        if visible_classes != self._runtime_vocabulary:
            self._runtime_vocabulary = visible_classes
            self._apply_vocabulary()
        results = self._model.predict(
            frame,
            verbose=False,
            conf=self.model_config.confidence_threshold,
            iou=self.model_config.iou_threshold,
        )
        return _detections_from_ultralytics_results(results)

    def describe_runtime_state(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "runtime_backend": self._runtime_backend,
            "runtime_vocabulary": list(self._runtime_vocabulary),
            "selected_provider": self.runtime_policy.provider,
        }

    def _apply_vocabulary(self) -> None:
        set_classes = getattr(self._model, "set_classes", None)
        if not callable(set_classes):
            raise RuntimeError(
                f"Open-vocab backend {self._runtime_backend!r} does not support set_classes."
            )
        set_classes(list(self._runtime_vocabulary))


def _load_ultralytics_model(path: str, backend: str) -> Any:
    if backend == "ultralytics_yolo_world":
        from ultralytics import YOLOWorld

        return YOLOWorld(path)
    if backend == "ultralytics_yoloe":
        from ultralytics import YOLOE

        return YOLOE(path)
    raise RuntimeError(f"Unsupported open-vocab runtime backend: {backend}")


def _detections_from_ultralytics_results(results: Iterable[Any]) -> list[Detection]:
    detections: list[Detection] = []
    for result in results:
        names = getattr(result, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        xyxy = _to_numpy(getattr(boxes, "xyxy", []), dtype=np.float32)
        confidences = _to_numpy(getattr(boxes, "conf", []), dtype=np.float32)
        class_ids = _to_numpy(getattr(boxes, "cls", []), dtype=np.float32)
        for bbox, confidence, class_id_value in zip(
            xyxy,
            confidences.tolist(),
            class_ids.tolist(),
            strict=False,
        ):
            if len(bbox) < 4:
                continue
            class_id = int(class_id_value)
            class_name = str(names.get(class_id, class_id))
            detections.append(
                Detection(
                    class_name=class_name,
                    class_id=class_id,
                    confidence=round(float(confidence), 6),
                    bbox=tuple(float(value) for value in bbox[:4]),
                )
            )
    return detections


def _to_numpy(value: Any, *, dtype: type[np.floating[Any]]) -> NDArray[np.float32]:
    cpu = getattr(value, "cpu", None)
    if callable(cpu):
        value = cpu()
    numpy = getattr(value, "numpy", None)
    if callable(numpy):
        value = numpy()
    return np.asarray(value, dtype=dtype)


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
