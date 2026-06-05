from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import TenantContext
from argus.api.v1 import router
from argus.billing.service import BillingService
from argus.core.security import AuthenticatedUser
from argus.maritime.billing import maritime_billing_meter_catalog
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")


def test_meter_positioning_labels_capacity_base_and_value_meters() -> None:
    catalog = maritime_billing_meter_catalog()

    assert catalog["capacity_guardrails"] == [
        "camera_capacity_tier",
        "managed_edge_node",
        "retained_evidence_gb",
        "managed_link_gb",
    ]
    assert catalog["base_commercial_unit"] == "vessel_month"
    assert {
        "evidence_pack_export",
        "support_session_hour",
        "operational_incident_resolved",
    } <= set(catalog["value_meters"])


@pytest.mark.asyncio
async def test_maritime_rollups_label_reseller_owner_charterer_and_vessel(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/maritime/billing/rollups")

    assert response.status_code == 200
    labels = response.json()["labels"]
    assert {"reseller", "fleet_manager", "owner", "charterer", "vessel"} <= set(labels)
    assert response.json()["meters"]["base_commercial_unit"] == "vessel_month"


@pytest.mark.asyncio
async def test_maritime_billing_usage_labels_pack_usage(client: AsyncClient) -> None:
    services = client._transport.app.state.services  # type: ignore[attr-defined]
    services.billing.record_usage(
        tenant_id=TENANT_ID,
        meter_key="vessel_month",
        quantity=1,
        source_object_type="vessel",
        source_object_id=UUID("00000000-0000-4000-8000-000000000010"),
        pack_id="maritime-fleet",
    )

    response = await client.get("/api/v1/maritime/billing/usage")

    assert response.status_code == 200
    assert response.json()["items"][0]["pack_id"] == "maritime-fleet"
    assert response.json()["items"][0]["label"] == "vessel month"


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    app = FastAPI()
    app.include_router(router)
    user = _user(RoleEnum.ADMIN)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        billing=BillingService(),
        packs=PackRegistry(),
    )
    app.state.security = _FakeSecurity(user)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


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
