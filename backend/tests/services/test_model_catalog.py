from __future__ import annotations

from uuid import uuid4

from argus.models.enums import DetectorCapability, ModelFormat, ModelTask
from argus.models.tables import Model
from argus.services.model_catalog import list_model_catalog_entries, resolve_catalog_status


def test_catalog_contains_recommended_fixed_vocab_models() -> None:
    entries = list_model_catalog_entries()
    ids = {entry.id for entry in entries}

    assert "yolo26n-coco-onnx" in ids
    assert "yolo26s-coco-onnx" in ids
    assert "yolo11n-coco-onnx" in ids
    assert "yolo11s-coco-onnx" in ids
    assert "yolo12n-coco-onnx" in ids


def test_catalog_marks_open_vocab_presets_experimental() -> None:
    entries = {entry.id: entry for entry in list_model_catalog_entries()}

    assert entries["yoloe-26n-open-vocab-pt"].capability is DetectorCapability.OPEN_VOCAB
    assert entries["yoloe-26n-open-vocab-pt"].format is ModelFormat.PT
    assert entries["yoloe-26n-open-vocab-pt"].capability_config.readiness == "experimental"
    assert entries["yolov8s-worldv2-open-vocab-pt"].capability_config.runtime_backend == (
        "ultralytics_yolo_world"
    )


def test_catalog_status_matches_registered_model_by_catalog_id(tmp_path) -> None:
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"fake")
    registered_model = Model(
        id=uuid4(),
        name="YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path=str(model_path),
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config={
            "catalog_id": "yolo26n-coco-onnx",
            "runtime_backend": "onnxruntime",
            "readiness": "ready",
        },
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=4,
        license="AGPL-3.0",
    )

    status = resolve_catalog_status([registered_model])
    yolo26n = next(entry for entry in status if entry.id == "yolo26n-coco-onnx")

    assert yolo26n.registered_model_id == registered_model.id
    assert yolo26n.artifact_exists is True
    assert yolo26n.registration_state == "registered"
