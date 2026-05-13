from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from argus.api.contracts import (
    NodePairingClaim,
    NodePairingSessionCreate,
    SupervisorServiceReportCreate,
)
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DeploymentServiceManager,
    WorkerRuntimeState,
)
from argus.models.tables import (
    DeploymentCredentialEvent,
    DeploymentNode,
    EdgeNode,
    NodePairingSession,
    Site,
    SupervisorNodeCredential,
    Tenant,
    WorkerRuntimeReport,
)
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
async def test_pairing_session_stores_only_hash_and_claim_returns_credential_once() -> None:
    tenant_id = uuid4()
    now = datetime(2026, 5, 13, 9, 15, tzinfo=UTC)
    service = DeploymentNodeService(_MemorySessionFactory(), now_factory=lambda: now)

    created = await service.create_pairing_session(
        tenant_id=tenant_id,
        payload=NodePairingSessionCreate(
            node_kind=DeploymentNodeKind.CENTRAL,
            hostname="vezor-central",
            requested_ttl_seconds=300,
        ),
        actor_subject="admin-1",
    )
    stored_sessions = [
        row
        for row in service.session_factory.session.rows
        if isinstance(row, NodePairingSession)
    ]
    claimed = await service.claim_pairing_session(
        tenant_id=tenant_id,
        session_id=created.id,
        payload=NodePairingClaim(
            pairing_code=created.pairing_code,
            supervisor_id="central-imac-1",
            hostname="vezor-central",
        ),
    )

    assert created.pairing_code
    assert stored_sessions[0].pairing_code_hash != created.pairing_code
    assert not any(
        getattr(row, "pairing_code", None) == created.pairing_code
        for row in service.session_factory.session.rows
    )
    assert claimed.credential_material
    assert claimed.credential_material != claimed.credential_hash
    assert claimed.node.supervisor_id == "central-imac-1"
    assert not any(
        getattr(row, "credential_material", None) == claimed.credential_material
        for row in service.session_factory.session.rows
    )
    credential_rows = [
        row
        for row in service.session_factory.session.rows
        if isinstance(row, SupervisorNodeCredential)
    ]
    assert credential_rows[0].credential_hash == claimed.credential_hash
    assert credential_rows[0].encrypted_credential is None
    assert credential_rows[0].status is DeploymentCredentialStatus.ACTIVE

    with pytest.raises(ValueError, match="already consumed"):
        await service.claim_pairing_session(
            tenant_id=tenant_id,
            session_id=created.id,
            payload=NodePairingClaim(
                pairing_code=created.pairing_code,
                supervisor_id="central-imac-1",
                hostname="vezor-central",
            ),
        )


@pytest.mark.asyncio
async def test_pairing_code_expires_and_wrong_code_fails() -> None:
    tenant_id = uuid4()
    now = datetime(2026, 5, 13, 9, 15, tzinfo=UTC)
    later = now + timedelta(minutes=6)
    service = DeploymentNodeService(_MemorySessionFactory(), now_factory=lambda: now)

    created = await service.create_pairing_session(
        tenant_id=tenant_id,
        payload=NodePairingSessionCreate(
            node_kind=DeploymentNodeKind.CENTRAL,
            hostname="vezor-central",
            requested_ttl_seconds=300,
        ),
        actor_subject="admin-1",
    )

    with pytest.raises(ValueError, match="Invalid pairing code"):
        await service.claim_pairing_session(
            tenant_id=tenant_id,
            session_id=created.id,
            payload=NodePairingClaim(
                pairing_code="wrong-code",
                supervisor_id="central-imac-1",
                hostname="vezor-central",
            ),
        )

    service.now_factory = lambda: later
    with pytest.raises(ValueError, match="expired"):
        await service.claim_pairing_session(
            tenant_id=tenant_id,
            session_id=created.id,
            payload=NodePairingClaim(
                pairing_code=created.pairing_code,
                supervisor_id="central-imac-1",
                hostname="vezor-central",
            ),
        )


@pytest.mark.asyncio
async def test_revoking_node_credential_appends_event_and_disables_validation() -> None:
    tenant_id = uuid4()
    now = datetime(2026, 5, 13, 9, 15, tzinfo=UTC)
    session_factory = _MemorySessionFactory()
    session_factory.session.add(Tenant(id=tenant_id, name="Argus Dev", slug="argus-dev"))
    service = DeploymentNodeService(session_factory, now_factory=lambda: now)
    created = await service.create_pairing_session(
        tenant_id=tenant_id,
        payload=NodePairingSessionCreate(
            node_kind=DeploymentNodeKind.CENTRAL,
            hostname="vezor-central",
            requested_ttl_seconds=300,
        ),
        actor_subject="admin-1",
    )
    claimed = await service.claim_pairing_session(
        tenant_id=tenant_id,
        session_id=created.id,
        payload=NodePairingClaim(
            pairing_code=created.pairing_code,
            supervisor_id="central-imac-1",
            hostname="vezor-central",
        ),
    )

    assert await service.validate_supervisor_credential(
        tenant_id=tenant_id,
        supervisor_id="central-imac-1",
        credential_material=claimed.credential_material,
    )
    tenant_context = await service.authenticate_supervisor_credential(
        credential_material=claimed.credential_material,
        supervisor_id="central-imac-1",
    )
    assert tenant_context.tenant_id == tenant_id
    assert tenant_context.user.subject == "supervisor:central-imac-1"

    revoked = await service.revoke_node_credentials(
        tenant_id=tenant_id,
        node_id=claimed.node.id,
        actor_subject="admin-1",
    )

    assert revoked.revoked_credentials == 1
    assert not await service.validate_supervisor_credential(
        tenant_id=tenant_id,
        supervisor_id="central-imac-1",
        credential_material=claimed.credential_material,
    )
    events = [
        row
        for row in service.session_factory.session.rows
        if isinstance(row, DeploymentCredentialEvent)
    ]
    assert [event.event_type for event in events] == ["credential.issued", "credential.revoked"]
    with pytest.raises(ValueError, match="Invalid supervisor credential"):
        await service.authenticate_supervisor_credential(
            credential_material=claimed.credential_material,
            supervisor_id="central-imac-1",
        )


@pytest.mark.asyncio
async def test_node_credential_service_report_cannot_change_node_shape() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    now = datetime(2026, 5, 13, 9, 15, tzinfo=UTC)
    session_factory = _MemorySessionFactory()
    _seed_edge_node_scope(session_factory, tenant_id=tenant_id, edge_node_id=edge_node_id)
    service = DeploymentNodeService(session_factory, now_factory=lambda: now)
    created = await service.create_pairing_session(
        tenant_id=tenant_id,
        payload=NodePairingSessionCreate(
            node_kind=DeploymentNodeKind.CENTRAL,
            hostname="vezor-central",
            requested_ttl_seconds=300,
        ),
        actor_subject="admin-1",
    )
    claimed = await service.claim_pairing_session(
        session_id=created.id,
        payload=NodePairingClaim(
            pairing_code=created.pairing_code,
            supervisor_id="central-imac-1",
            hostname="vezor-central",
        ),
    )

    with pytest.raises(ValueError, match="credential is not scoped"):
        await service.record_service_report(
            tenant_id=tenant_id,
            supervisor_id="central-imac-1",
            authenticated_node_id=claimed.node.id,
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
        session_id = params.get("id_1")
        supervisor_id = params.get("supervisor_id_1")
        deployment_node_id = params.get("deployment_node_id_1") or session_id
        edge_node_id = params.get("id_1")
        entities = {description.get("entity") for description in statement.column_descriptions}
        model_entities = {entity for entity in entities if isinstance(entity, type)}
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
        if model_entities:
            rows = [
                row
                for row in rows
                if any(isinstance(row, entity) for entity in model_entities)
            ]
        if session_id is not None and (
            DeploymentNode in entities or NodePairingSession in entities
        ):
            rows = [row for row in rows if getattr(row, "id", None) == session_id]
        if deployment_node_id is not None and SupervisorNodeCredential in entities:
            rows = [
                row
                for row in rows
                if getattr(row, "deployment_node_id", None) == deployment_node_id
            ]
        if deployment_node_id is not None and DeploymentCredentialEvent in entities:
            rows = [
                row
                for row in rows
                if getattr(row, "deployment_node_id", None) == deployment_node_id
            ]
        if supervisor_id is not None:
            rows = [
                row for row in rows if getattr(row, "supervisor_id", None) == supervisor_id
            ]
        return _Result(rows)

    def add(self, row: object) -> None:
        self.rows.append(row)

    async def get(self, entity: type[object], row_id: object) -> object | None:
        return next(
            (
                row
                for row in self.rows
                if isinstance(row, entity) and getattr(row, "id", None) == row_id
            ),
            None,
        )

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
