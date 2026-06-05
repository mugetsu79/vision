from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import SiteResponse, TenantContext
from argus.compat import UTC
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, get_current_user
from argus.fleet.service import FleetService
from argus.link.service import LinkService
from argus.main import create_app
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=RoleEnum.ADMIN,
        issuer="http://issuer",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(TENANT_ID),
        claims={},
    )


class _FakeTenancyService:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.context = TenantContext(
            tenant_id=TENANT_ID,
            tenant_slug="argus-dev",
            user=user,
        )

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        if explicit_tenant_id is None:
            return self.context
        return self.context.model_copy(update={"tenant_id": explicit_tenant_id})


class _FakeSiteService:
    async def get_site(self, tenant_context: TenantContext, site_id: UUID) -> SiteResponse:
        return SiteResponse(
            id=SITE_ID if site_id == SITE_ID else site_id,
            tenant_id=tenant_context.tenant_id,
            name="Packless Site",
            description=None,
            tz="UTC",
            geo_point=None,
            created_at=datetime.now(tz=UTC),
        )


@pytest.fixture
def empty_pack_app(tmp_path) -> FastAPI:  # noqa: ANN001
    user = _user()
    empty_packs_root = tmp_path / "packs"
    empty_packs_root.mkdir()
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        packs=PackRegistry(empty_packs_root),
        link=LinkService(),
        fleet=FleetService(),
        sites=_FakeSiteService(),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    return app


@pytest.mark.asyncio
async def test_link_routes_work_with_empty_pack_registry(empty_pack_app: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=empty_pack_app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/status"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["site_id"] == "00000000-0000-4000-8000-000000000002"
    assert payload.get("pack_id") is None


@pytest.mark.asyncio
async def test_fleet_routes_work_with_empty_pack_registry(empty_pack_app: FastAPI) -> None:
    empty_pack_app.state.services.fleet.upsert_site_state(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        heartbeat_status="stale",
        link_state="degraded",
        runtime_status="stopped",
        evidence_backlog_count=12,
        active_incident_count=1,
        privacy_status="mismatch",
        model_artifact_status="mismatch",
    )

    async with AsyncClient(
        transport=ASGITransport(app=empty_pack_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/fleet/exceptions")

    assert response.status_code == 200
    serialized = json.dumps(response.json()).lower()
    assert "vessel" not in serialized
    assert "voyage" not in serialized
