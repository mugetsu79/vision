# Live Signal Terrain And Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the Live scene card, add class-colored tracking boxes, replace the thin sparkline with Telemetry Terrain, and make the legends above the video calmer and clearer.

**Architecture:** Add a pure live-signal stability utility and a small hook that converts raw latest telemetry frames into live/held signal state. Feed that state into `TelemetryCanvas`, `DynamicStats`, a new `TelemetryTerrain` component, and a redesigned `SceneStatusStrip`. Keep the work frontend-only and do not change backend telemetry contracts.

**Tech Stack:** React 19, Vite 6, TypeScript 5.7, Tailwind v4, Zustand telemetry store, Vitest, React Testing Library, Playwright.

**Spec source:** `/Users/yann.moren/vision/docs/superpowers/specs/2026-05-09-live-signal-terrain-and-stability-design.md`

---

## Execution Protocol

The user prefers one implementation task at a time. Execute one task, run its verification, commit it, report the result, then wait for the next `go`.

Do not stage unrelated untracked scratch files. Current known unrelated untracked files include `.claude/`, `.codex/`, `.superpowers/brainstorm/*`, screenshot files, `camera-capture.md`, `codex-review-findings.md`, `docs/brand/2d_logo.png`, `docs/brand/3d_logo.png`, and `docs/strategy/`.

## Pre-flight

```bash
cd /Users/yann.moren/vision
git status --short
git rev-parse --abbrev-ref HEAD
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Expected:

- branch is `codex/omnisight-ui-spec-implementation` unless the user starts a new branch first
- frontend tests, lint, and build pass or show only the already-known warnings
- no unrelated scratch files are staged

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `frontend/src/lib/live-signal-stability.ts` | create | pure class colors, live/held track state, stabilized counts |
| `frontend/src/lib/live-signal-stability.test.ts` | create | stability and palette tests |
| `frontend/src/hooks/use-stable-signal-frame.ts` | create | per-scene hook over time-based live/held state |
| `frontend/src/hooks/use-stable-signal-frame.test.tsx` | create | hook timer tests |
| `frontend/src/components/live/TelemetryCanvas.tsx` | modify | draw colored live/held boxes |
| `frontend/src/components/live/TelemetryCanvas.test.tsx` | modify | canvas color and held-state tests |
| `frontend/src/components/live/TelemetryTerrain.tsx` | create | gradient terrain under video |
| `frontend/src/components/live/TelemetryTerrain.test.tsx` | create | terrain rendering tests |
| `frontend/src/components/live/DynamicStats.tsx` | modify | stable right-rail rows with held state |
| `frontend/src/components/live/DynamicStats.test.tsx` | create | right-rail stability tests |
| `frontend/src/components/operations/SceneStatusStrip.tsx` | modify | clearer scene-state bar above video |
| `frontend/src/components/operations/SceneStatusStrip.test.tsx` | modify | revised labels and tones |
| `frontend/src/pages/Live.tsx` | modify | use stable signal snapshots and Telemetry Terrain |
| `frontend/src/pages/Live.test.tsx` | modify | integration coverage for anti-flap and terrain |
| `frontend/CHANGELOG.md` | modify | document Live signal polish |

---

## Task 1: Shared Live Signal Stability Model

**Files:**
- Create: `frontend/src/lib/live-signal-stability.ts`
- Create: `frontend/src/lib/live-signal-stability.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/lib/live-signal-stability.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import {
  DEFAULT_SIGNAL_HOLD_MS,
  colorForClass,
  deriveSignalCounts,
  trackKey,
  updateSignalTracks,
} from "@/lib/live-signal-stability";
import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];
type TelemetryTrack = components["schemas"]["TelemetryTrack"];

function track(
  className: string,
  trackId: number,
  bbox: TelemetryTrack["bbox"] = { x1: 10, y1: 20, x2: 100, y2: 180 },
): TelemetryTrack {
  return {
    class_name: className,
    confidence: 0.91,
    bbox,
    track_id: trackId,
    speed_kph: null,
    direction_deg: null,
    zone_id: null,
    attributes: {},
  };
}

function frame(tracks: TelemetryTrack[]): TelemetryFrame {
  return {
    camera_id: "11111111-1111-1111-1111-111111111111",
    ts: "2026-05-09T08:00:00Z",
    profile: "central-gpu",
    stream_mode: "annotated-whip",
    counts: tracks.reduce<Record<string, number>>((counts, item) => {
      counts[item.class_name] = (counts[item.class_name] ?? 0) + 1;
      return counts;
    }, {}),
    tracks,
  };
}

describe("live signal stability", () => {
  test("creates stable track keys from class and track id", () => {
    expect(trackKey(track("person", 12))).toBe("person:12");
  });

  test("maps common classes to semantic colors", () => {
    expect(colorForClass("person").family).toBe("human");
    expect(colorForClass("car").family).toBe("vehicle");
    expect(colorForClass("hard_hat").family).toBe("safety");
    expect(colorForClass("forklift").family).toBe("other");
  });

  test("keeps a missing track as held within the hold window", () => {
    const first = updateSignalTracks({
      previous: [],
      frame: frame([track("person", 12)]),
      activeClasses: null,
      nowMs: 1_000,
    });

    const second = updateSignalTracks({
      previous: first,
      frame: frame([]),
      activeClasses: null,
      nowMs: 1_000 + DEFAULT_SIGNAL_HOLD_MS - 1,
    });

    expect(second).toHaveLength(1);
    expect(second[0]).toMatchObject({
      key: "person:12",
      state: "held",
      ageMs: DEFAULT_SIGNAL_HOLD_MS - 1,
    });
  });

  test("expires held tracks after the hold window", () => {
    const first = updateSignalTracks({
      previous: [],
      frame: frame([track("person", 12)]),
      activeClasses: null,
      nowMs: 1_000,
    });

    const expired = updateSignalTracks({
      previous: first,
      frame: frame([]),
      activeClasses: null,
      nowMs: 1_000 + DEFAULT_SIGNAL_HOLD_MS + 1,
    });

    expect(expired).toEqual([]);
  });

  test("filters live and held tracks by active classes", () => {
    const first = updateSignalTracks({
      previous: [],
      frame: frame([track("person", 12), track("car", 7)]),
      activeClasses: ["person"],
      nowMs: 1_000,
    });

    expect(first.map((item) => item.track.class_name)).toEqual(["person"]);
  });

  test("derives live held and total counts by class", () => {
    const first = updateSignalTracks({
      previous: [],
      frame: frame([track("person", 12), track("car", 7)]),
      activeClasses: null,
      nowMs: 1_000,
    });
    const second = updateSignalTracks({
      previous: first,
      frame: frame([track("car", 7)]),
      activeClasses: null,
      nowMs: 1_500,
    });

    const counts = deriveSignalCounts(second);

    expect(counts.liveTotal).toBe(1);
    expect(counts.heldTotal).toBe(1);
    expect(counts.rows.map((row) => [row.className, row.liveCount, row.heldCount])).toEqual([
      ["car", 1, 0],
      ["person", 0, 1],
    ]);
  });
});
```

- [ ] **Step 2: Run the failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/live-signal-stability.test.ts
```

Expected: FAIL because `@/lib/live-signal-stability` does not exist.

- [ ] **Step 3: Implement the utility**

Create `frontend/src/lib/live-signal-stability.ts`:

```ts
import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];
type TelemetryTrack = components["schemas"]["TelemetryTrack"];

export const DEFAULT_SIGNAL_HOLD_MS = 1_200;

export type SignalState = "live" | "held";
export type SignalColorFamily = "human" | "vehicle" | "safety" | "alert" | "other";

export type SignalColor = {
  family: SignalColorFamily;
  stroke: string;
  fill: string;
  text: string;
};

export type SignalTrack = {
  key: string;
  track: TelemetryTrack;
  color: SignalColor;
  state: SignalState;
  firstSeenMs: number;
  lastSeenMs: number;
  ageMs: number;
};

export type SignalCountRow = {
  className: string;
  color: SignalColor;
  liveCount: number;
  heldCount: number;
  totalCount: number;
  state: SignalState;
};

export type SignalCounts = {
  liveTotal: number;
  heldTotal: number;
  total: number;
  rows: SignalCountRow[];
};

const HUMAN_CLASSES = new Set(["person", "worker", "hi_vis_worker"]);
const VEHICLE_CLASSES = new Set(["car", "truck", "bus", "motorcycle", "bicycle", "forklift"]);
const SAFETY_CLASSES = new Set(["helmet", "vest", "ppe", "hard_hat"]);
const ALERT_CLASSES = new Set(["violation", "alert", "intrusion"]);

const FALLBACK_COLORS: SignalColor[] = [
  { family: "other", stroke: "#4dd7ff", fill: "rgba(77, 215, 255, 0.12)", text: "#d9f7ff" },
  { family: "other", stroke: "#a98bff", fill: "rgba(169, 139, 255, 0.13)", text: "#eee8ff" },
  { family: "other", stroke: "#f7c56b", fill: "rgba(247, 197, 107, 0.12)", text: "#fff1ca" },
];

export function trackKey(track: Pick<TelemetryTrack, "class_name" | "track_id">): string {
  return `${track.class_name}:${track.track_id}`;
}

export function colorForClass(className: string): SignalColor {
  const normalized = className.toLowerCase();
  if (HUMAN_CLASSES.has(normalized)) {
    return { family: "human", stroke: "#61e6a6", fill: "rgba(97, 230, 166, 0.12)", text: "#e8fff4" };
  }
  if (VEHICLE_CLASSES.has(normalized)) {
    return { family: "vehicle", stroke: "#62a6ff", fill: "rgba(98, 166, 255, 0.12)", text: "#e9f3ff" };
  }
  if (SAFETY_CLASSES.has(normalized)) {
    return { family: "safety", stroke: "#f7c56b", fill: "rgba(247, 197, 107, 0.13)", text: "#fff2cf" };
  }
  if (ALERT_CLASSES.has(normalized)) {
    return { family: "alert", stroke: "#ff6f9d", fill: "rgba(255, 111, 157, 0.13)", text: "#ffe7ef" };
  }
  return FALLBACK_COLORS[hashClassName(normalized) % FALLBACK_COLORS.length];
}

export function updateSignalTracks({
  previous,
  frame,
  activeClasses,
  nowMs,
  holdMs = DEFAULT_SIGNAL_HOLD_MS,
}: {
  previous: SignalTrack[];
  frame: TelemetryFrame | null | undefined;
  activeClasses: string[] | null;
  nowMs: number;
  holdMs?: number;
}): SignalTrack[] {
  const allowed = activeClasses && activeClasses.length > 0 ? new Set(activeClasses) : null;
  const nextByKey = new Map<string, SignalTrack>();
  const previousByKey = new Map(previous.map((item) => [item.key, item]));

  for (const track of frame?.tracks ?? []) {
    if (allowed && !allowed.has(track.class_name)) {
      continue;
    }
    const key = trackKey(track);
    const existing = previousByKey.get(key);
    nextByKey.set(key, {
      key,
      track,
      color: colorForClass(track.class_name),
      state: "live",
      firstSeenMs: existing?.firstSeenMs ?? nowMs,
      lastSeenMs: nowMs,
      ageMs: 0,
    });
  }

  for (const item of previous) {
    if (nextByKey.has(item.key)) {
      continue;
    }
    if (allowed && !allowed.has(item.track.class_name)) {
      continue;
    }
    const ageMs = nowMs - item.lastSeenMs;
    if (ageMs <= holdMs) {
      nextByKey.set(item.key, {
        ...item,
        state: "held",
        ageMs,
      });
    }
  }

  return Array.from(nextByKey.values()).sort(compareSignalTracks);
}

export function deriveSignalCounts(tracks: SignalTrack[]): SignalCounts {
  const rowsByClass = new Map<string, SignalCountRow>();
  for (const signal of tracks) {
    const className = signal.track.class_name;
    const row =
      rowsByClass.get(className) ??
      {
        className,
        color: signal.color,
        liveCount: 0,
        heldCount: 0,
        totalCount: 0,
        state: "held" as SignalState,
      };
    if (signal.state === "live") {
      row.liveCount += 1;
    } else {
      row.heldCount += 1;
    }
    row.totalCount += 1;
    row.state = row.liveCount > 0 ? "live" : "held";
    rowsByClass.set(className, row);
  }

  const rows = Array.from(rowsByClass.values()).sort(
    (left, right) =>
      right.liveCount - left.liveCount ||
      right.totalCount - left.totalCount ||
      left.className.localeCompare(right.className),
  );

  return {
    liveTotal: rows.reduce((total, row) => total + row.liveCount, 0),
    heldTotal: rows.reduce((total, row) => total + row.heldCount, 0),
    total: rows.reduce((total, row) => total + row.totalCount, 0),
    rows,
  };
}

function compareSignalTracks(left: SignalTrack, right: SignalTrack): number {
  if (left.state !== right.state) {
    return left.state === "live" ? -1 : 1;
  }
  return left.track.class_name.localeCompare(right.track.class_name) || left.track.track_id - right.track.track_id;
}

function hashClassName(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}
```

- [ ] **Step 4: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/live-signal-stability.test.ts
```

Expected: PASS.

- [ ] **Step 5: Run lint**

```bash
corepack pnpm --dir frontend lint
```

Expected: PASS with only known warnings.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/live-signal-stability.ts frontend/src/lib/live-signal-stability.test.ts
git commit -m "feat(live): derive stable signal state"
```

---

## Task 2: Stable Signal Hook

**Files:**
- Create: `frontend/src/hooks/use-stable-signal-frame.ts`
- Create: `frontend/src/hooks/use-stable-signal-frame.test.tsx`

- [ ] **Step 1: Write the failing hook tests**

Create `frontend/src/hooks/use-stable-signal-frame.test.tsx`:

```tsx
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { useStableSignalFrame } from "@/hooks/use-stable-signal-frame";
import type { components } from "@/lib/api.generated";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];

function frame(tracks: TelemetryFrame["tracks"]): TelemetryFrame {
  return {
    camera_id: "11111111-1111-1111-1111-111111111111",
    ts: new Date().toISOString(),
    profile: "central-gpu",
    stream_mode: "annotated-whip",
    counts: {},
    tracks,
  };
}

const person = {
  class_name: "person",
  confidence: 0.91,
  bbox: { x1: 10, y1: 20, x2: 100, y2: 180 },
  track_id: 12,
  speed_kph: null,
  direction_deg: null,
  zone_id: null,
  attributes: {},
};

describe("useStableSignalFrame", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("returns live tracks from the latest frame", () => {
    const view = renderHook(({ latest }) => useStableSignalFrame(latest, null), {
      initialProps: { latest: frame([person]) },
    });

    expect(view.result.current.counts.liveTotal).toBe(1);
    expect(view.result.current.tracks[0].state).toBe("live");
  });

  test("keeps missing tracks held until the hold window expires", () => {
    const view = renderHook(({ latest }) => useStableSignalFrame(latest, null), {
      initialProps: { latest: frame([person]) },
    });

    act(() => {
      vi.setSystemTime(1_500);
      view.rerender({ latest: frame([]) });
    });

    expect(view.result.current.counts.liveTotal).toBe(0);
    expect(view.result.current.counts.heldTotal).toBe(1);
    expect(view.result.current.tracks[0].state).toBe("held");

    act(() => {
      vi.setSystemTime(2_400);
      vi.advanceTimersByTime(900);
    });

    expect(view.result.current.counts.total).toBe(0);
  });
});
```

- [ ] **Step 2: Run the failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/hooks/use-stable-signal-frame.test.tsx
```

Expected: FAIL because the hook does not exist.

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/use-stable-signal-frame.ts`:

```ts
import { useEffect, useMemo, useState } from "react";

import type { components } from "@/lib/api.generated";
import {
  DEFAULT_SIGNAL_HOLD_MS,
  deriveSignalCounts,
  updateSignalTracks,
  type SignalCounts,
  type SignalTrack,
} from "@/lib/live-signal-stability";

type TelemetryFrame = components["schemas"]["TelemetryFrame"];

const HELD_REFRESH_MS = 200;

export type StableSignalSnapshot = {
  tracks: SignalTrack[];
  counts: SignalCounts;
  latestFrame: TelemetryFrame | null | undefined;
};

export function useStableSignalFrame(
  frame: TelemetryFrame | null | undefined,
  activeClasses: string[] | null,
  holdMs = DEFAULT_SIGNAL_HOLD_MS,
): StableSignalSnapshot {
  const [tracks, setTracks] = useState<SignalTrack[]>([]);

  useEffect(() => {
    setTracks((current) =>
      updateSignalTracks({
        previous: current,
        frame,
        activeClasses,
        nowMs: Date.now(),
        holdMs,
      }),
    );
  }, [activeClasses, frame, holdMs]);

  useEffect(() => {
    if (tracks.every((track) => track.state === "live")) {
      return;
    }

    const interval = window.setInterval(() => {
      setTracks((current) =>
        updateSignalTracks({
          previous: current,
          frame: null,
          activeClasses,
          nowMs: Date.now(),
          holdMs,
        }),
      );
    }, HELD_REFRESH_MS);

    return () => {
      window.clearInterval(interval);
    };
  }, [activeClasses, holdMs, tracks]);

  const counts = useMemo(() => deriveSignalCounts(tracks), [tracks]);

  return {
    tracks,
    counts,
    latestFrame: frame,
  };
}
```

- [ ] **Step 4: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/hooks/use-stable-signal-frame.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Run related utility tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/live-signal-stability.test.ts src/hooks/use-stable-signal-frame.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/use-stable-signal-frame.ts frontend/src/hooks/use-stable-signal-frame.test.tsx
git commit -m "feat(live): hold recent signal tracks"
```

---

## Task 3: Class-Colored Telemetry Overlay

**Files:**
- Modify: `frontend/src/components/live/TelemetryCanvas.tsx`
- Modify: `frontend/src/components/live/TelemetryCanvas.test.tsx`

- [ ] **Step 1: Update failing canvas tests**

Extend `frontend/src/components/live/TelemetryCanvas.test.tsx` so the first test passes `tracks` and expects class colors plus held styling:

```tsx
import { colorForClass, type SignalTrack } from "@/lib/live-signal-stability";
```

Add helper:

```ts
function signalTrack(
  track: TelemetryFrame["tracks"][number],
  state: "live" | "held" = "live",
): SignalTrack {
  return {
    key: `${track.class_name}:${track.track_id}`,
    track,
    color: colorForClass(track.class_name),
    state,
    firstSeenMs: 1_000,
    lastSeenMs: 1_000,
    ageMs: state === "held" ? 800 : 0,
  };
}
```

Add assertions:

```ts
expect(strokeRectMock).toHaveBeenCalledTimes(2);
expect(setLineDashMock).toHaveBeenCalledWith([6, 5]);
expect(fillTextMock.mock.calls.some(([label]) => String(label).includes("last seen"))).toBe(true);
```

Add mocked canvas methods:

```ts
const setLineDashMock = vi.fn();
const strokeMock = vi.fn();
```

- [ ] **Step 2: Run failing canvas tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/TelemetryCanvas.test.tsx
```

Expected: FAIL because `TelemetryCanvas` does not accept stable tracks or draw held styling yet.

- [ ] **Step 3: Update `TelemetryCanvas` props and drawing**

In `frontend/src/components/live/TelemetryCanvas.tsx`, import:

```ts
import { colorForClass, type SignalTrack } from "@/lib/live-signal-stability";
```

Change props:

```ts
export function TelemetryCanvas({
  frame,
  activeClasses,
  tracks,
}: {
  frame: TelemetryFrame | null | undefined;
  activeClasses: string[] | null;
  tracks?: SignalTrack[];
}) {
```

Add refs:

```ts
const tracksRef = useRef<SignalTrack[] | undefined>(tracks);
tracksRef.current = tracks;
```

Replace `visibleTracks` derivation:

```ts
const visibleTracks =
  tracksRef.current ??
  filterTracks(frameRef.current, activeClassesRef.current).map((track) => ({
    key: `${track.class_name}:${track.track_id}`,
    track,
    color: colorForClass(track.class_name),
    state: "live" as const,
    firstSeenMs: 0,
    lastSeenMs: 0,
    ageMs: 0,
  }));
```

Update coordinate reads from `track.bbox` to `signal.track.bbox`.

Before drawing each box:

```ts
const color = signal.color;
context.strokeStyle = color.stroke;
context.fillStyle = color.text;
context.globalAlpha = signal.state === "held" ? 0.55 : 1;
context.setLineDash?.(signal.state === "held" ? [6, 5] : []);
```

Use label:

```ts
const label = [
  `${track.class_name} #${track.track_id}`,
  signal.state === "held" ? "last seen" : null,
  track.speed_kph ? `${Math.round(track.speed_kph)} km/h` : null,
]
  .filter(Boolean)
  .join(" ");
```

After the loop reset:

```ts
context.globalAlpha = 1;
context.setLineDash?.([]);
```

- [ ] **Step 4: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/TelemetryCanvas.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/live/TelemetryCanvas.tsx frontend/src/components/live/TelemetryCanvas.test.tsx
git commit -m "feat(live): color stable telemetry boxes"
```

---

## Task 4: Telemetry Terrain Component

**Files:**
- Create: `frontend/src/components/live/TelemetryTerrain.tsx`
- Create: `frontend/src/components/live/TelemetryTerrain.test.tsx`

- [ ] **Step 1: Write the failing terrain tests**

Create `frontend/src/components/live/TelemetryTerrain.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import type { SignalCountRow } from "@/lib/live-signal-stability";
import { colorForClass } from "@/lib/live-signal-stability";

vi.mock("@/hooks/use-live-sparkline", () => ({
  useLiveSparkline: () => ({
    buckets: {
      person: [0, 1, 2, 4, 3, 1],
      car: [0, 0, 1, 1, 0, 0],
    },
    latestValues: { person: 1, car: 0 },
    loading: false,
    error: null,
  }),
}));

import { TelemetryTerrain } from "@/components/live/TelemetryTerrain";

const rows: SignalCountRow[] = [
  {
    className: "person",
    color: colorForClass("person"),
    liveCount: 1,
    heldCount: 0,
    totalCount: 1,
    state: "live",
  },
  {
    className: "car",
    color: colorForClass("car"),
    liveCount: 0,
    heldCount: 1,
    totalCount: 1,
    state: "held",
  },
];

describe("TelemetryTerrain", () => {
  test("renders a gradient terrain and stable class legend", () => {
    render(
      <TelemetryTerrain
        cameraId="camera-1"
        cameraName="North Gate"
        activeClasses={["person", "car"]}
        signalRows={rows}
      />,
    );

    const terrain = screen.getByTestId("telemetry-terrain");
    expect(terrain).toHaveAccessibleName(/north gate telemetry terrain/i);
    expect(within(terrain).getByText(/telemetry terrain/i)).toBeInTheDocument();
    expect(within(terrain).getByText(/person active/i)).toBeInTheDocument();
    expect(within(terrain).getByText(/car held/i)).toBeInTheDocument();
    expect(within(terrain).getByLabelText(/person signal terrain/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run failing terrain tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/TelemetryTerrain.test.tsx
```

Expected: FAIL because `TelemetryTerrain` does not exist.

- [ ] **Step 3: Implement `TelemetryTerrain`**

Create `frontend/src/components/live/TelemetryTerrain.tsx`:

```tsx
import { useMemo } from "react";

import { useLiveSparkline } from "@/hooks/use-live-sparkline";
import type { SignalCountRow } from "@/lib/live-signal-stability";

type TelemetryTerrainProps = {
  cameraId: string;
  cameraName: string;
  activeClasses: string[];
  signalRows: SignalCountRow[];
};

export function TelemetryTerrain({
  cameraId,
  cameraName,
  activeClasses,
  signalRows,
}: TelemetryTerrainProps) {
  const { buckets, loading, error } = useLiveSparkline(cameraId);
  const rankedRows = useMemo(
    () =>
      signalRows.length > 0
        ? signalRows.slice(0, 3)
        : activeClasses.slice(0, 3).map((className) => ({
            className,
            color: {
              family: "other" as const,
              stroke: "#62a6ff",
              fill: "rgba(98, 166, 255, 0.12)",
              text: "#e9f3ff",
            },
            liveCount: 0,
            heldCount: 0,
            totalCount: 0,
            state: "held" as const,
          })),
    [activeClasses, signalRows],
  );
  const primary = rankedRows[0];
  const series = primary ? buckets[primary.className] ?? [0, 0, 0, 0, 0, 0] : [0, 0, 0, 0, 0, 0];
  const terrainId = `terrain-${cameraId.replace(/[^a-zA-Z0-9]/g, "")}`;

  if (loading) {
    return <div className="h-24 animate-pulse rounded-[0.9rem] bg-white/[0.04]" />;
  }
  if (error) {
    return <p className="text-xs text-[#f0b7c1]">Telemetry terrain unavailable: {error.message}</p>;
  }

  return (
    <section
      aria-label={`${cameraName} telemetry terrain`}
      data-testid="telemetry-terrain"
      className="space-y-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
          Telemetry terrain
        </p>
        <div className="flex flex-wrap gap-2">
          {rankedRows.map((row) => (
            <span
              key={row.className}
              className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] font-semibold text-[var(--vz-text-secondary)]"
            >
              <span style={{ color: row.color.stroke }}>●</span>{" "}
              {row.className} {row.state === "live" ? "active" : "held"} · {row.totalCount}
            </span>
          ))}
        </div>
      </div>
      <svg
        aria-label={`${primary?.className ?? "scene"} signal terrain`}
        viewBox="0 0 100 48"
        preserveAspectRatio="none"
        className="h-20 w-full rounded-[0.9rem] border border-white/8 bg-white/[0.03]"
      >
        <defs>
          <linearGradient id={terrainId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor={primary?.color.stroke ?? "#62a6ff"} stopOpacity="0.72" />
            <stop offset="1" stopColor={primary?.color.stroke ?? "#62a6ff"} stopOpacity="0.05" />
          </linearGradient>
        </defs>
        <path d={buildAreaPath(series)} fill={`url(#${terrainId})`} />
        <path
          d={buildLinePath(series)}
          fill="none"
          stroke={primary?.color.stroke ?? "#62a6ff"}
          strokeWidth="2.4"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </section>
  );
}

function buildLinePath(series: number[]): string {
  const max = Math.max(1, ...series);
  return series
    .map((value, index) => {
      const x = series.length <= 1 ? 100 : (index / (series.length - 1)) * 100;
      const y = 42 - (value / max) * 32;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function buildAreaPath(series: number[]): string {
  return `${buildLinePath(series)} L 100 48 L 0 48 Z`;
}
```

- [ ] **Step 4: Run terrain tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/live/TelemetryTerrain.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/live/TelemetryTerrain.tsx frontend/src/components/live/TelemetryTerrain.test.tsx
git commit -m "feat(live): add telemetry terrain surface"
```

---

## Task 5: Calmer Live State Bar And Right Rail

**Files:**
- Modify: `frontend/src/components/operations/SceneStatusStrip.tsx`
- Modify: `frontend/src/components/operations/SceneStatusStrip.test.tsx`
- Modify: `frontend/src/components/live/DynamicStats.tsx`
- Create: `frontend/src/components/live/DynamicStats.test.tsx`

- [ ] **Step 1: Update SceneStatusStrip tests**

Replace expectations in `frontend/src/components/operations/SceneStatusStrip.test.tsx` with:

```tsx
expect(screen.getByText(/telemetry stale/i)).toBeInTheDocument();
expect(screen.getByText(/central scene/i)).toBeInTheDocument();
expect(screen.getByText(/worker running/i)).toBeInTheDocument();
expect(screen.getByText(/processed stream live/i)).toBeInTheDocument();
expect(screen.queryByText(/direct stream unavailable/i)).not.toBeInTheDocument();
```

Add a second row where `delivery.label` is `Direct stream unavailable` and assert:

```tsx
expect(screen.getByText(/native passthrough gated/i)).toBeInTheDocument();
```

- [ ] **Step 2: Write DynamicStats tests**

Create `frontend/src/components/live/DynamicStats.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { DynamicStats } from "@/components/live/DynamicStats";
import { colorForClass, type SignalCountRow } from "@/lib/live-signal-stability";

const rows: SignalCountRow[] = [
  {
    className: "person",
    color: colorForClass("person"),
    liveCount: 1,
    heldCount: 0,
    totalCount: 1,
    state: "live",
  },
  {
    className: "car",
    color: colorForClass("car"),
    liveCount: 0,
    heldCount: 1,
    totalCount: 1,
    state: "held",
  },
];

describe("DynamicStats", () => {
  test("renders live and held signal rows without dropping held rows", () => {
    render(<DynamicStats signalRows={rows} />);

    const rail = screen.getByRole("heading", { name: /live signals in view/i }).closest("section");
    expect(rail).not.toBeNull();
    expect(within(rail as HTMLElement).getByText("person")).toBeInTheDocument();
    expect(within(rail as HTMLElement).getByText("car")).toBeInTheDocument();
    expect(within(rail as HTMLElement).getByText(/held/i)).toBeInTheDocument();
  });

  test("shows the empty state only when no rows are present", () => {
    render(<DynamicStats signalRows={[]} />);

    expect(screen.getByText(/no live signals/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/SceneStatusStrip.test.tsx src/components/live/DynamicStats.test.tsx
```

Expected: FAIL because props/rendering have not changed.

- [ ] **Step 4: Update SceneStatusStrip**

In `frontend/src/components/operations/SceneStatusStrip.tsx`, keep the component name but render clearer groups:

```tsx
export function SceneStatusStrip({ row }: SceneStatusStripProps) {
  const deliveryCopy =
    row.delivery.label === "Direct stream unavailable"
      ? "Native passthrough gated"
      : "Processed stream live";

  return (
    <div
      role="group"
      aria-label={`${row.cameraName} operational status`}
      className="flex flex-wrap items-center gap-2 text-xs"
    >
      <StatusToneBadge tone={healthToTone(row.telemetry.health)}>
        {row.telemetry.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.delivery.health)}>
        {deliveryCopy}
      </StatusToneBadge>
      <StatusToneBadge tone="muted">
        {row.processingMode} scene
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.worker.health)}>
        {row.worker.label === "Worker not reported" ? "Worker awaiting report" : row.worker.label}
      </StatusToneBadge>
      {row.delivery.detail ? (
        <span className="text-xs text-[var(--vz-text-muted)]">
          {deliveryCopy}: {row.delivery.detail}
        </span>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 5: Update DynamicStats**

Change props in `frontend/src/components/live/DynamicStats.tsx`:

```ts
import type { SignalCountRow } from "@/lib/live-signal-stability";

export function DynamicStats({
  counts,
  signalRows,
}: {
  counts?: Record<string, number>;
  signalRows?: SignalCountRow[];
}) {
```

Derive entries:

```ts
const entries =
  signalRows ??
  Object.entries(counts ?? {})
    .filter(([, count]) => count > 0)
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([className, count]) => ({
      className,
      color: null,
      liveCount: count,
      heldCount: 0,
      totalCount: count,
      state: "live" as const,
    }));
```

Render each row with class name, total count, and `held` label when applicable. Keep existing empty copy for the no-row case.

- [ ] **Step 6: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/SceneStatusStrip.test.tsx src/components/live/DynamicStats.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/operations/SceneStatusStrip.tsx frontend/src/components/operations/SceneStatusStrip.test.tsx frontend/src/components/live/DynamicStats.tsx frontend/src/components/live/DynamicStats.test.tsx
git commit -m "feat(live): clarify scene state signals"
```

---

## Task 6: Live Page Integration

**Files:**
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`
- Modify: `frontend/CHANGELOG.md`

- [ ] **Step 1: Update Live page tests**

In `frontend/src/pages/Live.test.tsx`, update the mocks:

```ts
vi.mock("@/components/live/TelemetryTerrain", () => ({
  TelemetryTerrain: ({ cameraName }: { cameraName: string }) => (
    <div data-testid={`terrain-${cameraName}`}>Telemetry terrain for {cameraName}</div>
  ),
}));
```

Remove the `LiveSparkline` mock or leave it unused if needed by other imports.

Add a test case after a live frame:

```ts
act(() => {
  FakeWebSocket.instances[0]?.emit({
    camera_id: "11111111-1111-1111-1111-111111111111",
    ts: new Date().toISOString(),
    profile: "central-gpu",
    stream_mode: "annotated-whip",
    counts: { person: 1 },
    tracks: [
      {
        class_name: "person",
        confidence: 0.94,
        bbox: { x1: 100, y1: 120, x2: 260, y2: 330 },
        track_id: 12,
        speed_kph: null,
        direction_deg: null,
        zone_id: null,
        attributes: {},
      },
    ],
  });
});

await waitFor(() => expect(screen.getByText(/1 visible now/i)).toBeInTheDocument());

act(() => {
  FakeWebSocket.instances[0]?.emit({
    camera_id: "11111111-1111-1111-1111-111111111111",
    ts: new Date().toISOString(),
    profile: "central-gpu",
    stream_mode: "annotated-whip",
    counts: {},
    tracks: [],
  });
});

await waitFor(() => expect(screen.getByText(/1 signal held/i)).toBeInTheDocument());
expect(screen.queryByText(/0 visible now/i)).not.toBeInTheDocument();
```

Add an assertion:

```ts
expect(screen.getByTestId("terrain-North Gate")).toBeInTheDocument();
```

- [ ] **Step 2: Run failing Live tests**

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx
```

Expected: FAIL because Live still uses raw frames and `LiveSparkline`.

- [ ] **Step 3: Integrate stable signal hook in `Live.tsx`**

Update the existing React import so it includes the new hooks, then add the component and type imports:

```tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import { TelemetryTerrain } from "@/components/live/TelemetryTerrain";
import { useStableSignalFrame } from "@/hooks/use-stable-signal-frame";
import type { SceneHealthRow } from "@/lib/operational-health";
import type { SignalCountRow } from "@/lib/live-signal-stability";
```

Extract the existing `<article>` returned inside `cameras.map(...)` into a `ScenePortalCard` component in the same file. Preserve the existing markup and classes, then make the exact substitutions shown below so hook usage remains valid.

Add this component signature:

```tsx
function ScenePortalCard({
  camera,
  frame,
  classFilter,
  sceneHealth,
  onSignalRowsChange,
}: {
  camera: CameraResponse;
  frame: TelemetryFrame | undefined;
  classFilter: string[] | null;
  sceneHealth: SceneHealthRow | undefined;
  onSignalRowsChange: (cameraId: string, rows: SignalCountRow[]) => void;
}) {
}
```

Move the existing `<article ...>` markup from the current `cameras.map(...)` body into this component's return value. Then insert this stable signal setup at the top of the component body before the JSX return:

```tsx
  const stableSignal = useStableSignalFrame(frame, classFilter);
  const visibleCopy =
    stableSignal.counts.liveTotal > 0
      ? `${stableSignal.counts.liveTotal} visible now`
      : stableSignal.counts.heldTotal > 0
        ? `${stableSignal.counts.heldTotal} signal held`
        : "0 visible now";

  const heartbeatStatus = getHeartbeatStatus(frame);
  const deliveryProfileLabel = formatDeliveryProfile(camera);
```

Inside the moved article, use the `heartbeatStatus`, `deliveryProfileLabel`, `stableSignal`, and `visibleCopy` values from the new component. Apply these exact substitutions inside the moved article:

```tsx
<TelemetryCanvas
  frame={frame}
  activeClasses={classFilter}
  tracks={stableSignal.tracks}
/>
```

Replace visible count:

```tsx
<p className="mt-1 text-sm text-[#dce6f7]">{visibleCopy}</p>
```

Replace `LiveSparkline`:

```tsx
<TelemetryTerrain
  cameraId={camera.id}
  cameraName={camera.name}
  activeClasses={camera.active_classes ?? []}
  signalRows={stableSignal.counts.rows}
/>
```

- [ ] **Step 4: Use stable rows in the right rail**

Because hooks cannot run in an arbitrary loop only for the rail, derive rail rows from child card state by lifting a small map into `LivePage`.

Add state:

```tsx
const [signalRowsByCamera, setSignalRowsByCamera] = useState(
  () => new Map<string, SignalCountRow[]>(),
);
```

Add a stable callback in `WorkspacePage`:

```tsx
const handleSignalRowsChange = useCallback((cameraId: string, rows: SignalCountRow[]) => {
  setSignalRowsByCamera((current) => {
    const next = new Map(current);
    next.set(cameraId, rows);
    return next;
  });
}, []);
```

Replace the old inline article render in `cameras.map(...)` with:

```tsx
return (
  <ScenePortalCard
    key={camera.id}
    camera={camera}
    frame={frame}
    classFilter={classFilter}
    sceneHealth={sceneHealth}
    onSignalRowsChange={handleSignalRowsChange}
  />
);
```

In `ScenePortalCard`, report rows to the parent and clear stale rows when a card unmounts:

```tsx
useEffect(() => {
  onSignalRowsChange(camera.id, stableSignal.counts.rows);
  return () => {
    onSignalRowsChange(camera.id, []);
  };
}, [camera.id, onSignalRowsChange, stableSignal.counts.rows]);
```

Build right-rail rows:

```tsx
const signalRows = useMemo(() => {
  const rows = new Map<string, SignalCountRow>();
  for (const cameraRows of signalRowsByCamera.values()) {
    for (const row of cameraRows) {
      const current = rows.get(row.className);
      rows.set(row.className, {
        ...row,
        liveCount: (current?.liveCount ?? 0) + row.liveCount,
        heldCount: (current?.heldCount ?? 0) + row.heldCount,
        totalCount: (current?.totalCount ?? 0) + row.totalCount,
        state: (current?.liveCount ?? 0) + row.liveCount > 0 ? "live" : row.state,
      });
    }
  }
  return Array.from(rows.values()).sort(
    (left, right) =>
      right.liveCount - left.liveCount ||
      right.totalCount - left.totalCount ||
      left.className.localeCompare(right.className),
  );
}, [signalRowsByCamera]);
```

Pass to rail:

```tsx
<DynamicStats signalRows={signalRows} />
```

- [ ] **Step 5: Update changelog**

Add under the Phase 5A entry in `frontend/CHANGELOG.md`:

```md
- Added Live signal stabilization with class-colored overlays, calmer scene state labels, and a Telemetry Terrain surface for scene activity.
```

- [ ] **Step 6: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/components/live/TelemetryCanvas.test.tsx src/components/live/TelemetryTerrain.test.tsx src/components/live/DynamicStats.test.tsx src/components/operations/SceneStatusStrip.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx frontend/CHANGELOG.md
git commit -m "feat(live): stabilize terrain signal display"
```

---

## Task 7: Final Verification And Visual QA

**Files:**
- No planned code changes.

- [ ] **Step 1: Run full frontend verification**

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec playwright test e2e/operational-readiness.spec.ts
```

Expected:

- unit tests pass
- lint has 0 errors and only already-known warnings
- build passes
- operational readiness smoke passes

- [ ] **Step 2: Browser visual QA**

Open `/live` in the local app with at least one scene.

Check:

- colored object boxes are visible against bright video regions
- held boxes are visibly different from live boxes
- top scene state bar does not wrap awkwardly or dominate the video
- `Native passthrough gated` language does not imply the processed WebRTC stream is broken
- Telemetry Terrain looks intentional, not like a decorative blob
- right rail rows do not disappear on a one-frame miss
- mobile or narrow viewport does not overlap labels

- [ ] **Step 3: Inspect git status**

```bash
git status --short
```

Expected: only unrelated scratch files are untracked; intended files are committed.

- [ ] **Step 4: Push when approved**

```bash
git push origin codex/omnisight-ui-spec-implementation
```

Expected: branch pushes successfully.
