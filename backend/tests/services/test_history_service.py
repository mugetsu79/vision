from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import TenantContext
from argus.core.security import AuthenticatedUser, RoleEnum
from argus.models.enums import CountEventType, HistoryCoverageStatus, HistoryMetric
from argus.services.app import (
    HistoryService,
    _effective_granularity,
    _ensure_history_window,
)


def test_effective_granularity_keeps_requested_when_under_cap() -> None:
    starts = datetime(2026, 4, 23, tzinfo=UTC)
    ends = starts + timedelta(hours=1)  # 60 one-minute buckets, well under 500
    assert _effective_granularity("1m", starts_at=starts, ends_at=ends) == ("1m", False)


def test_effective_granularity_bumps_when_buckets_exceed_cap() -> None:
    starts = datetime(2026, 4, 23, tzinfo=UTC)
    # 10 days at 1m is 14400 buckets, way over 500 -> bump
    ends = starts + timedelta(days=10)
    new, adjusted = _effective_granularity("1m", starts_at=starts, ends_at=ends)
    assert adjusted is True
    assert new in {"5m", "1h", "1d"}


def test_ensure_history_window_rejects_over_31_days() -> None:
    starts = datetime(2026, 4, 1, tzinfo=UTC)
    ends = starts + timedelta(days=32)
    with pytest.raises(HTTPException) as info:
        _ensure_history_window(starts, ends)
    assert info.value.status_code == 400
    assert "31 days" in info.value.detail


def test_ensure_history_window_allows_exactly_31_days() -> None:
    starts = datetime(2026, 4, 1, tzinfo=UTC)
    ends = starts + timedelta(days=31)
    _ensure_history_window(starts, ends)  # no raise


@pytest.mark.asyncio
async def test_query_history_rejects_over_31_days() -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()

    starts = datetime(2026, 4, 1, tzinfo=UTC)
    ends = starts + timedelta(days=32)

    with pytest.raises(HTTPException) as info:
        await service.query_history(
            _tenant_context(),
            camera_ids=None,
            class_names=None,
            granularity="1h",
            starts_at=starts,
            ends_at=ends,
            metric=HistoryMetric.OCCUPANCY,
        )

    assert info.value.status_code == 400
    assert "31 days" in info.value.detail


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="test-tenant",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )


@pytest.mark.asyncio
async def test_query_series_without_speed_uses_aggregate_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    monkeypatch.setattr(
        service,
        "_fetch_series_rows_from_events",
        AsyncMock(
            return_value=[
                {
                    "bucket": datetime(2026, 4, 23, tzinfo=UTC),
                    "class_name": "car",
                    "event_count": 3,
                },
            ]
        ),
    )
    speed_mock = AsyncMock()
    monkeypatch.setattr(service, "_fetch_series_rows_with_speed", speed_mock)

    starts = datetime(2026, 4, 23, tzinfo=UTC)
    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="1h",
        starts_at=starts,
        ends_at=starts + timedelta(hours=6),
        metric=HistoryMetric.OCCUPANCY,
    )

    assert response.granularity == "1h"
    assert response.granularity_adjusted is False
    assert response.metric == HistoryMetric.OCCUPANCY
    assert response.class_names == ["car"]
    assert response.rows[0].values == {"car": 3}
    assert response.rows[0].speed_p50 is None
    speed_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_series_with_speed_populates_percentiles_and_violations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    starts = datetime(2026, 4, 23, 0, 0, tzinfo=UTC)
    bucket = starts
    monkeypatch.setattr(
        service,
        "_fetch_series_rows_with_speed",
        AsyncMock(
            return_value=[
                {
                    "bucket": bucket,
                    "class_name": "car",
                    "event_count": 10,
                    "speed_p50": 42.0,
                    "speed_p95": 58.0,
                    "speed_sample_count": 10,
                    "over_threshold_count": 3,
                },
                {
                    "bucket": bucket,
                    "class_name": "person",
                    "event_count": 5,
                    "speed_p50": None,
                    "speed_p95": None,
                    "speed_sample_count": 0,
                    "over_threshold_count": 0,
                },
            ]
        ),
    )

    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="5m",
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
        include_speed=True,
        speed_threshold=50.0,
        metric=HistoryMetric.OCCUPANCY,
    )

    row = response.rows[0]
    assert row.values == {"car": 10, "person": 5}
    assert row.speed_p50 == {"car": 42.0}
    assert row.speed_p95 == {"car": 58.0}
    assert row.speed_sample_count == {"car": 10}
    assert row.over_threshold_count == {"car": 3}
    assert response.speed_classes_used == ["car"]
    assert response.speed_classes_capped is False


@pytest.mark.asyncio
async def test_query_series_caps_speed_classes_at_20(monkeypatch: pytest.MonkeyPatch) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    starts = datetime(2026, 4, 23, tzinfo=UTC)

    rows = []
    for i in range(25):
        rows.append(
            {
                "bucket": starts,
                "class_name": f"class_{i:02d}",
                "event_count": 100 - i,  # class_00 is most frequent
                "speed_p50": 30.0 + i,
                "speed_p95": 40.0 + i,
                "speed_sample_count": 100 - i,
                "over_threshold_count": None,
            }
        )
    monkeypatch.setattr(service, "_fetch_series_rows_with_speed", AsyncMock(return_value=rows))

    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="5m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        include_speed=True,
        metric=HistoryMetric.OCCUPANCY,
    )

    assert response.speed_classes_capped is True
    assert len(response.speed_classes_used or []) == 20
    assert "class_00" in (response.speed_classes_used or [])
    assert "class_24" not in (response.speed_classes_used or [])
    assert len(response.class_names) == 25  # count chart uncapped


@pytest.mark.asyncio
async def test_list_classes_orders_by_event_count_desc(monkeypatch: pytest.MonkeyPatch) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()

    # Patch the session factory call chain to return fake rows
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_cm)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    execute_result = MagicMock()
    execute_result.mappings.return_value.all.return_value = [
        {"class_name": "person", "event_count": 42, "has_speed_data": False},
        {"class_name": "car", "event_count": 13, "has_speed_data": True},
    ]
    session_cm.execute = AsyncMock(return_value=execute_result)
    service.session_factory = MagicMock(return_value=session_cm)

    starts = datetime(2026, 4, 23, tzinfo=UTC)
    response = await service.list_classes(
        _tenant_context(),
        camera_ids=None,
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
        metric=HistoryMetric.OCCUPANCY,
    )

    assert [c.class_name for c in response.classes] == ["person", "car"]
    assert response.classes[0].has_speed_data is False
    assert response.metric == HistoryMetric.OCCUPANCY


@pytest.mark.asyncio
async def test_list_classes_count_events_uses_count_event_storage() -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_cm)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    class_result = MagicMock()
    class_result.mappings.return_value.all.return_value = [
        {"class_name": "person", "event_count": 8, "has_speed_data": True},
    ]
    boundary_result = MagicMock()
    boundary_result.mappings.return_value.all.return_value = [
        {"boundary_id": "driveway", "event_types": ["line_cross", "zone_enter"]},
    ]
    session_cm.execute = AsyncMock(side_effect=[class_result, boundary_result])
    service.session_factory = MagicMock(return_value=session_cm)

    starts = datetime(2026, 4, 23, tzinfo=UTC)
    response = await service.list_classes(
        _tenant_context(),
        camera_ids=None,
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
        metric=HistoryMetric.COUNT_EVENTS,
    )

    assert response.metric == HistoryMetric.COUNT_EVENTS
    assert response.classes[0].class_name == "person"
    assert response.boundaries[0].boundary_id == "driveway"
    assert response.boundaries[0].event_types == [
        CountEventType.LINE_CROSS,
        CountEventType.ZONE_ENTER,
    ]


@pytest.mark.asyncio
async def test_query_series_count_only_reads_tracking_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()

    fresh_rows = [
        {
            "bucket": datetime(2026, 4, 24, 14, 0, tzinfo=UTC),
            "class_name": "person",
            "event_count": 42,
        },
    ]
    from_events = AsyncMock(return_value=fresh_rows)
    monkeypatch.setattr(service, "_fetch_series_rows_from_events", from_events)
    aggregate = AsyncMock(return_value=[])
    monkeypatch.setattr(service, "_fetch_series_rows_aggregate", aggregate)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        metric=HistoryMetric.OCCUPANCY,
    )

    from_events.assert_awaited_once()
    aggregate.assert_not_awaited()
    assert response.class_names == ["person"]
    assert response.metric == HistoryMetric.OCCUPANCY
    assert response.rows[0].values == {"person": 42}
    assert response.rows[0].total_count == 42


@pytest.mark.asyncio
async def test_query_series_observations_use_tracking_event_density(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()

    from_events = AsyncMock(
        return_value=[
            {
                "bucket": datetime(2026, 4, 24, 14, 0, tzinfo=UTC),
                "class_name": "person",
                "event_count": 7,
            },
        ]
    )
    monkeypatch.setattr(service, "_fetch_series_rows_from_events", from_events)
    aggregate = AsyncMock(return_value=[])
    monkeypatch.setattr(service, "_fetch_series_rows_aggregate", aggregate)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        metric=HistoryMetric.OBSERVATIONS,
    )

    assert from_events.await_args.kwargs["metric"] == HistoryMetric.OBSERVATIONS
    aggregate.assert_not_awaited()
    assert response.metric == HistoryMetric.OBSERVATIONS
    assert response.rows[0].values == {"person": 7}


@pytest.mark.asyncio
async def test_query_series_count_events_use_count_event_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()

    count_event_rows = AsyncMock(
        return_value=[
            {
                "bucket": datetime(2026, 4, 24, 14, 0, tzinfo=UTC),
                "class_name": "person",
                "event_count": 11,
            },
        ]
    )
    monkeypatch.setattr(service, "_fetch_series_rows_aggregate", count_event_rows)
    from_events = AsyncMock(return_value=[])
    monkeypatch.setattr(service, "_fetch_series_rows_from_events", from_events)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="1h",
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
        metric=HistoryMetric.COUNT_EVENTS,
    )

    assert count_event_rows.await_args.kwargs["metric"] == HistoryMetric.COUNT_EVENTS
    from_events.assert_not_awaited()
    assert response.metric == HistoryMetric.COUNT_EVENTS
    assert response.rows[0].values == {"person": 11}


@pytest.mark.asyncio
async def test_query_series_returns_zero_buckets_for_empty_valid_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    monkeypatch.setattr(service, "_fetch_series_rows_from_events", AsyncMock(return_value=[]))

    starts = datetime(2026, 4, 26, 14, 0, tzinfo=UTC)
    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=["person"],
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=3),
        metric=HistoryMetric.OCCUPANCY,
    )

    assert response.coverage_status == HistoryCoverageStatus.ZERO
    assert response.effective_from == starts
    assert response.effective_to == starts + timedelta(minutes=3)
    assert response.bucket_count == 3
    assert response.bucket_span == "1m"
    assert response.class_names == ["person"]
    assert [row.bucket for row in response.rows] == [
        starts,
        starts + timedelta(minutes=1),
        starts + timedelta(minutes=2),
    ]
    assert [row.values for row in response.rows] == [{"person": 0}, {"person": 0}, {"person": 0}]
    assert [row.total_count for row in response.rows] == [0, 0, 0]
    assert [entry.status for entry in response.coverage_by_bucket] == [
        HistoryCoverageStatus.ZERO,
        HistoryCoverageStatus.ZERO,
        HistoryCoverageStatus.ZERO,
    ]


@pytest.mark.asyncio
async def test_query_series_materializes_missing_buckets_around_populated_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    starts = datetime(2026, 4, 26, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(
        service,
        "_fetch_series_rows_from_events",
        AsyncMock(
            return_value=[
                {
                    "bucket": starts + timedelta(minutes=1),
                    "class_name": "car",
                    "event_count": 7,
                }
            ]
        ),
    )

    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=["car"],
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=3),
        metric=HistoryMetric.OCCUPANCY,
    )

    assert response.coverage_status == HistoryCoverageStatus.POPULATED
    assert [row.values for row in response.rows] == [{"car": 0}, {"car": 7}, {"car": 0}]
    assert [entry.status for entry in response.coverage_by_bucket] == [
        HistoryCoverageStatus.ZERO,
        HistoryCoverageStatus.POPULATED,
        HistoryCoverageStatus.ZERO,
    ]


@pytest.mark.asyncio
async def test_query_series_zero_fill_preserves_speed_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    starts = datetime(2026, 4, 26, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(
        service,
        "_fetch_series_rows_with_speed",
        AsyncMock(
            return_value=[
                {
                    "bucket": starts,
                    "class_name": "car",
                    "event_count": 3,
                    "speed_p50": 41.0,
                    "speed_p95": 55.0,
                    "speed_sample_count": 3,
                    "over_threshold_count": 1,
                }
            ]
        ),
    )

    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=["car"],
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=2),
        metric=HistoryMetric.OCCUPANCY,
        include_speed=True,
        speed_threshold=50.0,
    )

    assert response.rows[0].speed_p50 == {"car": 41.0}
    assert response.rows[0].speed_p95 == {"car": 55.0}
    assert response.rows[0].speed_sample_count == {"car": 3}
    assert response.rows[0].over_threshold_count == {"car": 1}
    assert response.rows[1].values == {"car": 0}
    assert response.rows[1].speed_p50 == {}
    assert response.speed_classes_used == ["car"]


@pytest.mark.asyncio
async def test_fetch_series_rows_occupancy_uses_peak_concurrency_sql() -> None:
    service = HistoryService(session_factory=MagicMock())

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_cm)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    execute_result = MagicMock()
    execute_result.mappings.return_value.all.return_value = []
    session_cm.execute = AsyncMock(return_value=execute_result)
    service.session_factory = MagicMock(return_value=session_cm)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    await service._fetch_series_rows_from_events(
        camera_ids=None,
        class_names=None,
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        metric=HistoryMetric.OCCUPANCY,
    )

    statement = session_cm.execute.await_args.args[0]
    sql = " ".join(str(statement).split()).lower()
    assert "with active_by_ts as" in sql
    assert "max(active_count)::bigint as event_count" in sql
    assert "count(*)::bigint as active_count" in sql
    assert "count(distinct track_id)" not in sql
    assert "sum(occupancy_by_camera.event_count)::bigint as event_count" not in sql


@pytest.mark.asyncio
async def test_fetch_series_rows_counts_raw_observations() -> None:
    service = HistoryService(session_factory=MagicMock())

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_cm)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    execute_result = MagicMock()
    execute_result.mappings.return_value.all.return_value = []
    session_cm.execute = AsyncMock(return_value=execute_result)
    service.session_factory = MagicMock(return_value=session_cm)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    await service._fetch_series_rows_from_events(
        camera_ids=None,
        class_names=None,
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        metric=HistoryMetric.OBSERVATIONS,
    )

    statement = session_cm.execute.await_args.args[0]
    sql = " ".join(str(statement).split()).lower()
    assert "count(*)::bigint as event_count" in sql


@pytest.mark.asyncio
async def test_fetch_class_rows_occupancy_uses_visibility_samples_sql() -> None:
    service = HistoryService(session_factory=MagicMock())

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_cm)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    execute_result = MagicMock()
    execute_result.mappings.return_value.all.return_value = []
    session_cm.execute = AsyncMock(return_value=execute_result)
    service.session_factory = MagicMock(return_value=session_cm)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    await service._fetch_class_rows_from_tracking_events(
        camera_ids=None,
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        metric=HistoryMetric.OCCUPANCY,
    )

    statement = session_cm.execute.await_args.args[0]
    sql = " ".join(str(statement).split()).lower()
    assert "count(distinct (camera_id, ts))::bigint as event_count" in sql
    assert "track_id" not in sql


@pytest.mark.asyncio
async def test_fetch_series_rows_with_speed_occupancy_uses_peak_concurrency_sql() -> None:
    service = HistoryService(session_factory=MagicMock())

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_cm)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    execute_result = MagicMock()
    execute_result.mappings.return_value.all.return_value = []
    session_cm.execute = AsyncMock(return_value=execute_result)
    service.session_factory = MagicMock(return_value=session_cm)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    await service._fetch_series_rows_with_speed(
        camera_ids=None,
        class_names=None,
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        metric=HistoryMetric.OCCUPANCY,
        speed_threshold=None,
    )

    statement = session_cm.execute.await_args.args[0]
    sql = " ".join(str(statement).split()).lower()
    assert "with active_by_ts as" in sql
    assert "occupancy_by_camera" in sql
    assert "count(*)::bigint as active_count" in sql
    assert "count(distinct track_id)" not in sql
    assert "sum(occupancy_by_camera.event_count)::bigint as event_count" in sql


@pytest.mark.asyncio
async def test_fetch_history_rows_occupancy_uses_peak_concurrency_sql() -> None:
    service = HistoryService(session_factory=MagicMock())

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_cm)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    execute_result = MagicMock()
    execute_result.mappings.return_value.all.return_value = []
    session_cm.execute = AsyncMock(return_value=execute_result)
    service.session_factory = MagicMock(return_value=session_cm)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    await service._fetch_history_rows(
        camera_ids=None,
        class_names=None,
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        metric=HistoryMetric.OCCUPANCY,
    )

    statement = session_cm.execute.await_args.args[0]
    sql = " ".join(str(statement).split()).lower()
    assert "with active_by_ts as" in sql
    assert "max(active_count)::bigint as event_count" in sql
    assert "count(*)::bigint as active_count" in sql
    assert "count(distinct track_id)" not in sql
