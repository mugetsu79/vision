# Live Tile And Pattern Graph UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Live tile worker status, tile sizing/focus mode, and Live/History graph polish with shared object-class colors.

**Architecture:** Keep this as a frontend-only pass. Extract shared signal color semantics, derive operator-facing worker state from runtime plus fresh telemetry, add local tile layout state for Live, and polish the existing SVG/ECharts graph surfaces without replacing their data contracts.

**Tech Stack:** React, TypeScript, Tailwind, Vitest, Testing Library, ECharts, existing Vezor `--vz-*` design tokens.

---

## File Structure

- Create `frontend/src/lib/signal-colors.ts`: shared object class color types and `colorForClass`.
- Modify `frontend/src/lib/live-signal-stability.ts`: import and re-export shared colors so existing imports continue to work.
- Modify `frontend/src/lib/operational-health.ts`: derive `Worker active` from fresh telemetry when runtime report is missing.
- Modify `frontend/src/components/operations/SceneStatusStrip.tsx`: remove `Worker awaiting report` rewrite and render worker details quietly.
- Modify `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`: keep matrix aligned with new worker copy and detail.
- Create `frontend/src/hooks/use-live-tile-layout.ts`: local storage backed tile size preference.
- Create `frontend/src/hooks/use-live-tile-layout.test.ts`: persistence tests.
- Modify `frontend/src/pages/Live.tsx`: tile size controls, focus mode, larger graph mode.
- Modify `frontend/src/components/live/TelemetryTerrain.tsx`: larger multi-series signal trend using shared class colors.
- Modify `frontend/src/components/history/history-trend-chart-options.ts`: shared colors and polished ECharts options.
- Modify `frontend/src/components/history/HistoryTrendChart.tsx`: taller chart heights.
- Modify tests listed in each task.

---

### Task 1: Extract Shared Signal Colors

**Files:**
- Create: `frontend/src/lib/signal-colors.ts`
- Modify: `frontend/src/lib/live-signal-stability.ts`
- Test: `frontend/src/lib/live-signal-stability.test.ts`
- Test: `frontend/src/components/history/HistoryTrendChart.test.tsx`

- [ ] **Step 1: Write the failing history color test**

Add this test to `frontend/src/components/history/HistoryTrendChart.test.tsx`:

```ts
test("uses live signal colors for class series", () => {
  const option = buildHistoryChartOption({
    classNames: ["person", "car"],
    points: [
      {
        bucket: "2026-04-23T00:00:00Z",
        values: { person: 2, car: 1 },
        total_count: 3,
      },
    ],
  });

  const seriesList = option.series as unknown as Array<{
    name: string;
    color?: string;
  }>;

  expect(seriesList.find((entry) => entry.name === "person")?.color).toBe(
    "#61e6a6",
  );
  expect(seriesList.find((entry) => entry.name === "car")?.color).toBe(
    "#62a6ff",
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/history/HistoryTrendChart.test.tsx
```

Expected: FAIL because the history chart still uses its hardcoded palette.

- [ ] **Step 3: Create the shared color utility**

Create `frontend/src/lib/signal-colors.ts`:

```ts
export type SignalColorFamily =
  | "human"
  | "vehicle"
  | "safety"
  | "alert"
  | "other";

export type SignalColor = {
  family: SignalColorFamily;
  stroke: string;
  fill: string;
  text: string;
};

const HUMAN_CLASSES = new Set(["person", "worker", "hi_vis_worker"]);
const VEHICLE_CLASSES = new Set([
  "car",
  "truck",
  "bus",
  "motorcycle",
  "bicycle",
]);
const SAFETY_CLASSES = new Set(["helmet", "vest", "ppe", "hard_hat"]);
const ALERT_CLASSES = new Set(["violation", "alert", "intrusion"]);

const FALLBACK_COLORS: SignalColor[] = [
  {
    family: "other",
    stroke: "#4dd7ff",
    fill: "rgba(77, 215, 255, 0.12)",
    text: "#d9f7ff",
  },
  {
    family: "other",
    stroke: "#a98bff",
    fill: "rgba(169, 139, 255, 0.13)",
    text: "#eee8ff",
  },
  {
    family: "other",
    stroke: "#f7c56b",
    fill: "rgba(247, 197, 107, 0.12)",
    text: "#fff1ca",
  },
];

export function colorForClass(className: string): SignalColor {
  const normalized = className.toLowerCase();
  if (HUMAN_CLASSES.has(normalized)) {
    return {
      family: "human",
      stroke: "#61e6a6",
      fill: "rgba(97, 230, 166, 0.12)",
      text: "#e8fff4",
    };
  }
  if (VEHICLE_CLASSES.has(normalized)) {
    return {
      family: "vehicle",
      stroke: "#62a6ff",
      fill: "rgba(98, 166, 255, 0.12)",
      text: "#e9f3ff",
    };
  }
  if (SAFETY_CLASSES.has(normalized)) {
    return {
      family: "safety",
      stroke: "#f7c56b",
      fill: "rgba(247, 197, 107, 0.13)",
      text: "#fff2cf",
    };
  }
  if (ALERT_CLASSES.has(normalized)) {
    return {
      family: "alert",
      stroke: "#ff6f9d",
      fill: "rgba(255, 111, 157, 0.13)",
      text: "#ffe7ef",
    };
  }

  return FALLBACK_COLORS[hashClassName(normalized) % FALLBACK_COLORS.length];
}

function hashClassName(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}
```

- [ ] **Step 4: Re-export colors from live signal stability**

In `frontend/src/lib/live-signal-stability.ts`, replace the local signal color type and `colorForClass` definitions with imports/re-exports:

```ts
import type { components } from "@/lib/api.generated";
import { colorForClass, type SignalColor } from "@/lib/signal-colors";

export { colorForClass };
export type { SignalColor, SignalColorFamily } from "@/lib/signal-colors";
```

Delete the local `SignalColorFamily`, `SignalColor`, class set constants, `FALLBACK_COLORS`, `colorForClass`, and `hashClassName` definitions from that file.

- [ ] **Step 5: Run live stability tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/live-signal-stability.test.ts
```

Expected: PASS. Existing imports from `live-signal-stability` still work.

---

### Task 2: Fix Worker State Semantics

**Files:**
- Modify: `frontend/src/lib/operational-health.ts`
- Modify: `frontend/src/components/operations/SceneStatusStrip.tsx`
- Test: `frontend/src/lib/operational-health.test.ts`
- Test: `frontend/src/components/operations/SceneStatusStrip.test.tsx`
- Test: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Add worker-active test coverage**

In `frontend/src/lib/operational-health.test.ts`, add a test that creates a camera with a worker whose `runtime_status` is `not_reported` plus a fresh telemetry frame. Assert:

```ts
expect(row.worker).toEqual({
  health: "healthy",
  label: "Worker active",
  detail: "runtime report pending",
});
```

Use an ISO timestamp generated from `new Date().toISOString()` so `getHeartbeatStatus` sees the frame as fresh.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/lib/operational-health.test.ts
```

Expected: FAIL because `deriveWorkerSignal` does not inspect telemetry freshness yet.

- [ ] **Step 3: Update worker derivation**

In `frontend/src/lib/operational-health.ts`, change the call site in `deriveSceneReadinessRows`:

```ts
const telemetryFrame = framesByCamera[camera.id];
const telemetry = deriveTelemetrySignal(telemetryFrame);
const workerSignal = deriveWorkerSignal(worker, telemetryFrame);
```

Update the function signature and missing/not-reported branches:

```ts
function deriveWorkerSignal(
  worker: FleetCameraWorker | undefined,
  frame: TelemetryFrame | undefined,
): HealthSignal {
  const telemetryFresh = getHeartbeatStatus(frame) === "fresh";

  if (!worker) {
    if (telemetryFresh) {
      return {
        health: "healthy",
        label: "Worker active",
        detail: "runtime report pending",
      };
    }
    return { health: "unknown", label: "Worker starting" };
  }

  if (worker.runtime_status === "running") {
    return { health: "healthy", label: "Worker running" };
  }

  if (worker.runtime_status === "not_reported") {
    if (telemetryFresh) {
      return {
        health: "healthy",
        label: "Worker active",
        detail: "runtime report pending",
      };
    }
    return {
      health: "attention",
      label: "Worker starting",
      detail: worker.detail ?? undefined,
    };
  }

  if (worker.runtime_status === "stale") {
    return {
      health: "attention",
      label: "Worker stale",
      detail: worker.detail ?? undefined,
    };
  }

  if (worker.runtime_status === "offline") {
    return {
      health: "danger",
      label: "Worker offline",
      detail: worker.detail ?? undefined,
    };
  }

  return {
    health: "unknown",
    label: telemetryFresh ? "Worker active" : "Worker starting",
    detail: telemetryFresh
      ? "runtime report pending"
      : worker.detail ?? undefined,
  };
}
```

Do not remove stale/offline handling.

- [ ] **Step 4: Remove live tile rewrite**

In `frontend/src/components/operations/SceneStatusStrip.tsx`, remove:

```ts
const workerCopy =
  row.worker.label === "Worker not reported"
    ? "Worker awaiting report"
    : row.worker.label;
```

Render `row.worker.label` directly. Add a quiet detail line when present:

```tsx
<StatusToneBadge tone={healthToTone(row.worker.health)}>
  {row.worker.label}
</StatusToneBadge>
```

Then include worker detail in the `details` array:

```ts
row.worker.detail ? `${row.worker.label}: ${row.worker.detail}` : null,
```

- [ ] **Step 5: Update tests that asserted old copy**

In `frontend/src/pages/Live.test.tsx`, replace:

```ts
within(depotYardStatus).getByText(/worker awaiting report/i)
```

with an assertion for the new copy expected by the mocked frame:

```ts
within(depotYardStatus).getByText(/worker active/i)
```

In `SceneStatusStrip.test.tsx`, add a case for `Worker active` with `runtime report pending`.

- [ ] **Step 6: Run focused worker tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/lib/operational-health.test.ts \
  src/components/operations/SceneStatusStrip.test.tsx \
  src/pages/Live.test.tsx
```

Expected: PASS.

---

### Task 3: Add Local Tile Size Preferences

**Files:**
- Create: `frontend/src/hooks/use-live-tile-layout.ts`
- Create: `frontend/src/hooks/use-live-tile-layout.test.ts`
- Modify: `frontend/src/pages/Live.tsx`

- [ ] **Step 1: Write hook tests**

Create `frontend/src/hooks/use-live-tile-layout.test.ts` with tests for:

```ts
import { act, renderHook } from "@testing-library/react";
import { describe, expect, test, beforeEach } from "vitest";

import {
  LIVE_TILE_LAYOUT_STORAGE_KEY,
  useLiveTileLayout,
} from "@/hooks/use-live-tile-layout";

describe("useLiveTileLayout", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  test("defaults tiles to standard", () => {
    const { result } = renderHook(() => useLiveTileLayout());
    expect(result.current.tileSizeFor("camera-1")).toBe("standard");
  });

  test("persists per-camera tile sizes", () => {
    const { result, rerender } = renderHook(() => useLiveTileLayout());

    act(() => {
      result.current.setTileSize("camera-1", "large");
    });
    rerender();

    expect(result.current.tileSizeFor("camera-1")).toBe("large");
    expect(JSON.parse(localStorage.getItem(LIVE_TILE_LAYOUT_STORAGE_KEY)!)).toEqual({
      "camera-1": "large",
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/hooks/use-live-tile-layout.test.ts
```

Expected: FAIL because the hook does not exist.

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/use-live-tile-layout.ts`:

```ts
import { useCallback, useEffect, useState } from "react";

export const LIVE_TILE_LAYOUT_STORAGE_KEY = "vezor.live.tileLayout.v1";

export type LiveTileSize = "compact" | "standard" | "large";

type TileSizeMap = Record<string, LiveTileSize>;

const VALID_SIZES = new Set<LiveTileSize>(["compact", "standard", "large"]);

export function useLiveTileLayout() {
  const [sizes, setSizes] = useState<TileSizeMap>(() => readTileSizes());

  useEffect(() => {
    window.localStorage.setItem(
      LIVE_TILE_LAYOUT_STORAGE_KEY,
      JSON.stringify(sizes),
    );
  }, [sizes]);

  const tileSizeFor = useCallback(
    (cameraId: string): LiveTileSize => sizes[cameraId] ?? "standard",
    [sizes],
  );

  const setTileSize = useCallback(
    (cameraId: string, size: LiveTileSize) => {
      setSizes((current) => ({ ...current, [cameraId]: size }));
    },
    [],
  );

  return { tileSizeFor, setTileSize };
}

function readTileSizes(): TileSizeMap {
  try {
    const parsed = JSON.parse(
      window.localStorage.getItem(LIVE_TILE_LAYOUT_STORAGE_KEY) ?? "{}",
    );
    if (!parsed || typeof parsed !== "object") return {};

    return Object.fromEntries(
      Object.entries(parsed).filter((entry): entry is [string, LiveTileSize] => {
        const [, value] = entry;
        return typeof value === "string" && VALID_SIZES.has(value as LiveTileSize);
      }),
    );
  } catch {
    return {};
  }
}
```

- [ ] **Step 4: Wire tile size into Live grid**

In `frontend/src/pages/Live.tsx`:

```ts
import { useLiveTileLayout, type LiveTileSize } from "@/hooks/use-live-tile-layout";
```

Inside `WorkspacePage`:

```ts
const { tileSizeFor, setTileSize } = useLiveTileLayout();
const [focusedCameraId, setFocusedCameraId] = useState<string | null>(null);
```

Change the grid class:

```tsx
className="grid gap-4 md:grid-cols-2 xl:grid-cols-6"
```

Pass `tileSize`, `onTileSizeChange`, `isFocused`, `onFocus`, and `onCloseFocus` into `ScenePortalCard`.

Add a helper:

```ts
function tileSpanClass(size: LiveTileSize): string {
  if (size === "large") return "md:col-span-2 xl:col-span-6";
  if (size === "compact") return "xl:col-span-2";
  return "xl:col-span-3";
}
```

Use it on the article class.

- [ ] **Step 5: Run hook test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/hooks/use-live-tile-layout.test.ts
```

Expected: PASS.

---

### Task 4: Add Tile Controls And Focus Mode

**Files:**
- Modify: `frontend/src/pages/Live.tsx`
- Test: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Add Live test coverage**

In `frontend/src/pages/Live.test.tsx`, add tests that assert:

- each tile has buttons labeled `Use compact tile`, `Use standard tile`, `Use large tile`, and `Focus scene`;
- clicking `Use large tile` adds the large span class to the tile;
- clicking `Focus scene` opens a focused scene region with the graph still present;
- pressing Escape closes focus mode.

Use existing scene portal test setup and `userEvent`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx
```

Expected: FAIL because the controls do not exist.

- [ ] **Step 3: Add icon controls**

In `frontend/src/pages/Live.tsx`, import icons:

```ts
import { Maximize2, Minimize2, PanelTopOpen, Square } from "lucide-react";
```

Add a compact toolbar in `ScenePortalCard` header:

```tsx
<div className="flex items-center gap-1">
  <button
    type="button"
    aria-label={`Use compact tile for ${camera.name}`}
    title="Compact tile"
    onClick={() => onTileSizeChange("compact")}
    className={tileToolButtonClass(tileSize === "compact")}
  >
    <Minimize2 className="size-4" />
  </button>
  <button
    type="button"
    aria-label={`Use standard tile for ${camera.name}`}
    title="Standard tile"
    onClick={() => onTileSizeChange("standard")}
    className={tileToolButtonClass(tileSize === "standard")}
  >
    <Square className="size-4" />
  </button>
  <button
    type="button"
    aria-label={`Use large tile for ${camera.name}`}
    title="Large tile"
    onClick={() => onTileSizeChange("large")}
    className={tileToolButtonClass(tileSize === "large")}
  >
    <PanelTopOpen className="size-4" />
  </button>
  <button
    type="button"
    aria-label={`Focus scene ${camera.name}`}
    title="Focus scene"
    onClick={onFocus}
    className={tileToolButtonClass(false)}
  >
    <Maximize2 className="size-4" />
  </button>
</div>
```

Add the helper:

```ts
function tileToolButtonClass(active: boolean): string {
  return [
    "inline-flex size-8 items-center justify-center rounded-[var(--vz-r-sm)] border transition",
    active
      ? "border-[color:var(--vz-hair-focus)] bg-[rgba(110,189,255,0.12)] text-[var(--vz-text-primary)]"
      : "border-[color:var(--vz-hair)] bg-white/[0.03] text-[var(--vz-text-secondary)] hover:border-[color:var(--vz-hair-focus)] hover:text-[var(--vz-text-primary)]",
  ].join(" ");
}
```

- [ ] **Step 4: Add focus mode classes and Escape close**

In `WorkspacePage`, add:

```ts
useEffect(() => {
  if (!focusedCameraId) return;
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      setFocusedCameraId(null);
    }
  };
  window.addEventListener("keydown", onKeyDown);
  return () => window.removeEventListener("keydown", onKeyDown);
}, [focusedCameraId]);
```

In `ScenePortalCard`, add a focus close button when `isFocused` is true. The article class should include:

```ts
isFocused
  ? "fixed inset-3 z-50 max-h-[calc(100vh-1.5rem)] overflow-y-auto rounded-[var(--vz-r-lg)] shadow-[var(--vz-elev-3)]"
  : tileSpanClass(tileSize)
```

Add a backdrop from `WorkspacePage` when `focusedCameraId` is not null:

```tsx
{focusedCameraId ? (
  <button
    type="button"
    aria-label="Close focused scene"
    className="fixed inset-0 z-40 bg-black/70"
    onClick={() => setFocusedCameraId(null)}
  />
) : null}
```

Ensure the focused article is `z-50` so it sits above the backdrop.

- [ ] **Step 5: Run Live tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx
```

Expected: PASS.

---

### Task 5: Redesign Live Signal Trend

**Files:**
- Modify: `frontend/src/components/live/TelemetryTerrain.tsx`
- Test: `frontend/src/components/live/TelemetryTerrain.test.tsx`

- [ ] **Step 1: Update terrain tests**

In `TelemetryTerrain.test.tsx`, update expected heading from `Telemetry terrain` to `Signal trend`.

Add assertions:

```ts
expect(within(terrain).getByText(/person active/i)).toBeInTheDocument();
expect(within(terrain).getByText(/car held/i)).toBeInTheDocument();

const paths = screen
  .getByLabelText(/person signal trend/i)
  .querySelectorAll("path");
expect(paths.length).toBeGreaterThanOrEqual(3);
```

Add a style assertion that the person line uses `#61e6a6` and car line uses `#62a6ff`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/TelemetryTerrain.test.tsx
```

Expected: FAIL because the component still renders the old heading and one primary path.

- [ ] **Step 3: Update component visuals**

In `TelemetryTerrain.tsx`:

- Use `const { buckets, latestValues, loading, error } = useLiveSparkline(cameraId);`
- Keep `rankedRows.slice(0, 3)`.
- Build a series per ranked row:

```ts
const trendRows = rankedRows.map((row) => ({
  row,
  series: buckets[row.className] ?? EMPTY_SERIES,
  latestValue: latestValues[row.className] ?? 0,
}));
```

Render heading:

```tsx
Signal trend
```

Use a taller SVG:

```tsx
<svg
  aria-label={`${primary?.className ?? "scene"} signal trend`}
  className="h-32 w-full overflow-visible lg:h-36"
  preserveAspectRatio="none"
  role="img"
  viewBox="0 0 100 72"
>
```

Normalize paths against a 72 px viewport:

```ts
function normalizeSeries(series: number[]): Array<{ x: number; y: number }> {
  const values = series.length > 0 ? series : EMPTY_SERIES;
  const max = Math.max(1, ...values);
  const divisor = Math.max(1, values.length - 1);

  return values.map((value, index) => ({
    x: (index / divisor) * 100,
    y: 62 - (Math.max(0, value) / max) * 50,
  }));
}
```

Render primary area plus all class lines:

```tsx
{primaryTrend ? <path d={buildAreaPath(primaryTrend.series)} fill={`url(#${terrainId})`} /> : null}
{trendRows.map(({ row, series }, index) => (
  <path
    key={row.className}
    d={buildLinePath(series)}
    fill="none"
    stroke={row.color.stroke}
    strokeLinecap="round"
    strokeLinejoin="round"
    strokeWidth={index === 0 ? "3" : "2"}
    opacity={index === 0 ? 1 : 0.72}
    vectorEffect="non-scaling-stroke"
  />
))}
```

- [ ] **Step 4: Avoid nested-card feel**

Change the panel class to use product tokens and a flatter inset surface:

```tsx
className="space-y-3 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[linear-gradient(180deg,rgba(8,17,31,0.9),rgba(4,9,17,0.88))] p-4"
```

- [ ] **Step 5: Run terrain tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/TelemetryTerrain.test.tsx
```

Expected: PASS.

---

### Task 6: Polish History Pattern Trend

**Files:**
- Modify: `frontend/src/components/history/history-trend-chart-options.ts`
- Modify: `frontend/src/components/history/HistoryTrendChart.tsx`
- Modify: `frontend/src/components/history/HistoryTrendPanel.tsx`
- Test: `frontend/src/components/history/HistoryTrendChart.test.tsx`

- [ ] **Step 1: Update ECharts option tests**

In `HistoryTrendChart.test.tsx`, add assertions for:

```ts
expect((option.legend as { textStyle: { color: string } }).textStyle.color).toBe(
  "#dbe7ff",
);
expect((seriesList.find((entry) => entry.name === "car") as { lineStyle: { width: number } }).lineStyle.width).toBe(3);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/history/HistoryTrendChart.test.tsx
```

Expected: FAIL until chart options are updated.

- [ ] **Step 3: Replace palette logic**

In `history-trend-chart-options.ts`, import:

```ts
import { colorForClass } from "@/lib/signal-colors";
```

Replace the `PALETTE` map setup with:

```ts
const paletteOf = (cls: string) => colorForClass(cls).stroke;
const palette = Array.from(
  new Set([...series.classNames, ...speedClasses].map(paletteOf)),
);
```

Return `color: palette`.

- [ ] **Step 4: Polish primary count series**

For count lines:

```ts
lineStyle: { width: 3 },
areaStyle: { opacity: 0.12 },
emphasis: { focus: "series" },
```

Keep `smooth: true` and `showSymbol: false`.

- [ ] **Step 5: Polish speed and threshold series**

For speed p50:

```ts
lineStyle: { width: 2.4, type: "solid" },
```

For speed p95:

```ts
lineStyle: { width: 1.8, type: "dashed" },
areaStyle: { opacity: 0.06 },
```

For threshold mark line:

```ts
lineStyle: { color: "#ff6f9d", type: "dashed", width: 1.5 },
```

- [ ] **Step 6: Polish chart chrome**

Use product-like dark grid and tooltip values:

```ts
splitLine: { lineStyle: { color: "rgba(206, 224, 255, 0.08)" } },
axisLine: { lineStyle: { color: "rgba(206, 224, 255, 0.16)" } },
axisLabel: { color: "#8497b3" },
tooltip: {
  trigger: "axis",
  axisPointer: { type: "cross", link: [{ xAxisIndex: "all" }] },
  backgroundColor: "rgba(3, 5, 10, 0.96)",
  borderColor: "rgba(110, 189, 255, 0.28)",
  textStyle: { color: "#eef4ff" },
},
```

- [ ] **Step 7: Increase chart heights**

In `HistoryTrendChart.tsx`, change:

```ts
const height = series.includeSpeed
  ? series.speedThreshold !== null && series.speedThreshold !== undefined
    ? "740px"
    : "640px"
  : "440px";
```

- [ ] **Step 8: Run history chart tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/history/HistoryTrendChart.test.tsx
```

Expected: PASS.

---

### Task 7: Run Focused Verification

**Files:**
- No source edits unless failures reveal test gaps.

- [ ] **Step 1: Run focused frontend test slice**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/lib/live-signal-stability.test.ts \
  src/lib/operational-health.test.ts \
  src/hooks/use-live-tile-layout.test.ts \
  src/components/operations/SceneStatusStrip.test.tsx \
  src/components/live/TelemetryTerrain.test.tsx \
  src/components/history/HistoryTrendChart.test.tsx \
  src/pages/Live.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run full frontend tests**

Run:

```bash
corepack pnpm --dir frontend test
```

Expected: PASS.

- [ ] **Step 3: Run lint if available**

Run:

```bash
make lint
```

Expected: PASS.

---

### Task 8: Manual Visual QA

**Files:**
- No source edits unless visual issues are found.

- [ ] **Step 1: Start the frontend**

Run:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 \
VITE_OIDC_AUTHORITY=http://127.0.0.1:8080/realms/argus-dev \
VITE_OIDC_CLIENT_ID=argus-frontend \
VITE_OIDC_REDIRECT_URI=http://127.0.0.1:3000/auth/callback \
VITE_OIDC_POST_LOGOUT_REDIRECT_URI=http://127.0.0.1:3000/signin \
corepack pnpm --dir frontend exec vite --host 127.0.0.1 --port 3000
```

Expected: Vite serves the frontend at `http://127.0.0.1:3000`. Use the already running local master API and auth services at ports `8000` and `8080`.

- [ ] **Step 2: Check Live at desktop width**

At roughly 1440 px width:

- Verify compact tiles can fit three across.
- Verify standard tiles fit two across.
- Verify large tiles span the content width.
- Verify focus mode opens above the grid and shows video plus graph.
- Verify Escape closes focus mode.
- Verify no horizontal scroll appears.

- [ ] **Step 3: Check Live at laptop/mobile widths**

At 768 px and 375 px widths:

- Verify tile controls do not overlap title/status badges.
- Verify focus mode remains scrollable.
- Verify graph remains visible in focus mode.
- Verify text fits in rendition controls and status chips.

- [ ] **Step 4: Check color consistency**

With a scene containing a person and a vehicle:

- `person` box is green.
- `person` live signal line is green.
- `person` History line is green.
- vehicle box is blue.
- vehicle live signal line is blue.
- vehicle History line is blue.

- [ ] **Step 5: Check worker copy**

During startup/restart:

- If telemetry is fresh but runtime report is absent, Live shows `Worker active`, green.
- Lifecycle diagnostics can still show `Runtime: not_reported`.
- `Worker awaiting report` does not appear on Live.

---

### Task 9: Commit Implementation

**Files:**
- All modified frontend files and tests.

- [ ] **Step 1: Review changed files**

Run:

```bash
git status --short
```

Expected: only files from this plan plus intentional test snapshots if any.

- [ ] **Step 2: Stage implementation**

Run:

```bash
git add \
  frontend/src/lib/signal-colors.ts \
  frontend/src/lib/live-signal-stability.ts \
  frontend/src/lib/operational-health.ts \
  frontend/src/hooks/use-live-tile-layout.ts \
  frontend/src/hooks/use-live-tile-layout.test.ts \
  frontend/src/components/operations/SceneStatusStrip.tsx \
  frontend/src/components/operations/SceneStatusStrip.test.tsx \
  frontend/src/components/operations/SceneIntelligenceMatrix.tsx \
  frontend/src/components/live/TelemetryTerrain.tsx \
  frontend/src/components/live/TelemetryTerrain.test.tsx \
  frontend/src/components/history/history-trend-chart-options.ts \
  frontend/src/components/history/HistoryTrendChart.tsx \
  frontend/src/components/history/HistoryTrendChart.test.tsx \
  frontend/src/components/history/HistoryTrendPanel.tsx \
  frontend/src/pages/Live.tsx \
  frontend/src/pages/Live.test.tsx
```

- [ ] **Step 3: Commit**

Run:

```bash
git commit -m "feat(live): improve scene tile focus and signal graphs"
```

Expected: commit succeeds after verification passes.
