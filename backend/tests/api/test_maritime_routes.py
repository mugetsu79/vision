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
from argus.link.service import LinkService
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

    async def is_edge_site(self, tenant_context: TenantContext, site_id: UUID) -> bool:
        site = await self.get_site(tenant_context, site_id)
        return site.site_kind == "edge"


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
        link=LinkService(),
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
async def test_vessel_link_status_composes_core_link_status(
    seeded_app: FastAPI,
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    seeded_app.state.services.link.record_probe(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        latency_ms=900,
        throughput_mbps=0.4,
        packet_loss_percent=2.5,
        reachable=True,
        source="satellite",
    )

    response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/link-status"
    )

    assert response.status_code == 200
    assert response.json()["vessel_id"] == str(vessel_id)
    assert response.json()["site_id"] == str(SITE_ID)
    assert response.json()["link_state"] == "degraded"


@pytest.mark.asyncio
async def test_carrier_terminal_ingest_upserts_core_link_connection(
    seeded_client: AsyncClient,
    site_id: UUID,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "lte-a",
                "provider": "generic-lte",
                "transport_kind": "lte",
                "status": "online",
                "downlink_mbps": 45,
                "uplink_mbps": 12,
                "latency_ms": 90,
                "packet_loss_percent": 0.2,
            },
        },
    )
    connections_response = await seeded_client.get(
        f"/api/v1/link/sites/{site_id}/connections"
    )
    selection_response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 100_000_000},
    )

    assert response.status_code == 201
    assert connections_response.status_code == 200
    connections = connections_response.json()
    assert any(item["transport_kind"] == "lte" for item in connections)
    connection = next(item for item in connections if item["transport_kind"] == "lte")
    assert connection["status"] == "online"
    assert connection["availability_scope"] == "nearby"
    assert connection["metered"] is True
    assert connection["expected_downlink_mbps"] == 45
    assert connection["expected_uplink_mbps"] == 12
    assert connection["expected_latency_ms"] == 90
    assert connection["packet_loss_percent"] == 0.2
    assert connection["metadata"] == {
        "maritime_terminal_id": "lte-a",
        "provider": "generic-lte",
    }
    assert selection_response.status_code == 200
    assert selection_response.json()["transport"] == "lte"
    assert selection_response.json()["defer"] is False


@pytest.mark.asyncio
async def test_carrier_terminal_reassignment_moves_core_link_connection(
    seeded_client: AsyncClient,
    site_id: UUID,
    vessel_id: UUID,
) -> None:
    second_vessel_response = await seeded_client.post(
        "/api/v1/maritime/vessels",
        json={
            "name": "MV Second",
            "create_site": {"name": "MV Second Site"},
        },
    )
    assert second_vessel_response.status_code == 201
    second_vessel_id = second_vessel_response.json()["id"]
    second_site_id = second_vessel_response.json()["site_id"]

    first_ingest = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "shared-terminal",
                "provider": "generic",
                "transport_kind": "wifi",
                "status": "online",
            },
        },
    )
    second_ingest = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": second_vessel_id,
            "payload": {
                "terminal_id": "shared-terminal",
                "provider": "generic",
                "transport_kind": "wifi",
                "status": "online",
            },
        },
    )
    first_site_connections = await seeded_client.get(
        f"/api/v1/link/sites/{site_id}/connections"
    )
    second_site_connections = await seeded_client.get(
        f"/api/v1/link/sites/{second_site_id}/connections"
    )

    assert first_ingest.status_code == 201
    assert second_ingest.status_code == 201
    assert not any(
        item["metadata"].get("maritime_terminal_id") == "shared-terminal"
        for item in first_site_connections.json()
    )
    assert any(
        item["metadata"].get("maritime_terminal_id") == "shared-terminal"
        for item in second_site_connections.json()
    )


@pytest.mark.asyncio
async def test_carrier_selection_uses_legacy_link_state_when_status_missing(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "satellite-link-state-only",
                "provider": "generic-sat",
                "link_state": "satellite_good",
            },
        },
    )
    selection_response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 100_000_000},
    )

    assert response.status_code == 201
    assert selection_response.status_code == 200
    assert selection_response.json()["transport"] == "satellite"
    assert selection_response.json()["defer"] is False


@pytest.mark.asyncio
async def test_carrier_selection_defers_degraded_core_satellite_bulk_lane(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "degraded-sat",
                "provider": "generic-sat",
                "link_state": "satellite_degraded",
                "status": "degraded",
            },
        },
    )
    selection_response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 10_000},
    )

    assert response.status_code == 201
    assert selection_response.status_code == 200
    assert selection_response.json()["transport"] == "deferred"
    assert selection_response.json()["defer"] is True
    assert selection_response.json()["reason"] == "degraded_satellite_bulk_backpressure"


@pytest.mark.asyncio
async def test_carrier_selection_uses_available_core_connection_over_latest_degraded_terminal(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    wifi_response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "port-wifi-a",
                "provider": "generic-wifi",
                "transport_kind": "wifi",
                "status": "online",
            },
        },
    )
    satellite_response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "degraded-sat-latest",
                "provider": "generic-sat",
                "link_state": "satellite_degraded",
                "status": "degraded",
            },
        },
    )
    selection_response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 10_000},
    )

    assert wifi_response.status_code == 201
    assert satellite_response.status_code == 201
    assert selection_response.status_code == 200
    assert selection_response.json()["transport"] == "wifi"
    assert selection_response.json()["defer"] is False
    assert selection_response.json()["reason"] == "core_connection_selected"


@pytest.mark.asyncio
async def test_carrier_selection_treats_recovering_core_connection_as_satellite_degraded(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "recovering-sat",
                "provider": "generic-sat",
                "link_state": "recovering",
            },
        },
    )
    selection_response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 10_000},
    )

    assert response.status_code == 201
    assert selection_response.status_code == 200
    assert selection_response.json()["transport"] == "deferred"
    assert selection_response.json()["defer"] is True
    assert selection_response.json()["reason"] == "degraded_satellite_bulk_backpressure"


@pytest.mark.asyncio
async def test_carrier_selection_preserves_recovering_link_state_over_online_status(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "recovering-status-online",
                "provider": "generic-sat",
                "link_state": "recovering",
                "status": "online",
            },
        },
    )
    selection_response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 10_000},
    )

    assert response.status_code == 201
    assert selection_response.status_code == 200
    assert selection_response.json()["transport"] == "deferred"
    assert selection_response.json()["defer"] is True
    assert selection_response.json()["reason"] == "degraded_satellite_bulk_backpressure"


@pytest.mark.asyncio
async def test_carrier_selection_infers_null_transport_kind_from_recovering_link_state(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "recovering-null-transport",
                "provider": "generic-sat",
                "transport_kind": None,
                "link_state": "recovering",
                "status": "online",
            },
        },
    )
    selection_response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 10_000},
    )

    assert response.status_code == 201
    assert selection_response.status_code == 200
    assert selection_response.json()["transport"] == "deferred"
    assert selection_response.json()["defer"] is True
    assert selection_response.json()["reason"] == "degraded_satellite_bulk_backpressure"


@pytest.mark.asyncio
async def test_carrier_selection_preserves_dark_link_state_over_online_status(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "dark-status-online",
                "provider": "generic-sat",
                "link_state": "dark",
                "status": "online",
            },
        },
    )
    selection_response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 100_000_000},
    )

    assert response.status_code == 201
    assert selection_response.status_code == 200
    assert selection_response.json()["transport"] == "deferred"
    assert selection_response.json()["defer"] is True
    assert selection_response.json()["reason"] == "core_connection_unavailable"


@pytest.mark.asyncio
async def test_carrier_selection_rejects_invalid_priority_lane_without_core_connections(
    seeded_client: AsyncClient,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "invalid"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_carrier_terminal_ingest_truncates_core_link_label(
    seeded_client: AsyncClient,
    site_id: UUID,
    vessel_id: UUID,
) -> None:
    response = await seeded_client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "terminal-" + ("t" * 111),
                "provider": "p" * 80,
                "transport_kind": "ethernet",
                "status": "online",
            },
        },
    )
    connections_response = await seeded_client.get(
        f"/api/v1/link/sites/{site_id}/connections"
    )

    assert response.status_code == 201
    connections = connections_response.json()
    connection = next(
        item
        for item in connections
        if item["metadata"].get("maritime_terminal_id") == "terminal-" + ("t" * 111)
    )
    assert len(connection["label"]) <= 160


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
