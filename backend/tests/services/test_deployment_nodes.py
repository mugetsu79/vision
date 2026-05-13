from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from argus.api.contracts import SupervisorServiceReportCreate
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DeploymentServiceManager,
    WorkerRuntimeState,
)
from argus.models.tables import EdgeNode, Site, WorkerRuntimeReport
from argus.services.deployment_nodes import DeploymentNodeService


@pytest.mark.asyncio
async def test_records_central_and_edge_deployment_nodes_separately() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    now = datetime(2026, 5, 13, 9, 0, tzinfo=UTC)
    session_factory = _MemorySessionFactory()
    _seed_edge_node_scope(session_factory, tenant_id=tenant_id, edge_node_id=edge_node_id)
    service = DeploymentNodeService(session_factory, now_factory=lambda: now)

    central = await service.record_service_report(
        tenant_id=tenant_id,
        supervisor_id="central-imac-1",
        payload=SupervisorServiceReportCreate(
            node_kind=DeploymentNodeKind.CENTRAL,
            hostname="vezor-central",
            service_manager=DeploymentServiceManager.LAUNCHD,
            service_status="running",
            install_status=DeploymentInstallStatus.HEALTHY,
            credential_status=DeploymentCredentialStatus.ACTIVE,
            version="0.21.0",
            os_name="darwin",
            host_profile="macos-arm64-apple",
            heartbeat_at=now,
        ),
    )
    edge = await service.record_service_report(
        tenant_id=tenant_id,
        supervisor_id="edge-orin-1",
        payload=SupervisorServiceReportCreate(
            node_kind=DeploymentNodeKind.EDGE,
            edge_node_id=edge_node_id,
            hostname="orin-nano-01",
            service_manager=DeploymentServiceManager.SYSTEMD,
            service_status="running",
            install_status=DeploymentInstallStatus.HEALTHY,
            credential_status=DeploymentCredentialStatus.ACTIVE,
            version="0.21.0",
            os_name="linux",
            host_profile="linux-aarch64-nvidia-jetson",
            heartbeat_at=now,
        ),
    )

    nodes = await service.list_nodes(tenant_id=tenant_id)

    assert central.node_kind is DeploymentNodeKind.CENTRAL
    assert central.edge_node_id is None
    assert edge.node_kind is DeploymentNodeKind.EDGE
    assert edge.edge_node_id == edge_node_id
    assert [(node.supervisor_id, node.node_kind) for node in nodes] == [
        ("central-imac-1", DeploymentNodeKind.CENTRAL),
        ("edge-orin-1", DeploymentNodeKind.EDGE),
    ]


@pytest.mark.asyncio
async def test_service_reports_update_install_state_without_worker_runtime_reports() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    edge_node_id = uuid4()
    now = datetime(2026, 5, 13, 9, 5, tzinfo=UTC)
    session_factory = _MemorySessionFactory()
    _seed_edge_node_scope(session_factory, tenant_id=tenant_id, edge_node_id=edge_node_id)
    session_factory.session.add(
        WorkerRuntimeReport(
            tenant_id=tenant_id,
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            assignment_id=None,
            heartbeat_at=now,
            runtime_state=WorkerRuntimeState.RUNNING,
            restart_count=0,
            last_error=None,
            runtime_artifact_id=None,
            scene_contract_hash=None,
        )
    )
    service = DeploymentNodeService(session_factory, now_factory=lambda: now)

    node = await service.record_service_report(
        tenant_id=tenant_id,
        supervisor_id="edge-orin-1",
        payload=SupervisorServiceReportCreate(
            node_kind=DeploymentNodeKind.EDGE,
            edge_node_id=edge_node_id,
            hostname="orin-nano-01",
            service_manager=DeploymentServiceManager.SYSTEMD,
            service_status="running",
            install_status=DeploymentInstallStatus.DEGRADED,
            credential_status=DeploymentCredentialStatus.ACTIVE,
            version="0.21.0",
            os_name="linux",
            host_profile="linux-aarch64-nvidia-jetson",
            heartbeat_at=now,
            diagnostics={"storage": "missing local evidence directory"},
        ),
    )
    runtime_reports = [
        row for row in session_factory.session.rows if isinstance(row, WorkerRuntimeReport)
    ]

    assert node.install_status is DeploymentInstallStatus.DEGRADED
    assert len(runtime_reports) == 1
    assert runtime_reports[0].runtime_state is WorkerRuntimeState.RUNNING
    assert runtime_reports[0].last_error is None


@pytest.mark.asyncio
async def test_stale_service_report_produces_offline_install_status() -> None:
    tenant_id = uuid4()
    heartbeat_at = datetime(2026, 5, 13, 9, 0, tzinfo=UTC)
    service = DeploymentNodeService(
        _MemorySessionFactory(),
        now_factory=lambda: heartbeat_at + timedelta(hours=1),
    )

    recorded = await service.record_service_report(
        tenant_id=tenant_id,
        supervisor_id="central-imac-1",
        payload=SupervisorServiceReportCreate(
            node_kind=DeploymentNodeKind.CENTRAL,
            hostname="vezor-central",
            service_manager=DeploymentServiceManager.LAUNCHD,
            service_status="running",
            install_status=DeploymentInstallStatus.HEALTHY,
            credential_status=DeploymentCredentialStatus.ACTIVE,
            version="0.21.0",
            os_name="darwin",
            host_profile="macos-arm64-apple",
            heartbeat_at=heartbeat_at,
        ),
    )
    nodes = await service.list_nodes(tenant_id=tenant_id)

    assert recorded.install_status is DeploymentInstallStatus.OFFLINE
    assert nodes[0].install_status is DeploymentInstallStatus.OFFLINE
    assert nodes[0].last_service_reported_at == heartbeat_at


@pytest.mark.asyncio
async def test_service_report_diagnostics_are_redacted_recursively() -> None:
    tenant_id = uuid4()
    now = datetime(2026, 5, 13, 9, 10, tzinfo=UTC)
    service = DeploymentNodeService(_MemorySessionFactory(), now_factory=lambda: now)

    node = await service.record_service_report(
        tenant_id=tenant_id,
        supervisor_id="central-imac-1",
        payload=SupervisorServiceReportCreate(
            node_kind=DeploymentNodeKind.CENTRAL,
            hostname="vezor-central",
            service_manager=DeploymentServiceManager.LAUNCHD,
            service_status="running",
            install_status=DeploymentInstallStatus.HEALTHY,
            credential_status=DeploymentCredentialStatus.ACTIVE,
            version="0.21.0",
            os_name="darwin",
            host_profile="macos-arm64-apple",
            heartbeat_at=now,
            diagnostics={
                "pairing_code": "123456",
                "bearer": "bearer-token",
                "jwt": "jwt-token",
                "public_key": "node-key",
                "token": "raw-token",
                "nested": {"api_key": "raw-key", "status": "ok"},
                "items": [{"password": "raw-password"}, {"service": "ready"}],
            },
        ),
    )

    assert node.diagnostics == {
        "pairing_code": "[redacted]",
        "bearer": "[redacted]",
        "jwt": "[redacted]",
        "public_key": "[redacted]",
        "token": "[redacted]",
        "nested": {"api_key": "[redacted]", "status": "ok"},
        "items": [{"password": "[redacted]"}, {"service": "ready"}],
    }


@pytest.mark.asyncio
async def test_edge_service_reports_must_reference_edge_node_in_tenant_scope() -> None:
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    site_id = uuid4()
    edge_node_id = uuid4()
    now = datetime(2026, 5, 13, 9, 20, tzinfo=UTC)
    session_factory = _MemorySessionFactory()
    session_factory.session.add(
        Site(id=site_id, tenant_id=other_tenant_id, name="Other Site", tz="UTC")
    )
    session_factory.session.add(
        EdgeNode(
            id=edge_node_id,
            site_id=site_id,
            hostname="orin-nano-01",
            public_key="public",
            version="0.21.0",
        )
    )
    service = DeploymentNodeService(session_factory, now_factory=lambda: now)

    with pytest.raises(ValueError, match="Edge node is not in tenant scope"):
        await service.record_service_report(
            tenant_id=tenant_id,
            supervisor_id="edge-orin-1",
            payload=SupervisorServiceReportCreate(
                node_kind=DeploymentNodeKind.EDGE,
                edge_node_id=edge_node_id,
                hostname="orin-nano-01",
                service_manager=DeploymentServiceManager.SYSTEMD,
                service_status="running",
                install_status=DeploymentInstallStatus.HEALTHY,
                credential_status=DeploymentCredentialStatus.ACTIVE,
                version="0.21.0",
                os_name="linux",
                host_profile="linux-aarch64-nvidia-jetson",
                heartbeat_at=now,
            ),
        )


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
        supervisor_id = params.get("supervisor_id_1")
        edge_node_id = params.get("id_1")
        entities = {description.get("entity") for description in statement.column_descriptions}
        if EdgeNode in entities:
            site_ids = {
                row.id
                for row in self.rows
                if isinstance(row, Site) and (tenant_id is None or row.tenant_id == tenant_id)
            }
            rows = [
                row
                for row in self.rows
                if isinstance(row, EdgeNode)
                and (edge_node_id is None or row.id == edge_node_id)
                and row.site_id in site_ids
            ]
            return _Result(rows)
        rows = self.rows
        if tenant_id is not None:
            rows = [row for row in rows if getattr(row, "tenant_id", None) == tenant_id]
        if supervisor_id is not None:
            rows = [
                row for row in rows if getattr(row, "supervisor_id", None) == supervisor_id
            ]
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


def _seed_edge_node_scope(
    session_factory: _MemorySessionFactory,
    *,
    tenant_id: object,
    edge_node_id: object,
) -> None:
    site_id = uuid4()
    session_factory.session.add(Site(id=site_id, tenant_id=tenant_id, name="Test Site", tz="UTC"))
    session_factory.session.add(
        EdgeNode(
            id=edge_node_id,
            site_id=site_id,
            hostname="orin-nano-01",
            public_key="public",
            version="0.21.0",
        )
    )
