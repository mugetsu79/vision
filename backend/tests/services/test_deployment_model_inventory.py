from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    DeploymentModelAssignmentCreate,
    DeploymentModelInventoryItem,
    DeploymentModelInventoryReport,
)
from argus.compat import UTC
from argus.models.enums import (
    DeploymentInstallStatus,
    DeploymentModelAssignmentStatus,
    DeploymentNodeKind,
    DetectorCapability,
    ModelFormat,
    ModelTask,
)
from argus.models.tables import (
    DeploymentModelAssignment,
    DeploymentModelInventory,
    DeploymentNode,
    Model,
    Tenant,
)
from argus.services.model_lifecycle import ModelLifecycleService


@pytest.mark.asyncio
async def test_assign_model_to_deployment_node_creates_desired_assignment() -> None:
    tenant, model, node = _tenant_model_and_node()
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)

    assignment = await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )

    assert assignment.status is DeploymentModelAssignmentStatus.DESIRED
    assert assignment.model_id == model.id
    assert assignment.deployment_node_id == node.id


@pytest.mark.asyncio
async def test_duplicate_model_assignment_reuses_existing_assignment() -> None:
    tenant, model, node = _tenant_model_and_node()
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)

    first = await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )
    second = await service.assign_model_to_node(
        tenant_id=tenant.id,
        deployment_node_id=node.id,
        payload=DeploymentModelAssignmentCreate(model_id=model.id),
        actor_subject="admin@example.test",
    )

    assert second.id == first.id
    assert len(_rows(session_factory, DeploymentModelAssignment)) == 1


@pytest.mark.asyncio
async def test_inventory_report_upserts_node_assets() -> None:
    tenant, model, node = _tenant_model_and_node()
    first_reported_at = datetime(2026, 6, 8, 9, 0, tzinfo=UTC)
    second_reported_at = first_reported_at + timedelta(minutes=5)
    session_factory = _MemorySessionFactory([tenant, model, node])
    service = ModelLifecycleService(session_factory=session_factory)

    await service.record_model_inventory(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        payload=DeploymentModelInventoryReport(
            items=[_inventory_item(model, reported_at=first_reported_at)]
        ),
    )
    await service.record_model_inventory(
        tenant_id=tenant.id,
        supervisor_id=node.supervisor_id,
        authenticated_node_id=node.id,
        payload=DeploymentModelInventoryReport(
            items=[_inventory_item(model, reported_at=second_reported_at)]
        ),
    )

    rows = _rows(session_factory, DeploymentModelInventory)
    assert len(rows) == 1
    assert rows[0].reported_at == second_reported_at


@pytest.mark.asyncio
async def test_inventory_report_rejects_wrong_authenticated_node() -> None:
    tenant, model, node_a = _tenant_model_and_node(supervisor_id="edge-a")
    node_b = _deployment_node(tenant_id=tenant.id, supervisor_id="edge-b")
    session_factory = _MemorySessionFactory([tenant, model, node_a, node_b])
    service = ModelLifecycleService(session_factory=session_factory)

    with pytest.raises(PermissionError):
        await service.record_model_inventory(
            tenant_id=tenant.id,
            supervisor_id=node_b.supervisor_id,
            authenticated_node_id=node_a.id,
            payload=DeploymentModelInventoryReport(
                items=[_inventory_item(model, reported_at=datetime(2026, 6, 8, 9, 0, tzinfo=UTC))]
            ),
        )


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
        path="/models/yolo26n.onnx",
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


def _inventory_item(model: Model, *, reported_at: datetime) -> DeploymentModelInventoryItem:
    return DeploymentModelInventoryItem(
        asset_kind="model",
        asset_id=model.id,
        local_path="/var/lib/vezor/models/yolo26n.onnx",
        sha256=model.sha256,
        size_bytes=model.size_bytes,
        target_profile="linux-aarch64-nvidia-jetson",
        runtime_versions={"onnxruntime": "1.20.0"},
        reported_at=reported_at,
    )


def _rows(session_factory: _MemorySessionFactory, entity: type[object]) -> list:
    return [row for row in session_factory.rows if isinstance(row, entity)]


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
        compiled = statement.compile()
        rows = _filter_statement_rows(rows, compiled.params)
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
        elif key.startswith("asset_kind"):
            rows = [row for row in rows if getattr(row, "asset_kind", None) == value]
        elif key.startswith("asset_id"):
            rows = [row for row in rows if getattr(row, "asset_id", None) == value]
        elif key.startswith("sha256"):
            rows = [row for row in rows if getattr(row, "sha256", None) == value]
        elif key.startswith("status"):
            rows = [row for row in rows if getattr(row, "status", None) == value]
    return rows


def _ensure_persisted(row: object) -> None:
    if getattr(row, "id", None) is None:
        row.id = uuid4()
    now = datetime.now(UTC)
    if hasattr(row, "created_at") and getattr(row, "created_at", None) is None:
        row.created_at = now
    if hasattr(row, "updated_at") and getattr(row, "updated_at", None) is None:
        row.updated_at = now
