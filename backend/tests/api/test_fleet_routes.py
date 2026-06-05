from __future__ import annotations

import json
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
from argus.fleet.service import FleetService
from argus.link.service import LinkService
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
KNOWN_SITE_ID = UUID("00000000-0000-4000-8000-000000000002")
FORBIDDEN_VERTICAL_TERMS = (
    "vessel",
    "voyage",
    "owner",
    "manager",
    "charterer",
    "ais",
    "nmea",
    "port call",
)


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


def _create_app(user: AuthenticatedUser) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        packs=PackRegistry(),
        link=LinkService(),
        fleet=FleetService(),
        sites=_FakeSiteService(),
    )
    app.state.security = _FakeSecurity(user)
    return app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=_create_app(_user(RoleEnum.ADMIN))),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_fleet_group_hierarchy_rotation_and_assignment_routes_are_packless(
    client: AsyncClient,
) -> None:
    group_response = await client.post(
        "/api/v1/fleet/site-groups",
        json={"label": "Remote sites", "kind": "operator_group"},
    )
    hierarchy_response = await client.put(
        "/api/v1/fleet/hierarchy",
        json={
            "nodes": [
                {"id": "region-eu", "parent_id": None, "label": "Europe", "kind": "region"},
                {
                    "id": "site-node",
                    "parent_id": "region-eu",
                    "site_id": str(KNOWN_SITE_ID),
                    "label": "Packless Site",
                    "kind": "site",
                },
            ],
        },
    )
    rotation_response = await client.post(
        "/api/v1/fleet/rotation-groups",
        json={"label": "NOC day watch", "member_user_ids": ["operator-a", "operator-b"]},
    )
    assignment_response = await client.post(
        "/api/v1/fleet/site-assignments",
        json={
            "site_id": str(KNOWN_SITE_ID),
            "assignee_type": "support_queue",
            "assignee_id": "noc-day",
        },
    )
    list_response = await client.get("/api/v1/fleet/site-assignments")

    assert group_response.status_code == 201
    assert hierarchy_response.status_code == 200
    assert rotation_response.status_code == 201
    assert assignment_response.status_code == 201
    assert list_response.status_code == 200
    assert group_response.json()["pack_id"] is None
    assert hierarchy_response.json()["nodes"][1]["kind"] == "site"
    assert rotation_response.json()["pack_labels"] == {}
    assert list_response.json()["items"][0]["site_id"] == str(KNOWN_SITE_ID)
    _assert_no_vertical_terms(
        [
            group_response.json(),
            hierarchy_response.json(),
            rotation_response.json(),
            assignment_response.json(),
            list_response.json(),
        ]
    )


@pytest.mark.asyncio
async def test_fleet_site_state_route_returns_core_operational_fields() -> None:
    app = _create_app(_user(RoleEnum.ADMIN))
    app.state.services.fleet.upsert_site_state(
        tenant_id=TENANT_ID,
        site_id=KNOWN_SITE_ID,
        heartbeat_status="stale",
        link_state="degraded",
        runtime_status="stopped",
        evidence_backlog_count=12,
        active_incident_count=1,
        privacy_status="mismatch",
        model_artifact_status="mismatch",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/fleet/sites/{KNOWN_SITE_ID}/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == str(TENANT_ID)
    assert payload["site_id"] == str(KNOWN_SITE_ID)
    assert payload["heartbeat_status"] == "stale"
    assert payload["link_state"] == "degraded"
    assert payload["runtime_status"] == "stopped"
    assert payload["evidence_backlog_count"] == 12
    _assert_no_vertical_terms(payload)


@pytest.mark.asyncio
async def test_fleet_exceptions_route_is_packless_and_tenant_scoped() -> None:
    app = _create_app(_user(RoleEnum.ADMIN))
    app.state.services.fleet.upsert_site_state(
        tenant_id=TENANT_ID,
        site_id=KNOWN_SITE_ID,
        heartbeat_status="stale",
        link_state="degraded",
        runtime_status="stopped",
        evidence_backlog_count=12,
        active_incident_count=1,
        privacy_status="mismatch",
        model_artifact_status="mismatch",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/fleet/exceptions")

    assert response.status_code == 200
    payload = response.json()
    assert [item["kind"] for item in payload["items"]] == [
        "active_incident",
        "stopped_worker",
        "privacy_mismatch",
        "model_artifact_mismatch",
        "degraded_link",
        "evidence_backlog",
        "stale_heartbeat",
    ]
    assert all(item["tenant_id"] == str(TENANT_ID) for item in payload["items"])
    _assert_no_vertical_terms(payload)


@pytest.mark.asyncio
async def test_fleet_site_scoped_routes_return_404_for_unknown_or_foreign_site() -> None:
    unknown_site = "00000000-0000-4000-8000-000000000099"
    async with AsyncClient(
        transport=ASGITransport(app=_create_app(_user(RoleEnum.ADMIN))),
        base_url="http://test",
    ) as client:
        state_response = await client.get(f"/api/v1/fleet/sites/{unknown_site}/state")
        assignment_response = await client.post(
            "/api/v1/fleet/site-assignments",
            json={
                "site_id": unknown_site,
                "assignee_type": "support_queue",
                "assignee_id": "noc-day",
            },
        )

    assert state_response.status_code == 404
    assert assignment_response.status_code == 404


@pytest.mark.asyncio
async def test_fleet_assignment_rejects_foreign_rotation_group() -> None:
    app = _create_app(_user(RoleEnum.ADMIN))
    foreign_rotation = app.state.services.fleet.create_rotation_group(
        tenant_id=UUID("00000000-0000-4000-8000-000000000099"),
        label="NOC day watch",
        member_user_ids=["operator-a"],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/fleet/site-assignments",
            json={
                "site_id": str(KNOWN_SITE_ID),
                "assignee_type": "support_queue",
                "assignee_id": "noc-day",
                "rotation_group_id": str(foreign_rotation.id),
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Rotation group not found."
    assert app.state.services.fleet.list_site_assignments(tenant_id=TENANT_ID) == []


def _assert_no_vertical_terms(payload: object) -> None:
    serialized = json.dumps(payload).lower()
    for term in FORBIDDEN_VERTICAL_TERMS:
        assert term not in serialized
