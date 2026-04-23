from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    HistoryClassEntry,
    HistoryClassesResponse,
    HistorySeriesResponse,
    HistorySeriesRow,
    TenantContext,
)
from argus.api.v1.history import router


@pytest.fixture
def tenant_context() -> TenantContext:
    from argus.core.security import AuthenticatedUser
    from argus.models.enums import RoleEnum

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

    async def query_history(self, *args, **kwargs):
        return []

    async def query_series(self, *args, **kwargs) -> HistorySeriesResponse:
        self.calls.append({"kind": "series", **kwargs})
        now = datetime(2026, 4, 23, tzinfo=UTC)
        return HistorySeriesResponse(
            granularity=kwargs.get("granularity", "1h"),
            class_names=["car"],
            rows=[
                HistorySeriesRow(
                    bucket=now,
                    values={"car": 5},
                    total_count=5,
                    speed_p50={"car": 42.0} if kwargs.get("include_speed") else None,
                    speed_p95={"car": 55.0} if kwargs.get("include_speed") else None,
                    speed_sample_count={"car": 5} if kwargs.get("include_speed") else None,
                    over_threshold_count=(
                        {"car": 2} if kwargs.get("speed_threshold") is not None else None
                    ),
                ),
            ],
            granularity_adjusted=False,
            speed_classes_capped=False,
            speed_classes_used=["car"] if kwargs.get("include_speed") else None,
        )

    async def list_classes(self, *args, **kwargs) -> HistoryClassesResponse:
        self.calls.append({"kind": "classes", **kwargs})
        return HistoryClassesResponse.model_validate(
            {
                "from": kwargs["starts_at"],
                "to": kwargs["ends_at"],
                "classes": [
                    HistoryClassEntry(
                        class_name="person", event_count=10, has_speed_data=False
                    ),
                    HistoryClassEntry(class_name="car", event_count=3, has_speed_data=True),
                ],
            }
        )


def _app_with_fakes(history_service: _FakeHistoryService, context: TenantContext) -> FastAPI:
    from argus.api.dependencies import get_app_services, get_tenant_context
    from argus.core.security import AuthenticatedUser, get_current_user
    from argus.models.enums import RoleEnum

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
async def test_series_endpoint_passes_include_speed_and_threshold(
    tenant_context: TenantContext,
) -> None:
    service = _FakeHistoryService()
    app = _app_with_fakes(service, tenant_context)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/history/series",
            params={
                "from": "2026-04-23T00:00:00Z",
                "to": "2026-04-23T06:00:00Z",
                "granularity": "1h",
                "include_speed": "true",
                "speed_threshold": "50",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["rows"][0]["speed_p50"] == {"car": 42.0}
    assert body["rows"][0]["over_threshold_count"] == {"car": 2}
    assert service.calls[-1]["include_speed"] is True
    assert service.calls[-1]["speed_threshold"] == 50.0


@pytest.mark.asyncio
async def test_series_endpoint_defaults_speed_fields_to_null(
    tenant_context: TenantContext,
) -> None:
    service = _FakeHistoryService()
    app = _app_with_fakes(service, tenant_context)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/history/series",
            params={
                "from": "2026-04-23T00:00:00Z",
                "to": "2026-04-23T06:00:00Z",
                "granularity": "1h",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["rows"][0]["speed_p50"] is None
    assert body["rows"][0]["over_threshold_count"] is None


@pytest.mark.asyncio
async def test_classes_endpoint_returns_sorted_entries(
    tenant_context: TenantContext,
) -> None:
    service = _FakeHistoryService()
    app = _app_with_fakes(service, tenant_context)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/history/classes",
            params={
                "from": "2026-04-23T00:00:00Z",
                "to": "2026-04-23T06:00:00Z",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["from"] == "2026-04-23T00:00:00Z"
    assert body["classes"][0]["class_name"] == "person"
    assert body["classes"][0]["has_speed_data"] is False
