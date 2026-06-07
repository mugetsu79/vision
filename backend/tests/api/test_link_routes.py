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
    async def list_sites(self, tenant_context: TenantContext) -> list[SiteResponse]:
        return [
            SiteResponse(
                id=KNOWN_SITE_ID,
                tenant_id=tenant_context.tenant_id,
                name="Packless Site",
                description=None,
                tz="UTC",
                geo_point=None,
                created_at=datetime.now(tz=UTC),
            )
        ]

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
async def test_link_site_summary_route_is_packless_and_domain_neutral(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/link/sites/summary")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload
    assert {
        "site_id",
        "site_name",
        "site_tz",
        "link_state",
        "connection_count",
        "metered_connection_count",
        "queue_depth",
        "queued_bytes",
        "passport_hash",
    } <= set(payload[0])
    assert "vessel" not in payload[0]
    assert "voyage" not in payload[0]


@pytest.mark.asyncio
async def test_link_budget_update_requires_admin(viewer_client: AsyncClient) -> None:
    response = await viewer_client.put(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/budget",
        json={"monthly_bytes": 50_000_000_000, "bulk_daily_bytes": 5_000_000_000},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_link_connection_routes_are_packless(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections",
        json={
            "label": "Port fiber",
            "transport_kind": "fiber",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "local",
            "metered": False,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["transport_kind"] == "fiber"
    assert payload["label"] == "Port fiber"

    listed = await client.get(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections"
    )
    assert listed.status_code == 200
    assert listed.json()[0]["label"] == "Port fiber"

    selection = await client.get(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections/selection"
    )
    assert selection.status_code == 200
    assert selection.json()["id"] == payload["id"]

    patched = await client.patch(
        f"/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections/{payload['id']}",
        json={"status": "blocked"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "blocked"

    deleted = await client.delete(
        f"/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections/{payload['id']}"
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_link_probe_rejects_unknown_connection_id(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/probes",
        json={
            "connection_id": "00000000-0000-4000-8000-000000000099",
            "latency_ms": 12,
            "throughput_mbps": 50,
            "packet_loss_percent": 0,
            "reachable": True,
            "source": "packless-lab",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_link_probe_accepts_structured_source_fields(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probes",
        json={
            "latency_ms": 42,
            "throughput_mbps": 180.0,
            "packet_loss_percent": 0.1,
            "reachable": True,
            "source": "manual:operator-console",
            "target_id": "target-vezor-ingest",
            "target_label": "Vezor ingest",
            "target_address": "ingest.example.vezor",
            "probe_type": "https",
            "source_type": "manual",
            "source_label": "operator-console",
            "sample_kind": "manual",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["target_id"] == "target-vezor-ingest"
    assert payload["target_label"] == "Vezor ingest"
    assert payload["target_address"] == "ingest.example.vezor"
    assert payload["probe_type"] == "https"
    assert payload["source_type"] == "manual"
    assert payload["source_label"] == "operator-console"
    assert payload["sample_kind"] == "manual"
    assert payload["deleted_at"] is None


@pytest.mark.asyncio
async def test_delete_link_probe_hides_sample(client: AsyncClient) -> None:
    created = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probes",
        json={
            "latency_ms": 42,
            "throughput_mbps": 180.0,
            "packet_loss_percent": 0.1,
            "reachable": True,
            "source": "manual:operator-console",
        },
    )
    probe_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/link/sites/{KNOWN_SITE_ID}/probes/{probe_id}")
    history = await client.get(f"/api/v1/link/sites/{KNOWN_SITE_ID}/probes")

    assert deleted.status_code == 204
    assert history.status_code == 200
    assert history.json() == []


@pytest.mark.asyncio
async def test_run_link_probe_target_records_backend_synthetic_sample(client: AsyncClient) -> None:
    created = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/connections",
        json={
            "label": "ISP",
            "transport_kind": "ethernet",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "always",
            "metered": False,
            "metadata": {
                "monitoring_targets": [
                    {
                        "id": "target-gateway",
                        "label": "Gateway",
                        "address": "203.0.113.10",
                        "probe_type": "icmp",
                        "purpose": "gateway",
                        "monitoring": {
                            "enabled": True,
                            "source_type": "backend_synthetic",
                            "interval_seconds": 300,
                        },
                    }
                ]
            },
        },
    )

    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/target-gateway/run",
    )

    assert created.status_code == 201
    assert response.status_code == 201
    payload = response.json()
    assert payload["target_id"] == "target-gateway"
    assert payload["target_label"] == "Gateway"
    assert payload["target_address"] == "203.0.113.10"
    assert payload["probe_type"] == "icmp"
    assert payload["source_type"] == "backend_synthetic"
    assert payload["sample_kind"] == "automated"
    assert payload["reachable"] is False


@pytest.mark.asyncio
async def test_edge_agent_sample_computes_loss_from_packet_counts(client: AsyncClient) -> None:
    created = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/connections",
        json={
            "label": "Home",
            "transport_kind": "ethernet",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "always",
            "metered": False,
            "metadata": {
                "monitoring_targets": [
                    {
                        "id": "target-google-dns",
                        "label": "Google DNS",
                        "address": "8.8.8.8",
                        "probe_type": "icmp",
                        "purpose": "custom",
                        "monitoring": {
                            "enabled": True,
                            "source_type": "edge_agent",
                            "interval_seconds": 300,
                        },
                    }
                ]
            },
        },
    )

    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/target-google-dns/edge-samples",
        json={
            "agent_id": "macbook-home",
            "agent_label": "MacBook at home",
            "method": "icmp_sequence",
            "packet_count": 20,
            "packets_received": 19,
            "latency_ms": 24,
            "jitter_ms": 1.8,
            "duration_ms": 19024,
        },
    )

    assert created.status_code == 201
    assert response.status_code == 201
    payload = response.json()
    assert payload["source_type"] == "edge_agent"
    assert payload["sample_kind"] == "automated"
    assert payload["source"] == "edge_agent:macbook-home"
    assert payload["source_label"] == "MacBook at home"
    assert payload["target_id"] == "target-google-dns"
    assert payload["target_label"] == "Google DNS"
    assert payload["target_address"] == "8.8.8.8"
    assert payload["probe_type"] == "icmp"
    assert payload["packet_loss_percent"] == 5.0
    assert payload["measurement_metadata"]["agent_id"] == "macbook-home"
    assert payload["measurement_metadata"]["method"] == "icmp_sequence"
    assert payload["measurement_metadata"]["packet_count"] == 20
    assert payload["measurement_metadata"]["packets_received"] == 19
    assert payload["measurement_metadata"]["packets_lost"] == 1


@pytest.mark.asyncio
async def test_edge_agent_sample_rejects_received_count_above_sent(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/missing/edge-samples",
        json={
            "agent_id": "macbook-home",
            "method": "icmp_sequence",
            "packet_count": 20,
            "packets_received": 21,
            "latency_ms": 24,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_link_connection_patch_rejects_null_required_fields(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections",
        json={
            "label": "Local fiber",
            "transport_kind": "fiber",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "local",
            "metered": False,
        },
    )

    response = await client.patch(
        f"/api/v1/link/sites/00000000-0000-4000-8000-000000000002/connections/{created.json()['id']}",
        json={"label": None},
    )

    assert response.status_code == 422


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
