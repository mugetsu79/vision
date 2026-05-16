# Live Tile And Pattern Graph UX Design

Date: 2026-05-16
Status: Approved for implementation planning

## Goal

Make the Live scene tile and History pattern graph feel like one coherent Vezor operational surface: clear worker state, resizable video-first scene tiles, app-level focus mode with graphs still visible, and richer signal charts whose colors match the live object tracking colors.

This is a frontend UX and presentation pass. It does not change detection thresholds, tracker behavior, stream transport, MediaMTX path creation, runtime selection, or history aggregation semantics.

## Product Context

The current Live view now has the right streaming model: native passthrough is clean, annotated and reduced profiles burn boxes into the stream, and the browser overlay is optional only where it makes sense. The remaining issue is trust and hierarchy.

Three things currently feel weaker than the rest of the product:

- The live tile can show `Worker awaiting report` while the video and detections are visibly working. That reads like a fault even when the operator should see a healthy state.
- Scene tiles have one fixed size. The operator cannot promote a scene that matters right now without changing browser zoom or losing the graph.
- The live "Telemetry terrain" and History "Pattern trend" graphs look more like small debugging widgets than premium product surfaces. They do not consistently reuse the same object-class colors that appear on live tracking boxes.

The direction follows `docs/brand/omnisight-ui-spec-sheet.md`: dark operational cockpit, video and data first, restrained accents, clear status language, no marketing-page composition, no decorative blobs, no nested-card clutter.

## UX Principles

1. **Healthy work should look healthy.**
   If fresh telemetry is arriving and the stream is active, the live tile should not lead with a pending or unknown worker label.

2. **Diagnostics belong behind the primary state.**
   Raw runtime report truth is still useful, especially in Operations, but it should be secondary when the operator is watching a working scene.

3. **Layout controls are operator preferences.**
   Tile size and focus mode should not mutate camera configuration, stream profiles, or scene contracts. They are local view preferences.

4. **Class colors are a product language.**
   A person should be green on the live box, the live signal trend, and the history pattern graph. A car should be blue everywhere. Safety and alert colors should stay consistent too.

5. **Graphs should be first-class surfaces.**
   Lines should be smooth, readable, and tall enough to scan. Grid lines should support interpretation without looking like generic chart chrome.

## Worker State Semantics

### Current Problem

`SceneStatusStrip` rewrites `Worker not reported` as `Worker awaiting report`. The phrase is technically grounded in runtime report state, but it is confusing on Live because the operator can simultaneously see:

- a live WebRTC video stream,
- fresh telemetry frames,
- a person count,
- and burned-in boxes.

In that situation the scene is operational from the operator's point of view. The missing runtime report should be a detail, not the primary state.

### Desired Live Tile Copy

The live tile should use these states:

| Evidence | Primary Copy | Tone | Detail |
| --- | --- | --- | --- |
| Worker runtime status is `running` | `Worker running` | healthy | optional runtime detail |
| Runtime report is missing or `not_reported`, but telemetry for the scene is fresh | `Worker active` | healthy | `runtime report pending` |
| Supervisor owns the worker, but no fresh telemetry and no fresh report | `Worker starting` | attention | existing worker detail |
| Runtime status is `stale` | `Worker stale` | attention | worker detail |
| Runtime status is `offline` | `Worker offline` | danger | worker detail |
| No worker is desired for the camera | `Worker off` | muted | `no worker desired` |

Fresh telemetry means the same heartbeat test used by the Live page: `getHeartbeatStatus(frame) === "fresh"`.

### Desired Operations Page Copy

Operations should show the same operator-facing worker status in the Scene intelligence matrix, but the Supervisor lifecycle controls should still expose raw runtime report truth:

- `Heartbeat: Not reported`
- `Runtime: not_reported`
- `Last request: completed start`, `failed start`, etc.

This gives both layers their job: matrix and live tile explain current posture; lifecycle controls remain diagnostic.

## Live Tile Layout

### Tile Size Controls

Each scene tile gets compact icon controls in the tile header:

- Compact
- Standard
- Large
- Focus

The controls use icon buttons with `aria-label` and `title` text. They should not use large text buttons because they are view tools, not scene actions.

Tile size is stored in browser local storage under a versioned key:

```text
vezor.live.tileLayout.v1
```

The value maps camera id to size:

```json
{
  "camera-id": "large"
}
```

If the camera is removed, unused keys can remain harmlessly; the UI only reads sizes for current cameras.

### Grid Behavior

Use a responsive grid with stable spans:

| Size | Mobile | Medium | Wide |
| --- | --- | --- | --- |
| Compact | full width | 1 of 2 columns | 2 of 6 columns |
| Standard | full width | 1 of 2 columns | 3 of 6 columns |
| Large | full width | 2 of 2 columns | 6 of 6 columns |

The current standard experience should remain familiar. Large is the operator's way to promote a scene without leaving the grid.

### Focus Mode

Focus mode is an app-level overlay, not native video fullscreen. This is required because the graph must remain visible.

Focus mode layout:

- Top toolbar: camera name, status strip, size/focus close controls.
- Main region: large video surface with current rendition label and overlay behavior preserved.
- Secondary region: live rendition control, browser overlay toggle when valid, and the signal trend graph.
- On wide screens, video and graph/control area can sit in a two-column layout.
- On laptop and mobile widths, graph/control area stacks below the video.

Keyboard and accessibility:

- `Escape` closes focus mode.
- Close button has `aria-label="Close focused scene"`.
- Focus mode container has an accessible name including the camera name.
- The focused article must avoid horizontal overflow.

## Live Signal Trend

### Current Problem

`TelemetryTerrain` is visually small, one-series focused, and labeled like an internal metaphor. It shows useful data, but it does not have enough visual weight for a live scene tile.

### Desired Surface

Rename the visible heading to `Signal trend`. Keep the component/test id name if that minimizes code churn.

Visual requirements:

- Height: roughly 120-160 px in normal tiles, taller in large/focus mode.
- Primary class: smooth or stepped area line with a subtle gradient fill.
- Secondary classes: up to two thinner lines using the same class colors.
- Legend chips: class name, state, and current live/held count.
- Empty series: quiet baseline, not a blank panel.
- Loading state: same footprint as loaded state.
- Error state: compact inline error, same panel footprint where practical.

The graph should still use stable occupancy buckets from `useLiveSparkline(cameraId)`. It should not become a real-time animation that flashes. Motion remains minimal and respects reduced motion.

### Color Rules

Use the same `colorForClass` semantics everywhere:

| Class family | Examples | Color |
| --- | --- | --- |
| Human | `person`, `worker`, `hi_vis_worker` | `#61e6a6` |
| Vehicle | `car`, `truck`, `bus`, `motorcycle`, `bicycle` | `#62a6ff` |
| Safety / PPE | `helmet`, `vest`, `ppe`, `hard_hat` | `#f7c56b` |
| Alert | `violation`, `alert`, `intrusion` | `#ff6f9d` |
| Other | unknown/open-vocab classes | deterministic fallback |

The shared color mapping should live in a small utility that both live and history components can import.

## History Pattern Trend

### Current Problem

`HistoryTrendChart` uses a hardcoded palette that does not match live object colors. The chart is technically capable but visually generic: small-feeling lines, a conventional legend, and grid styling that does not feel as polished as the Live surface.

### Desired Surface

The Pattern trend panel remains ECharts based. It should be polished, not replaced.

Requirements:

- Use shared class colors from the live tracking palette.
- Increase default chart height:
  - Count only: 440 px.
  - Count + speed: 640 px.
  - Count + threshold + speed: 740 px.
- Use thicker primary lines and subtle area fills:
  - Count lines: width 3, smooth, no symbols by default.
  - Speed p50: width 2.4 solid.
  - Speed p95: width 1.8 dashed, same class color.
  - Threshold line: risk pink, dashed.
- Reduce chart chrome:
  - Dim grid lines.
  - Dark tooltip with strong contrast.
  - Legend text uses product text tokens.
  - Selected bucket shaft remains visible but should not overpower class lines.
- Preserve current functionality:
  - bucket click selection,
  - speed panel,
  - threshold bars,
  - brush/dataZoom controls.

## Component Scope

### Frontend Files To Change

- `frontend/src/lib/signal-colors.ts`
- `frontend/src/lib/live-signal-stability.ts`
- `frontend/src/lib/operational-health.ts`
- `frontend/src/components/operations/SceneStatusStrip.tsx`
- `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`
- `frontend/src/components/live/TelemetryTerrain.tsx`
- `frontend/src/components/history/history-trend-chart-options.ts`
- `frontend/src/components/history/HistoryTrendChart.tsx`
- `frontend/src/components/history/HistoryTrendPanel.tsx`
- `frontend/src/pages/Live.tsx`

### Tests To Update Or Add

- `frontend/src/lib/operational-health.test.ts`
- `frontend/src/components/operations/SceneStatusStrip.test.tsx`
- `frontend/src/components/live/TelemetryTerrain.test.tsx`
- `frontend/src/components/history/HistoryTrendChart.test.tsx`
- `frontend/src/pages/Live.test.tsx`
- Add `frontend/src/hooks/use-live-tile-layout.test.ts` if a dedicated hook is created.

## Non-Goals

- No backend schema changes.
- No changes to tracker or detector thresholds.
- No changes to MediaMTX stream publication.
- No change to the meaning of native, annotated, or reduced live rendition profiles.
- No browser-native fullscreen for this pass.
- No drag-and-drop dashboard builder.
- No new charting library.

## Acceptance Criteria

1. A scene with fresh telemetry and no runtime report shows a green `Worker active` state with `runtime report pending` as detail.
2. `Worker awaiting report` no longer appears on the Live tile.
3. Operations still exposes raw runtime report state in lifecycle controls.
4. Each live tile has compact, standard, large, and focus controls.
5. Tile size persists locally per camera across page reloads.
6. Focus mode shows video and graph at the same time.
7. Live signal trend uses the same class colors as object boxes.
8. History Pattern trend uses the same class colors as live object boxes.
9. Live signal trend is visibly larger and more polished than the current small terrain panel.
10. History chart is taller, cleaner, and still supports bucket selection, speed panels, threshold bars, and selected bucket marking.
11. Tests cover worker status copy/tone, tile layout persistence, focus mode, live graph colors, and history graph colors.

## Verification Plan

Run focused frontend tests:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/lib/operational-health.test.ts \
  src/components/operations/SceneStatusStrip.test.tsx \
  src/components/live/TelemetryTerrain.test.tsx \
  src/components/history/HistoryTrendChart.test.tsx \
  src/pages/Live.test.tsx
```

Run the full frontend test suite if focused tests pass:

```bash
corepack pnpm --dir frontend test
```

Perform visual QA in the browser at:

- 375 px mobile width
- 768 px tablet width
- 1440 px desktop width

Manual checks:

- Resize a tile, reload, confirm size persists.
- Open focus mode, confirm graph remains visible.
- Confirm `person` is green in live boxes, live signal trend, and History trend.
- Confirm vehicle classes are blue in the same three surfaces.
- Confirm no horizontal scroll appears on Live or History.
