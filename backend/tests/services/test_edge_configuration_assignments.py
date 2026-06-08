from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import EdgeConfigurationUpdate
from argus.compat import UTC
from argus.models.enums import (
    DeploymentInstallStatus,
    DeploymentNodeKind,
    EdgeConfigurationApplyStatus,
)
from argus.models.tables import DeploymentNode, Tenant
from argus.services.model_lifecycle import ModelLifecycleService


@pytest.mark.asyncio
async def test_put_edge_configuration_increments_revision() -> None:
    tenant, node = _tenant_and_node()
    session_factory = _MemorySessionFactory([tenant, node])
    service = ModelLifecycleService(session_factory=session_factory)

    first = await service.update_edge_configuration(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=EdgeConfigurationUpdate(
            desired_config={"model_store_path": "/var/lib/vezor/models"}
        ),
        actor_subject="admin@example.test",
    )
    second = await service.update_edge_configuration(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=EdgeConfigurationUpdate(
            desired_config={"model_store_path": "/srv/vezor/models"}
        ),
        actor_subject="admin@example.test",
    )

    assert first.revision == 1
    assert second.revision == 2
    assert second.apply_status is EdgeConfigurationApplyStatus.PENDING
    assert second.desired_config["model_store_path"] == "/srv/vezor/models"


@pytest.mark.asyncio
async def test_supervisor_fetches_only_own_edge_configuration() -> None:
    tenant, node_a = _tenant_and_node(supervisor_id="edge-a")
    node_b = _deployment_node(tenant_id=tenant.id, supervisor_id="edge-b")
    session_factory = _MemorySessionFactory([tenant, node_a, node_b])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.update_edge_configuration(
        tenant_id=tenant.id,
        deployment_node_id=node_a.id,
        payload=EdgeConfigurationUpdate(
            desired_config={"model_store_path": "/nodes/edge-a/models"}
        ),
        actor_subject="admin@example.test",
    )
    await service.update_edge_configuration(
        tenant_id=tenant.id,
        deployment_node_id=node_b.id,
        payload=EdgeConfigurationUpdate(
            desired_config={"model_store_path": "/nodes/edge-b/models"}
        ),
        actor_subject="admin@example.test",
    )

    configuration = await service.get_supervisor_edge_configuration(
        tenant_id=tenant.id,
        supervisor_id=node_a.supervisor_id,
        authenticated_node_id=node_a.id,
    )

    assert configuration.deployment_node_id == node_a.id
    assert configuration.desired_config == {"model_store_path": "/nodes/edge-a/models"}


@pytest.mark.asyncio
async def test_apply_report_marks_revision_applied() -> None:
    tenant, node = _tenant_and_node()
    session_factory = _MemorySessionFactory([tenant, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.update_edge_configuration(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=EdgeConfigurationUpdate(
            desired_config={"model_store_path": "/var/lib/vezor/models"}
        ),
        actor_subject="admin@example.test",
    )
    await service.update_edge_configuration(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=EdgeConfigurationUpdate(
            desired_config={"model_store_path": "/srv/vezor/models"}
        ),
        actor_subject="admin@example.test",
    )

    report = await service.record_edge_configuration_apply_report(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        revision=2,
        status=EdgeConfigurationApplyStatus.APPLIED,
        error=None,
    )

    assert report.applied_revision == 2
    assert report.apply_status is EdgeConfigurationApplyStatus.APPLIED
    assert report.error is None
    assert report.last_applied_at is not None


@pytest.mark.asyncio
async def test_apply_report_with_error_marks_failed() -> None:
    tenant, node = _tenant_and_node()
    session_factory = _MemorySessionFactory([tenant, node])
    service = ModelLifecycleService(session_factory=session_factory)
    await service.update_edge_configuration(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=EdgeConfigurationUpdate(
            desired_config={"model_store_path": "/var/lib/vezor/models"}
        ),
        actor_subject="admin@example.test",
    )
    await service.update_edge_configuration(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=EdgeConfigurationUpdate(
            desired_config={"model_store_path": "/srv/vezor/models"}
        ),
        actor_subject="admin@example.test",
    )

    report = await service.record_edge_configuration_apply_report(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        revision=2,
        status=EdgeConfigurationApplyStatus.FAILED,
        error="Unsupported edge configuration key: shell_command.",
    )

    assert report.revision == 2
    assert report.apply_status is EdgeConfigurationApplyStatus.FAILED
    assert report.error == "Unsupported edge configuration key: shell_command."


def _tenant_and_node(
    *,
    supervisor_id: str = "edge-orin-1",
) -> tuple[Tenant, DeploymentNode]:
    tenant = Tenant(id=uuid4(), name="Vezor Pilot", slug=f"tenant-{uuid4().hex[:8]}")
    return tenant, _deployment_node(tenant_id=tenant.id, supervisor_id=supervisor_id)


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
        elif key.startswith("supervisor_id"):
            rows = [row for row in rows if getattr(row, "supervisor_id", None) == value]
    return rows


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
