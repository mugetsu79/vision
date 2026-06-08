from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    DeploymentModelAssignmentCreate,
    RuntimeArtifactBuildJobCreate,
    SupervisorModelJobComplete,
    SupervisorModelJobEventCreate,
)
from argus.compat import UTC
from argus.models.enums import (
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DetectorCapability,
    ModelFormat,
    ModelLifecycleJobStatus,
    ModelTask,
    ProcessingMode,
    RuntimeArtifactBuildFormat,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeVocabularySource,
    TrackerType,
)
from argus.models.tables import (
    Camera,
    DeploymentNode,
    Model,
    ModelRuntimeArtifact,
    RuntimeArtifactBuildJob,
    Tenant,
)
from argus.services.model_lifecycle import ModelLifecycleService
from argus.vision.vocabulary import hash_vocabulary, normalize_vocabulary_terms


@pytest.mark.asyncio
async def test_create_fixed_vocab_tensorrt_build_job_requires_assignment() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)

    with pytest.raises(ValueError, match="assignment"):
        await service.create_runtime_artifact_build_job(
            tenant_id=tenant.id,
            model_id=model.id,
            payload=_build_job_payload(node.id),
            actor_subject="admin@example.test",
        )

    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )

    assert job.status is ModelLifecycleJobStatus.QUEUED
    assert job.build_format is RuntimeArtifactBuildFormat.TENSORRT_ENGINE
    assert job.payload["job_type"] == "artifact_build"
    assert job.payload["schema_version"] == 1
    assert job.payload["model_id"] == str(model.id)
    assert job.payload["source_model_sha256"] == model.sha256
    assert job.payload["source_model_path"] == model.path
    assert job.payload["build_format"] == "tensorrt_engine"
    assert job.payload["target_profile"] == "linux-aarch64-nvidia-jetson"
    assert job.payload["precision"] == "fp16"
    assert job.payload["runtime_vocabulary"] == []
    assert job.payload["output_dir"]


@pytest.mark.asyncio
async def test_create_open_vocab_build_job_uses_camera_vocabulary_hash() -> None:
    tenant, model, node = _tenant_model_and_node(capability=DetectorCapability.OPEN_VOCAB)
    node.host_profile = "linux-aarch64-nvidia-jetson"
    camera = _camera(model_id=model.id, runtime_vocabulary=["person", "laptop"])
    session_factory = _MemorySessionFactory([tenant, model, node, camera])
    service = ModelLifecycleService(session_factory=session_factory)

    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(
            node.id,
            camera_id=camera.id,
            export_formats=[
                RuntimeArtifactBuildFormat.ONNX_EXPORT,
                RuntimeArtifactBuildFormat.TENSORRT_ENGINE,
            ],
        ),
        actor_subject="admin@example.test",
    )

    expected_terms = normalize_vocabulary_terms(["person", "laptop"])
    assert job.camera_id == camera.id
    assert job.payload["runtime_vocabulary"] == expected_terms
    assert job.payload["vocabulary_hash"] == hash_vocabulary(expected_terms)
    assert job.payload["vocabulary_version"] == camera.runtime_vocabulary_version
    assert job.payload["export_formats"] == ["onnx_export", "tensorrt_engine"]


@pytest.mark.asyncio
async def test_open_vocab_build_job_requires_non_empty_camera_vocabulary() -> None:
    tenant, model, node = _tenant_model_and_node(capability=DetectorCapability.OPEN_VOCAB)
    node.host_profile = "linux-aarch64-nvidia-jetson"
    camera = _camera(model_id=model.id, runtime_vocabulary=[])
    session_factory = _MemorySessionFactory([tenant, model, node, camera])
    service = ModelLifecycleService(session_factory=session_factory)

    with pytest.raises(ValueError, match="vocabulary"):
        await service.create_runtime_artifact_build_job(
            tenant_id=tenant.id,
            model_id=model.id,
            payload=_build_job_payload(node.id, camera_id=camera.id),
            actor_subject="admin@example.test",
        )


@pytest.mark.asyncio
async def test_complete_runtime_artifact_build_job_creates_artifact() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )

    completed = await service.complete_runtime_artifact_build_job(
        tenant_id=tenant.id,
        authenticated_node_id=node.id,
        job_id=job.id,
        result=SupervisorModelJobComplete(
            status=ModelLifecycleJobStatus.SUCCEEDED,
            payload={"artifact": _artifact_payload(model)},
        ),
    )

    artifact_rows = _rows(session_factory, ModelRuntimeArtifact)
    assert completed.status is ModelLifecycleJobStatus.SUCCEEDED
    assert len(artifact_rows) == 1
    assert completed.artifact_id == artifact_rows[0].id
    assert artifact_rows[0].kind is RuntimeArtifactKind.TENSORRT_ENGINE
    completion_statement = _for_update_statement(session_factory, RuntimeArtifactBuildJob)
    assert completion_statement._for_update_arg.skip_locked is False


@pytest.mark.asyncio
async def test_poll_artifact_build_jobs_claims_job_once() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )

    first_poll = await service.poll_supervisor_model_jobs(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        limit=10,
    )
    second_poll = await service.poll_supervisor_model_jobs(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        limit=10,
    )

    job_row = _row(session_factory, RuntimeArtifactBuildJob, job.id)
    assert [polled_job.id for polled_job in first_poll] == [job.id]
    assert first_poll[0].status is ModelLifecycleJobStatus.ACCEPTED
    assert job_row.status is ModelLifecycleJobStatus.ACCEPTED
    assert job_row.claimed_by_supervisor_id == node.supervisor_id
    assert job_row.claimed_at is not None
    assert second_poll == []
    claim_statement = _for_update_statement(session_factory, RuntimeArtifactBuildJob)
    assert claim_statement._for_update_arg.skip_locked is True


@pytest.mark.asyncio
async def test_supervisor_complete_endpoint_registers_artifact_build_result() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )

    completed = await service.complete_supervisor_model_job(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        job_id=job.id,
        payload=SupervisorModelJobComplete(
            status=ModelLifecycleJobStatus.SUCCEEDED,
            payload={"artifact": _artifact_payload(model)},
        ),
    )

    artifact_rows = _rows(session_factory, ModelRuntimeArtifact)
    assert completed.status is ModelLifecycleJobStatus.SUCCEEDED
    assert completed.payload["job_type"] == "artifact_build"
    assert len(artifact_rows) == 1


@pytest.mark.asyncio
async def test_artifact_build_event_locks_job_before_status_update() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )

    updated = await service.record_supervisor_model_job_event(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        job_id=job.id,
        payload=SupervisorModelJobEventCreate(
            job_kind="artifact_build",
            status=ModelLifecycleJobStatus.RUNNING,
            message="Building runtime artifact.",
        ),
    )

    job_row = _row(session_factory, RuntimeArtifactBuildJob, job.id)
    event_lock_statement = _for_update_statement(session_factory, RuntimeArtifactBuildJob)
    assert updated.status is ModelLifecycleJobStatus.RUNNING
    assert job_row.status is ModelLifecycleJobStatus.RUNNING
    assert event_lock_statement._for_update_arg.skip_locked is False


@pytest.mark.asyncio
async def test_artifact_build_job_success_completion_is_idempotent() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )
    completion = SupervisorModelJobComplete(
        status=ModelLifecycleJobStatus.SUCCEEDED,
        payload={"artifact": _artifact_payload(model)},
    )

    first = await service.complete_runtime_artifact_build_job(
        tenant_id=tenant.id,
        authenticated_node_id=node.id,
        job_id=job.id,
        result=completion,
    )
    second = await service.complete_runtime_artifact_build_job(
        tenant_id=tenant.id,
        authenticated_node_id=node.id,
        job_id=job.id,
        result=completion,
    )
    failed_after_success = await service.complete_runtime_artifact_build_job(
        tenant_id=tenant.id,
        authenticated_node_id=node.id,
        job_id=job.id,
        result=SupervisorModelJobComplete(
            status=ModelLifecycleJobStatus.FAILED,
            error="late failure",
        ),
    )

    artifact_rows = _rows(session_factory, ModelRuntimeArtifact)
    assert first.status is ModelLifecycleJobStatus.SUCCEEDED
    assert second.status is ModelLifecycleJobStatus.SUCCEEDED
    assert failed_after_success.status is ModelLifecycleJobStatus.SUCCEEDED
    assert len(artifact_rows) == 1
    assert second.artifact_id == artifact_rows[0].id
    assert failed_after_success.artifact_id == artifact_rows[0].id


@pytest.mark.asyncio
async def test_artifact_build_job_rejects_source_hash_mismatch() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )
    artifact_payload = _artifact_payload(model)
    artifact_payload["source_model_sha256"] = "c" * 64

    completed = await service.complete_runtime_artifact_build_job(
        tenant_id=tenant.id,
        authenticated_node_id=node.id,
        job_id=job.id,
        result=SupervisorModelJobComplete(
            status=ModelLifecycleJobStatus.SUCCEEDED,
            payload={"artifact": artifact_payload},
        ),
    )

    assert completed.status is ModelLifecycleJobStatus.FAILED
    assert completed.error is not None
    assert "source_model_sha256" in completed.error
    assert _rows(session_factory, ModelRuntimeArtifact) == []


@pytest.mark.asyncio
async def test_artifact_build_job_rejects_result_that_does_not_match_job_spec() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )
    artifact_payload = _artifact_payload(model)
    artifact_payload["target_profile"] = "linux-x86_64-cuda"

    completed = await service.complete_runtime_artifact_build_job(
        tenant_id=tenant.id,
        authenticated_node_id=node.id,
        job_id=job.id,
        result=SupervisorModelJobComplete(
            status=ModelLifecycleJobStatus.SUCCEEDED,
            payload={"artifact": artifact_payload},
        ),
    )

    assert completed.status is ModelLifecycleJobStatus.FAILED
    assert completed.error is not None
    assert "target_profile" in completed.error
    assert _rows(session_factory, ModelRuntimeArtifact) == []


@pytest.mark.asyncio
async def test_failed_runtime_artifact_build_job_records_error_without_artifact() -> None:
    tenant, model, node = _tenant_model_and_node()
    node.host_profile = "linux-aarch64-nvidia-jetson"
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_runtime_artifact_build_job(
        tenant_id=tenant.id,
        model_id=model.id,
        payload=_build_job_payload(node.id),
        actor_subject="admin@example.test",
    )

    completed = await service.complete_runtime_artifact_build_job(
        tenant_id=tenant.id,
        authenticated_node_id=node.id,
        job_id=job.id,
        result=SupervisorModelJobComplete(
            status=ModelLifecycleJobStatus.FAILED,
            error="TensorRT export failed",
        ),
    )

    assert completed.status is ModelLifecycleJobStatus.FAILED
    assert completed.error == "TensorRT export failed"
    assert _rows(session_factory, ModelRuntimeArtifact) == []


def _tenant_model_and_node(
    *,
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB,
) -> tuple[Tenant, Model, DeploymentNode]:
    tenant = Tenant(id=uuid4(), name="Vezor Pilot", slug=f"tenant-{uuid4().hex[:8]}")
    model = Model(
        id=uuid4(),
        name="YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path="/models/yolo26n.onnx",
        format=ModelFormat.ONNX,
        capability=capability,
        capability_config={},
        classes=["person", "car"] if capability is DetectorCapability.FIXED_VOCAB else [],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=12_345,
        license="AGPL-3.0",
    )
    node = DeploymentNode(
        id=uuid4(),
        tenant_id=tenant.id,
        edge_node_id=uuid4(),
        supervisor_id="edge-orin-1",
        node_kind=DeploymentNodeKind.EDGE,
        hostname="edge-orin-1.local",
        install_status=DeploymentInstallStatus.HEALTHY,
        diagnostics={},
    )
    return tenant, model, node


def _camera(*, model_id: UUID, runtime_vocabulary: list[str]) -> Camera:
    return Camera(
        id=uuid4(),
        site_id=uuid4(),
        name="Dock",
        rtsp_url_encrypted="encrypted",
        processing_mode=ProcessingMode.CENTRAL,
        primary_model_id=model_id,
        secondary_model_id=None,
        tracker_type=TrackerType.BOTSORT,
        active_classes=[],
        runtime_vocabulary=runtime_vocabulary,
        runtime_vocabulary_source=RuntimeVocabularySource.MANUAL,
        runtime_vocabulary_version=7,
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


def _build_job_payload(
    deployment_node_id: UUID,
    *,
    camera_id: UUID | None = None,
    export_formats: list[RuntimeArtifactBuildFormat] | None = None,
) -> RuntimeArtifactBuildJobCreate:
    return RuntimeArtifactBuildJobCreate(
        deployment_node_id=deployment_node_id,
        camera_id=camera_id,
        build_format=RuntimeArtifactBuildFormat.TENSORRT_ENGINE,
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        export_formats=export_formats or [RuntimeArtifactBuildFormat.TENSORRT_ENGINE],
        builder_options={"output_dir": "/var/lib/vezor/artifacts"},
    )


def _artifact_payload(model: Model) -> dict[str, object]:
    return {
        "scope": RuntimeArtifactScope.MODEL.value,
        "kind": RuntimeArtifactKind.TENSORRT_ENGINE.value,
        "capability": DetectorCapability.FIXED_VOCAB.value,
        "runtime_backend": "tensorrt_engine",
        "path": "/var/lib/vezor/artifacts/yolo26n.engine",
        "target_profile": "linux-aarch64-nvidia-jetson",
        "precision": RuntimeArtifactPrecision.FP16.value,
        "input_shape": {"width": 640, "height": 640},
        "classes": ["person", "car"],
        "source_model_sha256": model.sha256,
        "sha256": "b" * 64,
        "size_bytes": 4567,
    }


def _rows(session_factory: _MemorySessionFactory, entity: type[object]) -> list:
    return [row for row in session_factory.rows if isinstance(row, entity)]


def _row(
    session_factory: _MemorySessionFactory,
    entity: type[object],
    row_id: UUID,
) -> object:
    row = next(
        (
            candidate
            for candidate in session_factory.rows
            if isinstance(candidate, entity) and getattr(candidate, "id", None) == row_id
        ),
        None,
    )
    assert row is not None
    return row


def _for_update_statement(
    session_factory: _MemorySessionFactory,
    entity: type[object],
) -> object:
    statement = next(
        (
            candidate
            for candidate in session_factory.statements
            if getattr(candidate, "_for_update_arg", None) is not None
            and _statement_targets(candidate, entity)
        ),
        None,
    )
    assert statement is not None
    return statement


def _statement_targets(statement: object, entity: type[object]) -> bool:
    descriptions = getattr(statement, "column_descriptions", [])
    return any(description.get("entity") is entity for description in descriptions)


class _MemorySessionFactory:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.statements: list[object] = []

    def __call__(self) -> _MemorySession:
        return _MemorySession(self)


class _MemorySession:
    def __init__(self, session_factory: _MemorySessionFactory) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> _MemorySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def add(self, row: object) -> None:
        _ensure_persisted(row)
        self.session_factory.rows.append(row)

    async def commit(self) -> None:
        return None

    async def refresh(self, row: object) -> None:
        _ensure_persisted(row)

    async def get(self, entity: type[object], row_id: object) -> object | None:
        return next(
            (
                row
                for row in self.session_factory.rows
                if isinstance(row, entity) and getattr(row, "id", None) == row_id
            ),
            None,
        )

    async def execute(self, statement):  # noqa: ANN001
        self.session_factory.statements.append(statement)
        entities = {
            description.get("entity") for description in statement.column_descriptions
        }
        rows = [
            row
            for row in self.session_factory.rows
            if any(isinstance(row, entity) for entity in entities if isinstance(entity, type))
        ]
        rows = _filter_statement_rows(rows, statement.compile().params)
        return _Result(rows)


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self.rows)


class _ScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows

    def first(self) -> object | None:
        return self.rows[0] if self.rows else None


def _filter_statement_rows(rows: list[object], params: dict[str, object]) -> list[object]:
    for key, value in params.items():
        if key.startswith("tenant_id"):
            rows = [row for row in rows if getattr(row, "tenant_id", None) == value]
        elif key.startswith("id"):
            rows = [row for row in rows if getattr(row, "id", None) == value]
        elif key.startswith("deployment_node_id"):
            rows = [row for row in rows if getattr(row, "deployment_node_id", None) == value]
        elif key.startswith("model_id"):
            rows = [row for row in rows if getattr(row, "model_id", None) == value]
        elif key.startswith("camera_id"):
            rows = [row for row in rows if getattr(row, "camera_id", None) == value]
        elif key.startswith("status"):
            rows = _filter_by_status(rows, value)
    return rows


def _filter_by_status(rows: list[object], value: object) -> list[object]:
    if isinstance(value, (list, tuple, set)):
        status_values = set(value)
        return [row for row in rows if getattr(row, "status", None) in status_values]
    return [row for row in rows if getattr(row, "status", None) == value]


def _ensure_persisted(row: object) -> None:
    if getattr(row, "id", None) is None:
        row.id = uuid4()
    now = datetime.now(UTC)
    if isinstance(row, RuntimeArtifactBuildJob) and row.status is None:
        row.status = ModelLifecycleJobStatus.QUEUED
    if hasattr(row, "created_at") and getattr(row, "created_at", None) is None:
        row.created_at = now
    if hasattr(row, "updated_at") and getattr(row, "updated_at", None) is None:
        row.updated_at = now
