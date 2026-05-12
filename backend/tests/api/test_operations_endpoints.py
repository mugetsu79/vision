from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    FleetBootstrapRequest,
    FleetBootstrapResponse,
    FleetCameraWorkerSummary,
    FleetOverviewResponse,
    FleetSummary,
    RuntimePassportSummary,
    TenantContext,
)
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import ProcessingMode, RoleEnum


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=RoleEnum.ADMIN,
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
        return self.user


class _FakeOperationsService:
    def __init__(self) -> None:
        self.bootstrap_payload: FleetBootstrapRequest | None = None

    async def get_fleet_overview(self, tenant_context: TenantContext) -> FleetOverviewResponse:
        return FleetOverviewResponse(
            mode="manual_dev",
            generated_at=datetime(2026, 4, 28, 7, 0, tzinfo=UTC),
            summary=FleetSummary(
                desired_workers=1,
                running_workers=0,
                stale_nodes=0,
                offline_nodes=0,
                native_unavailable_cameras=0,
            ),
            nodes=[],
            camera_workers=[
                FleetCameraWorkerSummary(
                    camera_id=UUID("00000000-0000-0000-0000-000000000321"),
                    camera_name="Dock Camera",
                    site_id=UUID("00000000-0000-0000-0000-000000000456"),
                    node_id=None,
                    node_hostname=None,
                    processing_mode=ProcessingMode.EDGE,
                    desired_state="manual",
                    runtime_status="running",
                    lifecycle_owner="manual_dev",
                    runtime_passport=RuntimePassportSummary(
                        id=UUID("00000000-0000-0000-0000-000000000654"),
                        passport_hash="e" * 64,
                        selected_backend="tensorrt_engine",
                        model_hash="f" * 64,
                        runtime_artifact_hash="d" * 64,
                        target_profile="linux-aarch64-nvidia-jetson",
                        precision="fp16",
                        validated_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
                        fallback_reason=None,
                    ),
                )
            ],
            delivery_diagnostics=[],
        )

    async def create_bootstrap_material(
        self,
        tenant_context: TenantContext,
        payload: FleetBootstrapRequest,
    ) -> FleetBootstrapResponse:
        self.bootstrap_payload = payload
        return FleetBootstrapResponse(
            edge_node_id=UUID("00000000-0000-0000-0000-000000000123"),
            api_key="edge_secret_once",
            nats_nkey_seed="nats_secret_once",
            subjects=["evt.tracking.00000000-0000-0000-0000-000000000123"],
            mediamtx_url="http://mediamtx:9997",
            overlay_network_hints={"nats_url": "nats://nats:4222"},
            dev_compose_command=(
                "ARGUS_EDGE_CAMERA_ID=<camera-id> "
                "docker compose -f infra/docker-compose.edge.yml up inference-worker"
            ),
            supervisor_environment={
                "ARGUS_API_BASE_URL": "http://argus-backend:8000",
                "ARGUS_EDGE_NODE_ID": "00000000-0000-0000-0000-000000000123",
            },
        )


def _create_app(context: TenantContext, operations: _FakeOperationsService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        operations=operations,
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_operations_fleet_route_returns_overview() -> None:
    context = _tenant_context()
    app = _create_app(context, _FakeOperationsService())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/operations/fleet",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "manual_dev"
    assert body["summary"]["desired_workers"] == 1
    assert body["camera_workers"][0]["runtime_passport"]["selected_backend"] == (
        "tensorrt_engine"
    )
    assert body["camera_workers"][0]["runtime_passport"]["runtime_artifact_hash"] == "d" * 64


@pytest.mark.asyncio
async def test_operations_bootstrap_route_returns_one_time_material() -> None:
    context = _tenant_context()
    operations = _FakeOperationsService()
    app = _create_app(context, operations)
    site_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/operations/bootstrap",
            headers={"Authorization": "Bearer token"},
            json={
                "site_id": str(site_id),
                "hostname": "edge-kit-01",
                "version": "0.1.0",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["api_key"] == "edge_secret_once"
    assert "docker compose" in body["dev_compose_command"]
    assert operations.bootstrap_payload is not None
    assert operations.bootstrap_payload.site_id == site_id
