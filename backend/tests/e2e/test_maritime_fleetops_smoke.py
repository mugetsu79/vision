from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient, Response

from argus.api.contracts import SiteCreate, SiteResponse, TenantContext
from argus.api.v1 import router
from argus.billing.service import BillingService
from argus.compat import UTC
from argus.core.security import AuthenticatedUser
from argus.fleet.service import FleetService
from argus.link.service import LinkService
from argus.maritime.evidence import MaritimeEvidenceService
from argus.maritime.service import MaritimeRuntimeService
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry
from argus.support.service import SupportNotFoundError, SupportService

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
CAMERA_ID = UUID("00000000-0000-4000-8000-000000000010")
SCENE_CONTRACT_ID = UUID("00000000-0000-4000-8000-000000000020")
NODE_ID = UUID("00000000-0000-4000-8000-000000000030")
INCIDENT_ID = UUID("00000000-0000-4000-8000-000000000040")
ARTIFACT_ID = UUID("00000000-0000-4000-8000-000000000050")
INCIDENT_TIME = datetime(2026, 6, 5, 9, 15, tzinfo=UTC)
PACKS_ROOT = Path(__file__).resolve().parents[3] / "packs"


def _user(role: RoleEnum) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=f"{role.value}-fleetops-smoke",
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
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request: object) -> AuthenticatedUser:
        return self.user


class _FakeSiteService:
    def __init__(self) -> None:
        self.sites: dict[tuple[UUID, UUID], SiteResponse] = {}

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

    async def create_site(self, tenant_context: TenantContext, payload: SiteCreate) -> SiteResponse:
        return self.add_site(
            tenant_id=tenant_context.tenant_id,
            site_id=uuid4(),
            name=payload.name,
        )

    async def get_site(self, tenant_context: TenantContext, site_id: UUID) -> SiteResponse:
        site = self.sites.get((tenant_context.tenant_id, site_id))
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found.",
            )
        return site

    async def delete_site(self, tenant_context: TenantContext, site_id: UUID) -> None:
        self.sites.pop((tenant_context.tenant_id, site_id), None)


class _FakeSupportResourceValidator:
    def __init__(self, site_service: _FakeSiteService) -> None:
        self.site_service = site_service

    async def validate_site(self, *, tenant_id: UUID, site_id: UUID) -> None:
        await self.site_service.get_site(_tenant_context(), site_id)

    async def validate_node(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        node_id: UUID,
    ) -> None:
        await self.validate_site(tenant_id=tenant_id, site_id=site_id)
        if node_id != NODE_ID:
            raise SupportNotFoundError("Node not found.")


class _FakeIncidentRuleService:
    def __init__(self) -> None:
        self.created: list[object] = []
        self.deleted: list[UUID] = []
        self.existing: list[object] = []

    async def list_rules(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> list[object]:
        return self.existing

    async def create_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: object,
    ) -> object:
        self.created.append(payload)
        return SimpleNamespace(id=UUID("00000000-0000-4000-8000-000000000031"))

    async def delete_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        rule_id: UUID,
    ) -> None:
        self.deleted.append(rule_id)


class _FakeCameraService:
    def __init__(self, incident_rules: _FakeIncidentRuleService) -> None:
        self.incident_rules = incident_rules
        self.updated_camera_id: UUID | None = None
        self.update_payload: object | None = None

    async def get_camera(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> object:
        return SimpleNamespace(
            active_classes=["boat"],
            runtime_vocabulary={"terms": ["boat"], "source": "manual", "version": 1},
            detection_regions=[],
            zones=[],
            privacy={"blur_faces": True, "blur_plates": True},
            recording_policy={"enabled": True, "mode": "event_clip"},
        )

    async def update_camera(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: object,
    ) -> object:
        self.updated_camera_id = camera_id
        self.update_payload = payload
        return SimpleNamespace(id=camera_id)

    async def get_worker_config(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> object:
        return SimpleNamespace(scene_contract_hash="a" * 64)


class _FakeSceneContractService:
    async def get_snapshot_by_hash(
        self,
        *,
        tenant_id: UUID,
        camera_id: UUID,
        contract_hash: str,
    ) -> object | None:
        return SimpleNamespace(id=SCENE_CONTRACT_ID, contract_hash=contract_hash)


def _tenant_context() -> TenantContext:
    user = _user(RoleEnum.ADMIN)
    return TenantContext(
        tenant_id=TENANT_ID,
        tenant_slug="argus-dev",
        user=user,
    )


def _create_app(user: AuthenticatedUser) -> FastAPI:
    pack_registry = PackRegistry(PACKS_ROOT)
    maritime = MaritimeRuntimeService(pack_registry=pack_registry)
    link = LinkService()
    sites = _FakeSiteService()
    incident_rules = _FakeIncidentRuleService()
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        packs=pack_registry,
        sites=sites,
        maritime=maritime,
        maritime_evidence=MaritimeEvidenceService(
            maritime_service=maritime,
            link_service=link,
            tenant_id=TENANT_ID,
        ),
        link=link,
        fleet=FleetService(),
        billing=BillingService(),
        support=SupportService(resource_validator=_FakeSupportResourceValidator(sites)),
        cameras=_FakeCameraService(incident_rules),
        incident_rules=incident_rules,
        scene_contracts=_FakeSceneContractService(),
    )
    app.state.security = _FakeSecurity(user)
    return app


@pytest_asyncio.fixture
async def app() -> FastAPI:
    return _create_app(_user(RoleEnum.ADMIN))


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


async def _created(response: Response) -> dict[str, Any]:
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def _ok(response: Response) -> dict[str, Any]:
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_maritime_fleetops_product_smoke(app: FastAPI, client: AsyncClient) -> None:
    services = app.state.services
    site = await services.sites.create_site(
        _tenant_context(),
        SiteCreate(name="MV Resolute Site", tz="UTC"),
    )

    vessel = await _created(
        await client.post(
            "/api/v1/maritime/vessels",
            json={
                "site_id": str(site.id),
                "name": "MV Resolute",
                "mmsi": "235012340",
                "imo_number": "9876543",
                "call_sign": "VZRS",
                "flag_state": "GB",
                "vessel_type": "offshore support",
                "owner_label": "North Sea Fleet",
                "manager_label": "Vezor Marine",
                "metadata": {
                    "evidence_queue": "4 pending exports",
                    "link_state": "satellite_degraded",
                    "templates": ["Gangway Access"],
                },
            },
        )
    )
    assert vessel["site_id"] == str(site.id)

    group = await _created(
        await client.post(
            "/api/v1/fleet/site-groups",
            json={
                "label": "North Sea Fleet",
                "kind": "fleet",
                "pack_id": "maritime-fleet",
            },
        )
    )
    hierarchy = await _ok(
        await client.put(
            "/api/v1/fleet/hierarchy",
            json={
                "nodes": [
                    {"id": "fleet-root", "label": group["label"], "kind": "site_group"},
                    {
                        "id": "mv-resolute",
                        "parent_id": "fleet-root",
                        "site_id": str(site.id),
                        "label": "MV Resolute",
                        "kind": "site",
                        "pack_id": "maritime-fleet",
                    },
                ]
            },
        )
    )
    assert len(hierarchy["nodes"]) == 2
    rotation = await _created(
        await client.post(
            "/api/v1/fleet/rotation-groups",
            json={
                "label": "FleetOps duty watch",
                "member_user_ids": ["ops-a", "ops-b"],
                "pack_labels": {"maritime-fleet": "FleetOps"},
            },
        )
    )
    assignment = await _created(
        await client.post(
            "/api/v1/fleet/site-assignments",
            json={
                "site_id": str(site.id),
                "assignee_type": "support_queue",
                "assignee_id": "fleetops-duty",
                "rotation_group_id": rotation["id"],
                "pack_id": "maritime-fleet",
            },
        )
    )
    assert assignment["site_id"] == str(site.id)
    services.fleet.upsert_site_state(
        tenant_id=TENANT_ID,
        site_id=site.id,
        heartbeat_status="stale",
        link_state="degraded",
        runtime_status="stopped",
        evidence_backlog_count=4,
        active_incident_count=1,
        privacy_status="ok",
        model_artifact_status="mismatch",
        last_heartbeat_at=INCIDENT_TIME - timedelta(minutes=45),
        pack_id="maritime-fleet",
    )
    exceptions = await _ok(await client.get("/api/v1/fleet/exceptions"))
    assert {item["kind"] for item in exceptions["items"]} >= {
        "active_incident",
        "degraded_link",
        "evidence_backlog",
        "model_artifact_mismatch",
        "stale_heartbeat",
        "stopped_worker",
    }

    node = await _created(
        await client.post(
            "/api/v1/billing/nodes",
            json={
                "label": "MV Resolute",
                "kind": "vessel",
                "pack_id": "maritime-fleet",
            },
        )
    )
    account = await _created(
        await client.post(
            "/api/v1/billing/accounts",
            json={
                "name": "North Sea Fleet",
                "node_ids": [node["id"]],
                "pack_id": "maritime-fleet",
            },
        )
    )
    entitlement = await _created(
        await client.post(
            "/api/v1/billing/entitlements",
            json={
                "account_id": account["id"],
                "feature_key": "fleetops_runtime",
                "effective_from": "2026-06-01",
                "pack_id": "maritime-fleet",
                "usage_limit": "500",
            },
        )
    )
    assert entitlement["pack_id"] == "maritime-fleet"
    await _created(
        await client.post(
            "/api/v1/billing/price-books",
            json={
                "currency": "USD",
                "effective_from": "2026-06-01",
                "meter_prices": {
                    "vessel_month": "299.00",
                    "evidence_pack_export": "9.00",
                    "support_session_hour": "125.00",
                },
            },
        )
    )

    budget = await _ok(
        await client.put(
            f"/api/v1/link/sites/{site.id}/budget",
            json={"monthly_bytes": 5000000000, "bulk_daily_bytes": 150000000},
        )
    )
    assert budget["site_id"] == str(site.id)
    await _created(
        await client.post(
            f"/api/v1/link/sites/{site.id}/probes",
            json={
                "latency_ms": 1200,
                "throughput_mbps": 1.8,
                "packet_loss_percent": 8.5,
                "reachable": True,
                "source": "carrier-terminal",
            },
        )
    )
    queue_item = services.link.enqueue_transfer(
        tenant_id=TENANT_ID,
        site_id=site.id,
        priority_lane="evidence",
        byte_size=42000000,
        source_object_type="evidence_artifact",
        source_object_id=ARTIFACT_ID,
        camera_id=CAMERA_ID,
        incident_id=INCIDENT_ID,
        evidence_artifact_id=ARTIFACT_ID,
    )
    link_status = await _ok(await client.get(f"/api/v1/link/sites/{site.id}/status"))
    assert link_status["link_state"] == "degraded"
    queue = await client.get(f"/api/v1/link/sites/{site.id}/queue")
    assert queue.status_code == 200
    assert queue.json()[0]["id"] == str(queue_item.id)

    template = await _ok(
        await client.post(
            f"/api/v1/maritime/cameras/{CAMERA_ID}/apply-template",
            json={"template_id": "gangway-access"},
        )
    )
    assert template["scene_contract_snapshot_id"] == str(SCENE_CONTRACT_ID)
    assert services.cameras.updated_camera_id == CAMERA_ID

    voyage = await _created(
        await client.post(
            f"/api/v1/maritime/vessels/{vessel['id']}/voyages",
            json={
                "name": "Rotterdam Service Leg",
                "voyage_number": "VZ-0605",
                "origin": "Aberdeen",
                "destination": "Rotterdam",
                "scheduled_departure_at": "2026-06-05T06:00:00Z",
                "scheduled_arrival_at": "2026-06-05T18:00:00Z",
            },
        )
    )
    await _ok(await client.post(f"/api/v1/maritime/voyages/{voyage['id']}/activate"))
    port_call = await _created(
        await client.post(
            f"/api/v1/maritime/voyages/{voyage['id']}/port-calls",
            json={
                "port_name": "Rotterdam",
                "un_locode": "NLRTM",
                "terminal_name": "Waalhaven",
                "berth": "7",
                "eta": "2026-06-05T17:45:00Z",
                "etd": "2026-06-06T04:30:00Z",
                "link_profile": "port_wifi",
            },
        )
    )
    await _created(
        await client.post(
            "/api/v1/maritime/ingest/ais",
            json={
                "vessel_id": vessel["id"],
                "source": "ais_json",
                "payload": {
                    "mmsi": "235012340",
                    "lat": 51.9244,
                    "lon": 4.4777,
                    "sog": 7.1,
                    "cog": 92.0,
                    "heading": 91.0,
                    "reported_at": INCIDENT_TIME.isoformat(),
                    "navigational_status": "under_way",
                },
            },
        )
    )
    await _created(
        await client.post(
            "/api/v1/maritime/ingest/carrier-terminal",
            json={
                "vessel_id": vessel["id"],
                "payload": {
                    "terminal_id": "st-mv-resolute",
                    "provider": "managed_satellite",
                    "transport_kind": "satellite",
                    "status": "degraded",
                    "link_state": "satellite_degraded",
                    "downlink_mbps": 1.8,
                    "uplink_mbps": 0.8,
                    "latency_ms": 1200,
                    "packet_loss_percent": 8.5,
                    "last_seen_at": INCIDENT_TIME.isoformat(),
                },
            },
        )
    )
    await _created(
        await client.post(
            "/api/v1/maritime/ingest/carrier-terminal",
            json={
                "vessel_id": vessel["id"],
                "payload": {
                    "terminal_id": "lte-mv-resolute",
                    "provider": "managed_lte",
                    "transport_kind": "lte",
                    "status": "online",
                    "link_state": "recovering",
                    "downlink_mbps": 18.0,
                    "uplink_mbps": 6.0,
                    "latency_ms": 80,
                    "packet_loss_percent": 0.8,
                    "last_seen_at": INCIDENT_TIME.isoformat(),
                },
            },
        )
    )
    fiber_connection = await _created(
        await client.post(
            f"/api/v1/link/sites/{site.id}/connections",
            json={
                "label": "Port fiber",
                "transport_kind": "fiber",
                "status": "online",
                "priority_rank": 5,
                "availability_scope": "local",
                "metered": False,
                "expected_downlink_mbps": 250.0,
                "expected_uplink_mbps": 250.0,
            },
        )
    )
    assert fiber_connection["transport_kind"] == "fiber"
    carrier_selection = await _ok(
        await client.get(
            f"/api/v1/maritime/vessels/{vessel['id']}/carrier-selection",
            params={"priority_lane": "bulk"},
        )
    )
    assert carrier_selection == {
        "transport": "fiber",
        "defer": False,
        "reason": "core_connection_selected",
    }

    services.maritime_evidence.register_camera_site(camera_id=CAMERA_ID, site_id=site.id)
    services.maritime_evidence.register_incident(
        incident_id=INCIDENT_ID,
        camera_id=CAMERA_ID,
        incident_time=INCIDENT_TIME,
        scene_contract_hash="scene-contract-hash",
        privacy_manifest_hash="privacy-manifest-hash",
        runtime_passport_hash="runtime-passport-hash",
        recording_policy={"mode": "event_clip", "pre_seconds": 4, "post_seconds": 8},
        artifact_hashes={ARTIFACT_ID: "sha256:artifact-hash"},
        ledger_summary={"entries": 3, "latest_sequence": 19},
        time_source={"source": "ptp", "offset_ms": 4},
    )
    context = await _ok(
        await client.get(
            "/api/v1/maritime/evidence-context",
            params={"incident_id": str(INCIDENT_ID)},
        )
    )
    assert context["vessel_name"] == "MV Resolute"
    assert context["port_call_id"] == port_call["id"]
    assert context["telemetry_freshness"] == {"ais": "fresh", "carrier": "fresh"}
    export = await _created(
        await client.post(
            "/api/v1/maritime/evidence-exports",
            json={"incident_id": str(INCIDENT_ID)},
        )
    )
    assert export["artifact_hashes"] == {str(ARTIFACT_ID): "sha256:artifact-hash"}
    assert export["metadata"]["maritime_context"]["vessel_name"] == "MV Resolute"
    assert export["metadata"]["link_passport_hash"].startswith("sha256:")

    usage = await _created(
        await client.post(
            "/api/v1/billing/usage",
            json={
                "meter_key": "evidence_pack_export",
                "quantity": "1",
                "account_id": account["id"],
                "node_id": node["id"],
                "source_object_type": "evidence_export",
                "source_object_id": export["id"],
                "occurred_on": "2026-06-05",
                "pack_id": "maritime-fleet",
                "metadata": {"incident_id": str(INCIDENT_ID), "vessel_id": vessel["id"]},
            },
        )
    )
    assert usage["pack_id"] == "maritime-fleet"
    invoice = await _created(
        await client.post(
            "/api/v1/billing/invoice-runs",
            json={
                "account_id": account["id"],
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
            },
        )
    )
    assert invoice["line_items"][0]["meter_key"] == "evidence_pack_export"
    maritime_usage = await _ok(await client.get("/api/v1/maritime/billing/usage"))
    assert maritime_usage["items"][0]["label"] == "evidence pack export"

    bundle = await _created(
        await client.post(
            "/api/v1/support/bundles",
            json={
                "site_id": str(site.id),
                "node_id": str(NODE_ID),
                "include_logs": True,
                "pack_id": "maritime-fleet",
                "diagnostics": {
                    "carrier_state": "degraded",
                    "api_token": "should-be-redacted",
                    "last_export_id": export["id"],
                },
            },
        )
    )
    assert bundle["pack_id"] == "maritime-fleet"
    assert "should-be-redacted" not in str(bundle["payload"])
    session = await _created(
        await client.post(
            "/api/v1/support/sessions",
            json={
                "site_id": str(site.id),
                "node_id": str(NODE_ID),
                "operator_id": "fleetops-support",
                "metadata": {"reason": "link diagnostics"},
            },
        )
    )
    assert session["usage_meter_key"] == "support_session_hour"
    tunnel = await _created(
        await client.post(
            "/api/v1/support/tunnels",
            json={
                "site_id": str(site.id),
                "node_id": str(NODE_ID),
                "transport": "ssh_reverse",
                "credential_ref": "vault://fleetops/mv-resolute/support",
                "relay_host": "relay.support.vezor.test",
                "allowed_ports": [22],
                "dispatch_method": "supervisor_poll",
                "metadata": {"link": "satellite"},
            },
        )
    )
    assert tunnel["transport"] == "ssh_reverse"
    assert len(tunnel["credential_ref_hash"]) == 64
    assert tunnel["credential_ref"] == "vault://fleetops/mv-resolute/support"
    break_glass = await _created(
        await client.post(
            "/api/v1/support/break-glass",
            json={
                "reason": "Recover constrained-link export queue",
                "scope": {"site_id": str(site.id), "pack_id": "maritime-fleet"},
                "actor_id": "fleetops-support",
                "approver_id": "duty-manager",
            },
        )
    )
    closed = await _ok(
        await client.post(
            f"/api/v1/support/break-glass/{break_glass['id']}/close",
            json={"closure_notes": "Queue recovered and access revoked."},
        )
    )
    assert closed["ended_at"] is not None
    onboarding = await _created(
        await client.post(
            "/api/v1/support/onboarding-checks/run",
            json={
                "site_id": str(site.id),
                "pack_id": "maritime-fleet",
                "metadata": {"vessel_id": vessel["id"]},
            },
        )
    )
    assert onboarding["pack_id"] == "maritime-fleet"
    assert {check["key"] for check in onboarding["checks"]} >= {
        "link_state",
        "billing_entitlement",
        "support_readiness",
    }
