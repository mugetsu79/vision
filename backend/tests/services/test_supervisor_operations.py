from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from argus.api.contracts import (
    OperationsLifecycleRequestCreate,
    SupervisorRuntimeReportCreate,
    WorkerAssignmentCreate,
)
from argus.models.enums import (
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
    SupervisorMode,
    WorkerRuntimeState,
)
from argus.services.supervisor_operations import (
    SupervisorOperationsService,
    resolve_worker_operations_controls,
)


@pytest.mark.asyncio
async def test_persists_worker_assignment_and_reassignment_records() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_a = uuid4()
    edge_b = uuid4()
    service = SupervisorOperationsService(_MemorySessionFactory())

    first = await service.create_assignment(
        tenant_id=tenant_id,
        payload=WorkerAssignmentCreate(
            camera_id=camera_id,
            edge_node_id=edge_a,
            desired_state="supervised",
        ),
        actor_subject="operator-1",
    )
    second = await service.create_assignment(
        tenant_id=tenant_id,
        payload=WorkerAssignmentCreate(
            camera_id=camera_id,
            edge_node_id=edge_b,
            desired_state="supervised",
        ),
        actor_subject="operator-2",
    )
    assignments = await service.list_assignments(tenant_id=tenant_id)

    assert first.camera_id == camera_id
    assert first.edge_node_id == edge_a
    assert first.active is False
    assert second.camera_id == camera_id
    assert second.edge_node_id == edge_b
    assert second.active is True
    assert second.supersedes_assignment_id == first.id
    assert [assignment.id for assignment in assignments] == [first.id, second.id]


@pytest.mark.asyncio
async def test_records_worker_runtime_report_with_heartbeat_and_runtime_truth() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    runtime_artifact_id = uuid4()
    scene_contract_hash = "a" * 64
    service = SupervisorOperationsService(_MemorySessionFactory())
    assignment = await service.create_assignment(
        tenant_id=tenant_id,
        payload=WorkerAssignmentCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            desired_state="supervised",
        ),
        actor_subject="operator-1",
    )

    report = await service.record_runtime_report(
        tenant_id=tenant_id,
        payload=SupervisorRuntimeReportCreate(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=assignment.id,
            heartbeat_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            runtime_state=WorkerRuntimeState.RUNNING,
            restart_count=3,
            last_error="recovered from stream timeout",
            runtime_artifact_id=runtime_artifact_id,
            scene_contract_hash=scene_contract_hash,
        ),
    )
    latest = await service.latest_runtime_reports_by_camera(
        tenant_id=tenant_id,
        camera_ids=[camera_id],
    )

    assert report.heartbeat_at == datetime(2026, 5, 13, 9, 0, tzinfo=UTC)
    assert report.runtime_state is WorkerRuntimeState.RUNNING
    assert report.restart_count == 3
    assert report.last_error == "recovered from stream timeout"
    assert report.runtime_artifact_id == runtime_artifact_id
    assert report.scene_contract_hash == scene_contract_hash
    assert latest[camera_id].id == report.id


@pytest.mark.asyncio
async def test_creates_lifecycle_requests_without_running_process_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    service = SupervisorOperationsService(_MemorySessionFactory())
    monkeypatch.setattr("subprocess.run", _fail_if_called)

    requests = [
        await service.create_lifecycle_request(
            tenant_id=tenant_id,
            payload=OperationsLifecycleRequestCreate(camera_id=camera_id, action=action),
            actor_subject="operator-1",
        )
        for action in (
            OperationsLifecycleAction.START,
            OperationsLifecycleAction.STOP,
            OperationsLifecycleAction.RESTART,
            OperationsLifecycleAction.DRAIN,
        )
    ]

    assert [request.action for request in requests] == [
        OperationsLifecycleAction.START,
        OperationsLifecycleAction.STOP,
        OperationsLifecycleAction.RESTART,
        OperationsLifecycleAction.DRAIN,
    ]
    assert {request.status for request in requests} == {
        OperationsLifecycleStatus.REQUESTED
    }


def test_resolved_operations_mode_controls_lifecycle_owner_and_actions() -> None:
    manual = resolve_worker_operations_controls(
        {
            "lifecycle_owner": "manual",
            "supervisor_mode": "disabled",
            "restart_policy": "never",
        },
        assigned_edge_node_id=None,
        supervisor_healthy=False,
    )
    disabled_supervisor = resolve_worker_operations_controls(
        {
            "lifecycle_owner": "edge_supervisor",
            "supervisor_mode": "disabled",
            "restart_policy": "on_failure",
        },
        assigned_edge_node_id=uuid4(),
        supervisor_healthy=True,
    )
    edge_supervisor = resolve_worker_operations_controls(
        {
            "lifecycle_owner": "edge_supervisor",
            "supervisor_mode": "polling",
            "restart_policy": "always",
        },
        assigned_edge_node_id=uuid4(),
        supervisor_healthy=True,
    )

    assert manual.lifecycle_owner == "manual"
    assert manual.supervisor_mode is SupervisorMode.DISABLED
    assert manual.allowed_actions == []
    assert manual.detail == "Manual mode requires operator-started worker processes."
    assert disabled_supervisor.lifecycle_owner == "edge_supervisor"
    assert disabled_supervisor.allowed_actions == []
    assert disabled_supervisor.detail == "Supervisor mode is disabled."
    assert edge_supervisor.lifecycle_owner == "edge_supervisor"
    assert edge_supervisor.supervisor_mode is SupervisorMode.POLLING
    assert edge_supervisor.restart_policy == "always"
    assert edge_supervisor.allowed_actions == [
        OperationsLifecycleAction.START,
        OperationsLifecycleAction.STOP,
        OperationsLifecycleAction.RESTART,
        OperationsLifecycleAction.DRAIN,
    ]


def test_missing_or_stale_runtime_reports_render_honest_states() -> None:
    service = SupervisorOperationsService(_MemorySessionFactory())
    now = datetime(2026, 5, 13, 10, 0, tzinfo=UTC)

    assert service.runtime_status_for_report(None, now=now) == "not_reported"
    assert (
        service.runtime_status_for_report(
            _ReportLike(heartbeat_at=now - timedelta(minutes=20)),
            now=now,
        )
        == "unknown"
    )


def _fail_if_called(*args, **kwargs) -> None:  # noqa: ANN002, ANN003
    raise AssertionError("Lifecycle requests must not shell out from the API process.")


class _ReportLike:
    def __init__(self, heartbeat_at: datetime) -> None:
        self.heartbeat_at = heartbeat_at
        self.runtime_state = WorkerRuntimeState.RUNNING


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[object]:
        return self.rows


class _MemorySession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    async def __aenter__(self) -> _MemorySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _Result:  # noqa: ANN001
        params = statement.compile().params
        tenant_id = params.get("tenant_id_1")
        camera_id = params.get("camera_id_1")
        rows = self.rows
        if tenant_id is not None:
            rows = [row for row in rows if getattr(row, "tenant_id", None) == tenant_id]
        if camera_id is not None:
            rows = [row for row in rows if getattr(row, "camera_id", None) == camera_id]
        return _Result(rows)

    def add(self, row: object) -> None:
        self.rows.append(row)

    async def commit(self) -> None:
        return None

    async def refresh(self, row: object) -> None:
        return None


class _MemorySessionFactory:
    def __init__(self) -> None:
        self.session = _MemorySession()

    def __call__(self) -> _MemorySession:
        return self.session
