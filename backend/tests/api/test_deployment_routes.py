from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    DeploymentNodeResponse,
    DeploymentSupportBundleResponse,
    MasterBootstrapComplete,
    MasterBootstrapCompleteResponse,
    MasterBootstrapRotateResponse,
    MasterBootstrapStatusResponse,
    NodeCredentialRevokeResponse,
    NodeCredentialRotateResponse,
    NodePairingClaim,
    NodePairingClaimResponse,
    NodePairingSessionCreate,
    NodePairingSessionResponse,
    SupervisorServiceReportCreate,
    SupervisorServiceReportResponse,
    TenantContext,
)
from argus.api.v1 import router
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DeploymentServiceManager,
    RoleEnum,
)


def _tenant_context() -> TenantContext:
    return _tenant_context_for_role(RoleEnum.ADMIN)


def _tenant_context_for_role(role: RoleEnum) -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=role,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )


class _FakeTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id=None,
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        authorization = request.headers.get("Authorization")
        if authorization is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token.",
            )
        if authorization == "Bearer node-credential":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer is not trusted.",
            )
        if authorization == "Bearer vzboot_local_once":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bootstrap tokens are not admin bearer tokens.",
            )
        return self.user


class _FakeDeploymentService:
    def __init__(self) -> None:
        self.report_payload: SupervisorServiceReportCreate | None = None
        self.pairing_payload: NodePairingSessionCreate | None = None
        self.claim_payload: NodePairingClaim | None = None
        self.revoked_node_id: UUID | None = None
        self.rotated_node_id: UUID | None = None
        self.tenant_id: UUID | None = None
        self.bootstrap_complete_payload: MasterBootstrapComplete | None = None
        self.bootstrap_rotate_actor_subject: str | None = None

    async def get_master_bootstrap_status(self) -> MasterBootstrapStatusResponse:
        return MasterBootstrapStatusResponse(
            first_run_required=True,
            has_active_local_token=True,
            active_token_expires_at=datetime(2026, 5, 13, 9, 5, tzinfo=UTC),
            completed_at=None,
            tenant_slug=None,
        )

    async def rotate_local_bootstrap_token(
        self,
        *,
        actor_subject: str | None,
    ) -> MasterBootstrapRotateResponse:
        self.bootstrap_rotate_actor_subject = actor_subject
        return MasterBootstrapRotateResponse(
            bootstrap_token="vzboot_local_once",
            expires_at=datetime(2026, 5, 13, 9, 5, tzinfo=UTC),
        )

    async def complete_master_bootstrap(
        self,
        payload: MasterBootstrapComplete,
    ) -> MasterBootstrapCompleteResponse:
        self.bootstrap_complete_payload = payload
        if payload.bootstrap_token != "vzboot_local_once":
            raise ValueError("Invalid bootstrap token.")
        tenant_id = UUID("00000000-0000-0000-0000-000000000920")
        return MasterBootstrapCompleteResponse(
            first_run_required=False,
            tenant_id=tenant_id,
            tenant_slug=payload.tenant_slug or "vezor-pilot",
            admin_subject=f"bootstrap:{payload.admin_email}",
            completed_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            central_node=DeploymentNodeResponse(
                id=UUID("00000000-0000-0000-0000-000000000921"),
                tenant_id=tenant_id,
                node_kind=DeploymentNodeKind.CENTRAL,
                edge_node_id=None,
                supervisor_id=payload.central_supervisor_id or "central-master",
                hostname=payload.central_node_name,
                install_status=DeploymentInstallStatus.INSTALLED,
                credential_status=DeploymentCredentialStatus.MISSING,
                service_manager=None,
                service_status=None,
                version=None,
                os_name=None,
                host_profile=None,
                last_service_reported_at=None,
                diagnostics={},
                created_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            ),
        )

    async def authenticate_supervisor_credential(
        self,
        *,
        credential_material: str,
        supervisor_id: str | None = None,
    ) -> TenantContext:
        if credential_material != "node-credential" or supervisor_id != "central-imac-1":
            raise ValueError("Invalid supervisor credential.")
        tenant_id = self.tenant_id or uuid4()
        return TenantContext(
            tenant_id=tenant_id,
            tenant_slug="argus-dev",
            user=AuthenticatedUser(
                subject="supervisor:central-imac-1",
                email=None,
                role=RoleEnum.OPERATOR,
                issuer="vezor-node-credential",
                realm="argus-dev",
                is_superadmin=False,
                tenant_context=str(tenant_id),
                claims={"auth_type": "supervisor_node_credential"},
            ),
        )

    async def list_nodes(self, *, tenant_id: UUID) -> list[DeploymentNodeResponse]:
        return [
            DeploymentNodeResponse(
                id=UUID("00000000-0000-0000-0000-000000000901"),
                tenant_id=tenant_id,
                node_kind=DeploymentNodeKind.CENTRAL,
                edge_node_id=None,
                supervisor_id="central-imac-1",
                hostname="vezor-central",
                install_status=DeploymentInstallStatus.HEALTHY,
                credential_status=DeploymentCredentialStatus.ACTIVE,
                service_manager=DeploymentServiceManager.LAUNCHD,
                service_status="running",
                version="0.21.0",
                os_name="darwin",
                host_profile="macos-arm64-apple",
                last_service_reported_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
                diagnostics={},
                created_at=datetime(2026, 5, 13, 8, 55, tzinfo=UTC),
                updated_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            ),
            DeploymentNodeResponse(
                id=UUID("00000000-0000-0000-0000-000000000902"),
                tenant_id=tenant_id,
                node_kind=DeploymentNodeKind.EDGE,
                edge_node_id=UUID("00000000-0000-0000-0000-000000000903"),
                supervisor_id="edge-orin-1",
                hostname="orin-nano-01",
                install_status=DeploymentInstallStatus.DEGRADED,
                credential_status=DeploymentCredentialStatus.ACTIVE,
                service_manager=DeploymentServiceManager.SYSTEMD,
                service_status="running",
                version="0.21.0",
                os_name="linux",
                host_profile="linux-aarch64-nvidia-jetson",
                last_service_reported_at=datetime(2026, 5, 13, 8, 59, tzinfo=UTC),
                diagnostics={"storage": "missing local evidence directory"},
                created_at=datetime(2026, 5, 13, 8, 54, tzinfo=UTC),
                updated_at=datetime(2026, 5, 13, 8, 59, tzinfo=UTC),
            ),
        ]

    async def record_service_report(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        payload: SupervisorServiceReportCreate,
        authenticated_node_id: UUID | None = None,
    ) -> SupervisorServiceReportResponse:
        del authenticated_node_id
        self.report_payload = payload
        return SupervisorServiceReportResponse(
            id=UUID("00000000-0000-0000-0000-000000000904"),
            tenant_id=tenant_id,
            deployment_node_id=UUID("00000000-0000-0000-0000-000000000901"),
            edge_node_id=payload.edge_node_id,
            supervisor_id=supervisor_id,
            node_kind=payload.node_kind,
            hostname=payload.hostname,
            service_manager=payload.service_manager,
            service_status=payload.service_status,
            install_status=DeploymentInstallStatus.HEALTHY,
            credential_status=payload.credential_status,
            version=payload.version,
            os_name=payload.os_name,
            host_profile=payload.host_profile,
            heartbeat_at=payload.heartbeat_at,
            diagnostics={
                "token": "[redacted]",
                "nested": {"api_key": "[redacted]", "status": "ok"},
            },
            created_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            node=DeploymentNodeResponse(
                id=UUID("00000000-0000-0000-0000-000000000901"),
                tenant_id=tenant_id,
                node_kind=payload.node_kind,
                edge_node_id=payload.edge_node_id,
                supervisor_id=supervisor_id,
                hostname=payload.hostname,
                install_status=DeploymentInstallStatus.HEALTHY,
                credential_status=payload.credential_status,
                service_manager=payload.service_manager,
                service_status=payload.service_status,
                version=payload.version,
                os_name=payload.os_name,
                host_profile=payload.host_profile,
                last_service_reported_at=payload.heartbeat_at,
                diagnostics={
                    "token": "[redacted]",
                    "nested": {"api_key": "[redacted]", "status": "ok"},
                },
                created_at=datetime(2026, 5, 13, 8, 55, tzinfo=UTC),
                updated_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            ),
        )

    async def create_pairing_session(
        self,
        *,
        tenant_id: UUID,
        payload: NodePairingSessionCreate,
        actor_subject: str | None,
    ) -> NodePairingSessionResponse:
        self.pairing_payload = payload
        self.tenant_id = tenant_id
        return NodePairingSessionResponse(
            id=UUID("00000000-0000-0000-0000-000000000905"),
            tenant_id=tenant_id,
            deployment_node_id=None,
            edge_node_id=payload.edge_node_id,
            node_kind=payload.node_kind,
            hostname=payload.hostname,
            status="pending",
            expires_at=datetime(2026, 5, 13, 9, 5, tzinfo=UTC),
            consumed_at=None,
            claimed_by_supervisor=None,
            created_by_subject=actor_subject,
            pairing_code="123456",
            created_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
        )

    async def get_pairing_session(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
    ) -> NodePairingSessionResponse:
        return NodePairingSessionResponse(
            id=session_id,
            tenant_id=tenant_id,
            deployment_node_id=None,
            edge_node_id=None,
            node_kind=DeploymentNodeKind.CENTRAL,
            hostname="vezor-central",
            status="pending",
            expires_at=datetime(2026, 5, 13, 9, 5, tzinfo=UTC),
            consumed_at=None,
            claimed_by_supervisor=None,
            created_by_subject="admin-1",
            pairing_code=None,
            created_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
        )

    async def claim_pairing_session(
        self,
        *,
        session_id: UUID,
        payload: NodePairingClaim,
        tenant_id: UUID | None = None,
    ) -> NodePairingClaimResponse:
        self.claim_payload = payload
        if payload.pairing_code == "wrong-code":
            raise ValueError("Invalid pairing code.")
        effective_tenant_id = tenant_id or self.tenant_id or uuid4()
        return NodePairingClaimResponse(
            session_id=session_id,
            credential_id=UUID("00000000-0000-0000-0000-000000000906"),
            credential_material="node-credential-once",
            credential_hash="a" * 64,
            node=DeploymentNodeResponse(
                id=UUID("00000000-0000-0000-0000-000000000901"),
                tenant_id=effective_tenant_id,
                node_kind=DeploymentNodeKind.CENTRAL,
                edge_node_id=None,
                supervisor_id=payload.supervisor_id,
                hostname=payload.hostname,
                install_status=DeploymentInstallStatus.INSTALLED,
                credential_status=DeploymentCredentialStatus.ACTIVE,
                service_manager=None,
                service_status=None,
                version=None,
                os_name=None,
                host_profile=None,
                last_service_reported_at=None,
                diagnostics={},
                created_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
            ),
        )

    async def revoke_node_credentials(
        self,
        *,
        tenant_id: UUID,
        node_id: UUID,
        actor_subject: str | None,
    ) -> NodeCredentialRevokeResponse:
        del tenant_id, actor_subject
        self.revoked_node_id = node_id
        return NodeCredentialRevokeResponse(
            node_id=node_id,
            revoked_credentials=1,
            credential_status=DeploymentCredentialStatus.REVOKED,
        )

    async def rotate_node_credentials(
        self,
        *,
        tenant_id: UUID,
        node_id: UUID,
        actor_subject: str | None,
    ) -> NodeCredentialRotateResponse:
        del tenant_id, actor_subject
        self.rotated_node_id = node_id
        return NodeCredentialRotateResponse(
            node_id=node_id,
            credential_id=UUID("00000000-0000-0000-0000-000000000907"),
            credential_material="vzcred_rotated_once",
            credential_hash="b" * 64,
            credential_version=2,
            revoked_credentials=1,
            credential_status=DeploymentCredentialStatus.ACTIVE,
            node=DeploymentNodeResponse(
                id=node_id,
                tenant_id=self.tenant_id or uuid4(),
                node_kind=DeploymentNodeKind.CENTRAL,
                edge_node_id=None,
                supervisor_id="central-imac-1",
                hostname="vezor-central",
                install_status=DeploymentInstallStatus.INSTALLED,
                credential_status=DeploymentCredentialStatus.ACTIVE,
                service_manager=None,
                service_status=None,
                version=None,
                os_name=None,
                host_profile=None,
                last_service_reported_at=None,
                diagnostics={},
                created_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 5, 13, 9, 1, tzinfo=UTC),
            ),
        )

    async def get_support_bundle(
        self,
        *,
        tenant_id: UUID,
        node_id: UUID,
    ) -> DeploymentSupportBundleResponse:
        return DeploymentSupportBundleResponse(
            node=(await self.list_nodes(tenant_id=tenant_id))[0],
            service_reports=[],
            lifecycle_summary={"by_status": {"completed": 1}},
            runtime_summary={"by_state": {"running": 1}},
            hardware_summary={"latest_reported_at": "2026-05-13T09:00:00Z"},
            model_admission_summary={"by_status": {"recommended": 1}},
            diagnostics={"node": {"authorization": "[redacted]", "storage": "ok"}},
            generated_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
        )


def _create_app(context: TenantContext, deployment: _FakeDeploymentService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.settings = Settings(_env_file=None)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        deployment=deployment,
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_bootstrap_status_route_is_unauthenticated_and_redacted() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeDeploymentService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/deployment/bootstrap/status")

    assert response.status_code == 200
    body = response.json()
    assert body["first_run_required"] is True
    assert body["has_active_local_token"] is True
    assert "vzboot_" not in response.text


@pytest.mark.asyncio
async def test_bootstrap_rotate_route_returns_one_time_local_token() -> None:
    context = _tenant_context()
    deployment = _FakeDeploymentService()
    app = _create_app(context, deployment)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/v1/deployment/bootstrap/rotate-local-token")

    assert response.status_code == 201
    assert response.json()["bootstrap_token"] == "vzboot_local_once"
    assert deployment.bootstrap_rotate_actor_subject == "local-bootstrap"


@pytest.mark.asyncio
async def test_bootstrap_rotate_route_accepts_docker_desktop_host_gateway() -> None:
    context = _tenant_context()
    deployment = _FakeDeploymentService()
    app = _create_app(context, deployment)

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.168.65.1", 54123)),
        base_url="http://127.0.0.1:8000",
    ) as client:
        response = await client.post("/api/v1/deployment/bootstrap/rotate-local-token")

    assert response.status_code == 201
    assert response.json()["bootstrap_token"] == "vzboot_local_once"


@pytest.mark.asyncio
async def test_bootstrap_rotate_route_rejects_unconfigured_lan_client() -> None:
    context = _tenant_context()
    deployment = _FakeDeploymentService()
    app = _create_app(context, deployment)

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.168.1.40", 54123)),
        base_url="http://127.0.0.1:8000",
    ) as client:
        response = await client.post("/api/v1/deployment/bootstrap/rotate-local-token")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bootstrap_complete_route_consumes_local_token_without_admin_jwt() -> None:
    context = _tenant_context()
    deployment = _FakeDeploymentService()
    app = _create_app(context, deployment)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/deployment/bootstrap/complete",
            json={
                "bootstrap_token": "vzboot_local_once",
                "tenant_name": "Vezor Pilot",
                "tenant_slug": "vezor-pilot",
                "admin_email": "admin@vezor.local",
                "admin_password": "not-returned",
                "central_node_name": "macbook-pro-master",
                "central_supervisor_id": "central-master",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["first_run_required"] is False
    assert body["tenant_slug"] == "vezor-pilot"
    assert body["central_node"]["supervisor_id"] == "central-master"
    assert "not-returned" not in response.text
    assert "vzboot_local_once" not in response.text
    assert deployment.bootstrap_complete_payload is not None


@pytest.mark.asyncio
async def test_bootstrap_token_cannot_call_normal_admin_routes() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeDeploymentService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/deployment/nodes",
            headers={"Authorization": "Bearer vzboot_local_once"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_deployment_nodes_route_returns_central_and_edge_install_state() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeDeploymentService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/deployment/nodes",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert [node["node_kind"] for node in body] == ["central", "edge"]
    assert body[0]["install_status"] == "healthy"
    assert body[0]["service_manager"] == "launchd"
    assert body[1]["install_status"] == "degraded"
    assert body[1]["diagnostics"]["storage"] == "missing local evidence directory"


@pytest.mark.asyncio
async def test_service_report_route_records_report_and_returns_resolved_node_state() -> None:
    context = _tenant_context()
    deployment = _FakeDeploymentService()
    app = _create_app(context, deployment)
    heartbeat_at = datetime(2026, 5, 13, 9, 0, tzinfo=UTC)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/deployment/supervisors/central-imac-1/service-reports",
            headers={"Authorization": "Bearer token"},
            json={
                "node_kind": "central",
                "hostname": "vezor-central",
                "service_manager": "launchd",
                "service_status": "running",
                "install_status": "healthy",
                "credential_status": "active",
                "version": "0.21.0",
                "os_name": "darwin",
                "host_profile": "macos-arm64-apple",
                "heartbeat_at": heartbeat_at.isoformat(),
                "diagnostics": {
                    "token": "raw-token",
                    "nested": {"api_key": "raw-key", "status": "ok"},
                },
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["supervisor_id"] == "central-imac-1"
    assert body["node"]["install_status"] == "healthy"
    assert body["diagnostics"] == {
        "token": "[redacted]",
        "nested": {"api_key": "[redacted]", "status": "ok"},
    }
    assert deployment.report_payload is not None
    assert deployment.report_payload.service_manager is DeploymentServiceManager.LAUNCHD


@pytest.mark.asyncio
async def test_service_report_route_accepts_node_credential_without_admin_jwt() -> None:
    context = _tenant_context()
    deployment = _FakeDeploymentService()
    app = _create_app(context, deployment)
    heartbeat_at = datetime(2026, 5, 13, 9, 0, tzinfo=UTC)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/deployment/supervisors/central-imac-1/service-reports",
            headers={"Authorization": "Bearer node-credential"},
            json={
                "node_kind": "central",
                "hostname": "vezor-central",
                "service_manager": "launchd",
                "service_status": "running",
                "install_status": "healthy",
                "credential_status": "active",
                "version": "0.21.0",
                "os_name": "darwin",
                "host_profile": "macos-arm64-apple",
                "heartbeat_at": heartbeat_at.isoformat(),
            },
        )

    assert response.status_code == 201
    assert response.json()["supervisor_id"] == "central-imac-1"
    assert deployment.report_payload is not None
    assert deployment.report_payload.credential_status is DeploymentCredentialStatus.ACTIVE


@pytest.mark.asyncio
async def test_pairing_session_routes_create_read_claim_and_revoke_credentials() -> None:
    context = _tenant_context()
    deployment = _FakeDeploymentService()
    app = _create_app(context, deployment)
    node_id = UUID("00000000-0000-0000-0000-000000000901")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/deployment/pairing-sessions",
            headers={"Authorization": "Bearer token"},
            json={
                "node_kind": "central",
                "hostname": "vezor-central",
                "requested_ttl_seconds": 300,
            },
        )
        session_id = create_response.json()["id"]
        get_response = await client.get(
            f"/api/v1/deployment/pairing-sessions/{session_id}",
            headers={"Authorization": "Bearer token"},
        )
        claim_response = await client.post(
            f"/api/v1/deployment/pairing-sessions/{session_id}/claim",
            json={
                "pairing_code": "123456",
                "supervisor_id": "central-imac-1",
                "hostname": "vezor-central",
            },
        )
        revoke_response = await client.post(
            f"/api/v1/deployment/nodes/{node_id}/credentials/revoke",
            headers={"Authorization": "Bearer token"},
        )
        rotate_response = await client.post(
            f"/api/v1/deployment/nodes/{node_id}/credentials/rotate",
            headers={"Authorization": "Bearer token"},
        )

    assert create_response.status_code == 201
    assert create_response.json()["pairing_code"] == "123456"
    assert get_response.status_code == 200
    assert get_response.json()["pairing_code"] is None
    assert claim_response.status_code == 200
    assert claim_response.json()["credential_material"] == "node-credential-once"
    assert revoke_response.status_code == 200
    assert revoke_response.json()["revoked_credentials"] == 1
    assert rotate_response.status_code == 200
    assert rotate_response.json()["credential_material"] == "vzcred_rotated_once"
    assert rotate_response.json()["credential_version"] == 2
    assert deployment.pairing_payload is not None
    assert deployment.claim_payload is not None
    assert deployment.revoked_node_id == node_id
    assert deployment.rotated_node_id == node_id


@pytest.mark.asyncio
async def test_pairing_claim_route_maps_expected_failures_without_admin_auth() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeDeploymentService())
    session_id = UUID("00000000-0000-0000-0000-000000000905")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/deployment/pairing-sessions/{session_id}/claim",
            json={
                "pairing_code": "wrong-code",
                "supervisor_id": "central-imac-1",
                "hostname": "vezor-central",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid pairing code."


@pytest.mark.asyncio
async def test_support_bundle_route_returns_redacted_diagnostics() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeDeploymentService())
    node_id = UUID("00000000-0000-0000-0000-000000000901")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/deployment/nodes/{node_id}/support-bundle",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["node"]["id"] == str(node_id)
    assert body["diagnostics"]["node"]["authorization"] == "[redacted]"
    assert body["lifecycle_summary"]["by_status"] == {"completed": 1}
    assert body["model_admission_summary"]["by_status"] == {"recommended": 1}


@pytest.mark.asyncio
async def test_deployment_routes_reject_unauthenticated_requests() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeDeploymentService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/deployment/nodes")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_deployment_routes_reject_non_admin_requests() -> None:
    context = _tenant_context_for_role(RoleEnum.VIEWER)
    app = _create_app(context, _FakeDeploymentService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/deployment/nodes",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403
