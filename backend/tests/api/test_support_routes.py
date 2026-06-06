from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum
from argus.support.service import SupportNotFoundError, SupportService

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
FOREIGN_TENANT_ID = UUID("00000000-0000-4000-8000-000000000099")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")
NODE_ID = UUID("00000000-0000-4000-8000-000000000030")


@pytest.mark.asyncio
async def test_support_bundle_route_creates_packless_bundle(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/support/bundles",
        json={
            "site_id": str(SITE_ID),
            "include_logs": True,
            "diagnostics": {
                "rtsp_url": "rtsp://user:password@camera.local/stream",
                "api_key": "secret-token",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["site_id"] == str(SITE_ID)
    assert payload["pack_id"] is None
    assert "password" not in str(payload["payload"])
    assert "secret-token" not in str(payload["payload"])


@pytest.mark.asyncio
async def test_support_bundle_route_lists_packless_bundles(client: AsyncClient) -> None:
    bundle_response = await client.post(
        "/api/v1/support/bundles",
        json={"site_id": str(SITE_ID), "include_logs": True},
    )

    response = await client.get("/api/v1/support/bundles")

    assert bundle_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == bundle_response.json()["id"]
    assert response.json()["items"][0]["pack_id"] is None


@pytest.mark.asyncio
async def test_support_routes_are_tenant_scoped(
    client: AsyncClient,
    foreign_bundle_id: UUID,
) -> None:
    response = await client.get(f"/api/v1/support/bundles/{foreign_bundle_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_support_bundle_route_rejects_foreign_site(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/support/bundles",
        json={
            "site_id": "00000000-0000-4000-8000-000000000088",
            "include_logs": True,
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_support_session_route_closes_with_billable_duration(
    client: AsyncClient,
) -> None:
    session_response = await client.post(
        "/api/v1/support/sessions",
        json={"site_id": str(SITE_ID), "operator_id": "noc-1"},
    )
    session = session_response.json()

    response = await client.patch(
        f"/api/v1/support/sessions/{session['id']}",
        json={"ended_at": "2026-06-05T13:30:00Z"},
    )

    assert session_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["usage_meter_key"] == "support_session_hour"
    assert response.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_support_tunnel_route_requests_and_revokes(client: AsyncClient) -> None:
    tunnel_response = await client.post(
        "/api/v1/support/tunnels",
        json={
            "site_id": str(SITE_ID),
            "node_id": str(NODE_ID),
            "transport": "ssh_reverse",
            "credential_ref": "node-local:ssh/support-tunnel",
            "relay_host": "noc-relay.mugetsu.tech",
            "allowed_ports": [22, 8000],
        },
    )
    tunnel = tunnel_response.json()

    revoke_response = await client.post(
        f"/api/v1/support/tunnels/{tunnel['id']}/revoke",
        json={"reason": "operator closed support case"},
    )

    assert tunnel_response.status_code == 201
    assert tunnel["status"] == "requested"
    assert tunnel["private_key"] is None
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_support_tunnel_route_rejects_unsafe_relay_host(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/support/tunnels",
        json={
            "site_id": str(SITE_ID),
            "node_id": str(NODE_ID),
            "transport": "ssh_reverse",
            "credential_ref": "node-local:ssh/support-tunnel",
            "relay_host": "-oProxyCommand=bad",
            "allowed_ports": [22],
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_break_glass_route_records_reason_scope_and_closure(
    client: AsyncClient,
) -> None:
    record_response = await client.post(
        "/api/v1/support/break-glass",
        json={
            "reason": "restore camera access",
            "scope": {"site_id": str(SITE_ID)},
            "actor_id": "captain",
            "approver_id": "fleet-admin",
        },
    )
    record = record_response.json()

    close_response = await client.post(
        f"/api/v1/support/break-glass/{record['id']}/close",
        json={"closure_notes": "rotated temporary credential"},
    )

    assert record_response.status_code == 201
    assert close_response.status_code == 200
    assert close_response.json()["closure_notes"] == "rotated temporary credential"


@pytest.mark.asyncio
async def test_onboarding_routes_return_core_checks(client: AsyncClient) -> None:
    run_response = await client.post(
        "/api/v1/support/onboarding-checks/run",
        json={"site_id": str(SITE_ID)},
    )
    list_response = await client.get(
        f"/api/v1/support/onboarding-checks?site_id={SITE_ID}"
    )

    assert run_response.status_code == 201
    assert list_response.status_code == 200
    check_keys = {check["key"] for check in list_response.json()["checks"]}
    assert {"identity", "support_readiness"} <= check_keys


@pytest.mark.asyncio
async def test_maritime_support_routes_contribute_shipboard_grouping(
    client: AsyncClient,
) -> None:
    checklist = await client.get("/api/v1/maritime/support/checklist")
    diagnostics = await client.get("/api/v1/maritime/support/diagnostics")

    assert checklist.status_code == 200
    assert diagnostics.status_code == 200
    assert "satellite_link" in diagnostics.json()["groups"]
    assert "eto_handoff" in checklist.json()["sections"]


@pytest_asyncio.fixture
async def client(support_service: SupportService) -> AsyncClient:
    app = FastAPI()
    app.include_router(router)
    user = _user(RoleEnum.ADMIN)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        support=support_service,
    )
    app.state.security = _FakeSecurity(user)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest.fixture
def support_service() -> SupportService:
    return SupportService(resource_validator=_FakeSupportResourceValidator())


@pytest.fixture
def foreign_bundle_id(support_service: SupportService) -> UUID:
    bundle = support_service.generate_bundle(
        tenant_id=FOREIGN_TENANT_ID,
        site_id=SITE_ID,
        diagnostics={"status": "foreign"},
    )
    return bundle.id


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
        if explicit_tenant_id is not None and explicit_tenant_id != TENANT_ID:
            return self.context.model_copy(update={"tenant_id": explicit_tenant_id})
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request: object) -> AuthenticatedUser:
        return self.user


class _FakeSupportResourceValidator:
    async def validate_site(self, *, tenant_id: UUID, site_id: UUID) -> None:
        if tenant_id != TENANT_ID or site_id != SITE_ID:
            raise SupportNotFoundError("Site not found.")

    async def validate_node(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        node_id: UUID,
    ) -> None:
        if tenant_id != TENANT_ID or site_id != SITE_ID or node_id != NODE_ID:
            raise SupportNotFoundError("Node not found.")


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
