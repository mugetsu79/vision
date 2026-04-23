# History Page Speed Visualization Design

- Date: 2026-04-23
- Scope: Frontend `/history` page — detection count defaults, stacked speed panel, user-configurable speed threshold, URL-persisted filter state; one additive endpoint change on `/api/v1/history/series`.
- Status: Approved design, pending user review before writing the implementation plan

## Goal

Make the History page show useful information on first load against existing `tracking_events` data, add a speed visualization alongside the detection count chart, let the operator pin a speed threshold to highlight breaches, and make all filter state survive navigation via URL query parameters. No worker or ingest changes.

## Why This Is Needed

Telemetry already flows end-to-end in production. The `tracking_events` hypertable captures per-detection `speed_kph`, `direction_deg`, `class_name`, `track_id`, `camera_id`, and `ts`, and the worker's homography transform produces `speed_kph` for every track it sees.

Today the History page renders a working count chart but feels empty and non-functional for three reasons:

- **Default view shows nothing.** The default filter window does not align with the time when test detections happened, so a fresh landing on `/history` looks broken even when the database has rows.
- **Filter state does not survive navigation.** Applying a natural-language filter populates the chart, but navigating to another page and back wipes the selection, reinforcing the "empty" feeling.
- **No speed visualization exists.** `tracking_events` has `speed_kph` on every row for homography-configured cameras, but the UI surfaces nothing about vehicle speed — no line, no threshold breach signal, no violation count.

The product spec (`product-spec-v4.md`) pins the data model, the endpoint contract, and the continuous aggregates (`events_1m`, `events_1h`) but does not prescribe the chart type or aggregation strategy for speed. That design space is settled here.

## In Scope

- Smart defaults on `/history` (last 24 h, all cameras, all classes, granularity 1 h).
- Empty-state banner with one-click "Try last 7 days" when the selected window has no data.
- URL-persisted filter state for `from`, `to`, `granularity`, `cameras`, `classes`, `speed`, `speedThreshold`.
- New stacked speed panel on the History page:
  - Per-class median (`p50`) and 95th percentile (`p95`) speed lines with a shaded band between them.
  - Horizontal threshold reference line (ECharts `markLine`) when a threshold is set.
  - Violation bars — a thin strip above the speed lines showing per-bucket count of events with `speed_kph > threshold`.
- User-editable `speedThreshold` numeric input (km/h, persisted in URL, enabled only when "Show speed" is on).
- Legend affordance so cameras missing a homography render as `<camera> (speed not configured)` instead of silently showing empty speed data.
- Additive extension of `GET /api/v1/history/series` with two optional query params:
  - `include_speed` (bool, default `false`)
  - `speed_threshold` (float, optional)
- Server-side guardrails:
  - Reject queries covering more than 31 days with HTTP 400 and a message pointing to a narrower range.
  - Auto-bump granularity one tier when the requested `from`/`to`/`granularity` would yield more than 500 buckets; the response reports the adjusted granularity so the UI can show a notice.
- Tests at unit, component, and e2e layers (see §Testing).

## Out of Scope (Deferred)

- Live dashboard counter UX refresh (tracked as Spec A).
- Observability container cleanup — Tempo config, Prometheus, otel-collector (tracked as Spec C).
- Video bounding-box persistence across frames (separate design; touches the worker, not the UI).
- Continuous aggregates for speed (add only if p95 endpoint latency becomes a problem).
- Per-track drill-down views.
- Unit switcher (km/h vs mph).
- Natural-language filter behaviour beyond making it URL-serialisable alongside the structured filters.

## Data and API

### Source
- Raw `tracking_events` hypertable. No new rollups for the first cut.
- Bucketing via `time_bucket(:granularity, ts)`.
- Percentiles via `percentile_cont(0.5) WITHIN GROUP (ORDER BY speed_kph)` and `percentile_cont(0.95) WITHIN GROUP (ORDER BY speed_kph)`.
- Violation count via `count(*) FILTER (WHERE speed_kph > :threshold AND speed_kph IS NOT NULL)`.

### Endpoint shape — `GET /api/v1/history/series`

New query parameters (both optional, both backward compatible):

| Name | Type | Default | Meaning |
| --- | --- | --- | --- |
| `include_speed` | bool | `false` | When true, each bucket includes `speed_p50`, `speed_p95`, `speed_sample_count`. |
| `speed_threshold` | float (km/h) | unset | When provided, each bucket also includes `over_threshold_count`. Ignored unless `include_speed=true`. |

Response shape (illustrative, speed fields only appear when `include_speed=true`):

```json
{
  "granularity": "5m",
  "granularity_adjusted": false,
  "from": "2026-04-23T13:00:00Z",
  "to":   "2026-04-23T14:00:00Z",
  "series": [
    {
      "bucket": "2026-04-23T14:00:00Z",
      "camera_id": "4f6380b8-75d6-4e92-90b8-d870f4ca06c0",
      "class_name": "car",
      "count": 47,
      "speed_p50": 41.2,
      "speed_p95": 58.8,
      "speed_sample_count": 47,
      "over_threshold_count": 8
    }
  ]
}
```

Speed fields are `null` for rows where `speed_kph IS NULL` (no homography configured on that camera at capture time). Frontend must render this as "(speed not configured)" rather than treating `null` as zero.

### Guardrails
- Window cap: reject `(to - from) > 31 days` with HTTP 400 and a structured error payload `{detail: "Window exceeds 31 days"}`.
- Bucket cap: auto-bump granularity one tier when the request would generate more than 500 buckets. Tiers: `1m → 5m → 1h → 1d`. Response sets `granularity_adjusted = true` and returns the effective granularity. UI shows a small notice when this happens.

### Why no new continuous aggregate yet
- `events_1m` and `events_1h` exist only for counts, per the product spec. Extending them to carry speed percentiles is a schema and migration commitment. Ship the on-the-fly query first; add aggregates only if real-world p95 latency of `/history/series` with `include_speed=true` degrades past the acceptability threshold (~500 ms at 5 m granularity across 24 h).

## UX

### Chart layout (stacked, shared X axis)

```
┌────────────────────────────────────────────────────────────┐
│  Detection count  (existing)                               │
│  ─────────── line per class ────────────                   │
├────────────────────────────────────────────────────────────┤
│  Violation bars   (only when speedThreshold set)           │
│  ▆▂▁▃▅▇▂▁ per-bucket count of speed_kph > threshold        │
├────────────────────────────────────────────────────────────┤
│  Speed            (only when "Show speed" toggled on)      │
│  ─── p50 (solid)   - - - p95 (dashed)   ░░░ band between   │
│  ─ ─ ─ ─ ─ ─ threshold markLine ─ ─ ─ ─                    │
└────────────────────────────────────────────────────────────┘
```

- Shared X axis via ECharts `grid` array of three panels bound to one `dataset`.
- Per-class colour consistency across all three panels.
- Tooltip groups all three panels so hovering any point shows count, violation count, and percentile values for the bucket.

### Controls
- Existing: time range picker, granularity selector, camera multi-select, class multi-select.
- New: toggle **Show speed** (maps to `speed` URL param).
- New: numeric input **Speed threshold (km/h)** — enabled only when Show speed is on, empty = no threshold.

### URL state
- Query params: `from`, `to`, `granularity`, `cameras` (comma-separated UUIDs), `classes` (comma-separated strings), `speed` (present as `"1"` when enabled, otherwise omitted entirely), `speedThreshold` (number, omitted when empty). The frontend writes truthy booleans as `"1"` and never writes `"false"` — absence means off. Arrays serialise as comma-separated ids with no trailing separator.
- Hydration: on mount, parse URL query → filter state; missing params fall back to smart defaults.
- Propagation: on any filter change, `history.replaceState` updates the URL without a new history entry, preserving natural back/forward semantics.
- Deep links: loading `/history?speed=true&speedThreshold=60&granularity=5m` applies state on first render.

### Empty state
- When the selected window and filters yield zero buckets, render a centred card:
  - Headline: "No detections in this window".
  - Body: "No events match the selected cameras and classes between `<from>` and `<to>`."
  - Primary action: button **Try last 7 days** (widens the window and refetches).
- If the 7-day window is still empty, render a secondary help link explaining how detections populate history.

### Homography-missing state
- If `speed_p50` is `null` for a camera across the entire window, the legend entry for that camera reads `<camera label> (speed not configured)` and its speed lines are hidden.
- Avoids silent "my cars have no speed" confusion.

### Accessibility and copy
- Tooltips and empty-state copy follow the existing UI refresh voice (calm, direct, operator-first).
- Threshold input is keyboard-focusable and announces its unit via `aria-describedby`.

## Component Changes

Frontend (React, TypeScript, ECharts 6):

- `frontend/src/pages/History.tsx` — add Show speed toggle, threshold input, empty-state card, smart-default hydration.
- `frontend/src/components/history/HistoryTrendChart.tsx` — extend to render optional violation bar panel and speed panel when props indicate.
- `frontend/src/hooks/use-history.ts` — extend `useHistorySeries` to pass `include_speed` and `speed_threshold` params; consume the extended response shape.
- `frontend/src/lib/history-url-state.ts` (new) — parse/serialise filter state to URL query params; one small module with round-trippable behaviour.

Backend (Python, FastAPI, SQLAlchemy, TimescaleDB):

- `backend/src/argus/api/v1/history.py` — accept `include_speed` and `speed_threshold`, pass through to the service, serialise extended response.
- `backend/src/argus/services/app.py` — `HistoryService.query_series` gets the speed-aware query path, percentile and violation computations, and the window/bucket guardrails. `query_history` (non-series legacy) stays unchanged.
- No new database migrations.

## Data Flow

1. User lands on `/history`. `History.tsx` reads URL query via `history-url-state` or falls back to smart defaults (`from = now - 24h`, `granularity = 1h`, all cameras, all classes, speed off).
2. `useHistorySeries` fires a request to `/api/v1/history/series` with the filter state plus `include_speed` and `speed_threshold` when applicable.
3. Backend bucket query runs against `tracking_events` with `time_bucket`, `percentile_cont`, and a `FILTER (WHERE speed_kph > threshold)` count when threshold is provided.
4. Response rendered by `HistoryTrendChart` into one ECharts instance with three grids (count, violation bars if threshold, speed if enabled).
5. Filter changes call a single `updateFilters()` helper → writes URL via `replaceState` → triggers refetch.

## Error Handling

- API 400 for window > 31 days → frontend shows inline error "Select a shorter window (max 31 days)" with a quick-fix button for last 7 days.
- API 5xx or network error → existing toast + empty-state with retry.
- Partial results: when some cameras have homography and others do not, the speed panel renders only the ones that do and the legend labels the rest as "(speed not configured)". Count chart is unaffected.
- `granularity_adjusted=true` response → small banner above the chart: "Showing at 5m granularity (bumped from 1m to keep the chart readable)."

## Testing

### Backend — pytest
- Unit tests for the history service:
  - Happy path: bucket, count, percentiles, sample count, violation count correct against a seeded fixture.
  - `speed_threshold=0` returns violation count equal to the number of rows with `speed_kph IS NOT NULL`.
  - Rows with `speed_kph IS NULL` (homography missing) are excluded from percentile and violation computations but counted in `count`.
  - Window > 31 days returns HTTP 400.
  - `granularity=1m` across a 10-day range auto-bumps to `5m` or higher and sets `granularity_adjusted=true`.
- Integration test: HTTP endpoint with `include_speed=true&speed_threshold=50`, verify response shape and absence of speed fields when `include_speed=false`.

### Frontend — vitest
- `history-url-state`: round-trip serialisation for every filter combination, including edge cases (empty camera list, `speed=true` without threshold, threshold `0`, unrealistically-large threshold).
- `HistoryTrendChart`:
  - Renders count only when `include_speed=false`.
  - Renders count + speed when `include_speed=true` and no threshold.
  - Renders count + violation bars + speed with threshold line when threshold is set.
  - Renders "(speed not configured)" legend entry for homography-null cameras.
- Empty state: "Try last 7 days" button updates URL and triggers a refetch with the widened window.

### e2e — Playwright
- Extend `frontend/e2e/prompt9-history-and-incidents.spec.ts`:
  - Load `/history`, assert default 24 h view renders data when the fixture DB has rows.
  - Change camera + class filter, navigate to `/live`, navigate back: URL preserved and filter state restored.
  - Toggle Show speed, set threshold to 60, assert the threshold line and violation bars appear.
  - Deep link visit `/history?speed=true&speedThreshold=60&granularity=5m` applies state on first render.

## Non-Functional Requirements

- Endpoint p95 latency with `include_speed=true` over a 24-hour window at 5-minute granularity should stay under ~500 ms on the dev Timescale instance. If it drifts above, fall back to pre-aggregated speed rollups (out of scope for first cut — would be a follow-up spec).
- No regression on existing `/history/series` callers (legacy path with no new params returns the same shape as today).
- No new secrets, no schema migrations, no worker-side changes.

## Rollout

- One branch: `new-features` (already created off `main` at `00f8e46`).
- Single PR targeting `main`.
- Feature-flaggable via env var `ARGUS_ENABLE_HISTORY_SPEED_PANEL` on the backend if we want to land incrementally; default on.

## Open Questions

- None blocking. The two that surfaced during brainstorming — threshold semantics and backward-compatible endpoint shape — are resolved above.
