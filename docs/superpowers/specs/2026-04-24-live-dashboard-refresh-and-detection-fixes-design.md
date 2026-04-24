# Live Dashboard Refresh and Detection Fixes Design

- Date: 2026-04-24
- Scope: Merge Dashboard and Live into a single "Live" page, add a per-camera 30-minute detection sparkline, fix five detection/telemetry bugs surfaced by the first iMac smoke test.
- Status: Approved design, pending user review before writing the implementation plan

## Goal

Land five detection bugs, consolidate the redundant Dashboard/Live pages into one canonical "Live" page, and give operators a live 30-minute detection pulse inline on each camera tile. After this, the operator workflow is: land on Live → see video + counter + sparkline in each tile → click to History only when investigating a specific time window.

## Why This Is Needed

The first end-to-end test of the Spec B history page on the iMac surfaced behaviour that makes the product unusable for its stated purpose:

- Bounding boxes render at the top-left of the video, not on the detected subject.
- Per-camera detection count increments every frame instead of stabilising on the same track.
- The History chart shows no data on first load unless "Show speed" is ticked, even though `tracking_events` has fresh rows.
- Live telemetry stops updating as soon as the operator navigates away from the Live page.
- Switching a camera to passthrough/native mode causes the worker's RTSP ingest to time out because the camera only supports one concurrent RTSP session and MediaMTX is already using it.

On top of that, the Dashboard and Live pages are architecturally redundant — `Live.tsx` is a six-line wrapper that re-exports `Dashboard.tsx` with a different header label. Two nav entries, one page, zero distinction.

And the Live page itself has no running chart. Operators see instantaneous counters that flash at 3 FPS; there is nothing to answer "what happened in the last half hour on this camera?" without leaving the page.

## In Scope

### Bug fixes

- **Bug 1 — Bounding box rescale.** Rewrite `_rescale_bbox` in `backend/src/argus/vision/detector.py` to always scale from model input space (`input_shape.width/height`) to the frame space (`frame_width`/`frame_height`). Remove the `max_coordinate <= max(frame_width, frame_height)` heuristic at lines 204–210. Outputs from `_prepare_tensor` are always in model input space, so there is no ambiguity to guard against.
- **Bug 2 — Tracker IDs don't persist.** Verify after Bug 1 lands on the iMac. If the tracker still assigns a fresh track_id per frame even with correct bbox coordinates, add a follow-up fix in `backend/src/argus/vision/tracker.py` `UltralyticsTrackerAdapter`. Budget one extra commit.
- **Bug 3 — History chart empty without "Show speed".** In `HistoryService.query_series` at `backend/src/argus/services/app.py`, route the count-only path (`include_speed=False`) at the `tracking_events` hypertable instead of the `events_1m`/`events_1h` continuous aggregates. Keep the existing `_fetch_series_rows` helper around, renamed to `_fetch_series_rows_aggregate`, in case we later decide to re-introduce the aggregate path for large deployments.
- **Bug 4 — Telemetry WebSocket lifecycle.** Move the `/ws/telemetry` subscription out of the Live page and into an app-level Zustand store (`frontend/src/stores/telemetry-store.ts`). A single shared connection, keyed on the authenticated user/tenant, with a union of subscribed cameras. Ref-counted — opens on first subscribe, closes on last-subscriber unmount plus a 10-second idle grace period so tab-to-tab navigation keeps the socket warm.
- **Bug 5 — Worker vs MediaMTX RTSP contention in passthrough mode.** When a camera's `stream.kind == "passthrough"` (and the runtime decides MediaMTX will pull from the camera), the worker reads from `rtsp://mediamtx:8554/cameras/<camera_id>/passthrough` instead of the camera URL directly. Annotated-mode workers keep pulling from the camera URL because MediaMTX does not open an RTSP session in that mode. One helper function with branch logic and a unit test.

### IA consolidation

- Delete `frontend/src/pages/Live.tsx` (the wrapper).
- Rename `frontend/src/pages/Dashboard.tsx` → `frontend/src/pages/Live.tsx`. The named exports become `LivePage` (existing) and nothing else — drop the obsolete `DashboardPage` wrapper.
- `frontend/src/app/router.tsx`: `/live` renders the renamed page; `/dashboard` becomes a `<Navigate to="/live" replace />` redirect so existing bookmarks and links continue to work without appearing in the nav.
- `frontend/src/components/layout/TopNav.tsx`: remove the "Dashboard" entry from the Operations group. Operations now reads: Live, History, Incidents.

### Live sparkline

- New component `frontend/src/components/live/LiveSparkline.tsx` — renders under the video in each camera tile.
- Fixed 30-minute window, per-minute buckets (30 data points).
- Per-class rate lines (Interpretation 1 — detections in each one-minute bucket). Top 3 most-active classes rendered as lines; remainder collapsed behind a `+N more` expander that reveals the full list when clicked.
- Per-class total badge next to each line showing the sum over the last 30 minutes.
- Line colour per class is consistent with the Spec B history chart where applicable; otherwise a palette seeded from the class order on that tile.
- New hook `frontend/src/hooks/use-live-sparkline.ts` that orchestrates the hybrid data source:
  - On mount, seed from `GET /api/v1/history/series?granularity=1m&from=now-30m&to=now&camera_id=<id>`.
  - After seed, live TelemetryFrames from the telemetry store append to the current minute's bucket.
  - Once per minute (Date.now()-rounded), roll the window forward — drop the oldest bucket, add a fresh empty bucket for the new minute.

### Supporting changes

- A shared ring buffer interface on the telemetry store so the sparkline can read buffered data without prop-drilling.
- Extend `useLiveTelemetry` to be a thin wrapper over `useTelemetryStore(...)` so existing call sites continue to work unchanged.

## Out of Scope (Deferred)

- Architectural relay of all camera streams through MediaMTX (Bug 5 option B). Only the passthrough-mode contention is fixed. The annotated-mode direct-pull is untouched because there is no contention there.
- Fleet-wide aggregate chart at the top of Live (would duplicate History).
- Per-camera speed sparkline (speed analysis stays on History).
- Attribute-driven filtering (Spec D).
- Observability container cleanup — otel-collector / Tempo / Prometheus (was Spec C, still Spec C).
- TimescaleDB realtime-aggregation retrofit (`WITH (timescaledb.materialized_only = false)`). Reading `tracking_events` directly sidesteps the staleness without a schema change; if query latency degrades at fleet scale, this would be the follow-up.
- Per-camera homography tag in the speed legend (still deferred from Spec B).

## Architecture

### Backend

`backend/src/argus/vision/detector.py`:

```python
def _rescale_bbox(
    self,
    bbox: tuple[float, float, float, float],
    frame_width: int,
    frame_height: int,
) -> tuple[float, float, float, float]:
    input_width = float(self.model_config.input_shape["width"])
    input_height = float(self.model_config.input_shape["height"])
    if input_width <= 0 or input_height <= 0 or frame_width <= 0 or frame_height <= 0:
        LOGGER.warning(
            "Invalid input/frame dimensions, returning bbox unchanged: "
            "input=%sx%s frame=%sx%s",
            input_width, input_height, frame_width, frame_height,
        )
        x1, y1, x2, y2 = bbox
        return (float(x1), float(y1), float(x2), float(y2))
    scale_x = frame_width / input_width
    scale_y = frame_height / input_height
    x1, y1, x2, y2 = bbox
    return (
        float(np.clip(x1 * scale_x, 0.0, frame_width)),
        float(np.clip(y1 * scale_y, 0.0, frame_height)),
        float(np.clip(x2 * scale_x, 0.0, frame_width)),
        float(np.clip(y2 * scale_y, 0.0, frame_height)),
    )
```

`backend/src/argus/services/app.py` — `HistoryService`:

- Rename existing `_fetch_series_rows` → `_fetch_series_rows_aggregate`.
- Add `_fetch_series_rows_from_events`: same shape as `_fetch_series_rows_with_speed` but without percentile/violation columns. Query `tracking_events` with `time_bucket(INTERVAL '<interval>', ts)` + `count(*)::bigint` grouped by bucket and class_name.
- `query_series` dispatch: `include_speed=True` → `_fetch_series_rows_with_speed`; `include_speed=False` → `_fetch_series_rows_from_events`. Both paths read the hypertable.

`backend/src/argus/vision/runtime.py` (or the worker bootstrap in `engine.py`):

- New helper `resolve_camera_read_url(camera_config, mediamtx_rtsp_base)` that returns either the camera's direct RTSP URL or the MediaMTX passthrough URL depending on `stream.kind`.
- Call this helper at worker startup where the worker currently wires up `CameraSourceConfig.source_uri`.
- Emit an INFO log line on selection ("Worker reading RTSP from MediaMTX passthrough path" / "… from camera URL directly") so the first iMac test shows which path is live.

### Frontend — IA

`frontend/src/app/router.tsx`:

```tsx
{ path: "live", lazy: async () => ({ Component: (await import("@/pages/Live")).LivePage }) },
{ path: "dashboard", element: <Navigate to="/live" replace /> },
```

`frontend/src/components/layout/TopNav.tsx`: drop the "Dashboard" entry. Operations items become `[Live, History, Incidents]`.

Move `frontend/src/pages/Dashboard.tsx` → `frontend/src/pages/Live.tsx` via `git mv`. Named export stays `LivePage`. Anything that imports `DashboardPage` is fixed — `frontend/src/pages/Live.tsx` wrapper is deleted, and `router.tsx` imports `LivePage` directly from the renamed file.

### Frontend — Telemetry store

`frontend/src/stores/telemetry-store.ts` (new):

```typescript
type TelemetryStoreState = {
  subscribers: Map<string, number>;      // camera_id → ref count
  socket: WebSocket | null;
  buffers: Map<string, RingBuffer<TelemetryFrame>>;   // camera_id → last-30-min frames
  subscribe: (cameraId: string) => void;
  unsubscribe: (cameraId: string) => void;
  getLatest: (cameraId: string) => TelemetryFrame | null;
  getBuffer: (cameraId: string) => TelemetryFrame[];
};
```

Lifecycle:

1. First `subscribe()` opens a WebSocket to `/ws/telemetry` and starts streaming.
2. Additional `subscribe()` calls just increment the ref count and push the camera into the union set sent to the server in an outgoing subscription message (or, if the WS protocol simply filters client-side, via the route handler).
3. `unsubscribe()` decrements. When the last subscriber's count hits 0, start a 10-second idle timer. If a new subscription arrives during that window, cancel the timer and reuse the socket. Otherwise close.
4. Ring buffer per camera holds the last 30 minutes (~5 400 frames at 3 FPS × 30 min = 5 400 entries, roughly 0.5 MB uncompressed — acceptable).
5. Frames arrive → append to the correct camera's ring buffer → evict the front if the oldest entry is more than 30 min 5 seconds old (5 s grace so the sparkline doesn't flicker on boundary).

`frontend/src/hooks/use-live-telemetry.ts`: becomes a thin selector hook:

```typescript
export function useLiveTelemetry(cameraIds: string[]) {
  useEffect(() => {
    cameraIds.forEach(id => useTelemetryStore.getState().subscribe(id));
    return () => {
      cameraIds.forEach(id => useTelemetryStore.getState().unsubscribe(id));
    };
  }, [cameraIds.join(",")]);
  return useTelemetryStore(s =>
    Object.fromEntries(cameraIds.map(id => [id, s.getLatest(id)])),
  );
}
```

No call-site changes.

### Frontend — Sparkline

`frontend/src/components/live/LiveSparkline.tsx` (new):

```tsx
type LiveSparklineProps = { cameraId: string; activeClasses: string[] };

export function LiveSparkline({ cameraId, activeClasses }: LiveSparklineProps) {
  const { buckets, totals, loading } = useLiveSparkline(cameraId);
  const top3 = useMemo(() => rankTop(totals, 3), [totals]);
  const rest = useMemo(() => activeClasses.filter(c => !top3.includes(c)), [activeClasses, top3]);
  const [showRest, setShowRest] = useState(false);

  if (loading) return <SparklineSkeleton />;

  return (
    <div>
      {top3.map(cls => <SparklineRow key={cls} class={cls} buckets={buckets[cls]} total={totals[cls]} />)}
      {rest.length > 0 && !showRest && (
        <button onClick={() => setShowRest(true)}>+{rest.length} more</button>
      )}
      {showRest && rest.map(cls => <SparklineRow key={cls} class={cls} buckets={buckets[cls]} total={totals[cls]} />)}
    </div>
  );
}
```

`frontend/src/hooks/use-live-sparkline.ts` (new):

```typescript
export function useLiveSparkline(cameraId: string) {
  const [buckets, setBuckets] = useState<Record<string, number[]>>({});
  const [loading, setLoading] = useState(true);

  // Seed from history
  useEffect(() => {
    const now = new Date();
    const from = new Date(now.getTime() - 30 * 60 * 1000);
    apiClient.GET("/api/v1/history/series", {
      params: { query: {
        granularity: "1m", from: from.toISOString(), to: now.toISOString(),
        camera_ids: [cameraId],
      }},
    }).then(({ data }) => {
      setBuckets(seedFromSeries(data?.rows ?? [], from, now));
      setLoading(false);
    });
  }, [cameraId]);

  // Live updates from telemetry store
  useTelemetryStore.subscribe(state => {
    const frame = state.getLatest(cameraId);
    if (frame) appendToBuckets(setBuckets, frame);
  });

  // Minute rollover
  useInterval(() => rollWindow(setBuckets), 60 * 1000);

  const totals = useMemo(() => Object.fromEntries(
    Object.entries(buckets).map(([cls, counts]) => [cls, counts.reduce((a, b) => a + b, 0)])
  ), [buckets]);

  return { buckets, totals, loading };
}
```

### Frontend — Tile integration

Within the camera tile renderer in `Live.tsx` (previously `Dashboard.tsx`), add the `<LiveSparkline>` component in the footer below the heartbeat and count overlay. Adjust the tile's `<article>` layout to accommodate ~80 px of extra vertical space (three sparkline rows × 24 px + padding).

## Data Flow

1. Camera RTSP → MediaMTX (passthrough mode only).
2. MediaMTX → Worker (passthrough mode, Bug 5 fix): worker reads from `rtsp://mediamtx:8554/cameras/<id>/passthrough`.
3. Camera RTSP → Worker (annotated mode): worker reads camera URL directly.
4. Worker → Detector → corrected bbox rescale (Bug 1) → Tracker → stable track IDs (Bug 2 verification) → Annotate.
5. Worker → NATS `evt.tracking.<id>` → backend subscriber → `/ws/telemetry` fan-out.
6. Worker → `tracking_events` hypertable (persistent rows with corrected bboxes).
7. Frontend telemetry store: single app-level WebSocket subscription, ref-counted, 10 s idle grace (Bug 4).
8. Live page tiles: each tile subscribes to its own camera, renders counter + video + sparkline. `TelemetryCanvas` uses corrected bboxes.
9. Live sparkline: hybrid hydration → seed from `/history/series` once → append live WS frames → roll window every minute.
10. History page: count-only path now reads `tracking_events` (Bug 3) → chart shows data immediately without "Show speed".

## Error Handling

- **Detector rescale**: zero or negative `frame_width` / `input_width` → log warning + return bbox unchanged. Avoids a divide-by-zero that would crash the worker loop.
- **Count-only history path**: same `_ensure_history_window` + `_effective_granularity` guards as the speed path. Empty result → `rows: []`. Frontend already handles that.
- **MediaMTX relay**: worker starts before MediaMTX registers the path → existing `_reconnect` logic retries with backoff. Log the URL source once at startup so operators can diagnose "is my worker using MediaMTX or the camera?" from one log line.
- **Telemetry store WebSocket**: disconnect → exponential backoff reconnect (existing 1.5 s start). Ring buffer survives disconnects so the sparkline doesn't flicker during short blips. Subscription union re-sent on reconnect.
- **Telemetry store oversize buffer**: ring buffer capped at 6000 entries per camera. That's 3 FPS × 60 sec × 30 min = 5400 frames under normal conditions, plus a 10 % safety margin so brief rate spikes don't truncate the window.
- **Sparkline seed failure**: if the hydration request fails, sparkline renders from WS only (starts empty, fills as minutes pass) and logs a console warning. Non-fatal; the live path still works.
- **Route redirect**: `/dashboard` uses `<Navigate replace>` so the browser history doesn't accumulate duplicate entries. Back button goes to wherever the user came from before, not `/dashboard`.

## Component Changes

Backend (Python, FastAPI, SQLAlchemy, TimescaleDB):

- `backend/src/argus/vision/detector.py` — rewrite `_rescale_bbox`.
- `backend/src/argus/services/app.py` — rename `_fetch_series_rows` → `_fetch_series_rows_aggregate`; add `_fetch_series_rows_from_events`; update `query_series` dispatch.
- `backend/src/argus/vision/runtime.py` (or a new helper module if cleaner) — `resolve_camera_read_url`.
- `backend/src/argus/inference/engine.py` — call the new helper at worker bootstrap, log selection.
- `backend/src/argus/vision/tracker.py` — touch only if Bug 1 fix doesn't stabilise tracker IDs on the iMac smoke test.

Frontend (React 19, Zustand 5, TanStack Query, ECharts 6):

- `frontend/src/pages/Live.tsx` (existing wrapper) — deleted first.
- `frontend/src/pages/Dashboard.tsx` — renamed to `frontend/src/pages/Live.tsx` via `git mv`, then extended to include `<LiveSparkline>` in each tile. After the rename only one `Live.tsx` file exists.
- `frontend/src/app/router.tsx` — `/dashboard` redirect, `/live` points at renamed page.
- `frontend/src/components/layout/TopNav.tsx` — drop Dashboard nav entry.
- `frontend/src/stores/telemetry-store.ts` — new.
- `frontend/src/hooks/use-live-telemetry.ts` — rewrite as thin store selector, preserve existing shape.
- `frontend/src/components/live/LiveSparkline.tsx` — new.
- `frontend/src/hooks/use-live-sparkline.ts` — new.

No database migrations.

## Testing

### Backend — pytest

- `tests/vision/test_detector.py`:
  - `test_rescale_bbox_scales_model_input_to_frame` — 1280×720 frame with 640×640 model, bbox (100, 100, 500, 500) must rescale to (200, 112.5, 1000, 562.5).
  - `test_rescale_bbox_clips_to_frame_bounds` — bbox partially outside input bounds clips correctly.
  - `test_rescale_bbox_handles_zero_dimensions` — zero input/frame dims → bbox unchanged, no crash.
- `tests/services/test_history_service.py`:
  - `test_query_series_count_only_reads_tracking_events` — seed hypertable fixtures (or mock `_fetch_series_rows_from_events`), assert response matches fresh rows not the stale aggregate.
- `tests/vision/test_camera.py` or a new `tests/vision/test_runtime.py`:
  - `test_resolve_camera_read_url_uses_mediamtx_passthrough` — passthrough camera config returns `rtsp://mediamtx:8554/cameras/<id>/passthrough`.
  - `test_resolve_camera_read_url_uses_direct_in_annotated` — annotated returns the camera URL unchanged.

### Frontend — vitest

- `stores/telemetry-store.test.ts`:
  - First subscribe opens the WebSocket.
  - Second subscribe does not open a second connection.
  - Last unsubscribe + 10 s idle closes the connection.
  - Re-subscribe within the grace period cancels the idle timer.
  - Ring buffer caps at configured size, drops oldest.
- `components/live/LiveSparkline.test.tsx`:
  - Seed data from `/history/series` renders 30 buckets for each class.
  - Simulated WS frame appends to the current bucket.
  - Only top 3 classes render by default; `+N more` expander reveals the rest.
  - Total badge matches the sum of the 30 buckets per class.
- `pages/Live.test.tsx`:
  - Renders video + counter + sparkline per tile.
  - Selected camera filter reflects in sparkline content.

### e2e — Playwright

- Extend `frontend/e2e/prompt8-live-dashboard.spec.ts` (or the current Live spec):
  - Visit `/dashboard` → URL becomes `/live` on first render. Only "Live" in Operations nav.
  - After WS frame arrives, tile counter and sparkline both update within 2 s.
  - Navigate away to `/history`, back to `/live` within 5 s → telemetry store still connected, counters and sparkline resume without a reconnection flicker.

## Non-Functional Requirements

- Detector fix is a pure function rewrite. No perf regression — the new path is strictly fewer conditionals.
- History count-only path now reads the hypertable. Target p95 latency with `include_speed=false` over a 24-hour window at 1-hour granularity: under ~300 ms on the dev TimescaleDB. If this degrades under fleet load, re-introduce the aggregate path via a feature flag on `HistoryService.query_series` — the renamed helper is still available.
- Telemetry store memory: 6000 frames × ~200 bytes ≈ 1.2 MB per camera max; 10 cameras = 12 MB. Acceptable.
- Sparkline hydration: one `/history/series` request per camera on mount. With 10 cameras on Live that's 10 concurrent requests — batched by TanStack Query's dedup logic when parameters overlap, otherwise acceptable.
- Route redirect uses `replace` — the browser history doesn't grow.
- No new secrets, no worker-side schema changes, no migrations.

## Rollout

Single branch off `new-features`. Single PR targeting `main`. No feature flag needed: the IA consolidation and bug fixes are self-contained per-URL changes; the sparkline is additive inside each tile.

## Known Deferred

- **Bug 2 deeper fix**: if Bug 1 doesn't stabilise tracker IDs on the iMac, a follow-up commit in `UltralyticsTrackerAdapter` as part of the same spec execution.
- **MediaMTX-relay for annotated mode** (Bug 5 option B): touched only if fleet-level native-mode contention surfaces.
- **Per-camera homography tag** in the speed legend: still Spec B follow-up.
- **Observability cleanup** (Tempo config, Prometheus, otel-collector): still Spec C.
- **Attribute-driven filtering** (person with a hat): still Spec D.
