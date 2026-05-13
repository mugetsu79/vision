from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    DeploymentNodeResponse,
    SupervisorServiceReportCreate,
    SupervisorServiceReportResponse,
    TenantContext,
)
from argus.api.v1 import router
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
        if request.headers.get("Authorization") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token.",
            )
        return self.user


class _FakeDeploymentService:
    def __init__(self) -> None:
        self.report_payload: SupervisorServiceReportCreate | None = None

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
    ) -> SupervisorServiceReportResponse:
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


def _create_app(context: TenantContext, deployment: _FakeDeploymentService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        deployment=deployment,
    )
    app.state.security = _FakeSecurity(context.user)
    return app


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
