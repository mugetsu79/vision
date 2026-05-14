from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    MasterBootstrapComplete,
    NodePairingClaim,
    NodePairingSessionCreate,
    SupervisorServiceReportCreate,
)
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DeploymentServiceManager,
    RoleEnum,
    WorkerRuntimeState,
)
from argus.models.tables import (
    DeploymentCredentialEvent,
    DeploymentNode,
    EdgeNode,
    EdgeNodeHardwareReport,
    MasterBootstrapSession,
    NodePairingSession,
    OperationsLifecycleRequest,
    Site,
    SupervisorNodeCredential,
    Tenant,
    User,
    WorkerModelAdmissionReport,
    WorkerRuntimeReport,
)
from argus.services.deployment_nodes import DeploymentNodeService


@pytest.mark.asyncio
async def test_fresh_master_bootstrap_status_requires_first_run_without_exposing_token() -> None:
    now = datetime(2026, 5, 14, 8, 0, tzinfo=UTC)
    service = DeploymentNodeService(_MemorySessionFactory(), now_factory=lambda: now)

    status = await service.get_master_bootstrap_status()

    assert status.first_run_required is True
    assert status.has_active_local_token is False
    assert status.active_token_expires_at is None
    assert "vzboot_" not in str(status.model_dump(mode="json"))


@pytest.mark.asyncio
async def test_rotating_master_bootstrap_token_stores_only_hash() -> None:
    now = datetime(2026, 5, 14, 8, 5, tzinfo=UTC)
    service = DeploymentNodeService(_MemorySessionFactory(), now_factory=lambda: now)

    rotated = await service.rotate_local_bootstrap_token(actor_subject="local-installer")
    status = await service.get_master_bootstrap_status()
    sessions = [
        row
        for row in service.session_factory.session.rows
        if isinstance(row, MasterBootstrapSession)
    ]

    assert rotated.bootstrap_token.startswith("vzboot_")
    assert rotated.expires_at > now
    assert status.has_active_local_token is True
    assert status.active_token_expires_at == rotated.expires_at
    assert sessions[0].token_hash != rotated.bootstrap_token
    assert sessions[0].status == "pending"
    assert not any(
        getattr(row, "bootstrap_token", None) == rotated.bootstrap_token
        for row in service.session_factory.session.rows
    )


@pytest.mark.asyncio
async def test_master_bootstrap_complete_creates_initial_tenant_admin_node() -> None:
    now = datetime(2026, 5, 14, 8, 10, tzinfo=UTC)
    service = DeploymentNodeService(_MemorySessionFactory(), now_factory=lambda: now)
    rotated = await service.rotate_local_bootstrap_token(actor_subject="local-installer")

    completed = await service.complete_master_bootstrap(
        MasterBootstrapComplete(
            bootstrap_token=rotated.bootstrap_token,
            tenant_name="Vezor Pilot",
            tenant_slug="vezor-pilot",
            admin_email="admin@vezor.local",
            admin_password="not-persisted-password",
            central_node_name="macbook-pro-master",
            central_supervisor_id="central-macbook-pro",
        )
    )

    rows = service.session_factory.session.rows
    tenants = [row for row in rows if isinstance(row, Tenant)]
    users = [row for row in rows if isinstance(row, User)]
    nodes = [row for row in rows if isinstance(row, DeploymentNode)]
    sessions = [row for row in rows if isinstance(row, MasterBootstrapSession)]
    serialized_rows = str([row.__dict__ for row in rows])

    assert completed.first_run_required is False
    assert completed.tenant_slug == "vezor-pilot"
    assert completed.admin_subject == "bootstrap:admin@vezor.local"
    assert completed.central_node.supervisor_id == "central-macbook-pro"
    assert tenants[0].name == "Vezor Pilot"
    assert users[0].email == "admin@vezor.local"
    assert users[0].role is RoleEnum.ADMIN
    assert nodes[0].node_kind is DeploymentNodeKind.CENTRAL
    assert nodes[0].install_status is DeploymentInstallStatus.INSTALLED
    assert sessions[0].status == "consumed"
    assert sessions[0].tenant_id == tenants[0].id
    assert sessions[0].consumed_at == now
    assert rotated.bootstrap_token not in serialized_rows
    assert "not-persisted-password" not in serialized_rows

    with pytest.raises(ValueError, match="already consumed|Invalid bootstrap token"):
        await service.complete_master_bootstrap(
            MasterBootstrapComplete(
                bootstrap_token=rotated.bootstrap_token,
                tenant_name="Vezor Pilot",
                tenant_slug="vezor-pilot",
                admin_email="admin@vezor.local",
                admin_password="not-persisted-password",
                central_node_name="macbook-pro-master",
                central_supervisor_id="central-macbook-pro",
            )
        )


@pytest.mark.asyncio
async def test_master_bootstrap_complete_provisions_oidc_admin_identity() -> None:
    now = datetime(2026, 5, 14, 8, 10, tzinfo=UTC)
    provisioner = _RecordingIdentityProvisioner(subject="keycloak-user-123")
    service = DeploymentNodeService(
        _MemorySessionFactory(),
        now_factory=lambda: now,
        identity_provisioner=provisioner,
    )
    rotated = await service.rotate_local_bootstrap_token(actor_subject="local-installer")

    completed = await service.complete_master_bootstrap(
        MasterBootstrapComplete(
            bootstrap_token=rotated.bootstrap_token,
            tenant_name="Vezor Pilot",
            tenant_slug="vezor-pilot",
            admin_email="admin@vezor.local",
            admin_password="not-persisted-password",
            central_node_name="macbook-pro-master",
        )
    )

    rows = service.session_factory.session.rows
    users = [row for row in rows if isinstance(row, User)]
    serialized_rows = str([row.__dict__ for row in rows])

    assert completed.admin_subject == "keycloak-user-123"
    assert users[0].oidc_sub == "keycloak-user-123"
    assert provisioner.calls == [
        {
            "tenant_id": users[0].tenant_id,
            "tenant_name": "Vezor Pilot",
            "tenant_slug": "vezor-pilot",
            "admin_email": "admin@vezor.local",
            "admin_password": "not-persisted-password",
        }
    ]
    assert "not-persisted-password" not in serialized_rows


@pytest.mark.asyncio
async def test_master_bootstrap_repairs_preexisting_placeholder_admin_identity() -> None:
    now = datetime(2026, 5, 14, 8, 10, tzinfo=UTC)
    session_factory = _MemorySessionFactory()
    service_without_identity = DeploymentNodeService(
        session_factory,
        now_factory=lambda: now,
    )
    initial = await service_without_identity.rotate_local_bootstrap_token(
        actor_subject="local-installer"
    )
    await service_without_identity.complete_master_bootstrap(
        MasterBootstrapComplete(
            bootstrap_token=initial.bootstrap_token,
            tenant_name="Vezor Pilot",
            tenant_slug="vezor-pilot",
            admin_email="admin@vezor.local",
            admin_password="old-password",
            central_node_name="macbook-pro-master",
        )
    )

    provisioner = _RecordingIdentityProvisioner(subject="keycloak-user-456")
    service = DeploymentNodeService(
        session_factory,
        now_factory=lambda: now,
        identity_provisioner=provisioner,
    )
    status = await service.get_master_bootstrap_status()
    rotated = await service.rotate_local_bootstrap_token(actor_subject="local-repair")

    repaired = await service.complete_master_bootstrap(
        MasterBootstrapComplete(
            bootstrap_token=rotated.bootstrap_token,
            tenant_name="Vezor Pilot",
            tenant_slug="vezor-pilot",
            admin_email="admin@vezor.local",
            admin_password="new-password",
            central_node_name="macbook-pro-master",
        )
    )

    rows = service.session_factory.session.rows
    tenants = [row for row in rows if isinstance(row, Tenant)]
    users = [row for row in rows if isinstance(row, User)]
    nodes = [row for row in rows if isinstance(row, DeploymentNode)]

    assert status.first_run_required is True
    assert repaired.admin_subject == "keycloak-user-456"
    assert len(tenants) == 1
    assert len(users) == 1
    assert len(nodes) == 1
    assert users[0].oidc_sub == "keycloak-user-456"
    assert provisioner.calls[0]["admin_password"] == "new-password"


@pytest.mark.asyncio
async def test_master_bootstrap_complete_rejects_missing_or_wrong_token() -> None:
    service = DeploymentNodeService(_MemorySessionFactory())

    with pytest.raises(ValueError, match="Invalid bootstrap token"):
        await service.complete_master_bootstrap(
            MasterBootstrapComplete(
                bootstrap_token="vzboot_wrong",
                tenant_name="Vezor Pilot",
                admin_email="admin@vezor.local",
                admin_password="not-persisted-password",
                central_node_name="macbook-pro-master",
            )
        )


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
        row for row in service.session_factory.session.rows if isinstance(row, NodePairingSession)
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
    assert any(
        SupervisorNodeCredential in snapshot and DeploymentCredentialEvent not in snapshot
        for snapshot in service.session_factory.session.flush_snapshots
    )

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
async def test_rotating_edge_node_credentials_revokes_old_material_and_returns_new_once() -> None:
    tenant_id = uuid4()
    edge_node_id = uuid4()
    now = datetime(2026, 5, 13, 9, 45, tzinfo=UTC)
    session_factory = _MemorySessionFactory()
    _seed_edge_node_scope(session_factory, tenant_id=tenant_id, edge_node_id=edge_node_id)
    session_factory.session.add(Tenant(id=tenant_id, name="Argus Dev", slug="argus-dev"))
    service = DeploymentNodeService(session_factory, now_factory=lambda: now)
    created = await service.create_pairing_session(
        tenant_id=tenant_id,
        payload=NodePairingSessionCreate(
            node_kind=DeploymentNodeKind.EDGE,
            edge_node_id=edge_node_id,
            hostname="orin-nano-01",
            requested_ttl_seconds=300,
        ),
        actor_subject="admin-1",
    )
    claimed = await service.claim_pairing_session(
        tenant_id=tenant_id,
        session_id=created.id,
        payload=NodePairingClaim(
            pairing_code=created.pairing_code,
            supervisor_id="edge-orin-1",
            hostname="orin-nano-01",
        ),
    )

    rotated = await service.rotate_edge_node_credentials(
        tenant_id=tenant_id,
        edge_node_id=edge_node_id,
        actor_subject="admin-1",
    )

    assert rotated.node_id == claimed.node.id
    assert rotated.credential_material.startswith("vzcred_")
    assert rotated.credential_material != claimed.credential_material
    assert rotated.credential_hash != rotated.credential_material
    assert rotated.credential_version == claimed.credential_version + 1
    assert rotated.revoked_credentials == 1
    assert not await service.validate_supervisor_credential(
        tenant_id=tenant_id,
        supervisor_id="edge-orin-1",
        credential_material=claimed.credential_material,
    )
    assert await service.validate_supervisor_credential(
        tenant_id=tenant_id,
        supervisor_id="edge-orin-1",
        credential_material=rotated.credential_material,
    )
    with pytest.raises(ValueError, match="Invalid supervisor credential"):
        await service.authenticate_supervisor_credential(
            credential_material=claimed.credential_material,
            supervisor_id="edge-orin-1",
        )
    tenant_context = await service.authenticate_supervisor_credential(
        credential_material=rotated.credential_material,
        supervisor_id="edge-orin-1",
    )
    assert tenant_context.user.subject == "supervisor:edge-orin-1"
    assert not any(
        getattr(row, "credential_material", None) == rotated.credential_material
        for row in service.session_factory.session.rows
    )
    credential_rows = [
        row
        for row in service.session_factory.session.rows
        if isinstance(row, SupervisorNodeCredential)
    ]
    assert [row.credential_version for row in credential_rows] == [1, 2]
    assert credential_rows[0].status is DeploymentCredentialStatus.REVOKED
    assert credential_rows[1].status is DeploymentCredentialStatus.ACTIVE
    events = [
        row
        for row in service.session_factory.session.rows
        if isinstance(row, DeploymentCredentialEvent)
    ]
    assert [event.event_type for event in events] == [
        "credential.issued",
        "credential.revoked",
        "credential.issued",
        "credential.rotated",
    ]
    assert events[-1].event_metadata["credential_version"] == 2
    assert rotated.credential_material not in str(
        [row for row in service.session_factory.session.rows if row is not rotated]
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
async def test_support_bundle_redacts_diagnostics_and_summarizes_node_context() -> None:
    tenant_id = uuid4()
    camera_id = uuid4()
    service = DeploymentNodeService(_MemorySessionFactory())
    now = datetime(2026, 5, 13, 9, 30, tzinfo=UTC)
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
                "storage": "ok",
                "authorization": "Bearer raw-token",
                "log_excerpt": "worker recovered after Bearer raw-token",
                "nested": {"credential": "vzcred_raw-secret", "status": "ok"},
            },
        ),
    )
    session = service.session_factory.session
    session.add(
        OperationsLifecycleRequest(
            id=uuid4(),
            tenant_id=tenant_id,
            camera_id=camera_id,
            edge_node_id=None,
            assignment_id=None,
            action="start",
            status="completed",
            requested_by_subject="operator-1",
            requested_at=now,
            request_payload={"model": "YOLO26n", "bearer": "raw-token"},
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        WorkerRuntimeReport(
            id=uuid4(),
            tenant_id=tenant_id,
            camera_id=camera_id,
            edge_node_id=None,
            assignment_id=None,
            heartbeat_at=now,
            runtime_state=WorkerRuntimeState.RUNNING,
            restart_count=1,
            last_error="recovered with credential=vzcred_raw-secret",
            runtime_artifact_id=None,
            scene_contract_hash=None,
            created_at=now,
        )
    )
    session.add(
        EdgeNodeHardwareReport(
            id=uuid4(),
            tenant_id=tenant_id,
            edge_node_id=None,
            supervisor_id="central-imac-1",
            reported_at=now,
            host_profile="macos-arm64-apple",
            os_name="darwin",
            machine_arch="arm64",
            accelerators=["coreml"],
            provider_capabilities={"CoreMLExecutionProvider": True},
            observed_performance=[],
            report_hash="b" * 64,
            created_at=now,
        )
    )
    session.add(
        WorkerModelAdmissionReport(
            id=uuid4(),
            tenant_id=tenant_id,
            camera_id=camera_id,
            edge_node_id=None,
            assignment_id=None,
            hardware_report_id=None,
            model_id=uuid4(),
            model_name="YOLO26n COCO",
            model_capability="fixed_vocab",
            stream_profile={"width": 1280, "height": 720, "fps": 10},
            status="recommended",
            selected_backend="CoreMLExecutionProvider",
            rationale="CoreML fits.",
            constraints={"credential": "secret"},
            evaluated_at=now,
            created_at=now,
        )
    )

    bundle = await service.get_support_bundle(tenant_id=tenant_id, node_id=node.node.id)
    serialized = bundle.model_dump(mode="json")

    assert bundle.node.id == node.node.id
    assert bundle.lifecycle_summary["by_status"] == {"completed": 1}
    assert bundle.runtime_summary["by_state"] == {"running": 1}
    assert bundle.hardware_summary["latest_reported_at"] == now
    assert bundle.model_admission_summary["by_status"] == {"recommended": 1}
    assert len(bundle.recent_lifecycle_requests) == 1
    assert len(bundle.recent_runtime_reports) == 1
    assert len(bundle.hardware_reports) == 1
    assert len(bundle.model_admission_reports) == 1
    assert bundle.diagnostics["node"]["authorization"] == "[redacted]"
    assert bundle.diagnostics["node"]["nested"]["credential"] == "[redacted]"
    assert bundle.recent_lifecycle_requests[0].request_payload["bearer"] == "[redacted]"
    assert bundle.recent_runtime_reports[0].last_error == "recovered with credential=[redacted]"
    assert bundle.model_admission_reports[0].constraints["credential"] == "[redacted]"
    assert bundle.selected_log_excerpts[0]["excerpt"] == "worker recovered after Bearer [redacted]"
    assert "raw-token" not in str(serialized)
    assert "vzcred_raw-secret" not in str(serialized)


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
        self.flush_snapshots: list[tuple[type[object], ...]] = []

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
        deployment_edge_node_id = params.get("edge_node_id_1")
        credential_hash = params.get("credential_hash_1")
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
                row for row in rows if any(isinstance(row, entity) for entity in model_entities)
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
        if deployment_edge_node_id is not None and DeploymentNode in entities:
            rows = [
                row for row in rows if getattr(row, "edge_node_id", None) == deployment_edge_node_id
            ]
        if credential_hash is not None and SupervisorNodeCredential in entities:
            rows = [row for row in rows if getattr(row, "credential_hash", None) == credential_hash]
        if deployment_node_id is not None and DeploymentCredentialEvent in entities:
            rows = [
                row
                for row in rows
                if getattr(row, "deployment_node_id", None) == deployment_node_id
            ]
        if supervisor_id is not None:
            rows = [row for row in rows if getattr(row, "supervisor_id", None) == supervisor_id]
        return _Result(rows)

    def add(self, row: object) -> None:
        self.rows.append(row)

    async def flush(self) -> None:
        self.flush_snapshots.append(tuple(type(row) for row in self.rows))

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


class _RecordingIdentityProvisioner:
    def __init__(self, *, subject: str) -> None:
        self.subject = subject
        self.calls: list[dict[str, Any]] = []

    async def provision_tenant_admin(
        self,
        *,
        tenant_id: UUID,
        tenant_name: str,
        tenant_slug: str,
        admin_email: str,
        admin_password: str,
    ) -> str:
        self.calls.append(
            {
                "tenant_id": tenant_id,
                "tenant_name": tenant_name,
                "tenant_slug": tenant_slug,
                "admin_email": admin_email,
                "admin_password": admin_password,
            }
        )
        return self.subject
