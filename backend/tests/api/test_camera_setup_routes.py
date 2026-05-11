from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    BrowserDeliverySettings,
    CameraSourceProbeRequest,
    CameraSourceProbeResponse,
    TenantContext,
)
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, get_current_user
from argus.main import create_app
from argus.models.enums import CameraSourceKind, RoleEnum


class _FakeCameraService:
    def __init__(self) -> None:
        self.probe_payload: CameraSourceProbeRequest | None = None

    async def probe_camera_source(
        self,
        tenant_context: TenantContext,
        payload: CameraSourceProbeRequest,
    ) -> CameraSourceProbeResponse:
        del tenant_context
        self.probe_payload = payload
        return CameraSourceProbeResponse(
            source_capability=None,
            browser_delivery=BrowserDeliverySettings(),
        )


class _FakeTenancyService:
    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id=None,
    ) -> TenantContext:
        return TenantContext(
            tenant_id=explicit_tenant_id or uuid4(),
            tenant_slug=user.realm,
            user=user,
        )


class _FakeServices:
    def __init__(self) -> None:
        self.tenancy = _FakeTenancyService()
        self.cameras = _FakeCameraService()

    async def close(self) -> None:
        return None


def _admin_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )


@pytest.mark.asyncio
async def test_source_probe_route_accepts_usb_camera_source_payload() -> None:
    services = _FakeServices()
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = services
    app.dependency_overrides[get_current_user] = _admin_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/cameras/source-probe",
            json={
                "camera_source": {
                    "kind": "usb",
                    "uri": "usb:///dev/video0",
                    "label": "Dock Door USB",
                },
                "processing_mode": "edge",
                "edge_node_id": str(uuid4()),
            },
        )

    assert response.status_code == 200
    assert services.cameras.probe_payload is not None
    assert services.cameras.probe_payload.camera_source is not None
    assert services.cameras.probe_payload.camera_source.kind is CameraSourceKind.USB
    assert services.cameras.probe_payload.camera_source.uri == "usb:///dev/video0"
