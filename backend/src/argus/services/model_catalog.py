from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from argus.api.contracts import (
    ModelCapabilityConfig,
    ModelCatalogEntryResponse,
    ModelCatalogRegistrationState,
)
from argus.models.enums import DetectorCapability, ModelFormat, ModelTask
from argus.models.tables import Model

type ModelFamily = Literal["yolo11", "yolo12", "yolo26", "yolo_world", "yoloe"]
type OpenVocabBackend = Literal["ultralytics_yolo_world", "ultralytics_yoloe"]


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    id: str
    name: str
    version: str
    task: ModelTask
    path_hint: str
    format: ModelFormat
    capability: DetectorCapability
    capability_config: ModelCapabilityConfig
    classes: tuple[str, ...]
    input_shape: dict[str, int]
    license: str
    note: str


def list_model_catalog_entries() -> list[ModelCatalogEntry]:
    return [
        _fixed(
            "yolo26n-coco-onnx",
            "YOLO26n COCO",
            "2026.1",
            "yolo26",
            "models/yolo26n.onnx",
            "Default fast detector.",
        ),
        _fixed(
            "yolo26s-coco-onnx",
            "YOLO26s COCO",
            "2026.1",
            "yolo26",
            "models/yolo26s.onnx",
            "Balanced accuracy and speed.",
        ),
        _fixed(
            "yolo11n-coco-onnx",
            "YOLO11n COCO",
            "2024.9",
            "yolo11",
            "models/yolo11n.onnx",
            "Stable fast fallback.",
        ),
        _fixed(
            "yolo11s-coco-onnx",
            "YOLO11s COCO",
            "2024.9",
            "yolo11",
            "models/yolo11s.onnx",
            "Stable balanced fallback.",
        ),
        _fixed(
            "yolo12n-coco-onnx",
            "YOLO12n COCO",
            "2025.2",
            "yolo12",
            "models/yolo12n.onnx",
            "Current lab compatibility option.",
        ),
        _open_vocab(
            "yoloe-26n-open-vocab-pt",
            "YOLOE-26N Open Vocab",
            "2026.1",
            "yoloe",
            "models/yoloe-26n-seg.pt",
            "ultralytics_yoloe",
            "Preferred experimental open-vocab lab path.",
        ),
        _open_vocab(
            "yoloe-26s-open-vocab-pt",
            "YOLOE-26S Open Vocab",
            "2026.1",
            "yoloe",
            "models/yoloe-26s-seg.pt",
            "ultralytics_yoloe",
            "Higher quality experimental open-vocab path.",
        ),
        _open_vocab(
            "yolov8s-worldv2-open-vocab-pt",
            "YOLOv8s-Worldv2 Open Vocab",
            "2024.1",
            "yolo_world",
            "models/yolov8s-worldv2.pt",
            "ultralytics_yolo_world",
            "Smaller experimental open-vocab fallback.",
        ),
        _planned_engine(
            "yolo26n-coco-tensorrt-engine",
            "YOLO26n COCO TensorRT Engine",
            "2026.1",
            "models/yolo26n.engine",
            "Planned acceleration path; raw engine detector support is not implemented.",
        ),
        _planned_engine(
            "yolo26s-coco-tensorrt-engine",
            "YOLO26s COCO TensorRT Engine",
            "2026.1",
            "models/yolo26s.engine",
            "Planned acceleration path; raw engine detector support is not implemented.",
        ),
    ]


def resolve_catalog_status(models: list[Model]) -> list[ModelCatalogEntryResponse]:
    registered_by_catalog_id = {
        str((model.capability_config or {}).get("catalog_id")): model
        for model in models
        if (model.capability_config or {}).get("catalog_id")
    }
    responses: list[ModelCatalogEntryResponse] = []
    for entry in list_model_catalog_entries():
        registered = registered_by_catalog_id.get(entry.id)
        artifact_path = Path(registered.path if registered is not None else entry.path_hint)
        readiness = entry.capability_config.readiness or "ready"
        if readiness == "planned":
            state = ModelCatalogRegistrationState.PLANNED
        elif registered is None:
            state = ModelCatalogRegistrationState.UNREGISTERED
        elif artifact_path.exists():
            state = ModelCatalogRegistrationState.REGISTERED
        else:
            state = ModelCatalogRegistrationState.MISSING_ARTIFACT
        responses.append(
            ModelCatalogEntryResponse(
                id=entry.id,
                name=entry.name,
                version=entry.version,
                task=entry.task,
                path_hint=entry.path_hint,
                format=entry.format,
                capability=entry.capability,
                capability_config=entry.capability_config,
                classes=list(entry.classes),
                input_shape=entry.input_shape,
                license=entry.license,
                registration_state=state,
                registered_model_id=UUID(str(registered.id)) if registered is not None else None,
                artifact_exists=artifact_path.exists(),
                note=entry.note,
            )
        )
    return responses


def _fixed(
    id: str,
    name: str,
    version: str,
    family: ModelFamily,
    path_hint: str,
    note: str,
) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        id=id,
        name=name,
        version=version,
        task=ModelTask.DETECT,
        path_hint=path_hint,
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config=ModelCapabilityConfig(
            model_family=family,
            runtime_backend="onnxruntime",
            readiness="ready",
            execution_profiles=[
                "linux-x86_64-nvidia",
                "linux-aarch64-nvidia-jetson",
                "linux-x86_64-intel",
                "macos-x86_64-intel",
                "macos-arm64-apple-silicon",
            ],
        ),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note=note,
    )


def _open_vocab(
    id: str,
    name: str,
    version: str,
    family: Literal["yolo_world", "yoloe"],
    path_hint: str,
    backend: OpenVocabBackend,
    note: str,
) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        id=id,
        name=name,
        version=version,
        task=ModelTask.DETECT,
        path_hint=path_hint,
        format=ModelFormat.PT,
        capability=DetectorCapability.OPEN_VOCAB,
        capability_config=ModelCapabilityConfig(
            supports_runtime_vocabulary_updates=True,
            max_runtime_terms=32,
            prompt_format="labels",
            model_family=family,
            runtime_backend=backend,
            readiness="experimental",
            requires_gpu=True,
            supports_masks=family == "yoloe",
            execution_profiles=["linux-x86_64-nvidia", "linux-aarch64-nvidia-jetson"],
        ),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note=note,
    )


def _planned_engine(
    id: str,
    name: str,
    version: str,
    path_hint: str,
    note: str,
) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        id=id,
        name=name,
        version=version,
        task=ModelTask.DETECT,
        path_hint=path_hint,
        format=ModelFormat.ENGINE,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config=ModelCapabilityConfig(
            model_family="yolo26",
            runtime_backend="tensorrt_engine",
            readiness="planned",
            execution_profiles=["linux-x86_64-nvidia", "linux-aarch64-nvidia-jetson"],
        ),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note=note,
    )
