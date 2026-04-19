from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from argus.core.config import Settings
from argus.models.tables import Tenant
from argus.services.app import TenancyService


class _FakeResult:
    def __init__(self, tenant: Tenant | None) -> None:
        self.tenant = tenant

    def scalar_one_or_none(self) -> Tenant | None:
        return self.tenant


class _FakeSession:
    def __init__(self, state: dict[str, Tenant | None]) -> None:
        self.state = state

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def execute(self, statement) -> _FakeResult:  # noqa: ANN001
        return _FakeResult(self.state["tenant"])

    def add(self, tenant: Tenant) -> None:
        self.state["tenant"] = tenant

    async def commit(self) -> None:
        return None

    async def refresh(self, tenant: Tenant) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _FakeSessionFactory:
    def __init__(self, tenant: Tenant | None = None) -> None:
        self.state: dict[str, Tenant | None] = {"tenant": tenant}

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.state)


@pytest.mark.asyncio
async def test_resolve_context_bootstraps_realm_tenant_in_development() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    session_factory = _FakeSessionFactory()
    service = TenancyService(session_factory=session_factory, settings=settings)
    user = SimpleNamespace(is_superadmin=False, tenant_context=None, realm="argus-dev")

    context = await service.resolve_context(user=user)

    assert context.tenant_slug == "argus-dev"
    assert context.tenant_id == session_factory.state["tenant"].id
    assert session_factory.state["tenant"].name == "Argus Dev"


@pytest.mark.asyncio
async def test_resolve_context_keeps_missing_tenant_strict_outside_development() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        enable_startup_services=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    service = TenancyService(session_factory=_FakeSessionFactory(), settings=settings)
    user = SimpleNamespace(is_superadmin=False, tenant_context=None, realm="argus-dev")

    with pytest.raises(HTTPException) as exc_info:
        await service.resolve_context(user=user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Tenant not found."
