from __future__ import annotations

from datetime import date
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
from argus.models.enums import RoleEnum

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")


@pytest.mark.asyncio
async def test_billing_account_route_creates_packless_account(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/billing/accounts",
        json={"name": "Packless account", "node_ids": []},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Packless account"
    assert response.json()["pack_id"] is None


@pytest.mark.asyncio
async def test_billing_routes_are_tenant_scoped(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/billing/accounts?tenant_id=00000000-0000-4000-8000-000000000099"
    )

    assert response.status_code in {403, 404}


@pytest.mark.asyncio
async def test_billing_node_route_returns_404_for_invalid_parent(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/billing/nodes",
        json={
            "label": "Invalid child",
            "kind": "deployment",
            "parent_id": "00000000-0000-4000-8000-000000000099",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_billing_account_route_returns_404_for_invalid_node(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/billing/accounts",
        json={
            "name": "Invalid account",
            "node_ids": ["00000000-0000-4000-8000-000000000099"],
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_billing_usage_route_returns_404_for_invalid_account_scope(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/billing/usage",
        json={
            "meter_key": "support_session_hour",
            "quantity": "1",
            "account_id": "00000000-0000-4000-8000-000000000099",
            "source_object_type": "support_session",
            "source_object_id": "00000000-0000-4000-8000-000000000020",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_billing_invoice_route_aggregates_usage(client: AsyncClient) -> None:
    account_response = await client.post(
        "/api/v1/billing/accounts",
        json={"name": "Invoice account", "node_ids": []},
    )
    await client.post(
        "/api/v1/billing/price-books",
        json={
            "currency": "USD",
            "effective_from": "2026-06-01",
            "meter_prices": {"support_session_hour": "25.00"},
        },
    )
    await client.post(
        "/api/v1/billing/usage",
        json={
            "meter_key": "support_session_hour",
            "quantity": "2",
            "source_object_type": "support_session",
            "source_object_id": "00000000-0000-4000-8000-000000000020",
            "occurred_on": "2026-06-15",
        },
    )

    response = await client.post(
        "/api/v1/billing/invoice-runs",
        json={
            "account_id": account_response.json()["id"],
            "period_start": "2026-06-01",
            "period_end": "2026-07-01",
        },
    )

    assert response.status_code == 201
    assert response.json()["line_items"][0]["total"] == "50.00"


@pytest.mark.asyncio
async def test_billing_meters_route_exposes_core_meters(client: AsyncClient) -> None:
    response = await client.get("/api/v1/billing/meters")

    assert response.status_code == 200
    meter_keys = {meter["meter_key"] for meter in response.json()["items"]}
    assert {"support_session_hour", "evidence_pack_export"} <= meter_keys
    assert all(meter["pack_id"] is None for meter in response.json()["items"])


@pytest.mark.asyncio
async def test_billing_export_route_returns_invoice_payload(client: AsyncClient) -> None:
    account = await client.post(
        "/api/v1/billing/accounts",
        json={"name": "Export account", "node_ids": []},
    )
    await client.post(
        "/api/v1/billing/usage",
        json={
            "meter_key": "support_session_hour",
            "quantity": "1",
            "source_object_type": "support_session",
            "source_object_id": "00000000-0000-4000-8000-000000000024",
        },
    )
    invoice = await client.post(
        "/api/v1/billing/invoice-runs",
        json={
            "account_id": account.json()["id"],
            "period_start": str(date(2026, 6, 1)),
            "period_end": str(date(2026, 7, 1)),
        },
    )
    export = client._transport.app.state.services.billing.export_billing(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID,
        invoice_run_id=UUID(invoice.json()["id"]),
        format="json",
    )

    response = await client.get(f"/api/v1/billing/exports/{export.id}")

    assert response.status_code == 200
    assert response.json()["payload"]["invoice_run_id"] == invoice.json()["id"]


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    app = FastAPI()
    app.include_router(router)
    user = _user(RoleEnum.ADMIN)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        billing=BillingService(),
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
        if explicit_tenant_id is not None and explicit_tenant_id != TENANT_ID:
            return self.context.model_copy(update={"tenant_id": explicit_tenant_id})
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
