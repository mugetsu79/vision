from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    CountEventBoundarySummary,
    HistoryBucketCoverage,
    HistoryClassEntry,
    HistoryClassesResponse,
    HistoryMetric,
    HistoryPoint,
    HistorySeriesResponse,
    HistorySeriesRow,
    TenantContext,
)
from argus.api.v1.history import router
from argus.models.enums import HistoryCoverageStatus


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
        self.calls.append({"kind": "history", **kwargs})
        now = datetime(2026, 4, 23, tzinfo=UTC)
        return [
            HistoryPoint(
                bucket=now,
                camera_id=None,
                class_name="car",
                event_count=4,
                granularity=kwargs.get("granularity", "1m"),
                metric=kwargs.get("metric", HistoryMetric.OCCUPANCY),
            )
        ]

    async def query_series(self, *args, **kwargs) -> HistorySeriesResponse:
        self.calls.append({"kind": "series", **kwargs})
        now = datetime(2026, 4, 23, tzinfo=UTC)
        return HistorySeriesResponse(
            granularity=kwargs.get("granularity", "1h"),
            metric=kwargs.get("metric", HistoryMetric.OCCUPANCY),
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
            effective_from=kwargs["starts_at"],
            effective_to=kwargs["ends_at"],
            bucket_count=1,
            bucket_span=kwargs.get("granularity", "1h"),
            coverage_status=HistoryCoverageStatus.POPULATED,
            coverage_by_bucket=[
                HistoryBucketCoverage(
                    bucket=now,
                    status=HistoryCoverageStatus.POPULATED,
                )
            ],
        )

    async def list_classes(self, *args, **kwargs) -> HistoryClassesResponse:
        self.calls.append({"kind": "classes", **kwargs})
        return HistoryClassesResponse.model_validate(
            {
                "from": kwargs["starts_at"],
                "to": kwargs["ends_at"],
                "metric": kwargs.get("metric", HistoryMetric.OCCUPANCY),
                "boundaries": [
                    CountEventBoundarySummary(
                        boundary_id="driveway",
                        event_types=["line_cross"],
                    )
                ],
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
                "metric": "count_events",
                "include_speed": "true",
                "speed_threshold": "50",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["metric"] == "count_events"
    assert body["rows"][0]["speed_p50"] == {"car": 42.0}
    assert body["rows"][0]["over_threshold_count"] == {"car": 2}
    assert service.calls[-1]["metric"] == HistoryMetric.COUNT_EVENTS
    assert service.calls[-1]["include_speed"] is True
    assert service.calls[-1]["speed_threshold"] == 50.0


@pytest.mark.asyncio
async def test_series_endpoint_serializes_coverage_metadata(
    tenant_context: TenantContext,
) -> None:
    service = _FakeHistoryService()
    app = _app_with_fakes(service, tenant_context)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/history/series",
            params={
                "from": "2026-04-23T00:00:00Z",
                "to": "2026-04-23T01:00:00Z",
                "granularity": "1h",
                "metric": "occupancy",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["effective_from"] == "2026-04-23T00:00:00Z"
    assert body["effective_to"] == "2026-04-23T01:00:00Z"
    assert body["bucket_count"] == 1
    assert body["bucket_span"] == "1h"
    assert body["coverage_status"] == "populated"
    assert body["coverage_by_bucket"] == [
        {
            "bucket": "2026-04-23T00:00:00Z",
            "status": "populated",
            "reason": None,
        }
    ]


@pytest.mark.asyncio
async def test_history_endpoint_passes_metric_and_serializes_points(
    tenant_context: TenantContext,
) -> None:
    service = _FakeHistoryService()
    app = _app_with_fakes(service, tenant_context)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/history",
            params={
                "from": "2026-04-23T00:00:00Z",
                "to": "2026-04-23T06:00:00Z",
                "granularity": "1m",
                "metric": "observations",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["metric"] == "observations"
    assert body[0]["event_count"] == 4
    assert service.calls[-1]["metric"] == HistoryMetric.OBSERVATIONS


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
                "metric": "count_events",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["metric"] == "count_events"
    assert body["from"] == "2026-04-23T00:00:00Z"
    assert body["classes"][0]["class_name"] == "person"
    assert body["classes"][0]["has_speed_data"] is False
    assert body["boundaries"][0]["boundary_id"] == "driveway"
    assert service.calls[-1]["metric"] == HistoryMetric.COUNT_EVENTS
