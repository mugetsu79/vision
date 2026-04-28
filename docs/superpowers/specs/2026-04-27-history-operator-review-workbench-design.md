# History Operator Review Workbench Design

> **Status:** Draft for review
>
> **Date:** 2026-04-27
>
> **Goal:** Turn History from a metric chart into an operator-grade review workbench with follow-now windows, explicit zero and coverage semantics, deterministic unified search, bucket-first drilldown, and a clean path to evidence thumbnails, video review, and later natural-language search.

---

## 1. Context

The current History page is already metric-aware:

- `occupancy` describes visible-object occupancy over time.
- `count_events` describes durable crossing, entry, and exit events.
- `observations` describes raw tracking/debug density.
- Speed overlays and threshold breach counts can be requested.
- Filters are URL-backed.
- The backend can auto-adjust granularity for wide windows.

The handoff identifies three remaining History problems:

1. **Follow-now UX:** History currently behaves like a fixed query window even when operators expect a live-relative window.
2. **Zero buckets:** Empty valid windows can look the same as missing data because only populated buckets are returned.
3. **Search:** Operators need to find cameras, classes, boundaries, spikes, gaps, and speed breaches without scanning long lists.

The current frontend also concentrates too many responsibilities in `frontend/src/pages/History.tsx`. The design below improves the page through focused components and clearer contracts without replacing the existing charting stack or rebuilding the whole analytics model.

---

## 2. Product Direction

History should become an **Operator Review Workbench**.

The page should answer:

- What happened in this time window?
- Which camera, class, or boundary contributed?
- Is this a true zero, an ingestion gap, or an operational outage?
- What bucket should I inspect next?
- Can I export the same view I am seeing?

The design is intentionally phased:

1. **Phase 1: Metric-first review**
   - relative and absolute time windows
   - follow-now behavior
   - explicit zero buckets
   - operational coverage states
   - deterministic unified search
   - bucket-first detail pane
   - exports aligned with the visible state
2. **Phase 2: Snapshot-aware review**
   - bucket/event thumbnails when evidence exists
   - evidence slots remain harmless when no thumbnail exists
3. **Phase 3: Video and NL review**
   - jump to retained video at a selected time
   - natural-language search after true open-vocabulary runtime validation gives NL a stronger product role

---

## 3. Goals

1. Make the default History view useful immediately: `Last 24h`, following now.
2. Preserve shareable investigation URLs and restore recent browser state only when no explicit URL state exists.
3. Distinguish zero detections from telemetry gaps and operational outages.
4. Let operators search across cameras, classes, boundaries, buckets, gaps, and threshold breaches from one command surface.
5. Keep the main chart readable while adding optional context lanes for events and coverage.
6. Make bucket selection the primary drilldown interaction.
7. Keep exports faithful to the visible metric/window/scope.
8. Create a clean contract for future thumbnails, retained video, and NL search.

### Non-goals

- Natural-language search in phase 1
- Saved investigations or annotations
- Retained video playback implementation
- Full observability coverage percentages
- Replacing ECharts
- Reworking the detector, tracker, or storage architecture beyond the History contract changes needed for this feature

---

## 4. UX Model

### 4.1 Layout

History uses a **search-first split review** layout.

Desktop layout:

1. **Top toolbar**
   - unified search
   - time mode controls
   - metric selector
   - scope summary
   - follow-now or resume-following control
2. **Main trend area**
   - primary trend chart
   - bucket semantics label
   - optional progressive lanes
3. **Right detail pane**
   - selected bucket review
   - totals, classes, cameras, boundaries
   - coverage and operational status
   - speed breaches
   - evidence slots for later thumbnails/video
4. **Compact status/action strip**
   - following or absolute mode
   - coverage summary
   - granularity adjustment notice
   - export actions

Mobile and tablet layout stacks the same concepts:

1. toolbar
2. chart
3. selected bucket detail
4. filters and export controls

The page should stay dense, quiet, and operational. It should not use a marketing-style hero, large decorative cards, or explanatory feature text. On-screen copy should label state and action, not teach the app in long prose.

### 4.2 Default Window Behavior

When the operator opens `/history` without explicit URL state:

- use relative window `last_24h`
- set `followNow=true`
- resolve `from/to` at query time
- auto-refresh at a cadence appropriate to the granularity

If an explicit URL includes a fixed `from` and `to`:

- use absolute mode
- set `followNow=false`
- show `Absolute window`
- offer `Resume following now`

If the user recently used History and opens `/history` without explicit URL state, the frontend may restore recent local browser state. URL state always wins over local state.

### 4.3 Bucket-First Detail

Clicking or keyboard-selecting a chart bucket selects that bucket in the detail pane.

The bucket detail pane should show:

- bucket start and span
- metric value and total count
- top classes
- camera contribution when available
- boundary contribution for `count_events`
- speed p50/p95 and threshold breach counts when speed is enabled
- coverage status for the bucket
- operational explanation if the bucket is a gap or outage
- future evidence slots for thumbnails and video jump targets

The chart remains visible while the operator reviews details. This avoids the "spike with no explanation" problem common in chart-led analytics pages.

### 4.4 Progressive Lanes

The default chart remains one readable trend chart.

Optional lanes appear below the main chart when relevant or enabled:

- count-event lane
- speed-threshold breach lane
- telemetry gap lane
- camera/worker/source status lane

Lanes should not crowd the page by default. They exist to add operational context during review, not to turn History into a full observability console.

---

## 5. Unified Search

Phase 1 search is deterministic, not natural language.

The search box should support:

- cameras by name
- classes by label
- count boundaries by id/name when viewing `count_events`
- buckets with spikes
- zero-detection windows
- no-telemetry windows
- speed threshold breaches
- count-event-heavy windows

Search uses a hybrid scope:

1. **Current-window search first**
   - search the already-loaded cameras, classes, boundaries, series rows, and coverage metadata
   - selecting a result updates filters or selects a bucket
2. **Search wider later**
   - reserve a UI affordance for broader backend search
   - the backend endpoint can arrive after the current-window search is stable

Search result groups:

- `Cameras`
- `Classes`
- `Boundaries`
- `Buckets`
- `Gaps`
- `Speed breaches`

Selecting a search result should be deterministic:

- camera/class/boundary result updates scope filters
- bucket/gap/speed result selects a bucket and, if needed, adjusts the visible window
- future backend-wide result may return a jump target containing filters plus a selected bucket/time range

Natural-language search is deferred until the open-vocabulary runtime path is validated beyond the current control-plane foundation. At that point, NL can sit above deterministic tokens instead of replacing them.

---

## 6. Data And API Contract

History responses should describe the requested window, not only the rows that happened to contain events.

### 6.1 Series Response

`GET /api/v1/history/series` should return a complete materialized bucket range for the effective query window.

Add or standardize:

- `effective_from`
- `effective_to`
- `bucket_count`
- `bucket_span`
- `coverage_status`
- `coverage_by_bucket`
- existing `granularity`
- existing `granularity_adjusted`
- existing `metric`
- existing `class_names`
- existing `rows`
- existing speed metadata

Coverage statuses:

- `populated`
- `zero`
- `no_telemetry`
- `camera_offline`
- `worker_offline`
- `source_unavailable`
- `no_scope`
- `access_limited`

Rules:

- A valid empty window returns explicit zero rows.
- A bucket with valid telemetry and no detections is `zero`, not `no_telemetry`.
- A bucket with no usable telemetry is a gap/outage state, not a zero.
- Per-bucket coverage can differ from the top-level coverage status.
- The top-level coverage status summarizes the window.
- API/network errors remain separate from coverage states.

For zero-filled rows:

- `values` contains selected classes with `0`.
- `total_count` is `0`.
- speed fields are empty/null unless meaningful speed samples exist.

### 6.2 Class And Boundary Discovery

`GET /api/v1/history/classes` continues to hydrate the filter surface by metric and window.

For `count_events`, the response should include the boundary summaries already supported by the current contracts. Future additions can include:

- boundary label/name
- camera association
- event type availability
- event count in the window

This supports the search box without forcing the operator into raw multi-select scanning.

### 6.3 Future Backend Search Contract

Do not implement broad backend search in phase 1. Phase 1 should keep search deterministic and current-window scoped, while preserving the UI affordance and endpoint shape for later.

Reserve a future endpoint shape such as:

- query text or normalized tokens
- metric
- window preset or absolute window
- camera/class/boundary scope
- result types: camera, class, boundary, bucket, gap, speed breach
- jump target: filters, window, selected bucket/time range

The UI should be shaped so this endpoint can back the future `Search wider` action.

### 6.4 Export Semantics

Exports should use the same resolved metric/window/scope as the visible page.

When the visual chart includes zero-filled buckets, CSV/Parquet export should include those buckets too. Operators should not see a flat zero chart and then export a sparse file that appears to contradict it.

---

## 7. Frontend Architecture

The design should split the current page into focused components while preserving existing hooks and generated API patterns.

### 7.1 Components

`HistoryPage`

- owns URL/local-state sync
- resolves query filters
- stores selected bucket
- coordinates search result actions

`HistoryToolbar`

- unified search entry point
- relative/absolute time controls
- metric selector
- scope summary
- follow-now/resume control

`HistoryTrendPanel`

- wraps the ECharts trend chart
- exposes bucket click/hover selection
- shows bucket semantic labels
- renders progressive lanes

`HistoryBucketDetail`

- renders selected bucket totals and breakdowns
- explains coverage states
- shows speed breach summaries
- reserves evidence thumbnail/video slots for later

`HistorySearchBox`

- deterministic result groups
- keyboard navigation
- result selection callbacks
- current-window search first

`HistoryFilterDrawer` or compact advanced filter panel

- camera/class/boundary lists
- `show all COCO classes`
- speed controls
- export controls if they do not fit in the toolbar/status strip

### 7.2 State

Extend `HistoryFilterState` with:

- `windowMode: "relative" | "absolute"`
- `relativeWindow: "last_15m" | "last_1h" | "last_24h" | "last_7d"`
- `followNow: boolean`
- existing `from`
- existing `to`
- existing `granularity`
- existing `metric`
- existing `cameraIds`
- existing `classNames`
- existing `speed`
- existing `speedThreshold`

Page-local state:

- `selectedBucket: string | null`
- `search: string`
- optional advanced filter panel open/closed state

URL behavior:

- relative mode serializes as `window=last_24h&follow=1`
- absolute mode serializes as `from=...&to=...`
- explicit URL parameters always override local storage
- local storage only restores recent state when no explicit URL view is present

Query behavior:

- relative windows are resolved to concrete `from/to` for existing backend calls unless backend relative parameters are added at the same time
- follow-now refreshes queries on a stable cadence
- changing filters should preserve selected bucket only when the bucket remains in the returned series

---

## 8. Error Handling And Empty States

The frontend must not collapse all empty-looking data into one message.

Required states:

- `zero`: chart is visible with flat zero buckets; message says `No detections in this window`.
- `populated`: normal chart and detail pane.
- `no_telemetry`: show gap lane/detail explanation; do not call it zero detections.
- `camera_offline`: explain the selected camera was offline.
- `worker_offline`: explain processing was unavailable.
- `source_unavailable`: explain the stream/source was unavailable.
- `no_scope`: explain filters exclude all usable cameras/classes/boundaries.
- `access_limited`: explain some data may be hidden by permissions or tenant scope.
- API/network error: render separately from coverage status.

Granularity behavior:

- If the backend adjusts granularity, keep the existing badge behavior but also make the bucket span obvious.
- For hourly buckets, show text such as `Hourly buckets` and `Current bucket: 14:00-14:59`.
- The timestamp shown for a bucket is the bucket start.

---

## 9. Testing Strategy

### 9.1 Backend

Add tests for:

- empty valid windows return zero-filled rows
- top-level `coverage_status` is `zero` for valid empty telemetry
- populated windows keep current class ordering and speed metadata behavior
- per-bucket coverage can represent gaps alongside populated buckets
- no-scope/access-limited cases return explicit status where the service can determine it
- metric-specific semantics remain intact:
  - `occupancy` uses occupancy semantics
  - `count_events` uses count-event storage
  - `observations` uses raw tracking samples
- granularity adjustment still caps excessive bucket counts

### 9.2 Frontend Unit And Component Tests

Add tests for:

- relative and absolute URL round trips
- default `last_24h` following-now state
- absolute window disables follow-now
- resume-following switches back to a relative window
- unified search filters cameras/classes/boundaries
- unified search selects buckets/gaps/speed breach results
- zero coverage renders a flat chart state, not a generic empty state
- operational coverage states render distinct messages
- bucket selection populates the detail pane
- export uses the resolved visible state

### 9.3 End-To-End

Add or extend E2E tests for:

- History opens quickly
- query/search/filter state survives navigation
- bucket click selects the detail pane
- CSV export uses the visible window and scope
- later: evidence thumbnail smoke test
- later: video jump smoke test

---

## 10. Implementation Phasing

### Phase 1A: Backend Trust Contract

- materialize zero buckets
- add coverage metadata
- preserve existing metric and speed behavior
- update OpenAPI/generated frontend client

### Phase 1B: Window State And Follow-Now

- add relative/absolute URL state
- default to `last_24h` following now
- add resume-following behavior
- clarify bucket semantics in the UI

### Phase 1C: Split Review And Bucket Detail

- split `History.tsx` into focused components
- wire chart bucket selection
- build selected bucket detail pane
- keep current charting stack

### Phase 1D: Deterministic Unified Search

- search cameras/classes/boundaries from loaded metadata
- search buckets/gaps/speed breaches from returned series
- selecting a result updates filters or selected bucket
- reserve `Search wider` affordance without implementing NL

### Phase 1E: Exports And E2E Polish

- align export parameters with visible resolved state
- add E2E coverage for navigation, selection, and export

---

## 11. Open Follow-Up Decisions

These are intentionally deferred:

- exact backend representation for per-bucket operational status when multiple cameras contribute mixed states
- whether broad backend search lands immediately after current-window search or waits for evidence/video work
- exact thumbnail/evidence contract
- retained video storage and jump URL contract
- NL search grammar after open-vocabulary runtime validation
