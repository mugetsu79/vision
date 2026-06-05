from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import SiteCreate, SiteResponse, TenantContext
from argus.api.v1 import router
from argus.compat import UTC
from argus.core.security import AuthenticatedUser
from argus.maritime.service import MaritimeConflictError, MaritimeRuntimeService
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
FOREIGN_TENANT_ID = UUID("00000000-0000-4000-8000-000000000099")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")
PACKS_ROOT = Path(__file__).resolve().parents[3] / "packs"


def _user(role: RoleEnum, *, tenant_id: UUID = TENANT_ID) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=f"{role.value}-{tenant_id}",
        email=f"{role.value}@argus.local",
        role=role,
        issuer="http://issuer",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(tenant_id),
        claims={},
    )


class _FakeTenancyService:
    def __init__(self, user: AuthenticatedUser, *, tenant_id: UUID = TENANT_ID) -> None:
        self.context = TenantContext(
            tenant_id=tenant_id,
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
    def __init__(self) -> None:
        self.sites: dict[tuple[UUID, UUID], SiteResponse] = {}
        self.add_site(tenant_id=TENANT_ID, site_id=SITE_ID, name="Existing Site")

    def add_site(self, *, tenant_id: UUID, site_id: UUID, name: str) -> SiteResponse:
        site = SiteResponse(
            id=site_id,
            tenant_id=tenant_id,
            name=name,
            description=None,
            tz="UTC",
            geo_point=None,
            created_at=datetime.now(tz=UTC),
        )
        self.sites[(tenant_id, site_id)] = site
        return site

    async def get_site(self, tenant_context: TenantContext, site_id: UUID) -> SiteResponse:
        site = self.sites.get((tenant_context.tenant_id, site_id))
        if site is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found.")
        return site

    async def create_site(self, tenant_context: TenantContext, payload: SiteCreate) -> SiteResponse:
        return self.add_site(tenant_id=tenant_context.tenant_id, site_id=uuid4(), name=payload.name)

    async def delete_site(self, tenant_context: TenantContext, site_id: UUID) -> None:
        self.sites.pop((tenant_context.tenant_id, site_id))


class _ConflictMaritimeService:
    async def aensure_vessel_identifiers_available(self, **kwargs: object) -> None:
        return None

    async def acreate_vessel(self, **kwargs: object) -> object:
        raise MaritimeConflictError("Duplicate vessel mmsi.")


def _create_app(user: AuthenticatedUser, *, tenant_id: UUID = TENANT_ID) -> FastAPI:
    pack_registry = PackRegistry(PACKS_ROOT)
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user, tenant_id=tenant_id),
        packs=pack_registry,
        maritime=MaritimeRuntimeService(pack_registry=pack_registry),
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


@pytest_asyncio.fixture
async def seeded_app() -> FastAPI:
    return _create_app(_user(RoleEnum.ADMIN))


@pytest_asyncio.fixture
async def seeded_client(seeded_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=seeded_app),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def site_id() -> UUID:
    return SITE_ID


@pytest_asyncio.fixture
async def vessel_id(seeded_app: FastAPI) -> UUID:
    vessel = seeded_app.state.services.maritime.create_vessel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        name="MV Seed",
        mmsi="235999999",
    )
    return vessel.id


@pytest_asyncio.fixture
async def voyage_id(seeded_app: FastAPI, vessel_id: UUID) -> UUID:
    voyage = seeded_app.state.services.maritime.create_voyage(
        tenant_id=TENANT_ID,
        vessel_id=vessel_id,
        name="Seed Leg",
    )
    return voyage.id


@pytest_asyncio.fixture
async def foreign_tenant_client(seeded_app: FastAPI) -> AsyncIterator[AsyncClient]:
    foreign_app = _create_app(
        _user(RoleEnum.ADMIN, tenant_id=FOREIGN_TENANT_ID),
        tenant_id=FOREIGN_TENANT_ID,
    )
    foreign_app.state.services.maritime = seeded_app.state.services.maritime
    async with AsyncClient(
        transport=ASGITransport(app=foreign_app),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_create_vessel_with_linked_site(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/maritime/vessels",
        json={"name": "MV Resolute", "mmsi": "235012345", "create_site": {"name": "MV Resolute"}},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "MV Resolute"
    assert payload["site"]["name"] == "MV Resolute"
    assert payload["site_id"] == payload["site"]["id"]


@pytest.mark.asyncio
async def test_create_vessel_attaches_existing_site(client: AsyncClient, site_id: UUID) -> None:
    response = await client.post(
        "/api/v1/maritime/vessels",
        json={"name": "MV Existing", "site_id": str(site_id), "imo_number": "9876543"},
    )
    assert response.status_code == 201
    assert response.json()["site_id"] == str(site_id)


@pytest.mark.asyncio
async def test_vessel_identifiers_are_unique_per_tenant(client: AsyncClient) -> None:
    payload = {
        "name": "MV Duplicate",
        "mmsi": "235012345",
        "create_site": {"name": "MV Duplicate"},
    }
    assert (await client.post("/api/v1/maritime/vessels", json=payload)).status_code == 201
    duplicate = await client.post(
        "/api/v1/maritime/vessels",
        json={**payload, "name": "MV Duplicate 2"},
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_linked_site_request_does_not_create_site(
    seeded_app: FastAPI,
    seeded_client: AsyncClient,
) -> None:
    payload = {
        "name": "MV Duplicate",
        "mmsi": "235012345",
        "create_site": {"name": "MV Duplicate"},
    }
    assert (await seeded_client.post("/api/v1/maritime/vessels", json=payload)).status_code == 201
    site_count = len(seeded_app.state.services.sites.sites)
    duplicate = await seeded_client.post(
        "/api/v1/maritime/vessels",
        json={**payload, "name": "MV Duplicate 2", "create_site": {"name": "Should Not Exist"}},
    )
    assert duplicate.status_code == 409
    assert len(seeded_app.state.services.sites.sites) == site_count


@pytest.mark.asyncio
async def test_linked_site_create_is_compensated_when_vessel_create_conflicts() -> None:
    app = _create_app(_user(RoleEnum.ADMIN))
    app.state.services.maritime = _ConflictMaritimeService()
    site_count = len(app.state.services.sites.sites)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        response = await http_client.post(
            "/api/v1/maritime/vessels",
            json={
                "name": "MV Conflict",
                "mmsi": "235012345",
                "create_site": {"name": "MV Conflict"},
            },
        )

    assert response.status_code == 409
    assert len(app.state.services.sites.sites) == site_count


@pytest.mark.asyncio
async def test_only_one_active_voyage_per_vessel(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    first = await seeded_client.post(
        f"/api/v1/maritime/vessels/{vessel_id}/voyages",
        json={"name": "Leg 1"},
    )
    second = await seeded_client.post(
        f"/api/v1/maritime/vessels/{vessel_id}/voyages",
        json={"name": "Leg 2"},
    )
    assert (
        await seeded_client.post(f"/api/v1/maritime/voyages/{first.json()['id']}/activate")
    ).status_code == 200
    conflict = await seeded_client.post(
        f"/api/v1/maritime/voyages/{second.json()['id']}/activate"
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_complete_voyage_requires_departure(
    seeded_client: AsyncClient,
    voyage_id: UUID,
) -> None:
    assert (
        await seeded_client.post(f"/api/v1/maritime/voyages/{voyage_id}/complete")
    ).status_code == 409
    assert (
        await seeded_client.post(f"/api/v1/maritime/voyages/{voyage_id}/activate")
    ).status_code == 200
    response = await seeded_client.post(f"/api/v1/maritime/voyages/{voyage_id}/complete")
    assert response.status_code == 200
    assert response.json()["actual_departure_at"] is not None


@pytest.mark.asyncio
async def test_update_voyage_details(
    seeded_client: AsyncClient,
    voyage_id: UUID,
) -> None:
    response = await seeded_client.patch(
        f"/api/v1/maritime/voyages/{voyage_id}",
        json={"destination": "Hamburg", "metadata": {"cargo": "reefers"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["destination"] == "Hamburg"
    assert payload["metadata"]["cargo"] == "reefers"


@pytest.mark.asyncio
async def test_port_call_state_transitions_are_validated(
    seeded_client: AsyncClient,
    voyage_id: UUID,
) -> None:
    port_call = await seeded_client.post(
        f"/api/v1/maritime/voyages/{voyage_id}/port-calls",
        json={"port_name": "Rotterdam", "un_locode": "NLRTM", "eta": "2026-06-10T08:00:00Z"},
    )
    port_call_id = port_call.json()["id"]
    assert (
        await seeded_client.post(f"/api/v1/maritime/port-calls/{port_call_id}/depart")
    ).status_code == 409
    assert (
        await seeded_client.post(f"/api/v1/maritime/port-calls/{port_call_id}/arrive")
    ).status_code == 200
    assert (
        await seeded_client.post(f"/api/v1/maritime/port-calls/{port_call_id}/depart")
    ).status_code == 200


@pytest.mark.asyncio
async def test_update_port_call_details(
    seeded_client: AsyncClient,
    voyage_id: UUID,
) -> None:
    created = await seeded_client.post(
        f"/api/v1/maritime/voyages/{voyage_id}/port-calls",
        json={"port_name": "Rotterdam", "un_locode": "NLRTM"},
    )
    response = await seeded_client.patch(
        f"/api/v1/maritime/port-calls/{created.json()['id']}",
        json={"berth": "A12", "link_profile": "port-wifi"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["berth"] == "A12"
    assert payload["link_profile"] == "port-wifi"


@pytest.mark.asyncio
async def test_cross_tenant_vessel_access_returns_404(
    foreign_tenant_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    response = await foreign_tenant_client.get(f"/api/v1/maritime/vessels/{vessel_id}")
    assert response.status_code == 404
