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
MASTER_SITE_ID = UUID("00000000-0000-4000-8000-000000000003")


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
    def __init__(self, *, edge_site_ids: set[UUID] | None = None) -> None:
        self.edge_site_ids = edge_site_ids or {KNOWN_SITE_ID}

    async def list_sites(self, tenant_context: TenantContext) -> list[SiteResponse]:
        return [
            self._site_response(tenant_context, KNOWN_SITE_ID, "Packless Site"),
            self._site_response(tenant_context, MASTER_SITE_ID, "Vezor Master"),
        ]

    async def list_edge_sites(self, tenant_context: TenantContext) -> list[SiteResponse]:
        sites = await self.list_sites(tenant_context)
        return [site for site in sites if site.id in self.edge_site_ids]

    async def list_link_performance_sites(
        self,
        tenant_context: TenantContext,
    ) -> list[SiteResponse]:
        return await self.list_sites(tenant_context)

    async def get_site(self, tenant_context: TenantContext, site_id: UUID) -> SiteResponse:
        if site_id == KNOWN_SITE_ID:
            return self._site_response(tenant_context, site_id, "Packless Site")
        if site_id == MASTER_SITE_ID:
            return self._site_response(tenant_context, site_id, "Vezor Master")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found.")

    async def is_edge_site(self, tenant_context: TenantContext, site_id: UUID) -> bool:
        await self.get_site(tenant_context, site_id)
        return site_id in self.edge_site_ids

    def _site_response(
        self,
        tenant_context: TenantContext,
        site_id: UUID,
        name: str,
    ) -> SiteResponse:
        if site_id not in {KNOWN_SITE_ID, MASTER_SITE_ID}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found.")
        return SiteResponse(
            id=site_id,
            tenant_id=tenant_context.tenant_id,
            name=name,
            description=None,
            tz="UTC",
            geo_point=None,
            site_kind="control_plane" if site_id == MASTER_SITE_ID else "edge",
            created_at=datetime.now(tz=UTC),
        )


def _create_app(
    user: AuthenticatedUser,
    *,
    include_sites: bool = True,
    edge_site_ids: set[UUID] | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        packs=PackRegistry(),
        link=LinkService(),
    )
    if include_sites:
        services.sites = _FakeSiteService(edge_site_ids=edge_site_ids)
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
        "site_role",
        "capabilities",
    } <= set(payload[0])
    assert "vessel" not in payload[0]
    assert "voyage" not in payload[0]


@pytest.mark.asyncio
async def test_link_site_summary_route_lists_edge_and_control_plane_target_sites(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/link/sites/summary")

    assert response.status_code == 200
    sites_by_id = {item["site_id"]: item for item in response.json()}
    assert sites_by_id[str(KNOWN_SITE_ID)]["site_role"] == "edge"
    assert sites_by_id[str(MASTER_SITE_ID)]["site_role"] == "control_plane"
    assert sites_by_id[str(KNOWN_SITE_ID)]["capabilities"]["can_configure_links"] is True
    assert sites_by_id[str(MASTER_SITE_ID)]["capabilities"]["can_configure_links"] is False
    assert sites_by_id[str(MASTER_SITE_ID)]["capabilities"]["can_receive_edge_probes"] is True


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
async def test_edge_agent_sample_can_target_control_plane_site(client: AsyncClient) -> None:
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
                        "id": "target-vezor-master",
                        "label": "Vezor Master",
                        "address": "master.vezor.local",
                        "target_site_id": str(MASTER_SITE_ID),
                        "probe_type": "udp",
                        "purpose": "control_plane",
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
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/target-vezor-master/edge-samples",
        json={
            "agent_id": "macbook-home",
            "agent_label": "MacBook at home",
            "method": "udp_sequence",
            "packet_count": 25,
            "packets_received": 24,
            "latency_ms": 31,
        },
    )
    master_history = await client.get(f"/api/v1/link/sites/{MASTER_SITE_ID}/probes")

    assert created.status_code == 201
    assert response.status_code == 201
    payload = response.json()
    assert payload["site_id"] == str(KNOWN_SITE_ID)
    assert payload["target_site_id"] == str(MASTER_SITE_ID)
    assert master_history.status_code == 200
    assert master_history.json()[0]["id"] == payload["id"]
    assert master_history.json()[0]["site_id"] == str(KNOWN_SITE_ID)


@pytest.mark.asyncio
async def test_edge_agent_udp_sequence_sample_stores_reflector_metadata(
    client: AsyncClient,
) -> None:
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
                        "id": "target-vezor-master",
                        "label": "Vezor Master reflector",
                        "address": "master.vezor.local",
                        "target_site_id": str(MASTER_SITE_ID),
                        "probe_type": "udp",
                        "purpose": "vezor_control",
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
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/target-vezor-master/edge-samples",
        json={
            "agent_id": "macbook-home",
            "method": "udp_sequence",
            "packet_count": 50,
            "packets_received": 49,
            "latency_ms": 24,
            "jitter_ms": 2.1,
            "duration_ms": 5900,
            "measurement_metadata": {
                "protocol": "vezor_udp_sequence",
                "reflector_profile_id": "master-reflector-default",
                "reflector_address": "master.vezor.local",
                "reflector_port": 8622,
                "packets_late": 0,
                "packets_duplicate": 0,
                "packets_out_of_order": 0,
                "rtt_avg_ms": 24.2,
                "rtt_variation_ms": 2.1,
            },
        },
    )

    assert created.status_code == 201
    assert response.status_code == 201
    metadata = response.json()["measurement_metadata"]
    assert metadata["protocol"] == "vezor_udp_sequence"
    assert metadata["reflector_profile_id"] == "master-reflector-default"
    assert metadata["reflector_address"] == "master.vezor.local"
    assert metadata["reflector_port"] == 8622
    assert metadata["packets_lost"] == 1
    assert metadata["packets_duplicate"] == 0
    assert metadata["packets_out_of_order"] == 0
    assert metadata["rtt_avg_ms"] == 24.2


@pytest.mark.asyncio
async def test_edge_agent_udp_sequence_sample_rejects_non_udp_target(
    client: AsyncClient,
) -> None:
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
                        "id": "target-https",
                        "label": "Vezor Master API",
                        "address": "https://master.vezor.local/healthz",
                        "probe_type": "https",
                        "purpose": "vezor_control",
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
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/probe-targets/target-https/edge-samples",
        json={
            "agent_id": "macbook-home",
            "method": "udp_sequence",
            "packet_count": 50,
            "packets_received": 49,
            "latency_ms": 24,
        },
    )

    assert created.status_code == 201
    assert response.status_code == 422
    assert response.json()["detail"] == "UDP sequence samples require a UDP probe target."


@pytest.mark.asyncio
async def test_master_reflector_profile_api_defaults_disabled(client: AsyncClient) -> None:
    response = await client.get("/api/v1/link/reflectors/master")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_kind"] == "master"
    assert payload["site_id"] == str(MASTER_SITE_ID)
    assert payload["enabled"] is False
    assert payload["mode"] == "vezor_udp_sequence"
    assert payload["udp_port"] == 8622
    assert payload["last_status"] == "disabled"
    assert payload["secret_state"] == "missing"
    assert "encrypted_secret" not in payload


@pytest.mark.asyncio
async def test_master_reflector_profile_mutations_require_admin(
    viewer_client: AsyncClient,
) -> None:
    response = await viewer_client.post(
        "/api/v1/link/reflectors/master/enable",
        json={"public_address": "vezor.example.local"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_master_reflector_profile_enable_update_disable_and_rotate(
    client: AsyncClient,
) -> None:
    enabled = await client.post(
        "/api/v1/link/reflectors/master/enable",
        json={
            "public_address": "vezor.example.local",
            "bind_address": "0.0.0.0",
            "udp_port": 8622,
            "rate_limit_pps_per_source": 75,
        },
    )
    updated = await client.put(
        "/api/v1/link/reflectors/master",
        json={
            "public_address": "master.vezor.local",
            "udp_port": 8623,
            "allowed_source_cidrs": ["198.51.100.0/24"],
        },
    )
    rotated = await client.post("/api/v1/link/reflectors/master/rotate-key")
    disabled = await client.post("/api/v1/link/reflectors/master/disable")

    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True
    assert enabled.json()["secret_state"] == "present"
    assert enabled.json()["last_status"] == "starting"
    assert updated.status_code == 200
    assert updated.json()["public_address"] == "master.vezor.local"
    assert updated.json()["udp_port"] == 8623
    assert updated.json()["allowed_source_cidrs"] == ["198.51.100.0/24"]
    assert rotated.status_code == 200
    assert rotated.json()["key_id"] != enabled.json()["key_id"]
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert disabled.json()["last_status"] == "disabled"


@pytest.mark.asyncio
async def test_control_target_helper_creates_https_only_master_target(
    client: AsyncClient,
) -> None:
    created = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/connections",
        json={
            "label": "Home",
            "transport_kind": "ethernet",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "always",
            "metered": False,
        },
    )

    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/control-targets/master",
        json={
            "mode": "https_only",
            "connection_id": created.json()["id"],
            "address": "https://vezor.example.local/healthz",
            "interval_seconds": 300,
        },
    )

    assert created.status_code == 201
    assert response.status_code == 201
    payload = response.json()
    targets = payload["metadata"]["monitoring_targets"]
    assert targets == [
        {
            "id": "vezor-master-https",
            "label": "Vezor Master API",
            "address": "https://vezor.example.local/healthz",
            "target_site_id": str(MASTER_SITE_ID),
            "probe_type": "https",
            "purpose": "vezor_control",
            "monitoring": {
                "enabled": True,
                "source_type": "edge_agent",
                "interval_seconds": 300,
            },
            "loss_method": "icmp_sequence",
            "loss_packet_count": 20,
        }
    ]


@pytest.mark.asyncio
async def test_control_target_helper_rejects_udp_when_reflector_disabled(
    client: AsyncClient,
) -> None:
    created = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/connections",
        json={
            "label": "Home",
            "transport_kind": "ethernet",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "always",
            "metered": False,
        },
    )

    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/control-targets/master",
        json={"mode": "udp_reflector", "connection_id": created.json()["id"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Master reflector is disabled."


@pytest.mark.asyncio
async def test_control_target_helper_creates_udp_reflector_target_when_enabled(
    client: AsyncClient,
) -> None:
    await client.post(
        "/api/v1/link/reflectors/master/enable",
        json={"public_address": "vezor.example.local"},
    )
    created = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/connections",
        json={
            "label": "Home",
            "transport_kind": "ethernet",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "always",
            "metered": False,
        },
    )

    response = await client.post(
        f"/api/v1/link/sites/{KNOWN_SITE_ID}/control-targets/master",
        json={
            "mode": "udp_reflector",
            "connection_id": created.json()["id"],
            "packet_count": 50,
            "packet_spacing_ms": 100,
            "loss_timeout_ms": 1000,
            "dscp": 46,
        },
    )

    assert response.status_code == 201
    targets = response.json()["metadata"]["monitoring_targets"]
    assert targets[0]["id"] == "vezor-master-udp-reflector"
    assert targets[0]["target_site_id"] == str(MASTER_SITE_ID)
    assert targets[0]["probe_type"] == "udp"
    assert targets[0]["loss_method"] == "udp_sequence"
    assert targets[0]["reflector_profile_id"] == "master-reflector-default"
    assert targets[0]["reflector_address"] == "vezor.example.local"
    assert targets[0]["reflector_port"] == 8622
    assert targets[0]["loss_packet_count"] == 50
    assert targets[0]["loss_packet_spacing_ms"] == 100
    assert targets[0]["loss_timeout_ms"] == 1000
    assert targets[0]["loss_dscp"] == 46


@pytest.mark.asyncio
async def test_control_target_helper_rejects_master_as_source_site(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/link/sites/{MASTER_SITE_ID}/control-targets/master",
        json={"mode": "https_only"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Core Link can only be configured for edge sites."


@pytest.mark.asyncio
async def test_link_configuration_rejects_master_or_non_edge_site(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/link/sites/{MASTER_SITE_ID}/connections",
        json={
            "label": "Master loopback",
            "transport_kind": "ethernet",
            "status": "online",
            "priority_rank": 5,
            "availability_scope": "always",
            "metered": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Core Link can only be configured for edge sites."


@pytest.mark.asyncio
async def test_link_probe_sample_rejects_master_or_non_edge_site(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/link/sites/{MASTER_SITE_ID}/probes",
        json={
            "latency_ms": 12,
            "throughput_mbps": 50,
            "packet_loss_percent": 0,
            "reachable": True,
            "source": "manual:operator-console",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Core Link probes can only be recorded for edge sites."


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
