from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import (
    BrowserDeliverySettings,
    SourceCapability,
    WorkerEvidenceStorageSettings,
    WorkerStreamDeliverySettings,
)
from argus.core.config import Settings
from argus.core.security import encrypt_rtsp_url
from argus.models.enums import (
    CameraSourceKind,
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
from argus.models.tables import (
    Camera,
    Model,
    ModelRuntimeArtifact,
    PrivacyManifestSnapshot,
    SceneContractSnapshot,
    Tenant,
)
from argus.services.app import (
    CameraService,
    _browser_delivery_with_stream_profile,
    _camera_to_worker_config,
    _stream_delivery_base_urls,
    derive_browser_profiles,
)
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
        if model_cls is Tenant:
            tenant = self.state.get("tenant")
            return tenant if getattr(tenant, "id", None) == model_id else None
        return None

    async def execute(self, statement):  # noqa: ANN001
        if "model_runtime_artifacts" in str(statement):
            artifacts = self.state["artifacts"]
            assert isinstance(artifacts, list)
            return _Result(artifacts)
        if "privacy_manifest_snapshots" in str(statement):
            snapshots = self.state["privacy_manifest_snapshots"]
            assert isinstance(snapshots, list)
            manifest_hash = _hash_param_from_statement(statement)
            return _Result(
                [
                    snapshot
                    for snapshot in snapshots
                    if manifest_hash is None or snapshot.manifest_hash == manifest_hash
                ]
            )
        if "scene_contract_snapshots" in str(statement):
            snapshots = self.state["scene_contract_snapshots"]
            assert isinstance(snapshots, list)
            contract_hash = _hash_param_from_statement(statement)
            return _Result(
                [
                    snapshot
                    for snapshot in snapshots
                    if contract_hash is None or snapshot.contract_hash == contract_hash
                ]
            )
        camera = self.state["camera"]
        return _Result([camera])

    def add(self, value: object) -> None:
        if isinstance(value, PrivacyManifestSnapshot):
            value.id = value.id or uuid4()
            snapshots = self.state["privacy_manifest_snapshots"]
            assert isinstance(snapshots, list)
            snapshots.append(value)
        if isinstance(value, SceneContractSnapshot):
            value.id = value.id or uuid4()
            snapshots = self.state["scene_contract_snapshots"]
            assert isinstance(snapshots, list)
            snapshots.append(value)

    async def commit(self) -> None:
        self.state["commits"] = int(self.state.get("commits", 0)) + 1

    async def rollback(self) -> None:
        self.state["rollbacks"] = int(self.state.get("rollbacks", 0)) + 1

    async def refresh(self, value: object) -> None:
        if isinstance(value, PrivacyManifestSnapshot | SceneContractSnapshot):
            value.created_at = value.created_at or datetime.now(tz=UTC)


class _WorkerConfigSessionFactory:
    def __init__(
        self,
        *,
        camera: Camera,
        models: dict[object, Model],
        artifacts: list[ModelRuntimeArtifact],
        tenant: Tenant | None = None,
    ) -> None:
        self.state: dict[str, object] = {
            "camera": camera,
            "models": models,
            "artifacts": artifacts,
            "privacy_manifest_snapshots": [],
            "scene_contract_snapshots": [],
            "tenant": tenant,
        }

    def __call__(self) -> _WorkerConfigSession:
        return _WorkerConfigSession(self.state)


class _FakeAuditLogger:
    async def record(self, **kwargs: object) -> None:
        return None


class _FakeOperatorConfigurationService:
    def __init__(
        self,
        evidence_storage: WorkerEvidenceStorageSettings | None = None,
        stream_delivery: WorkerStreamDeliverySettings | None = None,
    ) -> None:
        self.evidence_storage = evidence_storage
        self.stream_delivery = stream_delivery
        self.calls: list[tuple[object, object, object | None]] = []
        self.stream_calls: list[tuple[object, object, object | None]] = []

    async def resolve_worker_evidence_storage(
        self,
        tenant_context: object,
        *,
        camera_id: object,
        profile_id: object | None = None,
    ) -> WorkerEvidenceStorageSettings:
        self.calls.append((tenant_context, camera_id, profile_id))
        if self.evidence_storage is None:
            return WorkerEvidenceStorageSettings(
                profile_id=None,
                profile_name="Default local evidence",
                profile_hash=None,
                provider="local_filesystem",
                storage_scope="edge",
                config={"local_root": "/tmp/argus-incidents"},
                secrets={},
            )
        return self.evidence_storage

    async def resolve_worker_stream_delivery(
        self,
        tenant_context: object,
        *,
        camera_id: object,
        profile_id: object | None = None,
    ) -> WorkerStreamDeliverySettings:
        self.stream_calls.append((tenant_context, camera_id, profile_id))
        if self.stream_delivery is None:
            return WorkerStreamDeliverySettings(
                profile_id=None,
                profile_name="Default native stream delivery",
                profile_hash=None,
                delivery_mode="native",
                public_base_url=None,
                edge_override_url=None,
            )
        return self.stream_delivery


def _tenant_context(tenant_id=None):  # noqa: ANN001
    from argus.api.contracts import TenantContext
    from argus.core.security import AuthenticatedUser
    from argus.models.enums import RoleEnum

    tenant_id = tenant_id or uuid4()
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


def _tenant(tenant_id, *, allow_plaintext_plates: bool = False) -> Tenant:  # noqa: ANN001
    return Tenant(
        id=tenant_id,
        name="Worker Test Tenant",
        slug="worker-test",
        anpr_store_plaintext=allow_plaintext_plates,
        anpr_plaintext_justification="Dock audit policy" if allow_plaintext_plates else None,
    )


def _encrypted_rtsp_url(
    settings: Settings,
    url: str = "rtsp://lab-camera.local/live",
) -> str:
    return encrypt_rtsp_url(url, settings)


def _hash_param_from_statement(statement) -> str | None:  # noqa: ANN001
    for key, value in statement.compile().params.items():
        if "hash" in key and isinstance(value, str):
            return value
    return None


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
async def test_worker_config_includes_accountable_scene_hashes_and_recording_policy() -> None:
    settings = _settings()
    model = _model(uuid4())
    camera = _camera(
        primary_model_id=model.id,
        active_classes=["person"],
        rtsp_url_encrypted=_encrypted_rtsp_url(settings),
    )
    service = CameraService(
        session_factory=_WorkerConfigSessionFactory(
            camera=camera,
            models={model.id: model},
            artifacts=[],
        ),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
    )

    config = await service.get_worker_config(_tenant_context(), camera.id)

    assert config.recording_policy.enabled is True
    assert config.recording_policy.mode == "event_clip"
    assert config.recording_policy.pre_seconds == 4
    assert config.recording_policy.post_seconds == 8
    assert config.recording_policy.fps == 10
    assert config.recording_policy.max_duration_seconds == 15
    assert config.scene_contract_hash is not None
    assert len(config.scene_contract_hash) == 64
    assert config.privacy_manifest_hash is not None
    assert len(config.privacy_manifest_hash) == 64


@pytest.mark.asyncio
async def test_worker_config_includes_decrypted_evidence_storage_profile() -> None:
    settings = _settings()
    model = _model(uuid4())
    profile_id = uuid4()
    camera = _camera(
        primary_model_id=model.id,
        active_classes=["person"],
        rtsp_url_encrypted=_encrypted_rtsp_url(settings),
        evidence_recording_policy={
            "enabled": True,
            "mode": "event_clip",
            "pre_seconds": 4,
            "post_seconds": 8,
            "fps": 10,
            "max_duration_seconds": 15,
            "storage_profile": "cloud",
            "storage_profile_id": str(profile_id),
        },
    )
    configuration_service = _FakeOperatorConfigurationService(
        WorkerEvidenceStorageSettings(
            profile_id=profile_id,
            profile_name="Cloud S3",
            profile_hash="d" * 64,
            provider="s3_compatible",
            storage_scope="cloud",
            config={
                "endpoint": "s3.example.com",
                "region": "eu-central-1",
                "bucket": "omnisight-evidence",
                "secure": True,
            },
            secrets={"access_key": "cloud-key", "secret_key": "cloud-secret"},
        )
    )
    service = CameraService(
        session_factory=_WorkerConfigSessionFactory(
            camera=camera,
            models={model.id: model},
            artifacts=[],
        ),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        configuration_service=configuration_service,
    )
    tenant_context = _tenant_context()

    config = await service.get_worker_config(tenant_context, camera.id)

    assert configuration_service.calls == [(tenant_context, camera.id, profile_id)]
    assert config.recording_policy.storage_profile == "cloud"
    assert config.recording_policy.storage_profile_id == profile_id
    assert config.evidence_storage is not None
    assert config.evidence_storage.profile_id == profile_id
    assert config.evidence_storage.provider == "s3_compatible"
    assert config.evidence_storage.storage_scope == "cloud"
    assert config.evidence_storage.config["bucket"] == "omnisight-evidence"
    assert config.evidence_storage.secrets == {
        "access_key": "cloud-key",
        "secret_key": "cloud-secret",
    }


@pytest.mark.asyncio
async def test_worker_config_includes_resolved_stream_delivery_profile() -> None:
    settings = _settings()
    model = _model(uuid4())
    stream_profile_id = uuid4()
    camera = _camera(
        primary_model_id=model.id,
        active_classes=["person"],
        rtsp_url_encrypted=_encrypted_rtsp_url(settings),
        browser_delivery={
            "default_profile": "720p10",
            "allow_native_on_demand": True,
            "delivery_profile_id": str(stream_profile_id),
            "profiles": [],
        },
    )
    configuration_service = _FakeOperatorConfigurationService(
        stream_delivery=WorkerStreamDeliverySettings(
            profile_id=stream_profile_id,
            profile_name="Edge HLS delivery",
            profile_hash="e" * 64,
            delivery_mode="hls",
            public_base_url="https://streams.example.com",
            edge_override_url="https://edge-streams.example.com",
        )
    )
    service = CameraService(
        session_factory=_WorkerConfigSessionFactory(
            camera=camera,
            models={model.id: model},
            artifacts=[],
        ),
        settings=settings,
        audit_logger=_FakeAuditLogger(),
        configuration_service=configuration_service,
    )
    tenant_context = _tenant_context()

    config = await service.get_worker_config(tenant_context, camera.id)

    assert configuration_service.stream_calls == [
        (tenant_context, camera.id, stream_profile_id)
    ]
    assert config.stream_delivery is not None
    assert config.stream_delivery.profile_id == stream_profile_id
    assert config.stream_delivery.profile_name == "Edge HLS delivery"
    assert config.stream_delivery.profile_hash == "e" * 64
    assert config.stream_delivery.delivery_mode == "hls"
    assert config.stream_delivery.public_base_url == "https://streams.example.com"
    assert config.stream_delivery.edge_override_url == "https://edge-streams.example.com"


def test_worker_config_sends_usb_capture_uri_to_edge_runtime() -> None:
    settings = _settings()
    model = _model(uuid4())
    camera = _camera(
        edge_node_id=uuid4(),
        processing_mode=ProcessingMode.EDGE,
        primary_model_id=model.id,
        source_kind=CameraSourceKind.USB.value,
        source_config={
            "kind": CameraSourceKind.USB.value,
            "uri": "usb:///dev/video0",
            "capture_uri": "/dev/video0",
            "redacted_uri": "usb://***",
        },
    )

    config = _camera_to_worker_config(
        camera=camera,
        primary_model=model,
        secondary_model=None,
        settings=settings,
        rtsp_url="rtsp://legacy-camera.local/live",
    )

    assert config.camera.source_uri == "/dev/video0"
    assert config.camera.camera_source is not None
    assert config.camera.camera_source.kind is CameraSourceKind.USB
    assert config.camera.camera_source.uri == "usb:///dev/video0"


@pytest.mark.asyncio
async def test_worker_config_snapshots_redact_source_and_reflect_tenant_privacy() -> None:
    settings = _settings()
    tenant_id = uuid4()
    model = _model(uuid4())
    camera = _camera(
        primary_model_id=model.id,
        rtsp_url_encrypted=_encrypted_rtsp_url(
            settings,
            "rtsp://user:pass@camera.local/live?api_key=secret&signature=abc",
        ),
    )
    session_factory = _WorkerConfigSessionFactory(
        camera=camera,
        models={model.id: model},
        artifacts=[],
        tenant=_tenant(tenant_id, allow_plaintext_plates=True),
    )
    service = CameraService(
        session_factory=session_factory,
        settings=settings,
        audit_logger=_FakeAuditLogger(),
    )

    await service.get_worker_config(_tenant_context(tenant_id), camera.id)

    privacy_snapshots = session_factory.state["privacy_manifest_snapshots"]
    scene_snapshots = session_factory.state["scene_contract_snapshots"]
    assert isinstance(privacy_snapshots, list)
    assert isinstance(scene_snapshots, list)
    privacy_manifest = privacy_snapshots[0].manifest
    scene_contract = scene_snapshots[0].contract
    source = scene_contract["camera"]["source"]
    assert privacy_manifest["plates"]["plaintext_storage"] == "allowed"
    assert privacy_manifest["plates"]["plaintext_justification"] == "Dock audit policy"
    assert source["uri"] == "rtsp://camera.local/live"
    assert "secret" not in source["uri"]
    assert "signature" not in source["uri"]
    assert "user:pass" not in source["uri"]


@pytest.mark.asyncio
async def test_worker_config_rejection_does_not_commit_scene_snapshots() -> None:
    settings = _settings()
    model = _model(uuid4())
    camera = _camera(
        primary_model_id=model.id,
        rtsp_url_encrypted=_encrypted_rtsp_url(settings),
        vision_profile={
            "accuracy_mode": "balanced",
            "compute_tier": "edge_standard",
            "motion_metrics": {"speed_enabled": True},
        },
        homography=None,
    )
    session_factory = _WorkerConfigSessionFactory(
        camera=camera,
        models={model.id: model},
        artifacts=[],
    )
    service = CameraService(
        session_factory=session_factory,
        settings=settings,
        audit_logger=_FakeAuditLogger(),
    )

    with pytest.raises(HTTPException):
        await service.get_worker_config(_tenant_context(), camera.id)

    assert session_factory.state["privacy_manifest_snapshots"] == []
    assert session_factory.state["scene_contract_snapshots"] == []


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


def test_stream_delivery_profile_controls_playback_base_urls_and_mode() -> None:
    settings = _settings()
    delivery = WorkerStreamDeliverySettings(
        profile_id=uuid4(),
        profile_name="Edge HLS delivery",
        profile_hash="e" * 64,
        delivery_mode="hls",
        public_base_url="https://streams.example.com",
        edge_override_url="https://edge-streams.example.com",
    )

    resolved = _browser_delivery_with_stream_profile(
        BrowserDeliverySettings(default_profile="native"),
        delivery,
    )
    central_urls = _stream_delivery_base_urls(
        resolved,
        settings=settings,
        edge_node_id=None,
        processing_mode=ProcessingMode.CENTRAL,
    )
    edge_urls = _stream_delivery_base_urls(
        resolved,
        settings=settings,
        edge_node_id=uuid4(),
        processing_mode=ProcessingMode.EDGE,
    )

    assert resolved.default_profile == "annotated"
    assert resolved.delivery_profile_id == delivery.profile_id
    assert resolved.delivery_mode == "hls"
    assert central_urls["hls"] == "https://streams.example.com"
    assert central_urls["webrtc"] == "https://streams.example.com"
    assert edge_urls["hls"] == "https://edge-streams.example.com"


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
