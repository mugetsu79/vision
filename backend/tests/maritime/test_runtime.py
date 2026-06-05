from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.maritime.service import MaritimeRuntimeService
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKS_ROOT = REPO_ROOT / "packs"


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )


class _FakeTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

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


def _create_app(context: TenantContext) -> FastAPI:
    pack_registry = PackRegistry(PACKS_ROOT)
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        packs=pack_registry,
        maritime=MaritimeRuntimeService(pack_registry=pack_registry),
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    context = _tenant_context()
    async with AsyncClient(
        transport=ASGITransport(app=_create_app(context)),
        base_url="http://test",
    ) as http_client:
        yield http_client


def test_maritime_runtime_requires_manifest_enabled_pack() -> None:
    pack_registry = PackRegistry(PACKS_ROOT)

    runtime = MaritimeRuntimeService(pack_registry=pack_registry).runtime()

    assert runtime.pack_id == "maritime-fleet"
    assert runtime.enabled is True
    assert runtime.implementation_commitment is True
    assert {"argus.link", "argus.fleet", "argus.billing", "argus.support"} <= set(
        runtime.required_core_capabilities
    )
    assert runtime.manifest_version == "vezor.io/v1alpha1"
    assert {template["id"] for template in runtime.scene_templates} >= {
        "gangway-access",
        "deck-presence",
        "port-call-evidence",
    }


@pytest.mark.asyncio
async def test_maritime_runtime_routes_return_same_pack_contribution(
    client: AsyncClient,
) -> None:
    maritime_response = await client.get(
        "/api/v1/maritime/runtime",
        headers={"Authorization": "Bearer token"},
    )
    pack_response = await client.get(
        "/api/v1/packs/maritime-fleet/runtime",
        headers={"Authorization": "Bearer token"},
    )

    assert maritime_response.status_code == 200
    assert pack_response.status_code == 200
    assert maritime_response.json() == pack_response.json()
    assert maritime_response.json()["pack_id"] == "maritime-fleet"
    assert maritime_response.json()["enabled"] is True
