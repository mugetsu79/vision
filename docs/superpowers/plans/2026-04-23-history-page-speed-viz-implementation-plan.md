# History Page Speed Viz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/history` useful on first load, add a stacked speed panel (p50/p95 per class + user threshold + violation bars), and persist filter state in the URL so navigation and deep links work.

**Architecture:** Additive contract and endpoint changes. Counts continue to read the existing `events_1m` / `events_1h` continuous aggregates for speed; when `include_speed=true` the service takes a second SQL path that reads `tracking_events` directly to compute `percentile_cont(0.5)` / `percentile_cont(0.95)` / violation counts. A new `GET /api/v1/history/classes` endpoint powers a dynamic class filter. All frontend state round-trips via URL query params.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + TimescaleDB on the backend; React 19 + TanStack Query v5 + React Router v6 + ECharts 6 + vitest + Playwright on the frontend.

---

## File Structure

**Backend — modify:**
- `backend/src/argus/api/contracts.py` — extend `HistorySeriesRow` and `HistorySeriesResponse`; add `HistoryClassEntry`, `HistoryClassesResponse`.
- `backend/src/argus/api/v1/history.py` — extend `/series` params; add `/classes` endpoint.
- `backend/src/argus/services/app.py` — extend `HistoryService.query_series` with the speed-aware path, window/bucket guardrails, 20-class cap; add `HistoryService.list_classes`; add SQL helpers.

**Backend — create:**
- `backend/tests/services/test_history_service.py` — unit tests for the service (happy path, guardrails, speed path, classes).
- `backend/tests/api/test_history_endpoints.py` — integration tests for `/series` with new params and `/classes`.

**Frontend — modify:**
- `frontend/src/lib/api.generated.ts` — regenerated from updated OpenAPI schema (do not hand-edit).
- `frontend/src/pages/History.tsx` — URL hydration, new controls (Show speed toggle, threshold input, "Show all 80 COCO classes" expander), empty-state with "Try last 7 days", dynamic class list, granularity-adjusted notice.
- `frontend/src/pages/History.test.tsx` — cover the new controls and empty states.
- `frontend/src/components/history/HistoryTrendChart.tsx` — multi-grid ECharts config with optional violation bars and speed panel (p50 solid, p95 dashed, shaded band, threshold markLine).
- `frontend/src/hooks/use-history.ts` — extend `useHistorySeries` with `include_speed` / `speed_threshold`; add `useHistoryClasses`.
- `frontend/e2e/prompt9-history-and-incidents.spec.ts` — add scenarios for URL persistence, speed toggle, threshold violation bars, deep link.

**Frontend — create:**
- `frontend/src/lib/history-url-state.ts` — pure parse/serialise helpers for URL query params.
- `frontend/src/lib/history-url-state.test.ts` — round-trip tests.
- `frontend/src/lib/coco-classes.ts` — static list of 80 COCO class names for the "Show all" expander.
- `frontend/src/components/history/HistoryTrendChart.test.tsx` — unit tests for the chart's ECharts option generation (via an injected `renderOption` helper, see Task 10).

**No database migrations, no worker changes.**

---

## Task 1: Extend history contracts for speed and classes

**Files:**
- Modify: `backend/src/argus/api/contracts.py` (around lines 281–291)

- [ ] **Step 1: Inspect current contract shape**

Run: `sed -n '273,292p' backend/src/argus/api/contracts.py`
Expected: prints the current `HistoryPoint`, `HistorySeriesRow`, `HistorySeriesResponse` definitions.

- [ ] **Step 2: Extend contracts**

Replace the `HistorySeriesRow` and `HistorySeriesResponse` classes, and add two new classes, so the section reads exactly:

```python
class HistorySeriesRow(BaseModel):
    bucket: datetime
    values: dict[str, int]
    total_count: int
    speed_p50: dict[str, float] | None = None
    speed_p95: dict[str, float] | None = None
    speed_sample_count: dict[str, int] | None = None
    over_threshold_count: dict[str, int] | None = None


class HistorySeriesResponse(BaseModel):
    granularity: str
    class_names: list[str]
    rows: list[HistorySeriesRow]
    granularity_adjusted: bool = False
    speed_classes_capped: bool = False
    speed_classes_used: list[str] | None = None


class HistoryClassEntry(BaseModel):
    class_name: str
    event_count: int
    has_speed_data: bool


class HistoryClassesResponse(BaseModel):
    from_: datetime = Field(serialization_alias="from", validation_alias="from")
    to: datetime
    classes: list[HistoryClassEntry]
```

- [ ] **Step 3: Verify Python imports still resolve**

Run: `cd backend && python3 -m uv run python -c "from argus.api.contracts import HistorySeriesRow, HistorySeriesResponse, HistoryClassEntry, HistoryClassesResponse; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/src/argus/api/contracts.py
git commit -m "feat(history): extend contracts for speed fields and classes endpoint"
```

---

## Task 2: Add SQL helpers and window/bucket guardrails

**Files:**
- Modify: `backend/src/argus/services/app.py` (after `_history_view_and_bucket_expr` around line 1486)

- [ ] **Step 1: Add granularity, window cap, and class cap constants**

Insert these just after `_history_view_and_bucket_expr`:

```python
_GRANULARITY_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "1h": 3600,
    "1d": 86400,
}
_GRANULARITY_ORDER: tuple[str, ...] = ("1m", "5m", "1h", "1d")
_GRANULARITY_INTERVAL: dict[str, str] = {
    "1m": "1 minute",
    "5m": "5 minutes",
    "1h": "1 hour",
    "1d": "1 day",
}
_MAX_HISTORY_WINDOW = timedelta(days=31)
_MAX_HISTORY_BUCKETS = 500
_MAX_SPEED_CLASSES = 20


def _ensure_history_window(starts_at: datetime, ends_at: datetime) -> None:
    if ends_at - starts_at > _MAX_HISTORY_WINDOW:
        raise HTTPException(status_code=400, detail="Window exceeds 31 days")


def _effective_granularity(
    requested: str,
    *,
    starts_at: datetime,
    ends_at: datetime,
) -> tuple[str, bool]:
    span_seconds = max(1.0, (ends_at - starts_at).total_seconds())
    try:
        start_index = _GRANULARITY_ORDER.index(requested)
    except ValueError as exc:
        raise ValueError(f"Unsupported granularity: {requested}") from exc
    for candidate in _GRANULARITY_ORDER[start_index:]:
        if span_seconds / _GRANULARITY_SECONDS[candidate] <= _MAX_HISTORY_BUCKETS:
            return candidate, candidate != requested
    return _GRANULARITY_ORDER[-1], _GRANULARITY_ORDER[-1] != requested
```

Also add the imports at the top of `app.py` if not already present:

```python
from datetime import timedelta
from fastapi import HTTPException
```

- [ ] **Step 2: Write unit test for `_effective_granularity`**

Create `backend/tests/services/test_history_service.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from argus.services.app import (
    _MAX_HISTORY_BUCKETS,
    _ensure_history_window,
    _effective_granularity,
)


def test_effective_granularity_keeps_requested_when_under_cap() -> None:
    starts = datetime(2026, 4, 23, tzinfo=timezone.utc)
    ends = starts + timedelta(hours=1)  # 60 one-minute buckets, well under 500
    assert _effective_granularity("1m", starts_at=starts, ends_at=ends) == ("1m", False)


def test_effective_granularity_bumps_when_buckets_exceed_cap() -> None:
    starts = datetime(2026, 4, 23, tzinfo=timezone.utc)
    # 10 days at 1m is 14400 buckets, way over 500 -> bump
    ends = starts + timedelta(days=10)
    new, adjusted = _effective_granularity("1m", starts_at=starts, ends_at=ends)
    assert adjusted is True
    assert new in {"5m", "1h", "1d"}


def test_ensure_history_window_rejects_over_31_days() -> None:
    starts = datetime(2026, 4, 1, tzinfo=timezone.utc)
    ends = starts + timedelta(days=32)
    with pytest.raises(Exception) as info:
        _ensure_history_window(starts, ends)
    assert "31 days" in str(info.value)


def test_ensure_history_window_allows_exactly_31_days() -> None:
    starts = datetime(2026, 4, 1, tzinfo=timezone.utc)
    ends = starts + timedelta(days=31)
    _ensure_history_window(starts, ends)  # no raise
```

- [ ] **Step 3: Run the tests**

Run: `cd backend && python3 -m uv run pytest tests/services/test_history_service.py -q`
Expected: `4 passed`

- [ ] **Step 4: Commit**

```bash
git add backend/src/argus/services/app.py backend/tests/services/test_history_service.py
git commit -m "feat(history): add granularity/window guardrails for history service"
```

---

## Task 3: Extend query_series with speed-aware path

**Files:**
- Modify: `backend/src/argus/services/app.py` (the `HistoryService` class around lines 707–760, and helper `_fetch_series_rows` around lines 850–893)

- [ ] **Step 1: Add a new SQL helper for speed-aware series**

Add as a new method on `HistoryService`, placed immediately after `_fetch_series_rows`:

```python
    async def _fetch_series_rows_with_speed(
        self,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        speed_threshold: float | None,
    ) -> list[dict[str, Any]]:
        interval = _GRANULARITY_INTERVAL[granularity]
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters: list[str] = []
        if camera_ids:
            filters.append("AND camera_id IN :camera_ids")
            parameters["camera_ids"] = camera_ids
        if class_names:
            filters.append("AND class_name IN :class_names")
            parameters["class_names"] = class_names

        threshold_expr = (
            "count(*) FILTER (WHERE speed_kph IS NOT NULL AND speed_kph > :speed_threshold)::bigint"
            if speed_threshold is not None
            else "NULL::bigint"
        )
        if speed_threshold is not None:
            parameters["speed_threshold"] = float(speed_threshold)

        statement = text(
            f"""
            SELECT
              time_bucket(INTERVAL '{interval}', ts) AS bucket,
              class_name,
              count(*)::bigint AS event_count,
              percentile_cont(0.5) WITHIN GROUP (ORDER BY speed_kph)
                  FILTER (WHERE speed_kph IS NOT NULL) AS speed_p50,
              percentile_cont(0.95) WITHIN GROUP (ORDER BY speed_kph)
                  FILTER (WHERE speed_kph IS NOT NULL) AS speed_p95,
              count(speed_kph)::bigint AS speed_sample_count,
              {threshold_expr} AS over_threshold_count
            FROM tracking_events
            WHERE ts >= :starts_at
              AND ts <= :ends_at
              {' '.join(filters)}
            GROUP BY 1, 2
            ORDER BY 1 ASC, 2 ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))
        if class_names:
            statement = statement.bindparams(bindparam("class_names", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]
```

- [ ] **Step 2: Replace `query_series` with the extended version**

Find the existing `query_series` method (starts at `async def query_series` around line 707) and replace it entirely with:

```python
    async def query_series(
        self,
        tenant_context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        include_speed: bool = False,
        speed_threshold: float | None = None,
    ) -> HistorySeriesResponse:
        _ensure_history_window(starts_at, ends_at)
        await self._ensure_camera_access(tenant_context, camera_ids)

        effective_granularity, granularity_adjusted = _effective_granularity(
            granularity,
            starts_at=starts_at,
            ends_at=ends_at,
        )

        if include_speed:
            rows = await self._fetch_series_rows_with_speed(
                camera_ids=camera_ids,
                class_names=class_names,
                granularity=effective_granularity,
                starts_at=starts_at,
                ends_at=ends_at,
                speed_threshold=speed_threshold,
            )
        else:
            rows = await self._fetch_series_rows(
                camera_ids=camera_ids,
                class_names=class_names,
                granularity=effective_granularity,
                starts_at=starts_at,
                ends_at=ends_at,
            )

        buckets: dict[datetime, dict[str, int]] = {}
        speed_p50: dict[datetime, dict[str, float]] = {}
        speed_p95: dict[datetime, dict[str, float]] = {}
        speed_samples: dict[datetime, dict[str, int]] = {}
        violations: dict[datetime, dict[str, int]] = {}
        class_event_counts: dict[str, int] = {}
        class_has_speed: set[str] = set()
        ordered_classes: list[str] = []
        seen_classes: set[str] = set()

        for row in rows:
            bucket = cast(datetime, row["bucket"])
            class_name = cast(str, row["class_name"])
            event_count = int(row["event_count"])
            buckets.setdefault(bucket, {})[class_name] = event_count
            class_event_counts[class_name] = class_event_counts.get(class_name, 0) + event_count

            if class_name not in seen_classes:
                seen_classes.add(class_name)
                ordered_classes.append(class_name)

            if include_speed:
                p50 = row.get("speed_p50")
                p95 = row.get("speed_p95")
                sample_count = int(row.get("speed_sample_count") or 0)
                if sample_count > 0:
                    class_has_speed.add(class_name)
                    if p50 is not None:
                        speed_p50.setdefault(bucket, {})[class_name] = float(p50)
                    if p95 is not None:
                        speed_p95.setdefault(bucket, {})[class_name] = float(p95)
                    speed_samples.setdefault(bucket, {})[class_name] = sample_count
                if speed_threshold is not None and row.get("over_threshold_count") is not None:
                    violations.setdefault(bucket, {})[class_name] = int(
                        row["over_threshold_count"]
                    )

        if class_names:
            selected_classes = [c for c in class_names if c in seen_classes]
        else:
            selected_classes = ordered_classes

        speed_classes_capped = False
        speed_classes_used: list[str] | None = None
        if include_speed:
            eligible = [c for c in selected_classes if c in class_has_speed]
            eligible_sorted = sorted(
                eligible,
                key=lambda c: class_event_counts.get(c, 0),
                reverse=True,
            )
            if len(eligible_sorted) > _MAX_SPEED_CLASSES:
                speed_classes_capped = True
                speed_classes_used = eligible_sorted[:_MAX_SPEED_CLASSES]
            else:
                speed_classes_used = eligible_sorted

        def _project_speed(
            source: dict[datetime, dict[str, float]],
            bucket: datetime,
        ) -> dict[str, float] | None:
            if not include_speed:
                return None
            chosen = speed_classes_used or []
            per_bucket = source.get(bucket, {})
            return {c: per_bucket[c] for c in chosen if c in per_bucket}

        def _project_int(
            source: dict[datetime, dict[str, int]],
            bucket: datetime,
        ) -> dict[str, int] | None:
            if not include_speed:
                return None
            chosen = speed_classes_used or []
            per_bucket = source.get(bucket, {})
            return {c: per_bucket[c] for c in chosen if c in per_bucket}

        result_rows = []
        for bucket in sorted(buckets.keys()):
            values = buckets[bucket]
            row = HistorySeriesRow(
                bucket=bucket,
                values={c: values.get(c, 0) for c in selected_classes},
                total_count=sum(values.values()),
                speed_p50=_project_speed(speed_p50, bucket),
                speed_p95=_project_speed(speed_p95, bucket),
                speed_sample_count=_project_int(speed_samples, bucket),
                over_threshold_count=(
                    _project_int(violations, bucket) if speed_threshold is not None else None
                ),
            )
            result_rows.append(row)

        return HistorySeriesResponse(
            granularity=effective_granularity,
            class_names=selected_classes,
            rows=result_rows,
            granularity_adjusted=granularity_adjusted,
            speed_classes_capped=speed_classes_capped,
            speed_classes_used=speed_classes_used if include_speed else None,
        )
```

- [ ] **Step 3: Write tests for the extended behaviour**

Append to `backend/tests/services/test_history_service.py`:

```python
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from argus.api.contracts import TenantContext
from argus.services.app import HistoryService


def _tenant_context() -> TenantContext:
    return TenantContext(tenant_id=uuid4(), tenant_slug="test-tenant")


@pytest.mark.asyncio
async def test_query_series_without_speed_uses_aggregate_path(monkeypatch: pytest.MonkeyPatch) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    monkeypatch.setattr(
        service,
        "_fetch_series_rows",
        AsyncMock(
            return_value=[
                {"bucket": datetime(2026, 4, 23, tzinfo=timezone.utc), "class_name": "car", "event_count": 3},
            ]
        ),
    )
    speed_mock = AsyncMock()
    monkeypatch.setattr(service, "_fetch_series_rows_with_speed", speed_mock)

    starts = datetime(2026, 4, 23, tzinfo=timezone.utc)
    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="1h",
        starts_at=starts,
        ends_at=starts + timedelta(hours=6),
    )

    assert response.granularity == "1h"
    assert response.granularity_adjusted is False
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
    starts = datetime(2026, 4, 23, 0, 0, tzinfo=timezone.utc)
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
    starts = datetime(2026, 4, 23, tzinfo=timezone.utc)

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
    )

    assert response.speed_classes_capped is True
    assert len(response.speed_classes_used or []) == 20
    assert "class_00" in (response.speed_classes_used or [])
    assert "class_24" not in (response.speed_classes_used or [])
    assert len(response.class_names) == 25  # count chart uncapped
```

- [ ] **Step 4: Run all service tests**

Run: `cd backend && python3 -m uv run pytest tests/services/test_history_service.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/services/app.py backend/tests/services/test_history_service.py
git commit -m "feat(history): add speed-aware query_series with percentile/violation/class cap"
```

---

## Task 4: Add list_classes service method

**Files:**
- Modify: `backend/src/argus/services/app.py` (append to `HistoryService`)

- [ ] **Step 1: Add the method**

Add as a new public method on `HistoryService`, right after `query_series`:

```python
    async def list_classes(
        self,
        tenant_context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        starts_at: datetime,
        ends_at: datetime,
    ) -> HistoryClassesResponse:
        _ensure_history_window(starts_at, ends_at)
        await self._ensure_camera_access(tenant_context, camera_ids)

        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters: list[str] = []
        if camera_ids:
            filters.append("AND camera_id IN :camera_ids")
            parameters["camera_ids"] = camera_ids

        statement = text(
            f"""
            SELECT
              class_name,
              count(*)::bigint AS event_count,
              bool_or(speed_kph IS NOT NULL) AS has_speed_data
            FROM tracking_events
            WHERE ts >= :starts_at
              AND ts <= :ends_at
              {' '.join(filters)}
            GROUP BY class_name
            ORDER BY event_count DESC, class_name ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()

        return HistoryClassesResponse(
            from_=starts_at,
            to=ends_at,
            classes=[
                HistoryClassEntry(
                    class_name=row["class_name"],
                    event_count=int(row["event_count"]),
                    has_speed_data=bool(row["has_speed_data"]),
                )
                for row in rows
            ],
        )
```

Also add imports at the top of `app.py` if not already present:

```python
from argus.api.contracts import (  # extend existing import
    HistoryClassEntry,
    HistoryClassesResponse,
)
```

- [ ] **Step 2: Write a unit test**

Append to `backend/tests/services/test_history_service.py`:

```python
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

    starts = datetime(2026, 4, 23, tzinfo=timezone.utc)
    response = await service.list_classes(
        _tenant_context(),
        camera_ids=None,
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
    )

    assert [c.class_name for c in response.classes] == ["person", "car"]
    assert response.classes[0].has_speed_data is False
    assert response.classes[1].has_speed_data is True
```

- [ ] **Step 3: Run it**

Run: `cd backend && python3 -m uv run pytest tests/services/test_history_service.py -q`
Expected: `8 passed`

- [ ] **Step 4: Commit**

```bash
git add backend/src/argus/services/app.py backend/tests/services/test_history_service.py
git commit -m "feat(history): add HistoryService.list_classes for dynamic class filter"
```

---

## Task 5: Wire new endpoint params and add /classes route

**Files:**
- Modify: `backend/src/argus/api/v1/history.py`

- [ ] **Step 1: Add new query annotations and extend `/series`**

Replace the file with this exact content:

```python
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from argus.api.contracts import (
    HistoryClassesResponse,
    HistoryPoint,
    HistorySeriesResponse,
    TenantContext,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/history", tags=["history"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
CameraIdQuery = Annotated[UUID | None, Query()]
CameraIdsQuery = Annotated[list[UUID] | None, Query()]
ClassNamesQuery = Annotated[list[str] | None, Query()]
GranularityQuery = Annotated[str, Query(pattern="^(1m|5m|1h|1d)$")]
FromQuery = Annotated[datetime, Query(alias="from")]
ToQuery = Annotated[datetime, Query(alias="to")]
IncludeSpeedQuery = Annotated[bool, Query()]
SpeedThresholdQuery = Annotated[float | None, Query(ge=0)]


def _normalize_camera_ids(
    *,
    camera_id: UUID | None,
    camera_ids: list[UUID] | None,
) -> list[UUID] | None:
    combined: list[UUID] = []
    if camera_ids:
        combined.extend(camera_ids)
    if camera_id is not None:
        combined.append(camera_id)
    if not combined:
        return None
    unique: list[UUID] = []
    seen: set[UUID] = set()
    for value in combined:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


@router.get("", response_model=list[HistoryPoint])
async def get_history(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    from_: FromQuery,
    to: ToQuery,
    camera_id: CameraIdQuery = None,
    camera_ids: CameraIdsQuery = None,
    class_names: ClassNamesQuery = None,
    granularity: GranularityQuery = "1m",
) -> list[HistoryPoint]:
    return await services.history.query_history(
        tenant_context,
        camera_ids=_normalize_camera_ids(camera_id=camera_id, camera_ids=camera_ids),
        class_names=class_names,
        granularity=granularity,
        starts_at=from_,
        ends_at=to,
    )


@router.get("/series", response_model=HistorySeriesResponse)
async def get_history_series(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    from_: FromQuery,
    to: ToQuery,
    camera_id: CameraIdQuery = None,
    camera_ids: CameraIdsQuery = None,
    class_names: ClassNamesQuery = None,
    granularity: GranularityQuery = "1h",
    include_speed: IncludeSpeedQuery = False,
    speed_threshold: SpeedThresholdQuery = None,
) -> HistorySeriesResponse:
    return await services.history.query_series(
        tenant_context,
        camera_ids=_normalize_camera_ids(camera_id=camera_id, camera_ids=camera_ids),
        class_names=class_names,
        granularity=granularity,
        starts_at=from_,
        ends_at=to,
        include_speed=include_speed,
        speed_threshold=speed_threshold,
    )


@router.get("/classes", response_model=HistoryClassesResponse)
async def get_history_classes(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    from_: FromQuery,
    to: ToQuery,
    camera_id: CameraIdQuery = None,
    camera_ids: CameraIdsQuery = None,
) -> HistoryClassesResponse:
    return await services.history.list_classes(
        tenant_context,
        camera_ids=_normalize_camera_ids(camera_id=camera_id, camera_ids=camera_ids),
        starts_at=from_,
        ends_at=to,
    )
```

- [ ] **Step 2: Write endpoint integration tests**

Create `backend/tests/api/test_history_endpoints.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

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
    return TenantContext(tenant_id=uuid4(), tenant_slug="test-tenant")


class _FakeHistoryService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def query_history(self, *args, **kwargs):
        return []

    async def query_series(self, *args, **kwargs) -> HistorySeriesResponse:
        self.calls.append({"kind": "series", **kwargs})
        now = datetime(2026, 4, 23, tzinfo=timezone.utc)
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
        return HistoryClassesResponse(
            from_=kwargs["starts_at"],
            to=kwargs["ends_at"],
            classes=[
                HistoryClassEntry(class_name="person", event_count=10, has_speed_data=False),
                HistoryClassEntry(class_name="car", event_count=3, has_speed_data=True),
            ],
        )


def _app_with_fakes(history_service: _FakeHistoryService, context: TenantContext) -> FastAPI:
    from argus.api.dependencies import get_app_services, get_tenant_context
    from argus.core.security import AuthenticatedUser, require
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
            realm="argus-dev",
            role=RoleEnum.VIEWER,
            is_superadmin=False,
        )

    app.dependency_overrides[get_app_services] = _get_services
    app.dependency_overrides[get_tenant_context] = _get_context
    app.dependency_overrides[require(RoleEnum.VIEWER)] = _get_user
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
```

- [ ] **Step 3: Run all history tests**

Run: `cd backend && python3 -m uv run pytest tests/services/test_history_service.py tests/api/test_history_endpoints.py -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/src/argus/api/v1/history.py backend/tests/api/test_history_endpoints.py
git commit -m "feat(history): extend /series with speed params, add /classes endpoint"
```

---

## Task 6: Regenerate OpenAPI types + add COCO class list

**Files:**
- Regenerate: `frontend/src/lib/api.generated.ts`
- Create: `frontend/src/lib/coco-classes.ts`

- [ ] **Step 1: Start the backend locally to emit the new OpenAPI schema**

Pick one of:

- If your dev docker compose stack is up with the backend container on `localhost:8000`: skip to Step 2.
- Otherwise: `docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend` and wait ~5 s for Uvicorn to bind.

Verify: `curl -fsS http://127.0.0.1:8000/openapi.json | python3 -c "import json,sys; s=json.load(sys.stdin); print('HistorySeriesResponse' in s['components']['schemas'])"`
Expected: `True` (and the schema has the new fields).

- [ ] **Step 2: Regenerate types**

Run: `cd frontend && npx openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/api.generated.ts`
Expected: file updated, no errors.

- [ ] **Step 3: Verify the new fields exist**

Run: `grep -E 'speed_p50|HistoryClassesResponse|granularity_adjusted' frontend/src/lib/api.generated.ts | head`
Expected: sees `speed_p50`, `speed_p95`, `over_threshold_count`, `granularity_adjusted`, `speed_classes_capped`, `speed_classes_used`, `HistoryClassesResponse`, `HistoryClassEntry`.

- [ ] **Step 4: Add the COCO classes static list**

Create `frontend/src/lib/coco-classes.ts`:

```typescript
export const COCO_CLASSES: readonly string[] = [
  "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
  "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
  "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
  "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
  "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
  "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
  "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
  "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
  "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
  "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
  "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
  "hair drier", "toothbrush",
] as const;
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.generated.ts frontend/src/lib/coco-classes.ts
git commit -m "feat(history): regenerate OpenAPI types, add COCO class list"
```

---

## Task 7: URL state serialisation module

**Files:**
- Create: `frontend/src/lib/history-url-state.ts`
- Create: `frontend/src/lib/history-url-state.test.ts`

- [ ] **Step 1: Write the failing test first**

Create `frontend/src/lib/history-url-state.test.ts`:

```typescript
import { describe, expect, test } from "vitest";

import {
  type HistoryFilterState,
  readHistoryFiltersFromSearch,
  writeHistoryFiltersToSearch,
} from "@/lib/history-url-state";

function roundTrip(state: HistoryFilterState): HistoryFilterState {
  const params = writeHistoryFiltersToSearch(state);
  return readHistoryFiltersFromSearch(new URLSearchParams(params));
}

describe("history-url-state", () => {
  test("round trips full state", () => {
    const state: HistoryFilterState = {
      from: new Date("2026-04-01T00:00:00Z"),
      to: new Date("2026-04-02T00:00:00Z"),
      granularity: "5m",
      cameraIds: ["11111111-1111-1111-1111-111111111111"],
      classNames: ["person", "car"],
      speed: true,
      speedThreshold: 60,
    };
    expect(roundTrip(state)).toEqual(state);
  });

  test("treats absent speed as false", () => {
    const parsed = readHistoryFiltersFromSearch(new URLSearchParams());
    expect(parsed.speed).toBe(false);
  });

  test("omits speedThreshold and speed when speed disabled", () => {
    const params = writeHistoryFiltersToSearch({
      from: new Date("2026-04-01T00:00:00Z"),
      to: new Date("2026-04-02T00:00:00Z"),
      granularity: "1h",
      cameraIds: [],
      classNames: [],
      speed: false,
      speedThreshold: null,
    });
    const parsed = new URLSearchParams(params);
    expect(parsed.has("speed")).toBe(false);
    expect(parsed.has("speedThreshold")).toBe(false);
  });

  test("invalid granularity falls back to default", () => {
    const parsed = readHistoryFiltersFromSearch(new URLSearchParams("granularity=2d"));
    expect(parsed.granularity).toBe("1h");
  });

  test("comma-separated cameras serialise without trailing comma", () => {
    const params = writeHistoryFiltersToSearch({
      from: new Date("2026-04-01T00:00:00Z"),
      to: new Date("2026-04-02T00:00:00Z"),
      granularity: "1h",
      cameraIds: ["a", "b"],
      classNames: [],
      speed: false,
      speedThreshold: null,
    });
    expect(new URLSearchParams(params).get("cameras")).toBe("a,b");
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd frontend && npx vitest run src/lib/history-url-state.test.ts`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement the module**

Create `frontend/src/lib/history-url-state.ts`:

```typescript
export type HistoryGranularity = "1m" | "5m" | "1h" | "1d";

export interface HistoryFilterState {
  from: Date;
  to: Date;
  granularity: HistoryGranularity;
  cameraIds: string[];
  classNames: string[];
  speed: boolean;
  speedThreshold: number | null;
}

const GRANULARITIES = new Set<HistoryGranularity>(["1m", "5m", "1h", "1d"]);

function toDate(value: string | null, fallback: Date): Date {
  if (!value) {
    return fallback;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? fallback : parsed;
}

function toGranularity(value: string | null): HistoryGranularity {
  if (value && GRANULARITIES.has(value as HistoryGranularity)) {
    return value as HistoryGranularity;
  }
  return "1h";
}

function toList(value: string | null): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function toPositiveNumber(value: string | null): number | null {
  if (value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

export function defaultHistoryFilters(now = new Date()): HistoryFilterState {
  const to = new Date(now);
  to.setSeconds(0, 0);
  const from = new Date(to);
  from.setDate(from.getDate() - 1);
  return {
    from,
    to,
    granularity: "1h",
    cameraIds: [],
    classNames: [],
    speed: false,
    speedThreshold: null,
  };
}

export function readHistoryFiltersFromSearch(
  params: URLSearchParams,
  now = new Date(),
): HistoryFilterState {
  const defaults = defaultHistoryFilters(now);
  return {
    from: toDate(params.get("from"), defaults.from),
    to: toDate(params.get("to"), defaults.to),
    granularity: toGranularity(params.get("granularity")),
    cameraIds: toList(params.get("cameras")),
    classNames: toList(params.get("classes")),
    speed: params.get("speed") === "1",
    speedThreshold: toPositiveNumber(params.get("speedThreshold")),
  };
}

export function writeHistoryFiltersToSearch(state: HistoryFilterState): string {
  const params = new URLSearchParams();
  params.set("from", state.from.toISOString());
  params.set("to", state.to.toISOString());
  params.set("granularity", state.granularity);
  if (state.cameraIds.length > 0) {
    params.set("cameras", state.cameraIds.join(","));
  }
  if (state.classNames.length > 0) {
    params.set("classes", state.classNames.join(","));
  }
  if (state.speed) {
    params.set("speed", "1");
    if (state.speedThreshold !== null) {
      params.set("speedThreshold", String(state.speedThreshold));
    }
  }
  return params.toString();
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/lib/history-url-state.test.ts`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/history-url-state.ts frontend/src/lib/history-url-state.test.ts
git commit -m "feat(history): URL-serialisable history filter state"
```

---

## Task 8: Add useHistoryClasses hook and extend useHistorySeries

**Files:**
- Modify: `frontend/src/hooks/use-history.ts`

- [ ] **Step 1: Replace the hook file content**

Replace the entire contents of `frontend/src/hooks/use-history.ts` with:

```typescript
import { queryOptions, useQuery } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";
import { buildApiUrl } from "@/lib/ws";
import { useAuthStore } from "@/stores/auth-store";

export type HistorySeriesResponse = components["schemas"]["HistorySeriesResponse"];
export type HistoryClassesResponse = components["schemas"]["HistoryClassesResponse"];

export type HistoryFilters = {
  from: Date;
  to: Date;
  granularity: "1m" | "5m" | "1h" | "1d";
  cameraIds: string[];
  classNames: string[];
  includeSpeed?: boolean;
  speedThreshold?: number | null;
};

export function createDefaultHistoryFilters(now = new Date()): HistoryFilters {
  const to = new Date(now);
  to.setSeconds(0, 0);
  const from = new Date(to);
  from.setDate(from.getDate() - 1);

  return {
    from,
    to,
    granularity: "1h",
    cameraIds: [],
    classNames: [],
    includeSpeed: false,
    speedThreshold: null,
  };
}

export function historySeriesQueryOptions(filters: HistoryFilters) {
  return queryOptions({
    queryKey: [
      "history-series",
      filters.from.toISOString(),
      filters.to.toISOString(),
      filters.granularity,
      filters.cameraIds,
      filters.classNames,
      filters.includeSpeed ?? false,
      filters.speedThreshold ?? null,
    ],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/history/series", {
        params: {
          query: {
            from: filters.from.toISOString(),
            to: filters.to.toISOString(),
            granularity: filters.granularity,
            camera_ids: filters.cameraIds.length > 0 ? filters.cameraIds : undefined,
            class_names: filters.classNames.length > 0 ? filters.classNames : undefined,
            include_speed: filters.includeSpeed ? true : undefined,
            speed_threshold:
              filters.includeSpeed && filters.speedThreshold !== null && filters.speedThreshold !== undefined
                ? filters.speedThreshold
                : undefined,
          },
        },
      });
      if (error || !data) {
        throw toApiError(error, "Failed to load history.");
      }
      return data;
    },
  });
}

export function useHistorySeries(filters: HistoryFilters) {
  return useQuery(historySeriesQueryOptions(filters));
}

export function historyClassesQueryOptions(params: {
  from: Date;
  to: Date;
  cameraIds: string[];
}) {
  return queryOptions({
    queryKey: [
      "history-classes",
      params.from.toISOString(),
      params.to.toISOString(),
      params.cameraIds,
    ],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/history/classes", {
        params: {
          query: {
            from: params.from.toISOString(),
            to: params.to.toISOString(),
            camera_ids: params.cameraIds.length > 0 ? params.cameraIds : undefined,
          },
        },
      });
      if (error || !data) {
        throw toApiError(error, "Failed to load class list.");
      }
      return data;
    },
  });
}

export function useHistoryClasses(params: { from: Date; to: Date; cameraIds: string[] }) {
  return useQuery(historyClassesQueryOptions(params));
}

export async function downloadHistoryExport(
  filters: HistoryFilters,
  format: "csv" | "parquet",
) {
  const { accessToken, user } = useAuthStore.getState();
  const headers = new Headers();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  if (user?.tenantId) {
    headers.set("X-Tenant-ID", user.tenantId);
  }

  const response = await fetch(
    buildApiUrl("/api/v1/export", {
      from: filters.from.toISOString(),
      to: filters.to.toISOString(),
      granularity: filters.granularity,
      format,
      camera_ids: filters.cameraIds,
      class_names: filters.classNames,
    }),
    { headers },
  );

  if (!response.ok) {
    throw new Error(`Failed to export ${format.toUpperCase()} history.`);
  }

  const blob = await response.blob();
  const filename = parseFilename(response.headers.get("Content-Disposition"), format);

  if (typeof window === "undefined" || typeof window.URL.createObjectURL !== "function") {
    return;
  }

  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}

function parseFilename(header: string | null, format: "csv" | "parquet"): string {
  const match = header?.match(/filename="(?<filename>[^"]+)"/);
  return match?.groups?.filename ?? `history.${format}`;
}
```

- [ ] **Step 2: Verify typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exits 0 (no type errors).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/use-history.ts
git commit -m "feat(history): extend useHistorySeries and add useHistoryClasses"
```

---

## Task 9: Extend HistoryTrendChart with speed panel and violation bars

**Files:**
- Modify: `frontend/src/components/history/HistoryTrendChart.tsx`
- Create: `frontend/src/components/history/HistoryTrendChart.test.tsx`

- [ ] **Step 1: Expose an option-builder for testability, then rewrite the component**

Replace `frontend/src/components/history/HistoryTrendChart.tsx` with:

```typescript
import { useEffect, useMemo, useRef } from "react";
import type { EChartsOption } from "echarts";
import { BarChart, LineChart } from "echarts/charts";
import {
  BrushComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  ToolboxComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { init, type EChartsType, use as registerECharts } from "echarts/core";

import { cn } from "@/lib/utils";

type HistoryTrendPoint = {
  bucket: string;
  values: Record<string, number>;
  total_count?: number;
  speed_p50?: Record<string, number> | null;
  speed_p95?: Record<string, number> | null;
  speed_sample_count?: Record<string, number> | null;
  over_threshold_count?: Record<string, number> | null;
};

type HistoryTrendSeries = {
  classNames: string[];
  points: HistoryTrendPoint[];
  speedClassesUsed?: string[] | null;
  includeSpeed?: boolean;
  speedThreshold?: number | null;
};

registerECharts([
  LineChart,
  BarChart,
  BrushComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  ToolboxComponent,
  TooltipComponent,
  CanvasRenderer,
]);

const PALETTE = ["#4f8cff", "#8b6dff", "#26d0ff", "#6de4a7", "#ffaf52", "#ff6b91", "#c28bff", "#f5d570"];

export function buildHistoryChartOption(series: HistoryTrendSeries): EChartsOption {
  const buckets = series.points.map((p) => formatBucket(p.bucket));
  const speedOn = !!series.includeSpeed;
  const thresholdSet = speedOn && series.speedThreshold !== null && series.speedThreshold !== undefined;
  const speedClasses = series.speedClassesUsed ?? [];

  const grids: NonNullable<EChartsOption["grid"]> = [
    { top: 56, left: 20, right: 16, bottom: thresholdSet ? 260 : speedOn ? 216 : 56, containLabel: true },
  ];
  const xAxes: NonNullable<EChartsOption["xAxis"]> = [
    {
      type: "category",
      gridIndex: 0,
      boundaryGap: false,
      data: buckets,
      axisLine: { lineStyle: { color: "rgba(117, 146, 187, 0.32)" } },
      axisLabel: { color: "#8ea8cf", hideOverlap: true },
    },
  ];
  const yAxes: NonNullable<EChartsOption["yAxis"]> = [
    {
      type: "value",
      gridIndex: 0,
      minInterval: 1,
      splitLine: { lineStyle: { color: "rgba(117, 146, 187, 0.14)" } },
      axisLine: { show: false },
      axisLabel: { color: "#8ea8cf" },
    },
  ];

  const seriesList: NonNullable<EChartsOption["series"]> = series.classNames.map((cls, i) => ({
    name: cls,
    type: "line",
    smooth: true,
    showSymbol: false,
    color: PALETTE[i % PALETTE.length],
    lineStyle: { width: 2.5 },
    areaStyle: { opacity: 0.1 },
    xAxisIndex: 0,
    yAxisIndex: 0,
    data: series.points.map((p) => p.values[cls] ?? 0),
  }));

  if (thresholdSet) {
    grids.push({ top: 320, left: 20, right: 16, height: 56, containLabel: true });
    xAxes.push({
      type: "category",
      gridIndex: 1,
      boundaryGap: true,
      data: buckets,
      show: false,
    });
    yAxes.push({
      type: "value",
      gridIndex: 1,
      minInterval: 1,
      splitLine: { show: false },
      axisLine: { show: false },
      axisLabel: { color: "#8ea8cf" },
    });
    speedClasses.forEach((cls, i) => {
      seriesList.push({
        name: `${cls} (over threshold)`,
        type: "bar",
        stack: "violations",
        xAxisIndex: 1,
        yAxisIndex: 1,
        color: PALETTE[i % PALETTE.length],
        data: series.points.map((p) => p.over_threshold_count?.[cls] ?? 0),
      });
    });
  }

  if (speedOn) {
    const speedGridTop = thresholdSet ? 400 : 320;
    grids.push({ top: speedGridTop, left: 20, right: 16, bottom: 40, containLabel: true });
    xAxes.push({
      type: "category",
      gridIndex: grids.length - 1,
      boundaryGap: false,
      data: buckets,
      axisLine: { lineStyle: { color: "rgba(117, 146, 187, 0.32)" } },
      axisLabel: { color: "#8ea8cf", hideOverlap: true },
    });
    yAxes.push({
      type: "value",
      gridIndex: grids.length - 1,
      name: "km/h",
      nameTextStyle: { color: "#8ea8cf" },
      splitLine: { lineStyle: { color: "rgba(117, 146, 187, 0.14)" } },
      axisLine: { show: false },
      axisLabel: { color: "#8ea8cf" },
    });

    speedClasses.forEach((cls, i) => {
      const color = PALETTE[i % PALETTE.length];
      const xIndex = xAxes.length - 1;
      const yIndex = yAxes.length - 1;
      seriesList.push({
        name: `${cls} p50`,
        type: "line",
        smooth: true,
        showSymbol: false,
        xAxisIndex: xIndex,
        yAxisIndex: yIndex,
        color,
        lineStyle: { width: 2, type: "solid" },
        data: series.points.map((p) => p.speed_p50?.[cls] ?? null),
      });
      seriesList.push({
        name: `${cls} p95`,
        type: "line",
        smooth: true,
        showSymbol: false,
        xAxisIndex: xIndex,
        yAxisIndex: yIndex,
        color,
        lineStyle: { width: 1.5, type: "dashed" },
        areaStyle: { opacity: 0.08 },
        data: series.points.map((p) => p.speed_p95?.[cls] ?? null),
        markLine: thresholdSet && i === 0
          ? {
              symbol: "none",
              lineStyle: { color: "#ff6b91", type: "dashed" },
              data: [{ yAxis: series.speedThreshold ?? 0, name: "threshold" }],
            }
          : undefined,
      });
    });
  }

  return {
    animation: false,
    color: PALETTE,
    legend: { top: 0, textStyle: { color: "#dbe7ff" }, itemGap: 18 },
    grid: grids,
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", link: [{ xAxisIndex: "all" }] },
      backgroundColor: "rgba(6, 11, 18, 0.96)",
      borderColor: "rgba(90, 149, 255, 0.28)",
      textStyle: { color: "#eef4ff" },
    },
    toolbox: {
      right: 0,
      iconStyle: { borderColor: "#8ea8cf" },
      feature: {
        dataZoom: { yAxisIndex: "none" },
        restore: {},
      },
    },
    brush: { toolbox: ["rect", "clear"], xAxisIndex: "all" },
    xAxis: xAxes,
    yAxis: yAxes,
    series: seriesList,
  };
}

export function HistoryTrendChart({
  series,
  className,
}: {
  series: HistoryTrendSeries;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<EChartsType | null>(null);
  const option = useMemo(() => buildHistoryChartOption(series), [series]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart = chartRef.current ?? init(container, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(option, true);
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [option]);

  useEffect(() => {
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  const height = series.includeSpeed
    ? series.speedThreshold !== null && series.speedThreshold !== undefined
      ? "680px"
      : "560px"
    : "360px";

  return (
    <div
      ref={containerRef}
      className={cn("w-full", className)}
      style={{ height }}
      role="img"
      aria-label="History trend chart"
    />
  );
}

function formatBucket(value: string): string {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(date);
}
```

- [ ] **Step 2: Write a test for the option builder**

Create `frontend/src/components/history/HistoryTrendChart.test.tsx`:

```typescript
import { describe, expect, test } from "vitest";

import { buildHistoryChartOption } from "@/components/history/HistoryTrendChart";

const BASE_POINT = {
  bucket: "2026-04-23T00:00:00Z",
  values: { car: 12, person: 4 },
  total_count: 16,
};

describe("buildHistoryChartOption", () => {
  test("renders a single grid when speed is off", () => {
    const option = buildHistoryChartOption({
      classNames: ["car", "person"],
      points: [BASE_POINT],
      includeSpeed: false,
    });
    expect(Array.isArray(option.grid) ? option.grid.length : 1).toBe(1);
    expect(Array.isArray(option.series)).toBe(true);
    expect((option.series as unknown as { name: string }[]).map((s) => s.name)).toEqual([
      "car",
      "person",
    ]);
  });

  test("adds a speed panel with p50 and p95 series when speed is on", () => {
    const option = buildHistoryChartOption({
      classNames: ["car"],
      points: [
        {
          ...BASE_POINT,
          speed_p50: { car: 40 },
          speed_p95: { car: 55 },
          speed_sample_count: { car: 12 },
        },
      ],
      includeSpeed: true,
      speedClassesUsed: ["car"],
    });
    const names = (option.series as unknown as { name: string }[]).map((s) => s.name);
    expect(names).toContain("car p50");
    expect(names).toContain("car p95");
    expect(Array.isArray(option.grid) ? option.grid.length : 1).toBe(2);
  });

  test("adds violation bars and a threshold markLine when a threshold is set", () => {
    const option = buildHistoryChartOption({
      classNames: ["car"],
      points: [
        {
          ...BASE_POINT,
          speed_p50: { car: 40 },
          speed_p95: { car: 55 },
          speed_sample_count: { car: 12 },
          over_threshold_count: { car: 3 },
        },
      ],
      includeSpeed: true,
      speedThreshold: 50,
      speedClassesUsed: ["car"],
    });
    const seriesList = option.series as unknown as Array<{
      name: string;
      type: string;
      markLine?: { data: Array<{ yAxis: number }> };
    }>;
    const violation = seriesList.find((s) => s.name === "car (over threshold)");
    expect(violation).toBeDefined();
    expect(violation?.type).toBe("bar");
    const p95 = seriesList.find((s) => s.name === "car p95");
    expect(p95?.markLine?.data?.[0].yAxis).toBe(50);
  });
});
```

- [ ] **Step 3: Run the tests**

Run: `cd frontend && npx vitest run src/components/history/HistoryTrendChart.test.tsx src/lib/history-url-state.test.ts`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/history/HistoryTrendChart.tsx frontend/src/components/history/HistoryTrendChart.test.tsx
git commit -m "feat(history): stacked speed panel and violation bars in HistoryTrendChart"
```

---

## Task 10: Wire URL state, dynamic classes, and new controls into History page

**Files:**
- Modify: `frontend/src/pages/History.tsx`

- [ ] **Step 1: Replace the file**

Replace `frontend/src/pages/History.tsx` with:

```typescript
import { lazy, startTransition, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { productBrand } from "@/brand/product";
import { COCO_CLASSES } from "@/lib/coco-classes";
import {
  type HistoryFilterState,
  readHistoryFiltersFromSearch,
  writeHistoryFiltersToSearch,
} from "@/lib/history-url-state";
import { useCameras } from "@/hooks/use-cameras";
import {
  downloadHistoryExport,
  useHistoryClasses,
  useHistorySeries,
} from "@/hooks/use-history";

const HistoryTrendChart = lazy(async () => ({
  default: (await import("@/components/history/HistoryTrendChart")).HistoryTrendChart,
}));

export function HistoryPage() {
  const brandName = productBrand.name;
  const location = useLocation();
  const navigate = useNavigate();
  const { data: cameras = [] } = useCameras();

  const [state, setState] = useState<HistoryFilterState>(() =>
    readHistoryFiltersFromSearch(new URLSearchParams(location.search)),
  );
  const [showAllClasses, setShowAllClasses] = useState(false);
  const [isDownloading, setIsDownloading] = useState<"csv" | "parquet" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const applyState = useCallback(
    (next: HistoryFilterState | ((prev: HistoryFilterState) => HistoryFilterState)) => {
      setState((prev) => {
        const resolved = typeof next === "function" ? next(prev) : next;
        const search = writeHistoryFiltersToSearch(resolved);
        navigate({ pathname: location.pathname, search: `?${search}` }, { replace: true });
        return resolved;
      });
    },
    [location.pathname, navigate],
  );

  useEffect(() => {
    const parsed = readHistoryFiltersFromSearch(new URLSearchParams(location.search));
    setState(parsed);
  }, [location.search]);

  const filters = useMemo(
    () => ({
      from: state.from,
      to: state.to,
      granularity: state.granularity,
      cameraIds: state.cameraIds,
      classNames: state.classNames,
      includeSpeed: state.speed,
      speedThreshold: state.speedThreshold,
    }),
    [state],
  );

  const { data, isLoading, error } = useHistorySeries(filters);
  const { data: classesData } = useHistoryClasses({
    from: state.from,
    to: state.to,
    cameraIds: state.cameraIds,
  });

  const observedClasses = useMemo(
    () => classesData?.classes ?? [],
    [classesData],
  );
  const unseenCocoClasses = useMemo(() => {
    const seen = new Set(observedClasses.map((c) => c.class_name));
    return COCO_CLASSES.filter((name) => !seen.has(name));
  }, [observedClasses]);

  const chartSeries = useMemo(
    () => ({
      classNames: data?.class_names ?? [],
      points: data?.rows ?? [],
      includeSpeed: state.speed,
      speedThreshold: state.speedThreshold ?? null,
      speedClassesUsed: data?.speed_classes_used ?? null,
    }),
    [data, state.speed, state.speedThreshold],
  );

  const totalCount = useMemo(
    () => (data?.rows ?? []).reduce((sum, row) => sum + row.total_count, 0),
    [data],
  );

  const chartEmpty = !isLoading && (data?.rows.length ?? 0) === 0;
  const granularityBumped = data?.granularity_adjusted === true;
  const speedCapped = data?.speed_classes_capped === true;
  const speedRequestedButEmpty =
    state.speed && !isLoading && (data?.speed_classes_used?.length ?? 0) === 0;

  async function handleDownload(format: "csv" | "parquet") {
    setIsDownloading(format);
    setDownloadError(null);
    try {
      await downloadHistoryExport(filters, format);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : `Failed to export ${format}.`);
    } finally {
      setIsDownloading(null);
    }
  }

  function applyPresetRange(days: number) {
    applyState((prev) => {
      const to = new Date();
      to.setSeconds(0, 0);
      const from = new Date(to);
      from.setDate(from.getDate() - days);
      return { ...prev, from, to };
    });
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.98),rgba(5,8,14,0.96))]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">History</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
                Fleet history and speed telemetry.
              </h2>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                {brandName} aggregates detections and speeds in buckets so operators can pivot across classes and
                cameras without reshaping data in the browser.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">{state.granularity}</Badge>
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">{totalCount} detections</Badge>
              {granularityBumped ? (
                <Badge className="border-[#705e29] bg-[#1d1b08]/80 text-[#ffe5a8]">
                  granularity adjusted to {data?.granularity}
                </Badge>
              ) : null}
              {speedCapped ? (
                <Badge className="border-[#705e29] bg-[#1d1b08]/80 text-[#ffe5a8]">
                  speed panel capped at 20 classes
                </Badge>
              ) : null}
            </div>
          </div>
        </div>

        <div className="space-y-6 px-6 py-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea8cf]">Time window</p>
              <p className="mt-2 text-sm text-[#dce6f7]">{formatRangeLabel(state.from, state.to)}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                className="bg-white/[0.06] px-4 py-2 text-[#e7efff] shadow-none hover:bg-white/[0.1]"
                onClick={() => applyPresetRange(1)}
              >
                Last 24h
              </Button>
              <Button
                className="bg-white/[0.06] px-4 py-2 text-[#e7efff] shadow-none hover:bg-white/[0.1]"
                onClick={() => applyPresetRange(7)}
              >
                Last 7d
              </Button>
              <Button disabled={isDownloading !== null} onClick={() => void handleDownload("csv")}>
                {isDownloading === "csv" ? "Downloading..." : "Download CSV"}
              </Button>
              <Button
                disabled={isDownloading !== null}
                className="bg-white/[0.06] text-[#edf3ff] shadow-none hover:bg-white/[0.1]"
                onClick={() => void handleDownload("parquet")}
              >
                {isDownloading === "parquet" ? "Downloading..." : "Download Parquet"}
              </Button>
            </div>
          </div>

          <div className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(8,13,22,0.98),rgba(4,7,12,0.96))]">
            {isLoading ? (
              <div className="px-6 py-16 text-sm text-[#93a7c5]">Loading history…</div>
            ) : error ? (
              <div className="px-6 py-16 text-sm text-[#f0b7c1]">
                {error instanceof Error ? error.message : "Failed to load history."}
              </div>
            ) : chartEmpty ? (
              <div className="space-y-4 px-6 py-16 text-sm text-[#93a7c5]">
                <p>No detections in this window for the selected cameras and classes.</p>
                <Button onClick={() => applyPresetRange(7)}>Try last 7 days</Button>
              </div>
            ) : (
              <div className="space-y-3">
                {speedRequestedButEmpty ? (
                  <p className="px-6 pt-4 text-sm text-[#ffd28a]">
                    None of the selected classes have speed data in this window — try widening the range or check camera homography.
                  </p>
                ) : null}
                <Suspense fallback={<div className="px-6 py-16 text-sm text-[#93a7c5]">Loading chart…</div>}>
                  <HistoryTrendChart className="px-2 py-4" series={chartSeries} />
                </Suspense>
              </div>
            )}
          </div>

          {downloadError ? <p className="text-sm text-[#f0b7c1]">{downloadError}</p> : null}
        </div>
      </section>

      <aside className="space-y-6">
        <section className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,15,24,0.98),rgba(4,7,12,0.96))]">
          <div className="border-b border-white/8 px-5 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">Filters</p>
            <h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">Scope the historical view</h3>
          </div>

          <div className="space-y-4 px-5 py-5">
            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Granularity</span>
              <Select
                aria-label="Granularity"
                value={state.granularity}
                onChange={(e) =>
                  applyState((p) => ({ ...p, granularity: e.target.value as HistoryFilterState["granularity"] }))
                }
              >
                <option value="1m">1 minute</option>
                <option value="5m">5 minutes</option>
                <option value="1h">1 hour</option>
                <option value="1d">1 day</option>
              </Select>
            </label>

            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Camera filters</span>
              <Select
                aria-label="Camera filters"
                multiple
                className="min-h-36 rounded-[1.5rem] py-3"
                value={state.cameraIds}
                onChange={(e) =>
                  applyState((p) => ({ ...p, cameraIds: Array.from(e.currentTarget.selectedOptions, (o) => o.value) }))
                }
              >
                {cameras.map((camera) => (
                  <option key={camera.id} value={camera.id}>
                    {camera.name}
                  </option>
                ))}
              </Select>
            </label>

            <div className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Class filters</span>
              <Select
                aria-label="Class filters"
                multiple
                className="min-h-36 rounded-[1.5rem] py-3"
                value={state.classNames}
                onChange={(e) =>
                  applyState((p) => ({ ...p, classNames: Array.from(e.currentTarget.selectedOptions, (o) => o.value) }))
                }
              >
                {observedClasses.map((entry) => (
                  <option key={entry.class_name} value={entry.class_name}>
                    {entry.class_name} ({entry.event_count})
                    {entry.has_speed_data ? "" : " — no speed data in this window"}
                  </option>
                ))}
                {showAllClasses
                  ? unseenCocoClasses.map((name) => (
                      <option key={name} value={name}>
                        {name} (0)
                      </option>
                    ))
                  : null}
              </Select>
              <button
                type="button"
                className="text-xs text-[#8ea8cf] underline"
                onClick={() => setShowAllClasses((v) => !v)}
              >
                {showAllClasses ? "Hide unseen classes" : "Show all 80 COCO classes"}
              </button>
            </div>

            <label className="flex items-center gap-2 text-sm text-[#d9e5f7]">
              <input
                type="checkbox"
                aria-label="Show speed"
                checked={state.speed}
                onChange={(e) => applyState((p) => ({ ...p, speed: e.target.checked }))}
              />
              <span>Show speed</span>
            </label>

            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
                Speed threshold (km/h)
              </span>
              <Input
                aria-label="Speed threshold"
                type="number"
                min={0}
                step={1}
                disabled={!state.speed}
                value={state.speedThreshold ?? ""}
                onChange={(e) => {
                  const raw = e.target.value.trim();
                  applyState((p) => ({
                    ...p,
                    speedThreshold: raw === "" ? null : Number(raw),
                  }));
                }}
              />
            </label>
          </div>
        </section>
      </aside>
    </div>
  );
}

function formatRangeLabel(from: Date, to: Date): string {
  const fmt = (d: Date) =>
    d.toLocaleDateString("en-GB", { month: "short", day: "numeric", year: "numeric" });
  return `${fmt(from)} to ${fmt(to)}`;
}
```

- [ ] **Step 2: Verify typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/History.tsx
git commit -m "feat(history): URL-persisted filter state, dynamic classes, speed controls, empty state"
```

---

## Task 11: Update the History page vitest

**Files:**
- Modify: `frontend/src/pages/History.test.tsx`

- [ ] **Step 1: Replace the test file**

Replace `frontend/src/pages/History.test.tsx` with:

```typescript
import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/config", () => ({
  frontendConfig: {
    apiBaseUrl: "http://127.0.0.1:8000",
    oidcAuthority: "http://127.0.0.1:8080/realms/argus-dev",
    oidcClientId: "argus-frontend",
    oidcRedirectUri: "http://127.0.0.1:3000/auth/callback",
    oidcPostLogoutRedirectUri: "http://127.0.0.1:3000/signin",
  },
}));

vi.mock("@/components/history/HistoryTrendChart", () => ({
  HistoryTrendChart: ({ series }: { series: { classNames: string[]; points: unknown[]; includeSpeed?: boolean; speedThreshold?: number | null } }) => (
    <div data-testid="history-trend-chart">
      {series.classNames.join(",")}::{series.points.length}::speed={String(!!series.includeSpeed)}::threshold={String(series.speedThreshold ?? "none")}
    </div>
  ),
}));

import { createQueryClient } from "@/app/query-client";
import { HistoryPage } from "@/pages/History";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

function historySeriesResponse(overrides: Record<string, unknown> = {}) {
  return {
    granularity: "1h",
    class_names: ["car", "bus"],
    rows: [
      { bucket: "2026-04-12T00:00:00Z", values: { car: 22, bus: 6 }, total_count: 28 },
    ],
    granularity_adjusted: false,
    speed_classes_capped: false,
    speed_classes_used: null,
    ...overrides,
  };
}

function classesResponse() {
  return {
    from: "2026-04-12T00:00:00Z",
    to: "2026-04-19T00:00:00Z",
    classes: [
      { class_name: "car", event_count: 40, has_speed_data: true },
      { class_name: "bus", event_count: 10, has_speed_data: true },
      { class_name: "person", event_count: 5, has_speed_data: false },
    ],
  };
}

function renderPage(initialEntry = "/history") {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <HistoryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("HistoryPage", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState({
        status: "authenticated",
        accessToken: "history-token",
        user: {
          sub: "analyst-1",
          email: "analyst@argus.local",
          role: "viewer",
          realm: "argus-dev",
          tenantId: "tenant-1",
          isSuperadmin: false,
        },
      });
    });

    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);
      if (url.pathname === "/api/v1/cameras") return Promise.resolve(jsonResponse([]));
      if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
      if (url.pathname === "/api/v1/history/series") {
        if (url.searchParams.get("include_speed") === "true") {
          return Promise.resolve(
            jsonResponse(
              historySeriesResponse({
                rows: [
                  {
                    bucket: "2026-04-12T00:00:00Z",
                    values: { car: 22, bus: 6 },
                    total_count: 28,
                    speed_p50: { car: 42 },
                    speed_p95: { car: 55 },
                    speed_sample_count: { car: 22 },
                    over_threshold_count: url.searchParams.get("speed_threshold") ? { car: 5 } : null,
                  },
                ],
                speed_classes_used: ["car"],
              }),
            ),
          );
        }
        return Promise.resolve(jsonResponse(historySeriesResponse()));
      }
      return Promise.resolve(new Response("Not found", { status: 404 }));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("hydrates filter state from URL and calls endpoint with include_speed", async () => {
    renderPage("/history?speed=1&speedThreshold=50&granularity=5m");
    await waitFor(() =>
      expect(screen.getByTestId("history-trend-chart")).toHaveTextContent(
        "speed=true::threshold=50",
      ),
    );
  });

  test("toggling Show speed and entering a threshold updates the chart props", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("button", { name: /download csv/i });

    await user.click(screen.getByLabelText(/show speed/i));
    await user.type(screen.getByLabelText(/speed threshold/i), "60");

    await waitFor(() =>
      expect(screen.getByTestId("history-trend-chart")).toHaveTextContent(
        "speed=true::threshold=60",
      ),
    );
  });

  test("empty result shows the Try last 7 days button", async () => {
    vi.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve(jsonResponse(historySeriesResponse({ rows: [] }))),
    );
    renderPage();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /try last 7 days/i })).toBeInTheDocument(),
    );
  });

  test("class filter is populated by /history/classes", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /car \(40\)/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("option", { name: /person \(5\) — no speed/i })).toBeInTheDocument();
  });

  test("Show all 80 COCO classes expander reveals unseen classes", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("option", { name: /car \(40\)/i });
    await user.click(screen.getByRole("button", { name: /show all 80 coco classes/i }));
    expect(screen.getByRole("option", { name: /giraffe \(0\)/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run src/pages/History.test.tsx src/lib/history-url-state.test.ts src/components/history/HistoryTrendChart.test.tsx`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/History.test.tsx
git commit -m "test(history): cover URL hydration, speed controls, empty state, class dynamism"
```

---

## Task 12: Extend e2e spec for URL persistence + speed flow

**Files:**
- Modify: `frontend/e2e/prompt9-history-and-incidents.spec.ts`

- [ ] **Step 1: Add new test cases to the existing spec file**

Open the spec and append — after the existing `test(...)` block closes — this additional test. Add it inside the same file. You do not need to change the existing test.

```typescript
test("history filter state survives navigation via URL", async ({ page }) => {
  await page.route("**/api/v1/cameras", async (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([cameraPayload()]),
    }),
  );
  await page.route("**/api/v1/history/classes**", async (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        from: "2026-04-23T00:00:00Z",
        to: "2026-04-23T23:00:00Z",
        classes: [
          { class_name: "car", event_count: 40, has_speed_data: true },
        ],
      }),
    }),
  );
  await page.route("**/api/v1/history/series**", async (route) => {
    const url = new URL(route.request().url());
    const includeSpeed = url.searchParams.get("include_speed") === "true";
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        granularity: "1h",
        class_names: ["car"],
        rows: [
          {
            bucket: "2026-04-23T00:00:00Z",
            values: { car: 10 },
            total_count: 10,
            speed_p50: includeSpeed ? { car: 42 } : null,
            speed_p95: includeSpeed ? { car: 55 } : null,
            speed_sample_count: includeSpeed ? { car: 10 } : null,
            over_threshold_count:
              includeSpeed && url.searchParams.get("speed_threshold")
                ? { car: 3 }
                : null,
          },
        ],
        granularity_adjusted: false,
        speed_classes_capped: false,
        speed_classes_used: includeSpeed ? ["car"] : null,
      }),
    });
  });

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await page.getByRole("link", { name: "History" }).click();
  await expect(page).toHaveURL(/\/history/);

  await page.getByLabel("Show speed").check();
  await page.getByLabel("Speed threshold").fill("60");

  await expect(page).toHaveURL(/speed=1/);
  await expect(page).toHaveURL(/speedThreshold=60/);

  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/history.*speed=1.*speedThreshold=60/);
  await expect(page.getByLabel("Show speed")).toBeChecked();
  await expect(page.getByLabel("Speed threshold")).toHaveValue("60");
});

test("deep link with speed params applies state on load", async ({ page }) => {
  await page.route("**/api/v1/cameras", async (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([cameraPayload()]),
    }),
  );
  await page.route("**/api/v1/history/classes**", async (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        from: "2026-04-23T00:00:00Z",
        to: "2026-04-23T23:00:00Z",
        classes: [{ class_name: "car", event_count: 40, has_speed_data: true }],
      }),
    }),
  );
  await page.route("**/api/v1/history/series**", async (route) => {
    const url = new URL(route.request().url());
    expect(url.searchParams.get("include_speed")).toBe("true");
    expect(url.searchParams.get("speed_threshold")).toBe("60");
    expect(url.searchParams.get("granularity")).toBe("5m");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        granularity: "5m",
        class_names: ["car"],
        rows: [],
        granularity_adjusted: false,
        speed_classes_capped: false,
        speed_classes_used: ["car"],
      }),
    });
  });

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await page.goto("/history?speed=1&speedThreshold=60&granularity=5m");
  await expect(page.getByLabel("Show speed")).toBeChecked();
  await expect(page.getByLabel("Speed threshold")).toHaveValue("60");
});
```

- [ ] **Step 2: Run the e2e spec**

Run: `cd frontend && npx playwright test e2e/prompt9-history-and-incidents.spec.ts --reporter=line`
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/prompt9-history-and-incidents.spec.ts
git commit -m "test(e2e): history URL persistence, speed toggle, deep link"
```

---

## Final Verification

- [ ] **Step 1: Full backend test suite**

Run: `cd backend && python3 -m uv run pytest -q`
Expected: all pass.

- [ ] **Step 2: Full frontend unit tests**

Run: `cd frontend && npx vitest run`
Expected: all pass.

- [ ] **Step 3: Frontend typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 4: Verify the spec's success criteria manually in the dev stack**

Start the dev stack:

```bash
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend frontend
```

In a browser:

1. Visit `/history`. Default is last 24 h + all classes. Chart shows data if `tracking_events` has rows in that window.
2. Change filter (camera, class, granularity), navigate to `/live`, back to `/history`. Filter preserved (check URL bar).
3. Tick **Show speed**, enter threshold **60**. The speed panel appears with threshold line and violation bars.
4. If no data in 24 h window: see **Try last 7 days** button.
5. Deep link `/history?speed=1&speedThreshold=60&granularity=5m` applies state on first load.

If all five pass, the feature is implementation-complete against the spec.

### Known Deferred

- **Per-camera homography tag in the speed legend.** The spec mentions labelling a camera as "(speed not configured)" when its `homography` is null. The current `/history/classes` endpoint aggregates across cameras per class (not per camera), so `has_speed_data` is a class-level flag, not camera-level. Deferring per-camera tagging; the class-level flag on the selector and the empty-state banner already cover the common operator confusion ("where are my speeds?"). Track this as a small follow-up after Spec B lands.
