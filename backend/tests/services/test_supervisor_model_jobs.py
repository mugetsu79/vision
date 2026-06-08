from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    DeploymentModelAssignmentCreate,
    SupervisorModelJobComplete,
    SupervisorModelJobEventCreate,
)
from argus.compat import UTC
from argus.models.enums import (
    DeploymentInstallStatus,
    DeploymentModelAssignmentStatus,
    DeploymentNodeKind,
    DetectorCapability,
    ModelFormat,
    ModelLifecycleJobStatus,
    ModelTask,
)
from argus.models.tables import (
    DeploymentModelAssignment,
    DeploymentModelSyncJob,
    DeploymentNode,
    Model,
    SupervisorModelJobEvent,
    Tenant,
)
from argus.services.model_lifecycle import ModelLifecycleService


@pytest.mark.asyncio
async def test_create_model_sync_job_for_assigned_model_sets_assignment_syncing() -> None:
    tenant, model, node = _tenant_model_and_node()
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    assignment = await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(
            model_id=model.id,
            desired_path="/var/lib/vezor/models/yolo26n.onnx",
        ),
        actor_subject="admin@example.test",
    )

    job = await service.create_model_sync_job(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        actor_subject="admin@example.test",
    )

    assignment_row = _row(session_factory, DeploymentModelAssignment, assignment.id)
    assert job.status is ModelLifecycleJobStatus.QUEUED
    assert job.assignment_id == assignment.id
    assert job.payload == {
        "job_type": "model_sync",
        "schema_version": 1,
        "deployment_node_id": str(node.id),
        "model_id": str(model.id),
        "model_name": "YOLO26n COCO",
        "source_path": "models/yolo26n.onnx",
        "expected_sha256": "a" * 64,
        "size_bytes": 12_345,
        "target_path": "/var/lib/vezor/models/yolo26n.onnx",
    }
    assert assignment_row.status is DeploymentModelAssignmentStatus.SYNCING
    assert assignment_row.last_sync_job_id == job.id


@pytest.mark.asyncio
async def test_poll_model_jobs_returns_only_jobs_for_authenticated_node() -> None:
    tenant, model, node_a = _tenant_model_and_node(supervisor_id="edge-a")
    node_b = _deployment_node(tenant_id=tenant.id, supervisor_id="edge-b")
    session_factory = _MemorySessionFactory([tenant, model, node_a, node_b])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node_a.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node_b.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    node_a_job = await service.create_model_sync_job(
        tenant_id=tenant.id,
        deployment_node_id=node_a.id,
        actor_subject="admin@example.test",
    )
    node_b_job = await service.create_model_sync_job(
        tenant_id=tenant.id,
        deployment_node_id=node_b.id,
        actor_subject="admin@example.test",
    )

    jobs = await service.poll_supervisor_model_jobs(
        tenant_id=tenant.id,
        supervisor_id=node_a.supervisor_id,
        authenticated_node_id=node_a.id,
        limit=10,
    )

    claimed_job = _row(session_factory, DeploymentModelSyncJob, node_a_job.id)
    other_job = _row(session_factory, DeploymentModelSyncJob, node_b_job.id)
    assert [job.id for job in jobs] == [node_a_job.id]
    assert claimed_job.status is ModelLifecycleJobStatus.ACCEPTED
    assert claimed_job.claimed_by_supervisor_id == node_a.supervisor_id
    assert claimed_job.claimed_at is not None
    assert other_job.status is ModelLifecycleJobStatus.QUEUED
    assert other_job.claimed_by_supervisor_id is None


@pytest.mark.asyncio
async def test_poll_model_jobs_keeps_accepted_jobs_visible_after_claim() -> None:
    tenant, model, node = _tenant_model_and_node()
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_model_sync_job(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
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

    assert [polled_job.id for polled_job in first_poll] == [job.id]
    assert first_poll[0].status is ModelLifecycleJobStatus.ACCEPTED
    assert [polled_job.id for polled_job in second_poll] == [job.id]
    assert second_poll[0].status is ModelLifecycleJobStatus.ACCEPTED


@pytest.mark.asyncio
async def test_job_event_updates_status_and_records_event() -> None:
    tenant, model, node = _tenant_model_and_node()
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    job = await service.create_model_sync_job(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        actor_subject="admin@example.test",
    )

    updated = await service.record_supervisor_model_job_event(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        job_id=job.id,
        payload=SupervisorModelJobEventCreate(
            job_kind="model_sync",
            status=ModelLifecycleJobStatus.RUNNING,
            message="copy started",
            payload={"progress": 0.25},
        ),
    )

    event_rows = _rows(session_factory, SupervisorModelJobEvent)
    job_row = _row(session_factory, DeploymentModelSyncJob, job.id)
    assert updated.status is ModelLifecycleJobStatus.RUNNING
    assert job_row.status is ModelLifecycleJobStatus.RUNNING
    assert len(event_rows) == 1
    assert event_rows[0].job_id == job.id
    assert event_rows[0].deployment_node_id == node.id
    assert event_rows[0].status is ModelLifecycleJobStatus.RUNNING
    assert event_rows[0].message == "copy started"
    assert event_rows[0].payload == {"progress": 0.25}


@pytest.mark.asyncio
async def test_complete_model_sync_job_marks_assignment_synced() -> None:
    tenant, model, node = _tenant_model_and_node()
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    assignment = await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(
            model_id=model.id,
            desired_path="/var/lib/vezor/models/yolo26n.onnx",
        ),
        actor_subject="admin@example.test",
    )
    job = await service.create_model_sync_job(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        actor_subject="admin@example.test",
    )

    completed = await service.complete_supervisor_model_job(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        job_id=job.id,
        payload=SupervisorModelJobComplete(
            status=ModelLifecycleJobStatus.SUCCEEDED,
            local_path="/var/lib/vezor/models/yolo26n.onnx",
            sha256=model.sha256,
            size_bytes=model.size_bytes,
        ),
    )

    assignment_row = _row(session_factory, DeploymentModelAssignment, assignment.id)
    job_row = _row(session_factory, DeploymentModelSyncJob, job.id)
    assert completed.status is ModelLifecycleJobStatus.SUCCEEDED
    assert job_row.status is ModelLifecycleJobStatus.SUCCEEDED
    assert job_row.completed_at is not None
    assert assignment_row.status is DeploymentModelAssignmentStatus.SYNCED
    assert assignment_row.error is None


@pytest.mark.asyncio
async def test_complete_model_sync_job_with_wrong_path_does_not_sync_assignment() -> None:
    tenant, model, node = _tenant_model_and_node()
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)
    assignment = await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(
            model_id=model.id,
            desired_path="/var/lib/vezor/models/yolo26n.onnx",
        ),
        actor_subject="admin@example.test",
    )
    job = await service.create_model_sync_job(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        actor_subject="admin@example.test",
    )

    completed = await service.complete_supervisor_model_job(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        job_id=job.id,
        payload=SupervisorModelJobComplete(
            status=ModelLifecycleJobStatus.SUCCEEDED,
            local_path="/tmp/yolo26n.onnx",
            sha256=model.sha256,
            size_bytes=model.size_bytes,
        ),
    )

    assignment_row = _row(session_factory, DeploymentModelAssignment, assignment.id)
    assert completed.status is ModelLifecycleJobStatus.SUCCEEDED
    assert assignment_row.status is DeploymentModelAssignmentStatus.SYNCING


def _tenant_model_and_node(
    *,
    supervisor_id: str = "edge-orin-1",
) -> tuple[Tenant, Model, DeploymentNode]:
    tenant = Tenant(id=uuid4(), name="Vezor Pilot", slug=f"tenant-{uuid4().hex[:8]}")
    model = Model(
        id=uuid4(),
        name="YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path="models/yolo26n.onnx",
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config={},
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=12_345,
        license="AGPL-3.0",
    )
    node = _deployment_node(tenant_id=tenant.id, supervisor_id=supervisor_id)
    return tenant, model, node


def _deployment_node(*, tenant_id: UUID, supervisor_id: str) -> DeploymentNode:
    return DeploymentNode(
        id=uuid4(),
        tenant_id=tenant_id,
        edge_node_id=uuid4(),
        supervisor_id=supervisor_id,
        node_kind=DeploymentNodeKind.EDGE,
        hostname=f"{supervisor_id}.local",
        install_status=DeploymentInstallStatus.HEALTHY,
        diagnostics={},
    )


def _rows(session_factory: _MemorySessionFactory, entity: type[object]) -> list:
    return [row for row in session_factory.rows if isinstance(row, entity)]


def _row(session_factory: _MemorySessionFactory, entity: type[object], row_id: UUID) -> object:
    row = next(
        (
            row
            for row in session_factory.rows
            if isinstance(row, entity) and getattr(row, "id", None) == row_id
        ),
        None,
    )
    assert row is not None
    return row


class _MemorySessionFactory:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

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
        entities = {
            description.get("entity") for description in statement.column_descriptions
        }
        rows = [
            row
            for row in self.session_factory.rows
            if any(isinstance(row, entity) for entity in entities if isinstance(entity, type))
        ]
        rows = _filter_statement_rows(rows, statement.compile().params)
        rows = _apply_statement_limit(rows, statement)
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
        elif key.startswith("supervisor_id"):
            rows = [row for row in rows if getattr(row, "supervisor_id", None) == value]
        elif key.startswith("status"):
            rows = _filter_by_status(rows, value)
        elif key.startswith("job_id"):
            rows = [row for row in rows if getattr(row, "job_id", None) == value]
    return rows


def _filter_by_status(rows: list[object], value: object) -> list[object]:
    if isinstance(value, (list, tuple, set, frozenset)):
        status_values = set(value)
        return [row for row in rows if getattr(row, "status", None) in status_values]
    return [row for row in rows if getattr(row, "status", None) == value]


def _apply_statement_limit(rows: list[object], statement) -> list[object]:  # noqa: ANN001
    limit_clause = getattr(statement, "_limit_clause", None)
    limit_value = getattr(limit_clause, "value", None)
    if not isinstance(limit_value, int):
        return rows
    return rows[:limit_value]


def _ensure_persisted(row: object) -> None:
    if getattr(row, "id", None) is None:
        row.id = uuid4()
    now = datetime.now(UTC)
    if hasattr(row, "created_at") and getattr(row, "created_at", None) is None:
        row.created_at = now
    if hasattr(row, "updated_at") and getattr(row, "updated_at", None) is None:
        row.updated_at = now
