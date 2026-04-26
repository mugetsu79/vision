from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import ExportArtifact, TenantContext
from argus.api.v1.export import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import HistoryMetric, RoleEnum


@pytest.fixture
def tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="test-tenant",
        user=AuthenticatedUser(
            subject="u",
            email="u@example.com",
            role=RoleEnum.VIEWER,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )


class _FakeHistoryService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def export_history(self, *args, **kwargs) -> ExportArtifact:
        self.calls.append(kwargs)
        return ExportArtifact(
            filename="history.csv",
            media_type="text/csv; charset=utf-8",
            content=b"bucket,class_name,event_count\n",
        )


def _app_with_fakes(history_service: _FakeHistoryService, context: TenantContext) -> FastAPI:
    from argus.api.dependencies import get_app_services, get_tenant_context
    from argus.core.security import get_current_user

    app = FastAPI()
    app.include_router(router)

    class _Services:
        history = history_service

    async def _get_services() -> _Services:
        return _Services()

    async def _get_context() -> TenantContext:
        return context

    async def _get_user() -> AuthenticatedUser:
        return AuthenticatedUser(
            subject="u",
            email="u@example.com",
            role=RoleEnum.VIEWER,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        )

    app.dependency_overrides[get_app_services] = _get_services
    app.dependency_overrides[get_tenant_context] = _get_context
    app.dependency_overrides[get_current_user] = _get_user
    return app


@pytest.mark.asyncio
async def test_export_endpoint_passes_metric(tenant_context: TenantContext) -> None:
    service = _FakeHistoryService()
    app = _app_with_fakes(service, tenant_context)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/export",
            params={
                "from": "2026-04-23T00:00:00Z",
                "to": "2026-04-23T06:00:00Z",
                "granularity": "1h",
                "metric": "count_events",
                "format": "csv",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="history.csv"'
    assert service.calls[-1]["metric"] == HistoryMetric.COUNT_EVENTS
