from __future__ import annotations

from uuid import uuid4

from argus.api.contracts import RuntimeArtifactCreate, RuntimeArtifactResponse
from argus.models.enums import (
    DetectorCapability,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
)


def test_runtime_artifact_create_supports_fixed_vocab_model_scope() -> None:
    payload = RuntimeArtifactCreate(
        scope=RuntimeArtifactScope.MODEL,
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.FIXED_VOCAB,
        runtime_backend="tensorrt_engine",
        path="/models/yolo26n.jetson.fp16.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "car"],
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=1234,
    )

    assert payload.scope is RuntimeArtifactScope.MODEL
    assert payload.camera_id is None
    assert payload.validation_status is RuntimeArtifactValidationStatus.UNVALIDATED


def test_runtime_artifact_create_requires_camera_for_scene_scope() -> None:
    try:
        RuntimeArtifactCreate(
            scope=RuntimeArtifactScope.SCENE,
            kind=RuntimeArtifactKind.ONNX_EXPORT,
            capability=DetectorCapability.OPEN_VOCAB,
            runtime_backend="onnxruntime",
            path="/models/camera-a/person-chair.onnx",
            target_profile="linux-aarch64-nvidia-jetson",
            precision=RuntimeArtifactPrecision.FP16,
            input_shape={"width": 640, "height": 640},
            classes=["person", "chair"],
            vocabulary_hash="c" * 64,
            source_model_sha256="a" * 64,
            sha256="b" * 64,
            size_bytes=1234,
        )
    except ValueError as exc:
        assert "camera_id is required for scene-scoped artifacts" in str(exc)
    else:
        raise AssertionError("scene-scoped artifact without camera_id should fail")


def test_runtime_artifact_response_round_trips_scene_vocab_hash() -> None:
    camera_id = uuid4()
    artifact = RuntimeArtifactResponse(
        id=uuid4(),
        model_id=uuid4(),
        camera_id=camera_id,
        scope=RuntimeArtifactScope.SCENE,
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.OPEN_VOCAB,
        runtime_backend="tensorrt_engine",
        path="/models/camera-a/open-vocab.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "chair"],
        vocabulary_hash="d" * 64,
        vocabulary_version=7,
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=1234,
        validation_status=RuntimeArtifactValidationStatus.VALID,
    )

    assert artifact.camera_id == camera_id
    assert artifact.vocabulary_hash == "d" * 64
    assert artifact.vocabulary_version == 7
