from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import CameraSetupPreviewResponse, FrameSize, TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, get_current_user
from argus.main import create_app
from argus.models.enums import RoleEnum


class _FakeCameraService:
    async def get_setup_preview(
        self,
        tenant_context: TenantContext,
        camera_id,
    ) -> CameraSetupPreviewResponse:
        return CameraSetupPreviewResponse(
            camera_id=camera_id,
            preview_url=f"/api/v1/cameras/{camera_id}/setup-preview/image?rev=12345",
            frame_size=FrameSize(width=1280, height=720),
            captured_at=datetime(2026, 4, 26, 12, 0, tzinfo=UTC),
        )

    async def get_setup_preview_image(
        self,
        tenant_context: TenantContext,
        camera_id,
    ):
        class _Snapshot:
            image_bytes = b"\xff\xd8\xff\xdbsetup-preview"
            content_type = "image/jpeg"

        return _Snapshot()


class _FakeTenancyService:
    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id=None,
    ) -> TenantContext:
        tenant_id = explicit_tenant_id or uuid4()
        return TenantContext(
            tenant_id=tenant_id,
            tenant_slug=user.realm,
            user=user,
        )


class _FakeServices:
    def __init__(self) -> None:
        self.tenancy = _FakeTenancyService()
        self.cameras = _FakeCameraService()

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_health_and_metrics_routes_are_exposed() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        health_response = await client.get("/healthz")
        metrics_response = await client.get("/metrics")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert metrics_response.status_code == 200
    assert "python_info" in metrics_response.text
    assert "argus_http_requests_total" in metrics_response.text


@pytest.mark.asyncio
async def test_cors_allows_local_frontend_origin() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.options(
            "/api/v1/sites",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


@pytest.mark.asyncio
async def test_camera_setup_preview_route_returns_frame_size_and_preview_url() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)
    app.state.services = _FakeServices()
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )
    app.dependency_overrides[get_current_user] = lambda: user
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/v1/cameras/{camera_id}/setup-preview")

    assert response.status_code == 200
    assert response.json()["frame_size"] == {"width": 1280, "height": 720}
    assert response.json()["preview_url"].startswith(
        f"/api/v1/cameras/{camera_id}/setup-preview/image"
    )


@pytest.mark.asyncio
async def test_camera_setup_preview_image_route_returns_jpeg_bytes() -> None:
    settings = Settings(
        _env_file=None,
        enable_startup_services=False,
        enable_nats=False,
        enable_tracing=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    app = create_app(settings=settings)
    app.state.services = _FakeServices()
    user = AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )
    app.dependency_overrides[get_current_user] = lambda: user
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/v1/cameras/{camera_id}/setup-preview/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8\xff")
