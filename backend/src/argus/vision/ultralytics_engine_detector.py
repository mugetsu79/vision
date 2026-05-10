from __future__ import annotations

from collections.abc import Callable, Iterable
from importlib import import_module
from typing import Any

import numpy as np
from numpy.typing import NDArray

from argus.inference.engine import RuntimeArtifactSettings
from argus.models.enums import DetectorCapability
from argus.vision.types import Detection


class UltralyticsEngineDetector:
    capability: DetectorCapability

    def __init__(
        self,
        artifact: RuntimeArtifactSettings,
        *,
        model_loader: Callable[[str], Any] | None = None,
    ) -> None:
        self.artifact = artifact
        self.capability = artifact.capability
        self._model = (model_loader or _load_ultralytics_model)(artifact.path)

    def detect(
        self,
        frame: NDArray[np.uint8],
        allowed_classes: Iterable[str] | None = None,
    ) -> list[Detection]:
        results = self._model.predict(frame, verbose=False)
        detections = _detections_from_ultralytics_results(
            results,
            artifact_classes=self.artifact.classes,
        )
        if allowed_classes is None:
            return detections
        allowed = set(allowed_classes)
        return [detection for detection in detections if detection.class_name in allowed]

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None:
        return None

    def describe_runtime_state(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "runtime_backend": self.artifact.runtime_backend,
            "artifact_id": str(self.artifact.id),
            "artifact_path": self.artifact.path,
            "target_profile": self.artifact.target_profile,
        }


def _load_ultralytics_model(path: str) -> Any:
    ultralytics: Any = import_module("ultralytics")
    return ultralytics.YOLO(path)


def _detections_from_ultralytics_results(
    results: Iterable[Any],
    *,
    artifact_classes: list[str],
) -> list[Detection]:
    detections: list[Detection] = []
    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        names = getattr(result, "names", {}) or {}
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
            detections.append(
                Detection(
                    class_name=_class_name(
                        class_id,
                        names=names,
                        artifact_classes=artifact_classes,
                    ),
                    class_id=class_id,
                    confidence=round(float(confidence), 6),
                    bbox=(
                        float(bbox[0]),
                        float(bbox[1]),
                        float(bbox[2]),
                        float(bbox[3]),
                    ),
                )
            )
    return detections


def _class_name(
    class_id: int,
    *,
    names: dict[int, str],
    artifact_classes: list[str],
) -> str:
    name = names.get(class_id)
    if name is not None:
        return str(name)
    if class_id < len(artifact_classes):
        return str(artifact_classes[class_id])
    return str(class_id)


def _to_numpy(value: Any, *, dtype: type[np.floating[Any]]) -> NDArray[np.float32]:
    cpu = getattr(value, "cpu", None)
    if callable(cpu):
        value = cpu()
    numpy = getattr(value, "numpy", None)
    if callable(numpy):
        value = numpy()
    return np.asarray(value, dtype=dtype)
