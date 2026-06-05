from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import SiteResponse, TenantContext
from argus.api.v1 import router
from argus.compat import UTC
from argus.core.security import AuthenticatedUser
from argus.link.service import LinkService
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
KNOWN_SITE_ID = UUID("00000000-0000-4000-8000-000000000002")


def _user(role: RoleEnum) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=f"{role.value}-1",
        email=f"{role.value}@argus.local",
        role=role,
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


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request: object) -> AuthenticatedUser:
        return self.user


class _FakeSiteService:
    async def get_site(self, tenant_context: TenantContext, site_id: UUID) -> SiteResponse:
        if site_id != KNOWN_SITE_ID:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found.")
        return SiteResponse(
            id=site_id,
            tenant_id=tenant_context.tenant_id,
            name="Packless Site",
            description=None,
            tz="UTC",
            geo_point=None,
            created_at=datetime.now(tz=UTC),
        )


def _create_app(user: AuthenticatedUser, *, include_sites: bool = True) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        packs=PackRegistry(),
        link=LinkService(),
    )
    if include_sites:
        services.sites = _FakeSiteService()
    app.state.services = services
    app.state.security = _FakeSecurity(user)
    return app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=_create_app(_user(RoleEnum.ADMIN))),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def viewer_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=_create_app(_user(RoleEnum.VIEWER))),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_packless_link_status_route_returns_budget_queue_probe_and_state(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/link/sites/00000000-0000-4000-8000-000000000002/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["site_id"] == "00000000-0000-4000-8000-000000000002"
    assert payload["pack_id"] is None
    assert set(payload) >= {"budget", "queue_depth", "latest_probe", "link_state", "last_sync_at"}


@pytest.mark.asyncio
async def test_link_budget_update_requires_admin(viewer_client: AsyncClient) -> None:
    response = await viewer_client.put(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/budget",
        json={"monthly_bytes": 50_000_000_000, "bulk_daily_bytes": 5_000_000_000},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_queue_pause_resume_retry_routes_are_tenant_scoped(client: AsyncClient) -> None:
    foreign_item_id = "00000000-0000-4000-8000-000000000099"
    for action in ("pause", "resume", "retry"):
        response = await client.post(f"/api/v1/link/queue/{foreign_item_id}/{action}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_link_site_routes_return_404_for_unknown_or_foreign_site() -> None:
    unknown_site = "00000000-0000-4000-8000-000000000099"
    app = _create_app(_user(RoleEnum.ADMIN))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        status_response = await http_client.get(f"/api/v1/link/sites/{unknown_site}/status")
        budget_response = await http_client.put(
            f"/api/v1/link/sites/{unknown_site}/budget",
            json={"monthly_bytes": 50_000_000_000, "bulk_daily_bytes": 5_000_000_000},
        )
        probe_response = await http_client.post(
            f"/api/v1/link/sites/{unknown_site}/probes",
            json={
                "latency_ms": 12,
                "throughput_mbps": 50,
                "packet_loss_percent": 0,
                "reachable": True,
                "source": "packless-lab",
            },
        )
        policy_response = await http_client.put(
            f"/api/v1/link/sites/{unknown_site}/policies",
            json={"policy": {"priority_order": ["safety", "evidence", "telemetry", "bulk"]}},
        )

    assert status_response.status_code == 404
    assert budget_response.status_code == 404
    assert probe_response.status_code == 404
    assert policy_response.status_code == 404
