from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import (
    RuntimeArtifactCreate,
    RuntimeArtifactResponse,
    RuntimeArtifactUpdate,
)
from argus.models.enums import (
    DetectorCapability,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
    TrackerType,
)
from argus.models.tables import Camera, Model, ModelRuntimeArtifact
from argus.services.runtime_artifacts import (
    RuntimeArtifactService,
    artifact_matches_camera_vocabulary,
)
from argus.vision.vocabulary import hash_vocabulary


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


def test_runtime_artifact_create_requires_vocabulary_hash_for_open_vocab_scene() -> None:
    camera_id = uuid4()

    try:
        RuntimeArtifactCreate(
            camera_id=camera_id,
            scope=RuntimeArtifactScope.SCENE,
            kind=RuntimeArtifactKind.ONNX_EXPORT,
            capability=DetectorCapability.OPEN_VOCAB,
            runtime_backend="onnxruntime",
            path="/models/camera-a/person-chair.onnx",
            target_profile="linux-aarch64-nvidia-jetson",
            precision=RuntimeArtifactPrecision.FP16,
            input_shape={"width": 640, "height": 640},
            classes=["person", "chair"],
            source_model_sha256="a" * 64,
            sha256="b" * 64,
            size_bytes=1234,
        )
    except ValueError as exc:
        assert "vocabulary_hash is required for open-vocab artifacts" in str(exc)
    else:
        raise AssertionError("open-vocab artifact without vocabulary_hash should fail")


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


class _Result:
    def __init__(self, values: Iterable[object]) -> None:
        self.values = list(values)

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[object]:
        return self.values


class _FakeSession:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def add(self, artifact: ModelRuntimeArtifact) -> None:
        if artifact.id is None:
            artifact.id = uuid4()
        artifacts = self.state.setdefault("artifacts", [])
        assert isinstance(artifacts, list)
        artifacts.append(artifact)

    async def commit(self) -> None:
        artifacts = self.state.get("artifacts", [])
        assert isinstance(artifacts, list)
        self.state["artifact_timestamps_at_commit"] = [
            (
                getattr(artifact, "created_at", None),
                getattr(artifact, "updated_at", None),
            )
            for artifact in artifacts
        ]
        self.state["committed"] = True

    async def refresh(self, artifact: ModelRuntimeArtifact) -> None:
        artifact.created_at = artifact.created_at or datetime.now(tz=UTC)
        artifact.updated_at = artifact.updated_at or datetime.now(tz=UTC)

    async def get(self, model_cls, object_id):  # noqa: ANN001
        if model_cls is Model:
            model = self.state.get("model")
            return model if getattr(model, "id", None) == object_id else None
        if model_cls is Camera:
            camera = self.state.get("camera")
            return camera if getattr(camera, "id", None) == object_id else None
        if model_cls is ModelRuntimeArtifact:
            artifacts = self.state.get("artifacts", [])
            assert isinstance(artifacts, list)
            return next(
                (artifact for artifact in artifacts if getattr(artifact, "id", None) == object_id),
                None,
            )
        return None

    async def execute(self, statement):  # noqa: ANN001
        artifacts = self.state.get("artifacts", [])
        assert isinstance(artifacts, list)
        return _Result(artifacts)


class _FakeSessionFactory:
    def __init__(
        self,
        *,
        model: Model | None = None,
        camera: Camera | None = None,
        artifacts: list[ModelRuntimeArtifact] | None = None,
    ) -> None:
        self.state: dict[str, object] = {
            "model": model,
            "camera": camera,
            "artifacts": artifacts or [],
        }

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.state)


def _model(*, sha256: str = "a" * 64, capability: DetectorCapability | None = None) -> Model:
    return Model(
        id=uuid4(),
        name="YOLO26n",
        version="2026.1",
        task=ModelTask.DETECT,
        path="/models/yolo26n.onnx",
        format=ModelFormat.ONNX,
        capability=capability or DetectorCapability.FIXED_VOCAB,
        capability_config={},
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256=sha256,
        size_bytes=1234,
        license="AGPL-3.0",
    )


def _camera(*, model_id) -> Camera:  # noqa: ANN001
    return Camera(
        id=uuid4(),
        site_id=uuid4(),
        name="Dock",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["person"],
        runtime_vocabulary=[],
        runtime_vocabulary_source="default",
        runtime_vocabulary_version=0,
        runtime_vocabulary_updated_at=None,
        attribute_rules=[],
        zones=[],
        vision_profile={},
        detection_regions=[],
        homography=None,
        privacy={},
        browser_delivery={},
        source_capability=None,
        frame_skip=1,
        fps_cap=25,
    )


def _artifact(
    *,
    model_id,
    camera_id=None,
    scope: RuntimeArtifactScope = RuntimeArtifactScope.MODEL,
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB,
    source_model_sha256: str = "a" * 64,
    validation_status: RuntimeArtifactValidationStatus = RuntimeArtifactValidationStatus.VALID,
    vocabulary_hash: str | None = None,
    vocabulary_version: int | None = None,
) -> ModelRuntimeArtifact:
    return ModelRuntimeArtifact(
        id=uuid4(),
        model_id=model_id,
        camera_id=camera_id,
        scope=scope,
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=capability,
        runtime_backend="tensorrt_engine",
        path="/models/yolo26n.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "car"],
        vocabulary_hash=vocabulary_hash,
        vocabulary_version=vocabulary_version,
        source_model_sha256=source_model_sha256,
        sha256="b" * 64,
        size_bytes=4321,
        builder={},
        runtime_versions={},
        validation_status=validation_status,
        validation_error=None,
    )


def _payload(**overrides: object) -> RuntimeArtifactCreate:
    data = {
        "scope": RuntimeArtifactScope.MODEL,
        "kind": RuntimeArtifactKind.TENSORRT_ENGINE,
        "capability": DetectorCapability.FIXED_VOCAB,
        "runtime_backend": "tensorrt_engine",
        "path": "/models/yolo26n.engine",
        "target_profile": "linux-aarch64-nvidia-jetson",
        "precision": RuntimeArtifactPrecision.FP16,
        "input_shape": {"width": 640, "height": 640},
        "classes": ["person", "car"],
        "source_model_sha256": "a" * 64,
        "sha256": "b" * 64,
        "size_bytes": 4321,
    }
    data.update(overrides)
    return RuntimeArtifactCreate(**data)


@pytest.mark.asyncio
async def test_runtime_artifact_service_creates_artifact_for_existing_model() -> None:
    model = _model()
    session_factory = _FakeSessionFactory(model=model)
    service = RuntimeArtifactService(session_factory=session_factory)

    response = await service.create_for_model(model.id, _payload())

    assert response.model_id == model.id
    assert response.scope is RuntimeArtifactScope.MODEL
    assert session_factory.state["committed"] is True
    assert len(session_factory.state["artifacts"]) == 1


@pytest.mark.asyncio
async def test_runtime_artifact_service_sets_timestamps_before_insert() -> None:
    model = _model()
    session_factory = _FakeSessionFactory(model=model)
    service = RuntimeArtifactService(session_factory=session_factory)

    await service.create_for_model(model.id, _payload())

    timestamps = session_factory.state["artifact_timestamps_at_commit"]
    assert timestamps
    created_at, updated_at = timestamps[0]
    assert isinstance(created_at, datetime)
    assert isinstance(updated_at, datetime)


@pytest.mark.asyncio
async def test_runtime_artifact_service_lists_artifacts_by_model() -> None:
    model = _model()
    artifact = _artifact(model_id=model.id)
    service = RuntimeArtifactService(
        session_factory=_FakeSessionFactory(model=model, artifacts=[artifact])
    )

    response = await service.list_for_model(model.id)

    assert [item.id for item in response] == [artifact.id]


@pytest.mark.asyncio
async def test_runtime_artifact_service_rejects_scene_artifact_for_unrelated_camera() -> None:
    model = _model(capability=DetectorCapability.OPEN_VOCAB)
    camera = _camera(model_id=uuid4())
    service = RuntimeArtifactService(
        session_factory=_FakeSessionFactory(model=model, camera=camera)
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.create_for_model(
            model.id,
            _payload(
                scope=RuntimeArtifactScope.SCENE,
                camera_id=camera.id,
                capability=DetectorCapability.OPEN_VOCAB,
                kind=RuntimeArtifactKind.ONNX_EXPORT,
                runtime_backend="onnxruntime",
                vocabulary_hash="c" * 64,
            ),
        )

    assert exc_info.value.status_code == 422
    assert "camera does not use model" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_runtime_artifact_service_patches_validation_status() -> None:
    model = _model()
    artifact = _artifact(
        model_id=model.id,
        validation_status=RuntimeArtifactValidationStatus.UNVALIDATED,
    )
    service = RuntimeArtifactService(
        session_factory=_FakeSessionFactory(model=model, artifacts=[artifact])
    )

    response = await service.update_artifact(
        model.id,
        artifact.id,
        RuntimeArtifactUpdate(
            validation_status=RuntimeArtifactValidationStatus.VALID,
            validation_error=None,
        ),
    )

    assert response.validation_status is RuntimeArtifactValidationStatus.VALID
    assert artifact.validation_status is RuntimeArtifactValidationStatus.VALID


@pytest.mark.asyncio
async def test_runtime_artifact_service_marks_stale_when_model_hash_changes() -> None:
    model = _model(sha256="f" * 64)
    artifact = _artifact(model_id=model.id, source_model_sha256="a" * 64)
    service = RuntimeArtifactService(
        session_factory=_FakeSessionFactory(model=model, artifacts=[artifact])
    )

    response = await service.list_for_model(model.id)

    assert response[0].validation_status is RuntimeArtifactValidationStatus.STALE


def test_artifact_matches_camera_vocabulary_uses_runtime_vocabulary_hash() -> None:
    model = _model(capability=DetectorCapability.OPEN_VOCAB)
    camera = _camera(model_id=model.id)
    camera.runtime_vocabulary = ["person", "chair"]
    artifact = _artifact(
        model_id=model.id,
        camera_id=camera.id,
        scope=RuntimeArtifactScope.SCENE,
        capability=DetectorCapability.OPEN_VOCAB,
        vocabulary_hash=hash_vocabulary(["person", "chair"]),
        vocabulary_version=1,
    )

    assert artifact_matches_camera_vocabulary(artifact=artifact, camera=camera) is True

    artifact.vocabulary_hash = hash_vocabulary(["forklift"])

    assert artifact_matches_camera_vocabulary(artifact=artifact, camera=camera) is False
