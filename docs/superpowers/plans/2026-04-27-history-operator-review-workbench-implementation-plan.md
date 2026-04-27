# History Operator Review Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the phase-1 History Operator Review Workbench: complete bucket ranges, explicit coverage states, follow-now windows, split review, bucket details, deterministic unified search, and exports that match the visible state.

**Architecture:** Start with the backend trust contract so every frontend state has unambiguous data to render. Then extend URL/window state, split the existing History page into focused components, wire bucket selection, add current-window deterministic search, and finish with export and E2E coverage. Keep ECharts and existing TanStack Query/OpenAPI patterns.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, TimescaleDB, pytest, React, TypeScript, TanStack Query, ECharts, React Testing Library, Vitest, Playwright.

---

## File Structure

- Modify: `backend/src/argus/models/enums.py`
  - Add `HistoryCoverageStatus` as the shared enum for series and bucket coverage.
- Modify: `backend/src/argus/api/contracts.py`
  - Add `HistoryBucketCoverage`.
  - Extend `HistorySeriesResponse` with coverage and effective-window metadata.
- Modify: `backend/src/argus/services/app.py`
  - Add bucket-range helpers.
  - Materialize zero rows in `HistoryService.query_series`.
  - Update `HistoryService.export_history` to export the same bucket set the chart sees.
- Modify: `backend/tests/services/test_history_service.py`
  - Cover zero-filled rows, coverage metadata, speed preservation, and export flattening.
- Modify: `backend/tests/api/test_history_endpoints.py`
  - Cover response serialization of coverage fields.
- Modify: `backend/tests/api/test_export_endpoints.py`
  - Cover export forwarding and zero-bucket output.
- Modify: `frontend/src/lib/api.generated.ts`
  - Regenerated after backend OpenAPI changes.
- Modify: `frontend/src/lib/history-url-state.ts`
  - Add relative/absolute window state, follow-now, and local restore helpers.
- Modify: `frontend/src/lib/history-url-state.test.ts`
  - Cover URL round trips and default behavior.
- Modify: `frontend/src/hooks/use-history.ts`
  - Resolve relative windows to API `from/to`.
  - Carry coverage fields from generated types.
  - Keep export parameters aligned with visible state.
- Create: `frontend/src/lib/history-workbench.ts`
  - Pure derivation helpers for buckets, coverage copy, bucket labels, and total fallback series.
- Create: `frontend/src/lib/history-search.ts`
  - Pure deterministic search over loaded cameras, classes, boundaries, buckets, gaps, and speed breaches.
- Create: `frontend/src/components/history/HistorySearchBox.tsx`
  - Search input and grouped result list.
- Create: `frontend/src/components/history/HistoryToolbar.tsx`
  - Time controls, metric selector, follow/resume control, and search placement.
- Create: `frontend/src/components/history/HistoryTrendPanel.tsx`
  - Chart wrapper, bucket semantics, progressive lanes, and selected-bucket callbacks.
- Create: `frontend/src/components/history/HistoryBucketDetail.tsx`
  - Bucket totals, coverage explanation, class/camera/boundary breakdown, speed breach summary.
- Modify: `frontend/src/components/history/HistoryTrendChart.tsx`
  - Add optional bucket click event and total fallback display support.
- Modify: `frontend/src/components/history/HistoryTrendChart.test.tsx`
  - Cover total fallback and click wiring through chart options.
- Modify: `frontend/src/pages/History.tsx`
  - Coordinate workbench state and render the split review.
- Modify: `frontend/src/pages/History.test.tsx`
  - Cover follow-now, bucket selection, search, coverage states, and export state.
- Modify: `frontend/e2e/prompt9-history-and-incidents.spec.ts`
  - Cover split review interaction and export state.

---

## Task 1: Add Backend Coverage Contract And Zero-Filled Series

**Files:**
- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_history_service.py`
- Test: `backend/tests/api/test_history_endpoints.py`

- [ ] **Step 1: Add failing service tests for zero-filled rows and coverage metadata**

Append these tests to `backend/tests/services/test_history_service.py`:

```python
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
```

Add this import in the same test file:

```python
from argus.models.enums import CountEventType, HistoryCoverageStatus, HistoryMetric
```

- [ ] **Step 2: Run the failing backend tests**

Run:

```bash
python3 -m uv run pytest tests/services/test_history_service.py::test_query_series_returns_zero_buckets_for_empty_valid_window tests/services/test_history_service.py::test_query_series_materializes_missing_buckets_around_populated_rows -q
```

Expected: FAIL because `HistoryCoverageStatus`, `coverage_status`, `effective_from`, `effective_to`, `bucket_count`, `bucket_span`, and `coverage_by_bucket` do not exist yet.

- [ ] **Step 3: Add the coverage enum**

In `backend/src/argus/models/enums.py`, add this enum after `HistoryMetric`:

```python
class HistoryCoverageStatus(StrEnum):
    POPULATED = "populated"
    ZERO = "zero"
    NO_TELEMETRY = "no_telemetry"
    CAMERA_OFFLINE = "camera_offline"
    WORKER_OFFLINE = "worker_offline"
    SOURCE_UNAVAILABLE = "source_unavailable"
    NO_SCOPE = "no_scope"
    ACCESS_LIMITED = "access_limited"
```

- [ ] **Step 4: Extend history response contracts**

In `backend/src/argus/api/contracts.py`, import `HistoryCoverageStatus` from `argus.models.enums` and add this model immediately before `HistorySeriesResponse`:

```python
class HistoryBucketCoverage(BaseModel):
    bucket: datetime
    status: HistoryCoverageStatus
    reason: str | None = None
```

Replace `HistorySeriesResponse` with:

```python
class HistorySeriesResponse(BaseModel):
    granularity: str
    metric: HistoryMetric | None = None
    class_names: list[str]
    rows: list[HistorySeriesRow]
    granularity_adjusted: bool = False
    speed_classes_capped: bool = False
    speed_classes_used: list[str] | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    bucket_count: int = 0
    bucket_span: str | None = None
    coverage_status: HistoryCoverageStatus = HistoryCoverageStatus.POPULATED
    coverage_by_bucket: list[HistoryBucketCoverage] = Field(default_factory=list)
```

- [ ] **Step 5: Add bucket materialization helpers**

In `backend/src/argus/services/app.py`, import `HistoryBucketCoverage` and `HistoryCoverageStatus`. Add these helpers near `_ensure_history_window` and `_effective_granularity`:

```python
def _history_bucket_delta(granularity: str) -> timedelta:
    if granularity == "1m":
        return timedelta(minutes=1)
    if granularity == "5m":
        return timedelta(minutes=5)
    if granularity == "1h":
        return timedelta(hours=1)
    if granularity == "1d":
        return timedelta(days=1)
    raise ValueError(f"Unsupported history granularity: {granularity}")


def _history_bucket_range(
    starts_at: datetime,
    ends_at: datetime,
    granularity: str,
) -> list[datetime]:
    delta = _history_bucket_delta(granularity)
    buckets: list[datetime] = []
    current = starts_at
    while current < ends_at:
        buckets.append(current)
        current += delta
    return buckets


def _summarize_history_coverage(
    coverage_by_bucket: list[HistoryBucketCoverage],
) -> HistoryCoverageStatus:
    statuses = {entry.status for entry in coverage_by_bucket}
    if HistoryCoverageStatus.POPULATED in statuses:
        return HistoryCoverageStatus.POPULATED
    if statuses == {HistoryCoverageStatus.ZERO}:
        return HistoryCoverageStatus.ZERO
    if not statuses:
        return HistoryCoverageStatus.ZERO
    if len(statuses) == 1:
        return next(iter(statuses))
    return HistoryCoverageStatus.NO_TELEMETRY
```

- [ ] **Step 6: Materialize rows in `HistoryService.query_series`**

In `HistoryService.query_series`, replace the final `for bucket in sorted(buckets.keys())` block with:

```python
        result_rows: list[HistorySeriesRow] = []
        coverage_by_bucket: list[HistoryBucketCoverage] = []
        materialized_buckets = _history_bucket_range(
            starts_at,
            ends_at,
            effective_granularity,
        )
        for bucket in materialized_buckets:
            values = buckets.get(bucket, {})
            projected_values = {c: values.get(c, 0) for c in selected_classes}
            total_count = sum(projected_values.values())
            if not selected_classes and values:
                total_count = sum(values.values())
            status = (
                HistoryCoverageStatus.POPULATED
                if total_count > 0
                else HistoryCoverageStatus.ZERO
            )
            series_row = HistorySeriesRow(
                bucket=bucket,
                values=projected_values,
                total_count=total_count,
                speed_p50=_project_speed(speed_p50, bucket),
                speed_p95=_project_speed(speed_p95, bucket),
                speed_sample_count=_project_int(speed_samples, bucket),
                over_threshold_count=(
                    _project_int(violations, bucket) if speed_threshold is not None else None
                ),
            )
            result_rows.append(series_row)
            coverage_by_bucket.append(HistoryBucketCoverage(bucket=bucket, status=status))

        coverage_status = _summarize_history_coverage(coverage_by_bucket)
```

Update the returned `HistorySeriesResponse`:

```python
        return HistorySeriesResponse(
            granularity=effective_granularity,
            metric=metric,
            class_names=selected_classes,
            rows=result_rows,
            granularity_adjusted=granularity_adjusted,
            speed_classes_capped=speed_classes_capped,
            speed_classes_used=speed_classes_used if include_speed else None,
            effective_from=starts_at,
            effective_to=ends_at,
            bucket_count=len(materialized_buckets),
            bucket_span=effective_granularity,
            coverage_status=coverage_status,
            coverage_by_bucket=coverage_by_bucket,
        )
```

- [ ] **Step 7: Preserve speed metadata while materializing zero rows**

Add this test to `backend/tests/services/test_history_service.py`:

```python
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
```

- [ ] **Step 8: Run the service tests**

Run:

```bash
python3 -m uv run pytest tests/services/test_history_service.py -q
```

Expected: PASS.

- [ ] **Step 9: Add endpoint serialization test**

In `_FakeHistoryService.query_series` in `backend/tests/api/test_history_endpoints.py`, include the new fields in the fake response:

```python
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
```

Add imports:

```python
    HistoryBucketCoverage,
```

and:

```python
    HistoryCoverageStatus,
```

Append this test:

```python
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
```

- [ ] **Step 10: Run endpoint tests**

Run:

```bash
python3 -m uv run pytest tests/api/test_history_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 11: Commit backend trust contract**

Run:

```bash
git add backend/src/argus/models/enums.py backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/tests/services/test_history_service.py backend/tests/api/test_history_endpoints.py
git commit -m "feat(history): add coverage metadata and zero buckets"
```

Expected: commit succeeds.

---

## Task 2: Align History Export With Materialized Series

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_history_service.py`
- Test: `backend/tests/api/test_export_endpoints.py`

- [ ] **Step 1: Add failing service test for zero-bucket CSV export**

Append this test to `backend/tests/services/test_history_service.py`:

```python
@pytest.mark.asyncio
async def test_export_history_includes_zero_buckets_from_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    starts = datetime(2026, 4, 26, 14, 0, tzinfo=UTC)
    service.query_series = AsyncMock(
        return_value=HistorySeriesResponse(
            granularity="1m",
            metric=HistoryMetric.COUNT_EVENTS,
            class_names=["car"],
            rows=[
                HistorySeriesRow(bucket=starts, values={"car": 0}, total_count=0),
                HistorySeriesRow(
                    bucket=starts + timedelta(minutes=1),
                    values={"car": 2},
                    total_count=2,
                ),
            ],
            effective_from=starts,
            effective_to=starts + timedelta(minutes=2),
            bucket_count=2,
            bucket_span="1m",
            coverage_status=HistoryCoverageStatus.POPULATED,
        )
    )

    artifact = await service.export_history(
        _tenant_context(),
        camera_ids=None,
        class_names=["car"],
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=2),
        format_name="csv",
        metric=HistoryMetric.COUNT_EVENTS,
    )

    csv_text = artifact.content.decode("utf-8")
    assert "2026-04-26T14:00:00+00:00,,car,0,1m" in csv_text
    assert "2026-04-26T14:01:00+00:00,,car,2,1m" in csv_text
```

Add imports if missing:

```python
from argus.api.contracts import HistorySeriesResponse, HistorySeriesRow
```

- [ ] **Step 2: Run the failing export test**

Run:

```bash
python3 -m uv run pytest tests/services/test_history_service.py::test_export_history_includes_zero_buckets_from_series -q
```

Expected: FAIL because `export_history` still calls `query_history`, which returns sparse rows.

- [ ] **Step 3: Add series-to-export flattening helper**

In `backend/src/argus/services/app.py`, add this helper near `_serialize_csv`:

```python
def _series_response_to_history_points(
    response: HistorySeriesResponse,
) -> list[HistoryPoint]:
    rows: list[HistoryPoint] = []
    for series_row in response.rows:
        if response.class_names:
            for class_name in response.class_names:
                rows.append(
                    HistoryPoint(
                        bucket=series_row.bucket,
                        camera_id=None,
                        class_name=class_name,
                        event_count=series_row.values.get(class_name, 0),
                        granularity=response.granularity,
                        metric=response.metric,
                    )
                )
        else:
            rows.append(
                HistoryPoint(
                    bucket=series_row.bucket,
                    camera_id=None,
                    class_name="total",
                    event_count=series_row.total_count,
                    granularity=response.granularity,
                    metric=response.metric,
                )
            )
    return rows
```

- [ ] **Step 4: Change `export_history` to use `query_series`**

Replace the first block in `HistoryService.export_history` with:

```python
        series = await self.query_series(
            tenant_context,
            camera_ids=camera_ids,
            class_names=class_names,
            granularity=granularity,
            starts_at=starts_at,
            ends_at=ends_at,
            metric=metric,
        )
        rows = _series_response_to_history_points(series)
```

- [ ] **Step 5: Run service export tests**

Run:

```bash
python3 -m uv run pytest tests/services/test_history_service.py::test_export_history_includes_zero_buckets_from_series tests/api/test_export_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit export alignment**

Run:

```bash
git add backend/src/argus/services/app.py backend/tests/services/test_history_service.py backend/tests/api/test_export_endpoints.py
git commit -m "fix(history): export materialized buckets"
```

Expected: commit succeeds.

---

## Task 3: Regenerate API Types And Add Frontend Window State

**Files:**
- Modify: `frontend/src/lib/api.generated.ts`
- Modify: `frontend/src/lib/history-url-state.ts`
- Modify: `frontend/src/lib/history-url-state.test.ts`
- Modify: `frontend/src/hooks/use-history.ts`

- [ ] **Step 1: Regenerate frontend API types**

Run:

```bash
corepack pnpm --dir frontend generate:api
```

Expected: PASS and `frontend/src/lib/api.generated.ts` includes `HistoryBucketCoverage`, `HistoryCoverageStatus`, and the new `HistorySeriesResponse` fields.

- [ ] **Step 2: Add failing URL-state tests**

Append these tests to `frontend/src/lib/history-url-state.test.ts`:

```ts
test("defaults to last 24h following now", () => {
  const parsed = readHistoryFiltersFromSearch(
    new URLSearchParams(),
    new Date("2026-04-27T12:34:56Z"),
  );

  expect(parsed.windowMode).toBe("relative");
  expect(parsed.relativeWindow).toBe("last_24h");
  expect(parsed.followNow).toBe(true);
  expect(parsed.to.toISOString()).toBe("2026-04-27T12:34:00.000Z");
  expect(parsed.from.toISOString()).toBe("2026-04-26T12:34:00.000Z");
});

test("round trips relative follow-now windows", () => {
  const state: HistoryFilterState = {
    ...defaultHistoryFilters(new Date("2026-04-27T12:00:00Z")),
    windowMode: "relative",
    relativeWindow: "last_1h",
    followNow: true,
    granularity: "5m",
    metric: "occupancy",
  };

  const params = new URLSearchParams(writeHistoryFiltersToSearch(state));

  expect(params.get("window")).toBe("last_1h");
  expect(params.get("follow")).toBe("1");
  expect(params.has("from")).toBe(false);
  expect(params.has("to")).toBe(false);
  expect(readHistoryFiltersFromSearch(params, new Date("2026-04-27T12:00:00Z")).relativeWindow).toBe("last_1h");
});

test("absolute from and to disable follow-now", () => {
  const parsed = readHistoryFiltersFromSearch(
    new URLSearchParams("from=2026-04-01T00%3A00%3A00.000Z&to=2026-04-02T00%3A00%3A00.000Z"),
  );

  expect(parsed.windowMode).toBe("absolute");
  expect(parsed.followNow).toBe(false);
  expect(writeHistoryFiltersToSearch(parsed)).toContain("from=2026-04-01T00%3A00%3A00.000Z");
});
```

- [ ] **Step 3: Run the failing URL-state tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/history-url-state.test.ts
```

Expected: FAIL because `windowMode`, `relativeWindow`, and `followNow` do not exist.

- [ ] **Step 4: Extend `HistoryFilterState`**

In `frontend/src/lib/history-url-state.ts`, add:

```ts
export type HistoryWindowMode = "relative" | "absolute";
export type RelativeHistoryWindow = "last_15m" | "last_1h" | "last_24h" | "last_7d";
```

Extend `HistoryFilterState`:

```ts
  windowMode: HistoryWindowMode;
  relativeWindow: RelativeHistoryWindow;
  followNow: boolean;
```

Add:

```ts
const RELATIVE_WINDOWS = new Set<RelativeHistoryWindow>(["last_15m", "last_1h", "last_24h", "last_7d"]);

function toRelativeWindow(value: string | null): RelativeHistoryWindow {
  if (value && RELATIVE_WINDOWS.has(value as RelativeHistoryWindow)) {
    return value as RelativeHistoryWindow;
  }
  return "last_24h";
}

export function resolveRelativeWindow(
  window: RelativeHistoryWindow,
  now = new Date(),
): { from: Date; to: Date } {
  const to = new Date(now);
  to.setSeconds(0, 0);
  const from = new Date(to);
  if (window === "last_15m") from.setMinutes(from.getMinutes() - 15);
  if (window === "last_1h") from.setHours(from.getHours() - 1);
  if (window === "last_24h") from.setDate(from.getDate() - 1);
  if (window === "last_7d") from.setDate(from.getDate() - 7);
  return { from, to };
}
```

Update `defaultHistoryFilters`:

```ts
export function defaultHistoryFilters(now = new Date()): HistoryFilterState {
  const { from, to } = resolveRelativeWindow("last_24h", now);
  return {
    windowMode: "relative",
    relativeWindow: "last_24h",
    followNow: true,
    from,
    to,
    granularity: "1h",
    metric: null,
    cameraIds: [],
    classNames: [],
    speed: false,
    speedThreshold: null,
  };
}
```

Update `readHistoryFiltersFromSearch`:

```ts
  const hasAbsoluteWindow = params.has("from") || params.has("to");
  const relativeWindow = toRelativeWindow(params.get("window"));
  const resolvedRelative = resolveRelativeWindow(relativeWindow, now);
  return {
    windowMode: hasAbsoluteWindow ? "absolute" : "relative",
    relativeWindow,
    followNow: !hasAbsoluteWindow && params.get("follow") !== "0",
    from: toDate(params.get("from"), hasAbsoluteWindow ? defaults.from : resolvedRelative.from),
    to: toDate(params.get("to"), hasAbsoluteWindow ? defaults.to : resolvedRelative.to),
    granularity: toGranularity(params.get("granularity")),
    metric: toMetric(params.get("metric")),
    cameraIds: toList(params.get("cameras")),
    classNames: toList(params.get("classes")),
    speed: params.get("speed") === "1",
    speedThreshold: toPositiveNumber(params.get("speedThreshold")),
  };
```

Update `writeHistoryFiltersToSearch`:

```ts
  if (state.windowMode === "relative") {
    params.set("window", state.relativeWindow);
    params.set("follow", state.followNow ? "1" : "0");
  } else {
    params.set("from", state.from.toISOString());
    params.set("to", state.to.toISOString());
  }
```

- [ ] **Step 5: Update existing test fixtures with new fields**

In `frontend/src/lib/history-url-state.test.ts`, update each inline `HistoryFilterState` fixture with:

```ts
      windowMode: "absolute",
      relativeWindow: "last_24h",
      followNow: false,
```

Use `windowMode: "relative"` only in tests that assert relative serialization.

- [ ] **Step 6: Update `use-history.ts` for resolved filters**

In `frontend/src/hooks/use-history.ts`, import `HistoryGranularity`, `HistoryMetric`, and resolved window types from `history-url-state`. Add this type:

```ts
export type ResolvedHistoryFilters = {
  from: Date;
  to: Date;
  granularity: HistoryGranularity;
  metric: HistoryMetric;
  cameraIds: string[];
  classNames: string[];
  includeSpeed?: boolean;
  speedThreshold?: number | null;
};
```

Keep `historySeriesQueryOptions`, `useHistorySeries`, `historyClassesQueryOptions`, `useHistoryClasses`, and `downloadHistoryExport` accepting `ResolvedHistoryFilters`. This preserves the existing backend query shape while the page owns relative-window resolution.

- [ ] **Step 7: Run frontend state tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/history-url-state.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit API types and URL state**

Run:

```bash
git add frontend/src/lib/api.generated.ts frontend/src/lib/history-url-state.ts frontend/src/lib/history-url-state.test.ts frontend/src/hooks/use-history.ts
git commit -m "feat(history-ui): add follow-now window state"
```

Expected: commit succeeds.

---

## Task 4: Add Workbench Derivation Helpers

**Files:**
- Create: `frontend/src/lib/history-workbench.ts`
- Create: `frontend/src/lib/history-workbench.test.ts`

- [ ] **Step 1: Write failing derivation tests**

Create `frontend/src/lib/history-workbench.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import {
  buildBucketDetails,
  buildDisplaySeries,
  formatBucketSpan,
  getCoverageCopy,
} from "@/lib/history-workbench";

const response = {
  granularity: "1h",
  metric: "occupancy",
  class_names: ["car"],
  rows: [
    { bucket: "2026-04-27T10:00:00Z", values: { car: 0 }, total_count: 0 },
    { bucket: "2026-04-27T11:00:00Z", values: { car: 4 }, total_count: 4 },
  ],
  coverage_status: "populated",
  coverage_by_bucket: [
    { bucket: "2026-04-27T10:00:00Z", status: "zero", reason: null },
    { bucket: "2026-04-27T11:00:00Z", status: "populated", reason: null },
  ],
} as const;

describe("history-workbench", () => {
  test("builds selected bucket details with coverage copy", () => {
    const detail = buildBucketDetails(response, "2026-04-27T10:00:00Z");

    expect(detail?.bucket).toBe("2026-04-27T10:00:00Z");
    expect(detail?.totalCount).toBe(0);
    expect(detail?.coverage.status).toBe("zero");
    expect(detail?.coverage.label).toBe("No detections");
  });

  test("falls back to total series when no class names exist", () => {
    const display = buildDisplaySeries({
      ...response,
      class_names: [],
      rows: [{ bucket: "2026-04-27T10:00:00Z", values: {}, total_count: 0 }],
    });

    expect(display.classNames).toEqual(["Total"]);
    expect(display.points[0].values).toEqual({ Total: 0 });
  });

  test("formats hourly bucket spans", () => {
    expect(formatBucketSpan("2026-04-27T10:00:00Z", "1h")).toBe("10:00-10:59");
  });

  test("returns operational copy for worker offline", () => {
    expect(getCoverageCopy("worker_offline").message).toBe("Processing was unavailable for this bucket.");
  });
});
```

- [ ] **Step 2: Run failing derivation tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/history-workbench.test.ts
```

Expected: FAIL because `history-workbench.ts` does not exist.

- [ ] **Step 3: Implement `history-workbench.ts`**

Create `frontend/src/lib/history-workbench.ts`:

```ts
import type { HistorySeriesResponse } from "@/hooks/use-history";

type CoverageStatus = NonNullable<HistorySeriesResponse["coverage_status"]>;
type HistoryRow = HistorySeriesResponse["rows"][number];

export type CoverageCopy = {
  status: CoverageStatus;
  label: string;
  message: string;
};

export type BucketDetail = {
  bucket: string;
  bucketSpan: string;
  values: Record<string, number>;
  totalCount: number;
  coverage: CoverageCopy;
  speedP50: Record<string, number>;
  speedP95: Record<string, number>;
  overThresholdCount: Record<string, number>;
};

const COVERAGE_COPY: Record<CoverageStatus, Omit<CoverageCopy, "status">> = {
  populated: {
    label: "Populated",
    message: "Detections are available for this bucket.",
  },
  zero: {
    label: "No detections",
    message: "Telemetry was valid and no detections matched this scope.",
  },
  no_telemetry: {
    label: "No telemetry",
    message: "No usable telemetry was available for this bucket.",
  },
  camera_offline: {
    label: "Camera offline",
    message: "The selected camera was offline for this bucket.",
  },
  worker_offline: {
    label: "Worker offline",
    message: "Processing was unavailable for this bucket.",
  },
  source_unavailable: {
    label: "Source unavailable",
    message: "The stream source was unavailable for this bucket.",
  },
  no_scope: {
    label: "No scope selected",
    message: "The current filters exclude usable cameras, classes, or boundaries.",
  },
  access_limited: {
    label: "Access limited",
    message: "Some matching data may be hidden by your tenant or permission scope.",
  },
};

export function getCoverageCopy(status: CoverageStatus | undefined | null): CoverageCopy {
  const resolved: CoverageStatus = status ?? "populated";
  return { status: resolved, ...COVERAGE_COPY[resolved] };
}

export function buildDisplaySeries(series: HistorySeriesResponse) {
  if (series.class_names.length > 0) {
    return {
      classNames: series.class_names,
      points: series.rows,
    };
  }

  return {
    classNames: ["Total"],
    points: series.rows.map((row) => ({
      ...row,
      values: { Total: row.total_count },
    })),
  };
}

export function buildBucketDetails(
  series: HistorySeriesResponse,
  selectedBucket: string | null,
): BucketDetail | null {
  if (!selectedBucket) return null;
  const row = series.rows.find((entry) => entry.bucket === selectedBucket);
  if (!row) return null;
  const coverageEntry = series.coverage_by_bucket?.find((entry) => entry.bucket === selectedBucket);
  return {
    bucket: row.bucket,
    bucketSpan: formatBucketSpan(row.bucket, series.granularity),
    values: row.values,
    totalCount: row.total_count,
    coverage: getCoverageCopy(coverageEntry?.status ?? series.coverage_status),
    speedP50: compactRecord(row.speed_p50),
    speedP95: compactRecord(row.speed_p95),
    overThresholdCount: compactRecord(row.over_threshold_count),
  };
}

export function formatBucketSpan(bucket: string, granularity: string): string {
  const start = new Date(bucket);
  const end = new Date(start);
  if (granularity === "1m") end.setMinutes(end.getMinutes() + 1);
  if (granularity === "5m") end.setMinutes(end.getMinutes() + 5);
  if (granularity === "1h") end.setHours(end.getHours() + 1);
  if (granularity === "1d") end.setDate(end.getDate() + 1);
  end.setMilliseconds(end.getMilliseconds() - 1);
  const format = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
  return `${format.format(start)}-${format.format(end)}`;
}

function compactRecord(value: Record<string, number> | null | undefined): Record<string, number> {
  return value ?? {};
}
```

- [ ] **Step 4: Run derivation tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/history-workbench.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit derivation helpers**

Run:

```bash
git add frontend/src/lib/history-workbench.ts frontend/src/lib/history-workbench.test.ts
git commit -m "feat(history-ui): add workbench derivation helpers"
```

Expected: commit succeeds.

---

## Task 5: Add Bucket Selection To The Trend Chart

**Files:**
- Modify: `frontend/src/components/history/HistoryTrendChart.tsx`
- Modify: `frontend/src/components/history/HistoryTrendChart.test.tsx`

- [ ] **Step 1: Add failing chart option test for selected bucket marking**

Append to `frontend/src/components/history/HistoryTrendChart.test.tsx`:

```ts
test("marks the selected bucket on each primary series", () => {
  const option = buildHistoryChartOption({
    classNames: ["car"],
    points: [
      { bucket: "2026-04-23T00:00:00Z", values: { car: 1 }, total_count: 1 },
      { bucket: "2026-04-23T01:00:00Z", values: { car: 2 }, total_count: 2 },
    ],
    selectedBucket: "2026-04-23T01:00:00Z",
  });

  const seriesList = option.series as unknown as Array<{
    name: string;
    markLine?: { data: Array<{ xAxis: string }> };
  }>;
  expect(seriesList.find((entry) => entry.name === "car")?.markLine?.data[0].xAxis).toBe("23 Apr, 01:00");
});
```

- [ ] **Step 2: Run failing chart test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/history/HistoryTrendChart.test.tsx
```

Expected: FAIL because `selectedBucket` is not part of `HistoryTrendSeries`.

- [ ] **Step 3: Extend chart series type and mark selected bucket**

In `frontend/src/components/history/HistoryTrendChart.tsx`, extend `HistoryTrendSeries`:

```ts
  selectedBucket?: string | null;
```

Inside `buildHistoryChartOption`, after `const buckets = ...`, add:

```ts
  const selectedBucketLabel = series.selectedBucket ? formatBucket(series.selectedBucket) : null;
```

In the primary `seriesList` map, add:

```ts
    markLine: selectedBucketLabel
      ? {
          symbol: "none",
          lineStyle: { color: "#f5d570", type: "dashed", width: 1.5 },
          data: [{ xAxis: selectedBucketLabel, name: "selected bucket" }],
        }
      : undefined,
```

- [ ] **Step 4: Add click callback support**

Update the `HistoryTrendChart` props:

```ts
  onBucketSelect,
}: {
  series: HistoryTrendSeries;
  className?: string;
  metric?: HistoryMetric;
  onBucketSelect?: (bucket: string) => void;
}) {
```

In the chart `useEffect`, after `chart.setOption(option, true);`, add:

```ts
    const onClick = (params: { dataIndex?: number }) => {
      if (typeof params.dataIndex !== "number") return;
      const point = series.points[params.dataIndex];
      if (point?.bucket) {
        onBucketSelect?.(point.bucket);
      }
    };
    chart.off("click");
    chart.on("click", onClick);
```

Update the cleanup:

```ts
    return () => {
      chart.off("click", onClick);
      window.removeEventListener("resize", onResize);
    };
```

- [ ] **Step 5: Run chart tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/history/HistoryTrendChart.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit chart selection support**

Run:

```bash
git add frontend/src/components/history/HistoryTrendChart.tsx frontend/src/components/history/HistoryTrendChart.test.tsx
git commit -m "feat(history-ui): support bucket selection in chart"
```

Expected: commit succeeds.

---

## Task 6: Build Split Review Components

**Files:**
- Create: `frontend/src/components/history/HistoryBucketDetail.tsx`
- Create: `frontend/src/components/history/HistoryTrendPanel.tsx`
- Create: `frontend/src/components/history/HistoryToolbar.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Test: `frontend/src/pages/History.test.tsx`

- [ ] **Step 1: Update chart mock in page tests**

In `frontend/src/pages/History.test.tsx`, replace the `HistoryTrendChart` mock with a clickable mock:

```tsx
vi.mock("@/components/history/HistoryTrendChart", () => ({
  HistoryTrendChart: ({
    series,
    metric,
    onBucketSelect,
  }: {
    series: {
      classNames: string[];
      points: Array<{ bucket: string }>;
      includeSpeed?: boolean;
      speedThreshold?: number | null;
      selectedBucket?: string | null;
    };
    metric?: string;
    onBucketSelect?: (bucket: string) => void;
  }) => (
    <button
      type="button"
      data-testid="history-trend-chart"
      onClick={() => onBucketSelect?.(series.points[0]?.bucket ?? "")}
    >
      {series.classNames.join(",")}::{series.points.length}::speed={String(!!series.includeSpeed)}::threshold={String(series.speedThreshold ?? "none")}::metric={metric ?? "none"}::selected={series.selectedBucket ?? "none"}
    </button>
  ),
}));
```

- [ ] **Step 2: Add failing split review tests**

Append to `frontend/src/pages/History.test.tsx`:

```tsx
test("renders split review and selects a bucket from the chart", async () => {
  const user = userEvent.setup();
  renderPage();

  await screen.findByTestId("history-trend-chart");
  expect(screen.getByRole("heading", { name: /bucket review/i })).toBeInTheDocument();
  expect(screen.getByText(/select a bucket/i)).toBeInTheDocument();

  await user.click(screen.getByTestId("history-trend-chart"));

  expect(screen.getByText(/apr 12/i)).toBeInTheDocument();
  expect(screen.getByText(/28 visible samples/i)).toBeInTheDocument();
});

test("shows following-now controls by default and resumes from absolute windows", async () => {
  const user = userEvent.setup();
  renderPage("/history?from=2026-04-01T00%3A00%3A00.000Z&to=2026-04-02T00%3A00%3A00.000Z");

  await screen.findByTestId("history-trend-chart");
  expect(screen.getByText(/absolute window/i)).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /resume following now/i }));

  expect(screen.getByText(/following now/i)).toBeInTheDocument();
});
```

- [ ] **Step 3: Run failing page tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx
```

Expected: FAIL because split review components and bucket selection are not wired.

- [ ] **Step 4: Create `HistoryBucketDetail.tsx`**

Create `frontend/src/components/history/HistoryBucketDetail.tsx`:

```tsx
import { Badge } from "@/components/ui/badge";
import { type BucketDetail } from "@/lib/history-workbench";
import { type HistoryMetric, historyMetricCopy } from "@/lib/history-url-state";

export function HistoryBucketDetail({
  detail,
  metric,
}: {
  detail: BucketDetail | null;
  metric: HistoryMetric;
}) {
  const metricCopy = historyMetricCopy(metric);

  return (
    <section className="rounded-lg border border-white/10 bg-[#07101c] p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Bucket review</p>
          <h3 className="mt-1 text-lg font-semibold text-[#f3f7ff]">
            {detail ? formatBucketHeading(detail.bucket) : "Select a bucket"}
          </h3>
        </div>
        {detail ? <Badge>{detail.coverage.label}</Badge> : null}
      </div>

      {!detail ? (
        <p className="mt-4 text-sm text-[#93a7c5]">Select a bucket from the chart to inspect totals, coverage, and speed signals.</p>
      ) : (
        <div className="mt-4 space-y-4">
          <div>
            <p className="text-2xl font-semibold text-[#f4f8ff]">
              {detail.totalCount} {metricCopy.countLabel}
            </p>
            <p className="mt-1 text-sm text-[#93a7c5]">{detail.bucketSpan} UTC · {detail.coverage.message}</p>
          </div>
          <div className="space-y-2">
            {Object.entries(detail.values).map(([className, value]) => (
              <div key={className} className="flex items-center justify-between rounded-md bg-white/[0.04] px-3 py-2 text-sm">
                <span className="text-[#dce6f7]">{className}</span>
                <span className="font-semibold text-[#f4f8ff]">{value}</span>
              </div>
            ))}
          </div>
          {Object.keys(detail.overThresholdCount).length > 0 ? (
            <div className="rounded-md border border-[#705e29] bg-[#1d1b08]/80 px-3 py-2 text-sm text-[#ffe5a8]">
              {Object.entries(detail.overThresholdCount).map(([className, value]) => (
                <p key={className}>{value} {className} over speed threshold</p>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

function formatBucketHeading(bucket: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(new Date(bucket));
}
```

- [ ] **Step 5: Create `HistoryTrendPanel.tsx`**

Create `frontend/src/components/history/HistoryTrendPanel.tsx`:

```tsx
import { Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { HistoryTrendChart } from "@/components/history/HistoryTrendChart";
import type { HistoryMetric } from "@/lib/history-url-state";
import type { CoverageCopy } from "@/lib/history-workbench";

type TrendSeries = {
  classNames: string[];
  points: Array<{ bucket: string; values: Record<string, number>; total_count?: number }>;
  includeSpeed?: boolean;
  speedThreshold?: number | null;
  speedClassesUsed?: string[] | null;
  selectedBucket?: string | null;
};

export function HistoryTrendPanel({
  series,
  metric,
  granularity,
  coverage,
  onBucketSelect,
}: {
  series: TrendSeries;
  metric: HistoryMetric;
  granularity: string;
  coverage: CoverageCopy;
  onBucketSelect: (bucket: string) => void;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-white/10 bg-[#050912]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Trend</p>
          <p className="mt-1 text-sm text-[#dce6f7]">{bucketCopy(granularity)}</p>
        </div>
        <Badge>{coverage.label}</Badge>
      </div>
      <Suspense fallback={<div className="px-6 py-16 text-sm text-[#93a7c5]">Loading chart...</div>}>
        <HistoryTrendChart
          className="px-2 py-4"
          metric={metric}
          series={series}
          onBucketSelect={onBucketSelect}
        />
      </Suspense>
    </section>
  );
}

function bucketCopy(granularity: string): string {
  if (granularity === "1h") return "Hourly buckets · timestamps mark bucket starts";
  if (granularity === "1d") return "Daily buckets · timestamps mark bucket starts";
  if (granularity === "5m") return "5-minute buckets · timestamps mark bucket starts";
  return "1-minute buckets · timestamps mark bucket starts";
}
```

- [ ] **Step 6: Create `HistoryToolbar.tsx`**

Create `frontend/src/components/history/HistoryToolbar.tsx`:

```tsx
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  type HistoryFilterState,
  type HistoryMetric,
  historyMetricCopy,
} from "@/lib/history-url-state";

export function HistoryToolbar({
  state,
  metric,
  onChange,
  onResumeFollowing,
}: {
  state: HistoryFilterState;
  metric: HistoryMetric;
  onChange: (next: HistoryFilterState | ((previous: HistoryFilterState) => HistoryFilterState)) => void;
  onResumeFollowing: () => void;
}) {
  return (
    <section className="rounded-lg border border-white/10 bg-[#07101c] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">History</p>
          <h2 className="mt-1 text-2xl font-semibold text-[#f4f8ff]">{historyMetricCopy(metric).label}</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md border border-white/10 px-3 py-2 text-sm text-[#dce6f7]">
            {state.windowMode === "relative" && state.followNow ? "Following now" : "Absolute window"}
          </span>
          {state.windowMode === "absolute" ? (
            <Button type="button" onClick={onResumeFollowing}>Resume following now</Button>
          ) : null}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Select
          aria-label="Metric"
          value={metric}
          onChange={(event) => onChange((previous) => ({ ...previous, metric: event.target.value as HistoryMetric }))}
        >
          <option value="occupancy">{historyMetricCopy("occupancy").label}</option>
          <option value="count_events">{historyMetricCopy("count_events").label}</option>
          <option value="observations">{historyMetricCopy("observations").label} (debug)</option>
        </Select>
        <Select
          aria-label="Time window"
          value={state.windowMode === "relative" ? state.relativeWindow : "absolute"}
          onChange={(event) => {
            const value = event.target.value;
            if (value === "absolute") return;
            onChange((previous) => ({
              ...previous,
              windowMode: "relative",
              relativeWindow: value as HistoryFilterState["relativeWindow"],
              followNow: true,
            }));
          }}
        >
          <option value="last_15m">Last 15m</option>
          <option value="last_1h">Last 1h</option>
          <option value="last_24h">Last 24h</option>
          <option value="last_7d">Last 7d</option>
          {state.windowMode === "absolute" ? <option value="absolute">Absolute window</option> : null}
        </Select>
        <Select
          aria-label="Granularity"
          value={state.granularity}
          onChange={(event) => onChange((previous) => ({ ...previous, granularity: event.target.value as HistoryFilterState["granularity"] }))}
        >
          <option value="1m">1 minute</option>
          <option value="5m">5 minutes</option>
          <option value="1h">1 hour</option>
          <option value="1d">1 day</option>
        </Select>
      </div>
    </section>
  );
}
```

- [ ] **Step 7: Wire split review in `History.tsx`**

In `frontend/src/pages/History.tsx`:

1. Import:

```ts
import { HistoryBucketDetail } from "@/components/history/HistoryBucketDetail";
import { HistoryToolbar } from "@/components/history/HistoryToolbar";
import { HistoryTrendPanel } from "@/components/history/HistoryTrendPanel";
import { buildBucketDetails, buildDisplaySeries, getCoverageCopy } from "@/lib/history-workbench";
import { resolveRelativeWindow } from "@/lib/history-url-state";
```

2. Add state:

```ts
  const [selectedBucket, setSelectedBucket] = useState<string | null>(null);
```

3. Resolve relative windows before building `filters`:

```ts
  const resolvedWindow = useMemo(() => {
    if (state.windowMode === "relative") {
      return resolveRelativeWindow(state.relativeWindow);
    }
    return { from: state.from, to: state.to };
  }, [state.from, state.relativeWindow, state.to, state.windowMode]);
```

4. Use `resolvedWindow.from` and `resolvedWindow.to` in `filters` and `useHistoryClasses`.

5. Add:

```ts
  const displaySeries = useMemo(
    () => data ? buildDisplaySeries(data) : { classNames: [], points: [] },
    [data],
  );
  const bucketDetail = useMemo(
    () => data ? buildBucketDetails(data, selectedBucket) : null,
    [data, selectedBucket],
  );
  const coverageCopy = getCoverageCopy(data?.coverage_status);

  function resumeFollowingNow() {
    applyState((previous) => ({
      ...previous,
      windowMode: "relative",
      relativeWindow: "last_24h",
      followNow: true,
    }));
  }
```

6. Render the new shell above the existing advanced filter aside:

```tsx
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-4">
        <HistoryToolbar
          state={state}
          metric={metric}
          onChange={applyState}
          onResumeFollowing={resumeFollowingNow}
        />
        {isLoading ? (
          <div className="rounded-lg border border-white/10 bg-[#050912] px-6 py-16 text-sm text-[#93a7c5]">Loading history...</div>
        ) : error ? (
          <div className="rounded-lg border border-white/10 bg-[#050912] px-6 py-16 text-sm text-[#f0b7c1]">
            {error instanceof Error ? error.message : "Failed to load history."}
          </div>
        ) : data ? (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
            <HistoryTrendPanel
              series={{
                classNames: displaySeries.classNames,
                points: displaySeries.points,
                includeSpeed: state.speed,
                speedThreshold: state.speedThreshold ?? null,
                speedClassesUsed: data.speed_classes_used ?? null,
                selectedBucket,
              }}
              metric={metric}
              granularity={data.granularity}
              coverage={coverageCopy}
              onBucketSelect={setSelectedBucket}
            />
            <HistoryBucketDetail detail={bucketDetail} metric={metric} />
          </div>
        ) : null}
      </div>
      <aside className="space-y-6">
        ...
      </aside>
    </div>
```

Retain the existing advanced filters inside the aside for this task. Remove the old duplicate hero/chart block after the new workbench shell is rendering.

- [ ] **Step 8: Run page tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx
```

Expected: PASS.

- [ ] **Step 9: Commit split review**

Run:

```bash
git add frontend/src/components/history/HistoryBucketDetail.tsx frontend/src/components/history/HistoryTrendPanel.tsx frontend/src/components/history/HistoryToolbar.tsx frontend/src/pages/History.tsx frontend/src/pages/History.test.tsx
git commit -m "feat(history-ui): add split review bucket workbench"
```

Expected: commit succeeds.

---

## Task 7: Add Deterministic Unified Search

**Files:**
- Create: `frontend/src/lib/history-search.ts`
- Create: `frontend/src/lib/history-search.test.ts`
- Create: `frontend/src/components/history/HistorySearchBox.tsx`
- Modify: `frontend/src/components/history/HistoryToolbar.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Test: `frontend/src/pages/History.test.tsx`

- [ ] **Step 1: Write failing search utility tests**

Create `frontend/src/lib/history-search.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import { buildHistorySearchResults } from "@/lib/history-search";

const cameras = [
  { id: "cam-1", name: "Gate camera", zones: [{ id: "entry-line", type: "line" }] },
  { id: "cam-2", name: "Warehouse", zones: [] },
];

const classes = [
  { class_name: "car", event_count: 40, has_speed_data: true },
  { class_name: "person", event_count: 2, has_speed_data: false },
];

const series = {
  granularity: "1h",
  metric: "count_events",
  class_names: ["car"],
  rows: [
    { bucket: "2026-04-27T10:00:00Z", values: { car: 0 }, total_count: 0, over_threshold_count: null },
    { bucket: "2026-04-27T11:00:00Z", values: { car: 12 }, total_count: 12, over_threshold_count: { car: 3 } },
  ],
  coverage_status: "populated",
  coverage_by_bucket: [
    { bucket: "2026-04-27T10:00:00Z", status: "zero", reason: null },
    { bucket: "2026-04-27T11:00:00Z", status: "populated", reason: null },
  ],
} as const;

describe("history-search", () => {
  test("finds cameras classes and boundaries", () => {
    const results = buildHistorySearchResults({ query: "gate", cameras, classes, series });
    expect(results.map((result) => result.label)).toContain("Gate camera");
  });

  test("finds zero buckets", () => {
    const results = buildHistorySearchResults({ query: "zero", cameras, classes, series });
    expect(results).toContainEqual(expect.objectContaining({ type: "bucket", bucket: "2026-04-27T10:00:00Z" }));
  });

  test("finds speed breach buckets", () => {
    const results = buildHistorySearchResults({ query: "speed", cameras, classes, series });
    expect(results).toContainEqual(expect.objectContaining({ type: "bucket", bucket: "2026-04-27T11:00:00Z" }));
  });
});
```

- [ ] **Step 2: Run failing search tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/history-search.test.ts
```

Expected: FAIL because `history-search.ts` does not exist.

- [ ] **Step 3: Implement search utility**

Create `frontend/src/lib/history-search.ts`:

```ts
import type { HistoryClassesResponse, HistorySeriesResponse } from "@/hooks/use-history";
import type { Camera } from "@/hooks/use-cameras";

export type HistorySearchResult =
  | { id: string; type: "camera"; group: "Cameras"; label: string; cameraId: string }
  | { id: string; type: "class"; group: "Classes"; label: string; className: string }
  | { id: string; type: "boundary"; group: "Boundaries"; label: string; boundaryId: string; cameraId?: string }
  | { id: string; type: "bucket"; group: "Buckets" | "Gaps" | "Speed breaches"; label: string; bucket: string };

export function buildHistorySearchResults({
  query,
  cameras,
  classes,
  series,
}: {
  query: string;
  cameras: Camera[];
  classes: HistoryClassesResponse["classes"];
  series: HistorySeriesResponse | null | undefined;
}): HistorySearchResult[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return [];

  const results: HistorySearchResult[] = [];
  for (const camera of cameras) {
    if (camera.name.toLowerCase().includes(normalized)) {
      results.push({ id: `camera:${camera.id}`, type: "camera", group: "Cameras", label: camera.name, cameraId: camera.id });
    }
    for (const zone of camera.zones ?? []) {
      const boundaryId = String((zone as Record<string, unknown>).id ?? (zone as Record<string, unknown>).name ?? "");
      if (boundaryId.toLowerCase().includes(normalized)) {
        results.push({
          id: `boundary:${camera.id}:${boundaryId}`,
          type: "boundary",
          group: "Boundaries",
          label: boundaryId,
          boundaryId,
          cameraId: camera.id,
        });
      }
    }
  }

  for (const entry of classes) {
    if (entry.class_name.toLowerCase().includes(normalized)) {
      results.push({
        id: `class:${entry.class_name}`,
        type: "class",
        group: "Classes",
        label: entry.class_name,
        className: entry.class_name,
      });
    }
  }

  if (series) {
    const coverageByBucket = new Map((series.coverage_by_bucket ?? []).map((entry) => [entry.bucket, entry.status]));
    for (const row of series.rows) {
      const coverage = coverageByBucket.get(row.bucket);
      const overThreshold = Object.values(row.over_threshold_count ?? {}).reduce((sum, value) => sum + value, 0);
      if ((normalized === "zero" || normalized.includes("zero")) && coverage === "zero") {
        results.push({ id: `bucket:zero:${row.bucket}`, type: "bucket", group: "Buckets", label: `Zero detections · ${formatBucket(row.bucket)}`, bucket: row.bucket });
      }
      if ((normalized.includes("gap") || normalized.includes("telemetry")) && coverage === "no_telemetry") {
        results.push({ id: `bucket:gap:${row.bucket}`, type: "bucket", group: "Gaps", label: `No telemetry · ${formatBucket(row.bucket)}`, bucket: row.bucket });
      }
      if ((normalized.includes("speed") || normalized.includes("breach")) && overThreshold > 0) {
        results.push({ id: `bucket:speed:${row.bucket}`, type: "bucket", group: "Speed breaches", label: `${overThreshold} speed breaches · ${formatBucket(row.bucket)}`, bucket: row.bucket });
      }
      if ((normalized.includes("spike") || normalized.includes("heavy")) && row.total_count >= 10) {
        results.push({ id: `bucket:spike:${row.bucket}`, type: "bucket", group: "Buckets", label: `${row.total_count} events · ${formatBucket(row.bucket)}`, bucket: row.bucket });
      }
    }
  }

  return results.slice(0, 20);
}

function formatBucket(bucket: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(new Date(bucket));
}
```

- [ ] **Step 4: Create `HistorySearchBox.tsx`**

Create `frontend/src/components/history/HistorySearchBox.tsx`:

```tsx
import { Input } from "@/components/ui/input";
import type { HistorySearchResult } from "@/lib/history-search";

export function HistorySearchBox({
  value,
  results,
  onChange,
  onSelect,
}: {
  value: string;
  results: HistorySearchResult[];
  onChange: (value: string) => void;
  onSelect: (result: HistorySearchResult) => void;
}) {
  const grouped = results.reduce<Record<string, HistorySearchResult[]>>((acc, result) => {
    acc[result.group] = [...(acc[result.group] ?? []), result];
    return acc;
  }, {});

  return (
    <div className="relative">
      <Input
        aria-label="Search history"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {value.trim() && results.length > 0 ? (
        <div className="absolute left-0 right-0 top-full z-20 mt-2 max-h-80 overflow-auto rounded-lg border border-white/10 bg-[#07101c] p-2 shadow-xl">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group} className="py-1">
              <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">{group}</p>
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="block w-full rounded-md px-2 py-2 text-left text-sm text-[#dce6f7] hover:bg-white/[0.06]"
                  onClick={() => onSelect(item)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 5: Wire search into toolbar and page**

In `HistoryToolbar.tsx`, import `HistorySearchBox` and `HistorySearchResult`, then extend props:

```ts
  search: string;
  searchResults: HistorySearchResult[];
  onSearchChange: (value: string) => void;
  onSearchSelect: (result: HistorySearchResult) => void;
```

Render `HistorySearchBox` above the selects:

```tsx
      <div className="mt-4">
        <HistorySearchBox
          value={search}
          results={searchResults}
          onChange={onSearchChange}
          onSelect={onSearchSelect}
        />
      </div>
```

In `History.tsx`, import `buildHistorySearchResults` and `HistorySearchResult`, add:

```ts
  const [search, setSearch] = useState("");
  const searchResults = useMemo(
    () =>
      buildHistorySearchResults({
        query: search,
        cameras,
        classes: observedClasses,
        series: data,
      }),
    [cameras, data, observedClasses, search],
  );

  function selectSearchResult(result: HistorySearchResult) {
    if (result.type === "camera") {
      applyState((previous) => ({ ...previous, cameraIds: [result.cameraId] }));
    }
    if (result.type === "class") {
      applyState((previous) => ({ ...previous, classNames: [result.className] }));
    }
    if (result.type === "boundary" && result.cameraId) {
      applyState((previous) => ({ ...previous, cameraIds: [result.cameraId] }));
    }
    if (result.type === "bucket") {
      setSelectedBucket(result.bucket);
    }
    setSearch("");
  }
```

Pass search props to `HistoryToolbar`.

- [ ] **Step 6: Add page tests for search**

Append to `frontend/src/pages/History.test.tsx`:

```tsx
test("unified search selects cameras classes and buckets", async () => {
  const user = userEvent.setup();
  renderPage();

  await screen.findByTestId("history-trend-chart");
  await user.type(screen.getByLabelText(/search history/i), "car");
  await user.click(screen.getByRole("button", { name: "car" }));

  await waitFor(() => {
    const request = recordedRequests.find((url) => url.pathname === "/api/v1/history/series" && url.searchParams.get("class_names") === "car");
    expect(request).toBeDefined();
  });

  await user.clear(screen.getByLabelText(/search history/i));
  await user.type(screen.getByLabelText(/search history/i), "spike");
  await user.click(screen.getByRole("button", { name: /28 events/i }));

  expect(screen.getByText(/28 visible samples/i)).toBeInTheDocument();
});
```

- [ ] **Step 7: Run search tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/history-search.test.ts src/pages/History.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit unified search**

Run:

```bash
git add frontend/src/lib/history-search.ts frontend/src/lib/history-search.test.ts frontend/src/components/history/HistorySearchBox.tsx frontend/src/components/history/HistoryToolbar.tsx frontend/src/pages/History.tsx frontend/src/pages/History.test.tsx
git commit -m "feat(history-ui): add deterministic unified search"
```

Expected: commit succeeds.

---

## Task 8: Add Coverage Empty States And Progressive Lanes

**Files:**
- Modify: `frontend/src/components/history/HistoryTrendPanel.tsx`
- Modify: `frontend/src/pages/History.test.tsx`
- Modify: `frontend/src/lib/history-workbench.test.ts`

- [ ] **Step 1: Add failing coverage-state page tests**

Append to `frontend/src/pages/History.test.tsx`:

```tsx
test("renders zero coverage as no detections instead of generic emptiness", async () => {
  vi.spyOn(global, "fetch").mockImplementation((input, init) => {
    const request = input instanceof Request ? input : new Request(String(input), init);
    const url = new URL(request.url);
    if (url.pathname === "/api/v1/cameras") return Promise.resolve(jsonResponse([]));
    if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
    if (url.pathname === "/api/v1/history/series") {
      return Promise.resolve(
        jsonResponse(
          historySeriesResponse({
            class_names: ["car"],
            rows: [{ bucket: "2026-04-12T00:00:00Z", values: { car: 0 }, total_count: 0 }],
            coverage_status: "zero",
            coverage_by_bucket: [{ bucket: "2026-04-12T00:00:00Z", status: "zero", reason: null }],
          }),
        ),
      );
    }
    return Promise.resolve(new Response("Not found", { status: 404 }));
  });

  renderPage();

  await screen.findByText(/no detections/i);
  expect(screen.getByTestId("history-trend-chart")).toBeInTheDocument();
});

test("renders no telemetry coverage distinctly", async () => {
  vi.spyOn(global, "fetch").mockImplementation((input, init) => {
    const request = input instanceof Request ? input : new Request(String(input), init);
    const url = new URL(request.url);
    if (url.pathname === "/api/v1/cameras") return Promise.resolve(jsonResponse([]));
    if (url.pathname === "/api/v1/history/classes") return Promise.resolve(jsonResponse(classesResponse()));
    if (url.pathname === "/api/v1/history/series") {
      return Promise.resolve(
        jsonResponse(
          historySeriesResponse({
            class_names: ["car"],
            rows: [{ bucket: "2026-04-12T00:00:00Z", values: { car: 0 }, total_count: 0 }],
            coverage_status: "no_telemetry",
            coverage_by_bucket: [{ bucket: "2026-04-12T00:00:00Z", status: "no_telemetry", reason: null }],
          }),
        ),
      );
    }
    return Promise.resolve(new Response("Not found", { status: 404 }));
  });

  renderPage();

  await screen.findByText(/no telemetry/i);
  expect(screen.getByText(/no usable telemetry/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run failing coverage tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx
```

Expected: FAIL until coverage copy is surfaced above the chart and detail pane.

- [ ] **Step 3: Add lane summary rendering**

In `HistoryTrendPanel.tsx`, add this under the chart:

```tsx
      {coverage.status !== "populated" ? (
        <div className="border-t border-white/8 px-4 py-3 text-sm text-[#dce6f7]">
          <span className="font-semibold">{coverage.label}</span>
          <span className="ml-2 text-[#93a7c5]">{coverage.message}</span>
        </div>
      ) : null}
```

- [ ] **Step 4: Run coverage tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit coverage states**

Run:

```bash
git add frontend/src/components/history/HistoryTrendPanel.tsx frontend/src/pages/History.test.tsx frontend/src/lib/history-workbench.test.ts
git commit -m "feat(history-ui): show operational coverage states"
```

Expected: commit succeeds.

---

## Task 9: Finalize Export State And E2E Coverage

**Files:**
- Modify: `frontend/src/hooks/use-history.ts`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/History.test.tsx`
- Modify: `frontend/e2e/prompt9-history-and-incidents.spec.ts`

- [ ] **Step 1: Add page test for relative export resolution**

Append to `frontend/src/pages/History.test.tsx`:

```tsx
test("exports the visible resolved follow-now window", async () => {
  const user = userEvent.setup();
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-04-27T12:34:56Z"));

  const createObjectURL = vi.fn(() => "blob:history");
  const revokeObjectURL = vi.fn();
  const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  Object.defineProperty(window.URL, "createObjectURL", { configurable: true, writable: true, value: createObjectURL });
  Object.defineProperty(window.URL, "revokeObjectURL", { configurable: true, writable: true, value: revokeObjectURL });

  renderPage("/history?window=last_1h&follow=1&metric=count_events");
  await screen.findByTestId("history-trend-chart");
  await user.click(screen.getByRole("button", { name: /download csv/i }));

  await waitFor(() => {
    const request = findHistoryRequest("/api/v1/export", "count_events");
    expect(request?.searchParams.get("from")).toBe("2026-04-27T11:34:00.000Z");
    expect(request?.searchParams.get("to")).toBe("2026-04-27T12:34:00.000Z");
  });

  clickSpy.mockRestore();
  vi.useRealTimers();
});
```

- [ ] **Step 2: Run failing export state test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx -t "exports the visible resolved follow-now window"
```

Expected: FAIL if `downloadHistoryExport` still receives stale `state.from` and `state.to`.

- [ ] **Step 3: Ensure download uses resolved filters**

In `History.tsx`, confirm `handleDownload` calls:

```ts
      await downloadHistoryExport(filters, format);
```

and confirm `filters` uses `resolvedWindow.from` and `resolvedWindow.to`. If any call uses `state.from` or `state.to` directly, replace it with `filters`.

- [ ] **Step 4: Add E2E split review assertions**

In `frontend/e2e/prompt9-history-and-incidents.spec.ts`, update `historySeriesPayload()` to include coverage fields:

```ts
    coverage_status: "populated",
    coverage_by_bucket: rows.map((row) => ({
      bucket: row.bucket,
      status: row.total_count > 0 ? "populated" : "zero",
      reason: null,
    })),
    effective_from: "2026-04-12T00:00:00Z",
    effective_to: "2026-04-19T00:00:00Z",
    bucket_count: rows.length,
    bucket_span: "1h",
```

After the chart is visible in the first E2E test, add:

```ts
  await expect(page.getByRole("heading", { name: /bucket review/i })).toBeVisible();
  await page.getByRole("img", { name: /history trend chart/i }).click();
  await expect(page.getByText(/visible samples/i)).toBeVisible();
```

If clicking the real ECharts canvas is unreliable in Playwright, replace the click with keyboard focus on the chart container after adding `tabIndex={0}` and an `Enter` handler in `HistoryTrendPanel`.

- [ ] **Step 5: Run frontend unit and E2E tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/history-url-state.test.ts src/lib/history-workbench.test.ts src/lib/history-search.test.ts src/components/history/HistoryTrendChart.test.tsx src/pages/History.test.tsx
corepack pnpm --dir frontend exec playwright test frontend/e2e/prompt9-history-and-incidents.spec.ts
```

Expected: PASS.

- [ ] **Step 6: Commit export and E2E polish**

Run:

```bash
git add frontend/src/hooks/use-history.ts frontend/src/pages/History.tsx frontend/src/pages/History.test.tsx frontend/e2e/prompt9-history-and-incidents.spec.ts
git commit -m "test(history-ui): cover workbench export flow"
```

Expected: commit succeeds.

---

## Task 10: Full Verification

**Files:**
- No planned file edits.

- [ ] **Step 1: Run backend History checks**

Run:

```bash
python3 -m uv run pytest tests/services/test_history_service.py tests/api/test_history_endpoints.py tests/api/test_export_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 2: Run backend lint and type checks on touched modules**

Run:

```bash
python3 -m uv run ruff check src/argus/models/enums.py src/argus/api/contracts.py src/argus/services/app.py tests/services/test_history_service.py tests/api/test_history_endpoints.py tests/api/test_export_endpoints.py
python3 -m uv run mypy src/argus/services/app.py src/argus/api/contracts.py
```

Expected: PASS.

- [ ] **Step 3: Run frontend checks**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/history-url-state.test.ts src/lib/history-workbench.test.ts src/lib/history-search.test.ts src/components/history/HistoryTrendChart.test.tsx src/pages/History.test.tsx
corepack pnpm --dir frontend build
```

Expected: PASS.

- [ ] **Step 4: Run E2E check**

Run:

```bash
corepack pnpm --dir frontend exec playwright test frontend/e2e/prompt9-history-and-incidents.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Check formatting and worktree**

Run:

```bash
git diff --check
git status --short --branch
```

Expected: `git diff --check` prints no output. `git status` shows only expected untracked pre-existing files and no unstaged tracked changes.

- [ ] **Step 6: Final commit if verification caused generated-file updates**

If `frontend/src/lib/api.generated.ts` changed during verification, run:

```bash
git add frontend/src/lib/api.generated.ts
git commit -m "chore(history): refresh generated api types"
```

Expected: commit succeeds only if generated API types changed after the earlier API generation commit.
