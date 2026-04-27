# History Follow-Now, Zero Buckets, and Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make History feel live and understandable by adding relative/absolute time modes, explicit zero-detection buckets, clearer bucket semantics, and search across cameras, classes, and count boundaries.

**Architecture:** Extend the backend history contract so the API always returns complete bucket ranges and lightweight coverage metadata, then update the frontend state model to separate live relative windows from fixed absolute windows. Add one search-first filter surface instead of making operators scan long lists manually.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, React, TypeScript, TanStack Query, Vitest, React Testing Library, pytest.

---

## File Structure

- Modify: `backend/src/argus/api/contracts.py`
  - Add history window mode and coverage metadata to the series response.
- Modify: `backend/src/argus/services/app.py`
  - Materialize bucket ranges with zeros and distinguish zero coverage from missing data.
- Modify: `backend/src/argus/api/v1/history.py`
  - Accept relative-window query parameters when requested.
- Test: `backend/tests/services/test_history_service.py`
  - Cover zero-filled buckets and coverage metadata.
- Test: `backend/tests/api/test_history_endpoints.py`
  - Cover the new query/response contract.
- Modify: `frontend/src/lib/history-url-state.ts`
  - Add relative vs absolute mode and follow-now state.
- Modify: `frontend/src/hooks/use-history.ts`
  - Send the new window parameters and expose series metadata.
- Modify: `frontend/src/pages/History.tsx`
  - Add live-window controls, bucket semantic labels, search, and empty-state distinctions.
- Create: `frontend/src/components/history/HistorySearchBox.tsx`
  - Shared omnibox/typeahead search surface.
- Test: `frontend/src/pages/History.test.tsx`
  - Cover follow-now, zero buckets, and search behavior.
- Test: `frontend/src/lib/history-url-state.test.ts`
  - Cover URL serialization for the new time model.

### Task 1: Zero-fill history buckets in the backend

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_history_service.py`
- Test: `backend/tests/api/test_history_endpoints.py`

- [ ] **Step 1: Write the failing backend tests for empty-but-valid history windows**

```python
@pytest.mark.asyncio
async def test_query_series_returns_zero_rows_for_empty_valid_window(monkeypatch):
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

    assert [row.total_count for row in response.rows] == [0, 0, 0]
    assert response.coverage_status == "zero"
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `python3 -m uv run pytest backend/tests/services/test_history_service.py backend/tests/api/test_history_endpoints.py -q`

Expected: FAIL because empty windows currently return no rows and no coverage metadata.

- [ ] **Step 3: Add range materialization and coverage metadata**

```python
class HistoryCoverageStatus(StrEnum):
    ZERO = "zero"
    POPULATED = "populated"
    GAP = "gap"


def _bucket_range(starts_at: datetime, ends_at: datetime, granularity: str) -> list[datetime]:
    step = {"1m": timedelta(minutes=1), "5m": timedelta(minutes=5), "1h": timedelta(hours=1), "1d": timedelta(days=1)}[granularity]
    buckets: list[datetime] = []
    current = starts_at
    while current < ends_at:
        buckets.append(current)
        current += step
    return buckets
```

```python
for bucket in _bucket_range(starts_at, ends_at, effective_granularity):
    values = buckets.get(bucket, {})
    result_rows.append(
        HistorySeriesRow(
            bucket=bucket,
            values={c: values.get(c, 0) for c in selected_classes},
            total_count=sum(values.values()),
            ...
        )
    )
```

- [ ] **Step 4: Re-run the backend tests**

Run: `python3 -m uv run pytest backend/tests/services/test_history_service.py backend/tests/api/test_history_endpoints.py -q`

Expected: PASS with explicit zero rows and coverage metadata.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/tests/services/test_history_service.py backend/tests/api/test_history_endpoints.py
git commit -m "feat: zero-fill history buckets and add coverage metadata"
```

### Task 2: Add relative live windows and bucket semantics in frontend state

**Files:**
- Modify: `frontend/src/lib/history-url-state.ts`
- Modify: `frontend/src/hooks/use-history.ts`
- Modify: `frontend/src/pages/History.tsx`
- Test: `frontend/src/lib/history-url-state.test.ts`
- Test: `frontend/src/pages/History.test.tsx`

- [ ] **Step 1: Write the failing frontend tests for follow-now mode**

```tsx
test("keeps relative live windows in follow-now mode", async () => {
  renderPage("/history?window=last_1h");

  expect(screen.getByText(/following now/i)).toBeInTheDocument();
  expect(screen.getByText(/hourly buckets/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `corepack pnpm --dir frontend exec vitest run src/lib/history-url-state.test.ts src/pages/History.test.tsx`

Expected: FAIL because history only understands absolute `from`/`to` windows today.

- [ ] **Step 3: Add a proper time-window state model**

```ts
export type HistoryWindowMode = "relative" | "absolute";
export type RelativeWindowPreset = "last_15m" | "last_1h" | "last_24h" | "last_7d";

export interface HistoryFilterState {
  windowMode: HistoryWindowMode;
  relativeWindow: RelativeWindowPreset;
  followNow: boolean;
  from: Date;
  to: Date;
  ...
}
```

```ts
if (state.windowMode === "relative") {
  params.set("window", state.relativeWindow);
  params.set("follow", state.followNow ? "1" : "0");
} else {
  params.set("from", state.from.toISOString());
  params.set("to", state.to.toISOString());
}
```

- [ ] **Step 4: Update HistoryPage to render bucket semantics and auto-refresh**

```tsx
{state.windowMode === "relative" && state.followNow ? (
  <Badge className="border-[#2d5e46] bg-[#0b1b13] text-[#bff3d0]">Following now</Badge>
) : (
  <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">Absolute window</Badge>
)}

<p className="text-sm text-[#93a7c5]">
  {state.granularity === "1h" ? "Hourly buckets · Current bucket: 14:00–14:59" : "Live bucketed view"}
</p>
```

- [ ] **Step 5: Re-run the frontend tests**

Run: `corepack pnpm --dir frontend exec vitest run src/lib/history-url-state.test.ts src/pages/History.test.tsx`

Expected: PASS with relative window serialization and follow-now UI.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/history-url-state.ts frontend/src/hooks/use-history.ts frontend/src/pages/History.tsx frontend/src/lib/history-url-state.test.ts frontend/src/pages/History.test.tsx
git commit -m "feat: add follow-now history windows and bucket semantics"
```

### Task 3: Add search and differentiated empty states

**Files:**
- Create: `frontend/src/components/history/HistorySearchBox.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/hooks/use-history.ts`
- Test: `frontend/src/pages/History.test.tsx`

- [ ] **Step 1: Write the failing tests for history search and zero-vs-gap empty states**

```tsx
test("filters class and camera lists from one search box", async () => {
  renderPage("/history");

  await user.type(screen.getByLabelText(/search history filters/i), "per");

  expect(screen.getByText("person")).toBeInTheDocument();
  expect(screen.queryByText("bus")).not.toBeInTheDocument();
});

test("renders a flat zero message instead of generic emptiness for zero coverage", async () => {
  mockHistorySeries({ rows: zeroRows, coverage_status: "zero" });
  renderPage("/history");

  expect(screen.getByText(/no detections in this window/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the failing tests**

Run: `corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx`

Expected: FAIL because there is no search box and no coverage-specific empty-state rendering.

- [ ] **Step 3: Add the search box and use it to filter cameras/classes/boundaries**

```tsx
<HistorySearchBox
  value={search}
  onChange={setSearch}
  placeholder="Search cameras, classes, or boundaries"
/>
```

```ts
const filteredClasses = observedClasses.filter((entry) =>
  entry.class_name.toLowerCase().includes(search.toLowerCase()),
);
```

- [ ] **Step 4: Render empty states based on `coverage_status`**

```tsx
if (chartEmpty && data?.coverage_status === "zero") {
  return <p>No detections in this window.</p>;
}
if (chartEmpty && data?.coverage_status === "gap") {
  return <p>No telemetry coverage is available for this window.</p>;
}
```

- [ ] **Step 5: Re-run the History tests**

Run: `corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx`

Expected: PASS for search and empty-state behavior.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/history/HistorySearchBox.tsx frontend/src/pages/History.tsx frontend/src/hooks/use-history.ts frontend/src/pages/History.test.tsx
git commit -m "feat: add history search and explicit zero coverage states"
```

### Task 4: End-to-end verification

**Files:**
- Test: `backend/tests/services/test_history_service.py`
- Test: `backend/tests/api/test_history_endpoints.py`
- Test: `frontend/src/lib/history-url-state.test.ts`
- Test: `frontend/src/pages/History.test.tsx`

- [ ] **Step 1: Run focused verification**

Run:

```bash
python3 -m uv run pytest backend/tests/services/test_history_service.py backend/tests/api/test_history_endpoints.py -q
corepack pnpm --dir frontend exec vitest run src/lib/history-url-state.test.ts src/pages/History.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Build the frontend**

Run: `corepack pnpm --dir frontend build`

Expected: PASS with no new type errors.

- [ ] **Step 3: Commit final polish**

```bash
git add docs/superpowers/specs/2026-04-26-operator-setup-history-delivery-hardening-design.md
git commit -m "docs: record history hardening implementation completion"
```
