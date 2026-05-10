from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import SourceCapability
from argus.core.config import Settings
from argus.core.security import encrypt_rtsp_url
from argus.models.enums import (
    DetectorCapability,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
    RuntimeVocabularySource,
    TrackerType,
)
from argus.models.tables import Camera, Model, ModelRuntimeArtifact
from argus.services.app import CameraService, _camera_to_worker_config, derive_browser_profiles
from argus.vision.vocabulary import hash_vocabulary


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )


def _model(model_id):
    return Model(
        id=model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config={},
        classes=["person", "car", "bus", "truck"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )


def _camera(**overrides):
    values = {
        "id": uuid4(),
        "site_id": uuid4(),
        "edge_node_id": None,
        "name": "Dock Camera",
        "rtsp_url_encrypted": "encrypted",
        "processing_mode": ProcessingMode.CENTRAL,
        "primary_model_id": uuid4(),
        "secondary_model_id": None,
        "tracker_type": TrackerType.BOTSORT,
        "active_classes": [],
        "runtime_vocabulary": [],
        "runtime_vocabulary_source": RuntimeVocabularySource.DEFAULT,
        "runtime_vocabulary_version": 0,
        "runtime_vocabulary_updated_at": None,
        "attribute_rules": [],
        "zones": [],
        "vision_profile": {},
        "detection_regions": [],
        "homography": None,
        "privacy": {
            "blur_faces": False,
            "blur_plates": False,
            "method": "gaussian",
            "strength": 7,
        },
        "browser_delivery": {
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        "frame_skip": 1,
        "fps_cap": 17,
    }
    values.update(overrides)
    return Camera(**values)


class _Result:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def scalar_one_or_none(self) -> object | None:
        return self.values[0] if self.values else None

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[object]:
        return self.values


class _WorkerConfigSession:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    async def __aenter__(self) -> _WorkerConfigSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def get(self, model_cls, model_id):  # noqa: ANN001
        models = self.state["models"]
        assert isinstance(models, dict)
        if model_cls is Model:
            return models.get(model_id)
        return None

    async def execute(self, statement):  # noqa: ANN001
        if "model_runtime_artifacts" in str(statement):
            artifacts = self.state["artifacts"]
            assert isinstance(artifacts, list)
            return _Result(artifacts)
        camera = self.state["camera"]
        return _Result([camera])


class _WorkerConfigSessionFactory:
    def __init__(
        self,
        *,
        camera: Camera,
        models: dict[object, Model],
        artifacts: list[ModelRuntimeArtifact],
    ) -> None:
        self.state: dict[str, object] = {
            "camera": camera,
            "models": models,
            "artifacts": artifacts,
        }

    def __call__(self) -> _WorkerConfigSession:
        return _WorkerConfigSession(self.state)


class _FakeAuditLogger:
    async def record(self, **kwargs: object) -> None:
        return None


def _tenant_context():
    from argus.api.contracts import TenantContext
    from argus.core.security import AuthenticatedUser
    from argus.models.enums import RoleEnum

    tenant_id = uuid4()
    user = AuthenticatedUser(
        subject="worker-test",
        email="worker@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(tenant_id),
        claims={},
    )
    return TenantContext(tenant_id=tenant_id, tenant_slug="argus-dev", user=user)


def _encrypted_rtsp_url(settings: Settings) -> str:
    return encrypt_rtsp_url("rtsp://lab-camera.local/live", settings)


def _runtime_artifact(
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
        path="/models/yolo12n.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "car", "bus", "truck"],
        vocabulary_hash=vocabulary_hash,
        vocabulary_version=vocabulary_version,
        source_model_sha256=source_model_sha256,
        sha256="b" * 64,
        size_bytes=1234,
        builder={},
        runtime_versions={},
        validation_status=validation_status,
        validation_error=None,
    )


def test_source_capability_hides_1080p_above_720p_source() -> None:
    source = SourceCapability(width=1280, height=720, fps=20, codec="h264")

    profiles = derive_browser_profiles(source)

    assert [profile.id for profile in profiles.allowed] == [
        "native",
        "annotated",
        "720p10",
        "540p5",
    ]
    assert profiles.unsupported[0].id == "1080p15"
    assert profiles.unsupported[0].reason == "source_resolution_too_small"


def test_camera_worker_config_maps_camera_models_and_homography_for_engine() -> None:
    camera_id = uuid4()
    primary_model_id = uuid4()
    secondary_model_id = uuid4()
    camera = Camera(
        id=camera_id,
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=primary_model_id,
        secondary_model_id=secondary_model_id,
        tracker_type=TrackerType.BOTSORT,
        active_classes=["bus", "truck"],
        attribute_rules=[{"kind": "ppe"}],
        zones=[{"id": "gate-1", "type": "line"}],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={"blur_faces": True, "blur_plates": False, "method": "pixelate", "strength": 20},
        browser_delivery={
            "default_profile": "720p10",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=2,
        fps_cap=10,
    )
    primary_model = Model(
        id=primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car", "bus", "truck"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    secondary_model = Model(
        id=secondary_model_id,
        name="PPE",
        version="lab-1",
        task=ModelTask.ATTRIBUTE,
        path="/models/ppe.onnx",
        format=ModelFormat.ONNX,
        classes=["hi_vis", "hard_hat"],
        input_shape={"width": 224, "height": 224},
        sha256="b" * 64,
        size_bytes=456,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=secondary_model,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.camera_id == camera_id
    assert config.mode is ProcessingMode.CENTRAL
    assert config.camera.rtsp_url == "rtsp://lab-camera.local/live"
    assert config.camera.frame_skip == 2
    assert config.camera.fps_cap == 10
    assert config.model.name == "YOLO12n"
    assert config.model.path == "/models/yolo12n.onnx"
    assert config.model.classes == ["person", "car", "bus", "truck"]
    assert config.secondary_model is not None
    assert config.secondary_model.name == "PPE"
    assert config.publish.subject_prefix == "evt.tracking"
    assert config.publish.http_fallback_url is None
    assert config.stream.model_dump() == {
        "profile_id": "720p10",
        "kind": "transcode",
        "width": 1280,
        "height": 720,
        "fps": 10,
    }
    assert config.tracker.tracker_type is TrackerType.BOTSORT
    assert config.tracker.frame_rate == 10
    assert config.privacy.blur_faces is True
    assert config.privacy.blur_plates is False
    assert config.privacy.method == "pixelate"
    assert config.privacy.strength == 20
    assert config.active_classes == ["bus", "truck"]
    assert config.attribute_rules == [{"kind": "ppe"}]
    assert [zone.model_dump(exclude_none=True, mode="python") for zone in config.zones] == [
        {"id": "gate-1", "type": "line"}
    ]
    assert config.homography == {
        "src_points": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "dst_points": [[0, 0], [10, 0], [10, 10], [0, 10]],
        "ref_distance_m": 12.5,
    }


@pytest.mark.asyncio
async def test_worker_config_includes_valid_fixed_vocab_runtime_artifact() -> None:
    settings = _settings()
    model = _model(uuid4())
    camera = _camera(
        primary_model_id=model.id,
        active_classes=["person"],
        rtsp_url_encrypted=_encrypted_rtsp_url(settings),
    )
    artifact = _runtime_artifact(model_id=model.id)
    service = CameraService(
        session_factory=_WorkerConfigSessionFactory(
            camera=camera,
            models={model.id: model},
            artifacts=[artifact],
        ),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
    )

    config = await service.get_worker_config(_tenant_context(), camera.id)

    assert [candidate.id for candidate in config.runtime_artifacts] == [artifact.id]
    assert config.runtime_artifacts[0].runtime_backend == "tensorrt_engine"


@pytest.mark.asyncio
async def test_worker_config_excludes_invalid_and_stale_runtime_artifacts() -> None:
    settings = _settings()
    model = _model(uuid4())
    camera = _camera(
        primary_model_id=model.id,
        active_classes=["person"],
        rtsp_url_encrypted=_encrypted_rtsp_url(settings),
    )
    invalid = _runtime_artifact(
        model_id=model.id,
        validation_status=RuntimeArtifactValidationStatus.INVALID,
    )
    stale = _runtime_artifact(model_id=model.id, source_model_sha256="f" * 64)
    service = CameraService(
        session_factory=_WorkerConfigSessionFactory(
            camera=camera,
            models={model.id: model},
            artifacts=[invalid, stale],
        ),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
    )

    config = await service.get_worker_config(_tenant_context(), camera.id)

    assert config.runtime_artifacts == []


@pytest.mark.asyncio
async def test_worker_config_includes_matching_open_vocab_scene_artifact_only() -> None:
    settings = _settings()
    model = _model(uuid4())
    model.capability = DetectorCapability.OPEN_VOCAB
    model.capability_config = {
        "supports_runtime_vocabulary_updates": True,
        "max_runtime_terms": 32,
        "runtime_backend": "ultralytics_yoloe",
    }
    model.classes = []
    terms = ["person", "chair"]
    expected_hash = hash_vocabulary(terms)
    camera = _camera(
        primary_model_id=model.id,
        active_classes=[],
        runtime_vocabulary=terms,
        runtime_vocabulary_source=RuntimeVocabularySource.MANUAL,
        runtime_vocabulary_version=7,
        rtsp_url_encrypted=_encrypted_rtsp_url(settings),
    )
    matching = _runtime_artifact(
        model_id=model.id,
        camera_id=camera.id,
        scope=RuntimeArtifactScope.SCENE,
        capability=DetectorCapability.OPEN_VOCAB,
        vocabulary_hash=expected_hash,
        vocabulary_version=7,
    )
    wrong_camera = _runtime_artifact(
        model_id=model.id,
        camera_id=uuid4(),
        scope=RuntimeArtifactScope.SCENE,
        capability=DetectorCapability.OPEN_VOCAB,
        vocabulary_hash=expected_hash,
        vocabulary_version=7,
    )
    wrong_vocab = _runtime_artifact(
        model_id=model.id,
        camera_id=camera.id,
        scope=RuntimeArtifactScope.SCENE,
        capability=DetectorCapability.OPEN_VOCAB,
        vocabulary_hash=hash_vocabulary(["forklift"]),
        vocabulary_version=6,
    )
    service = CameraService(
        session_factory=_WorkerConfigSessionFactory(
            camera=camera,
            models={model.id: model},
            artifacts=[matching, wrong_camera, wrong_vocab],
        ),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
    )

    config = await service.get_worker_config(_tenant_context(), camera.id)

    assert [candidate.id for candidate in config.runtime_artifacts] == [matching.id]
    assert config.runtime_artifacts[0].vocabulary_hash == expected_hash
    assert config.runtime_artifacts[0].vocabulary_version == 7


@pytest.mark.asyncio
async def test_worker_config_excludes_open_vocab_scene_artifact_after_vocabulary_changes() -> None:
    settings = _settings()
    model = _model(uuid4())
    model.capability = DetectorCapability.OPEN_VOCAB
    model.capability_config = {
        "supports_runtime_vocabulary_updates": True,
        "max_runtime_terms": 32,
        "runtime_backend": "ultralytics_yoloe",
    }
    model.classes = []
    camera = _camera(
        primary_model_id=model.id,
        active_classes=[],
        runtime_vocabulary=["person", "chair", "backpack"],
        runtime_vocabulary_source=RuntimeVocabularySource.MANUAL,
        runtime_vocabulary_version=8,
        rtsp_url_encrypted=_encrypted_rtsp_url(settings),
    )
    artifact = _runtime_artifact(
        model_id=model.id,
        camera_id=camera.id,
        scope=RuntimeArtifactScope.SCENE,
        capability=DetectorCapability.OPEN_VOCAB,
        vocabulary_hash=hash_vocabulary(["person", "chair"]),
        vocabulary_version=7,
    )
    service = CameraService(
        session_factory=_WorkerConfigSessionFactory(
            camera=camera,
            models={model.id: model},
            artifacts=[artifact],
        ),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
    )

    config = await service.get_worker_config(_tenant_context(), camera.id)

    assert config.runtime_artifacts == []


def test_camera_worker_config_returns_denormalized_detection_regions() -> None:
    camera = _camera(
        detection_regions=[
            {
                "id": "lab-floor",
                "mode": "include",
                "polygon": [[100, 100], [1100, 100], [1100, 700], [100, 700]],
                "class_names": ["person"],
                "frame_size": {"width": 1280, "height": 720},
                "points_normalized": [
                    [0.078125, 0.138889],
                    [0.859375, 0.138889],
                    [0.859375, 0.972222],
                    [0.078125, 0.972222],
                ],
            }
        ],
    )
    primary_model = _model(camera.primary_model_id)

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=_settings(),
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert len(config.detection_regions) == 1
    region = config.detection_regions[0]
    assert region.polygon == [[100.0, 100.0], [1100.0, 100.0], [1100.0, 700.0], [100.0, 700.0]]
    assert region.points_normalized == [
        [0.078125, 0.138889],
        [0.859375, 0.138889],
        [0.859375, 0.972222],
        [0.078125, 0.972222],
    ]


def test_camera_worker_config_speed_enabled_profile_includes_homography() -> None:
    camera = _camera(
        vision_profile={
            "accuracy_mode": "balanced",
            "compute_tier": "edge_standard",
            "motion_metrics": {"speed_enabled": True},
        },
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
    )
    primary_model = _model(camera.primary_model_id)

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=_settings(),
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.vision_profile.motion_metrics.speed_enabled is True
    assert config.homography == {
        "src_points": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "dst_points": [[0, 0], [10, 0], [10, 10], [0, 10]],
        "ref_distance_m": 12.5,
    }


def test_camera_worker_config_speed_disabled_profile_can_return_no_homography() -> None:
    camera = _camera(
        vision_profile={
            "accuracy_mode": "fast",
            "compute_tier": "cpu_low",
            "motion_metrics": {"speed_enabled": False},
        },
        homography=None,
    )
    primary_model = _model(camera.primary_model_id)

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=_settings(),
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.vision_profile.motion_metrics.speed_enabled is False
    assert config.homography is None


def test_camera_worker_config_rejects_speed_enabled_without_homography() -> None:
    camera = _camera(
        vision_profile={
            "accuracy_mode": "balanced",
            "compute_tier": "edge_standard",
            "motion_metrics": {"speed_enabled": True},
        },
        homography=None,
    )
    primary_model = _model(camera.primary_model_id)

    with pytest.raises(HTTPException) as exc_info:
        _camera_to_worker_config(
            camera=camera,
            primary_model=primary_model,
            secondary_model=None,
            settings=_settings(),
            rtsp_url="rtsp://lab-camera.local/live",
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Homography is required when speed metrics are enabled."


def test_camera_worker_config_preserves_jetson_tier() -> None:
    camera = _camera(
        vision_profile={
            "accuracy_mode": "maximum_accuracy",
            "compute_tier": "edge_advanced_jetson",
            "scene_difficulty": "crowded",
            "object_domain": "people",
        },
    )
    primary_model = _model(camera.primary_model_id)

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=_settings(),
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.vision_profile.compute_tier == "edge_advanced_jetson"


def test_edge_native_browser_delivery_keeps_passthrough_stream() -> None:
    camera = Camera(
        id=uuid4(),
        site_id=uuid4(),
        edge_node_id=uuid4(),
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={"blur_faces": False, "blur_plates": False, "method": "gaussian", "strength": 7},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=17,
    )
    primary_model = Model(
        id=camera.primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.stream.model_dump() == {
        "profile_id": "native",
        "kind": "passthrough",
        "width": None,
        "height": None,
        "fps": 17,
    }
    assert config.model.classes == ["person", "car"]


def test_central_native_browser_delivery_without_privacy_keeps_passthrough_stream() -> None:
    camera = Camera(
        id=uuid4(),
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={"blur_faces": False, "blur_plates": False, "method": "gaussian", "strength": 7},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=17,
    )
    primary_model = Model(
        id=camera.primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.stream.model_dump() == {
        "profile_id": "native",
        "kind": "passthrough",
        "width": None,
        "height": None,
        "fps": 17,
    }


def test_annotated_browser_delivery_uses_processed_full_rate_stream() -> None:
    camera = Camera(
        id=uuid4(),
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={"blur_faces": True, "blur_plates": False, "method": "gaussian", "strength": 7},
        browser_delivery={
            "default_profile": "annotated",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=17,
    )
    primary_model = Model(
        id=camera.primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.stream.model_dump() == {
        "profile_id": "annotated",
        "kind": "transcode",
        "width": None,
        "height": None,
        "fps": 17,
    }


def test_central_native_browser_delivery_with_privacy_resolves_to_annotated_stream() -> None:
    camera = Camera(
        id=uuid4(),
        site_id=uuid4(),
        edge_node_id=None,
        name="Dock Camera",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=uuid4(),
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        attribute_rules=[],
        zones=[],
        homography={
            "src": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "dst": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "ref_distance_m": 12.5,
        },
        privacy={"blur_faces": True, "blur_plates": False, "method": "gaussian", "strength": 7},
        browser_delivery={
            "default_profile": "native",
            "allow_native_on_demand": True,
            "profiles": [],
        },
        frame_skip=1,
        fps_cap=17,
    )
    primary_model = Model(
        id=camera.primary_model_id,
        name="YOLO12n",
        version="lab-1",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123,
        license="lab",
    )
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=primary_model,
        secondary_model=None,
        settings=settings,
        rtsp_url="rtsp://lab-camera.local/live",
    )

    assert config.stream.model_dump() == {
        "profile_id": "annotated",
        "kind": "transcode",
        "width": None,
        "height": None,
        "fps": 17,
    }
