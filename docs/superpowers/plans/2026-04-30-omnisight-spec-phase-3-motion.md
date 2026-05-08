# OmniSight Spec — Phase 3: Motion Choreography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the product alive with purposeful motion — a sliding "lens focus" indicator on the nav, an evidence selection cross-fade, a Patterns bucket-selection slide, a token-driven `Toast` surface, and a `useReducedMotionSafe` helper used everywhere. All token-driven; all keyboard- and reduced-motion-safe.

**Architecture:** Adds Framer Motion (`framer-motion`) as the single motion library. Introduces `MotionProvider` only if needed (most uses are component-local). All animations use `--vz-dur-*` and `--vz-ease-*` tokens already shipped in Phase 1. Reduced motion is the default fallback.

**Tech Stack:** React 19, Vite 6, Tailwind v4, Vitest 2 + `@testing-library/react`, ESLint 9, TypeScript 5.7, **Framer Motion 11**. Frontend root: `/Users/yann.moren/vision/frontend`. Recommended branch: `codex/omnisight-ui-spec-implementation`.

**Spec source:** `/Users/yann.moren/vision/docs/brand/omnisight-ui-spec-sheet.md` (sections 4.1–4.4, 6.9, 6.11, 7.4, 7.5).

**Prerequisites:** Phases 1 and 2 must be merged. Required tokens (`--vz-dur-*`, `--vz-ease-*`) live in `frontend/src/index.css`.

---

## Pre-flight

```bash
cd /Users/yann.moren/vision
git status
git rev-parse --abbrev-ref HEAD
grep -c -- "--vz-ease-product" frontend/src/index.css   # ≥ 1
grep -c -- "OmniSightLens" frontend/src/components/brand/OmniSightLens.tsx   # ≥ 1
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `frontend/package.json` | modify | add `framer-motion` dep |
| `frontend/src/lib/motion.ts` | create | `useReducedMotionSafe`, `motionPresets` |
| `frontend/src/lib/motion.test.ts` | create | tests |
| `frontend/src/components/layout/AppContextRail.tsx` | modify | NavLink wraps a `motion.span` with `layoutId="nav-focus"` |
| `frontend/src/components/layout/AppContextRail.test.tsx` | create | tests for active-state focus dot |
| `frontend/src/pages/Incidents.tsx` | modify | wrap selected media in `AnimatePresence` + slide-fade |
| `frontend/src/pages/Incidents.test.tsx` | modify | assert presence under selection |
| `frontend/src/components/history/HistoryTrendPanel.tsx` | modify | bucket-selection animated shaft (translate-only) |
| `frontend/src/components/history/HistoryTrendPanel.test.tsx` | modify or create | snapshot the active-bucket marker |
| `frontend/src/components/feedback/Toast.tsx` | create | toast primitive |
| `frontend/src/components/feedback/ToastProvider.tsx` | create | provider/portal |
| `frontend/src/components/feedback/Toast.test.tsx` | create | tests |
| `frontend/src/main.tsx` | modify | mount `ToastProvider` near the root |
| `frontend/src/hooks/use-toast.ts` | create | tiny imperative API |
| `frontend/src/pages/Incidents.tsx` | modify (second pass) | call `useToast` on review success/failure |

---

## Task 1: Install Framer Motion

- [ ] **Step 1: Add the dependency**

```bash
pnpm --dir frontend add framer-motion@^11
```

Expected: `framer-motion` lands in `frontend/package.json` `dependencies`.

- [ ] **Step 2: Confirm install + types**

```bash
pnpm --dir frontend exec tsc -b --noEmit
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore(frontend): add framer-motion@11"
```

---

## Task 2: `useReducedMotionSafe` and motion presets

**Files:**
- Create: `frontend/src/lib/motion.ts`
- Create: `frontend/src/lib/motion.test.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/lib/motion.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import { motionPresets } from "@/lib/motion";

describe("motionPresets", () => {
  test("rise preset uses 240ms ease-product duration tokens", () => {
    expect(motionPresets.rise.transition.duration).toBeCloseTo(0.24);
    expect(motionPresets.rise.transition.ease).toEqual([0.22, 1, 0.36, 1]);
  });

  test("evidenceSwap is slide-from-right + fade", () => {
    expect(motionPresets.evidenceSwap.initial).toMatchObject({
      x: expect.any(Number),
      opacity: 0,
    });
    expect(motionPresets.evidenceSwap.animate).toMatchObject({
      x: 0,
      opacity: 1,
    });
  });

  test("lensSnap uses spring or product easing within 320ms cap", () => {
    expect(motionPresets.lensSnap.transition.duration).toBeLessThanOrEqual(0.32);
  });
});
```

- [ ] **Step 2: Run test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/lib/motion.test.ts
```

- [ ] **Step 3: Create `frontend/src/lib/motion.ts`**

```ts
import { useReducedMotion } from "framer-motion";

export const easings = {
  product: [0.22, 1, 0.36, 1] as const,
  out: [0.16, 1, 0.3, 1] as const,
  inOut: [0.65, 0, 0.35, 1] as const,
  spring: [0.34, 1.56, 0.64, 1] as const,
};

export const durations = {
  instant: 0.09,
  quick: 0.18,
  base: 0.24,
  soft: 0.32,
};

export const motionPresets = {
  rise: {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: durations.base, ease: easings.product },
  },
  lensSnap: {
    initial: { opacity: 0, scale: 0.97 },
    animate: { opacity: 1, scale: 1 },
    transition: { duration: durations.soft, ease: easings.product },
  },
  evidenceSwap: {
    initial: { x: 24, opacity: 0 },
    animate: { x: 0, opacity: 1 },
    exit: { x: -16, opacity: 0 },
    transition: { duration: durations.base, ease: easings.product },
  },
} as const;

export type MotionPresetName = keyof typeof motionPresets;

export function useReducedMotionSafe(preset: MotionPresetName) {
  const reduce = useReducedMotion();
  if (reduce) {
    return {
      initial: false as const,
      animate: { opacity: 1 },
      exit: { opacity: 0 },
      transition: { duration: 0 },
    };
  }
  return motionPresets[preset];
}
```

- [ ] **Step 4: Run test + lint + commit**

```bash
pnpm --dir frontend exec vitest run src/lib/motion.test.ts
pnpm --dir frontend lint
git add frontend/src/lib/motion.ts frontend/src/lib/motion.test.ts
git commit -m "feat(motion): add motion presets and useReducedMotionSafe"
```

---

## Task 3: Sliding nav focus dot in `AppContextRail`

**Files:**
- Modify: `frontend/src/components/layout/AppContextRail.tsx`
- Create: `frontend/src/components/layout/AppContextRail.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/layout/AppContextRail.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, test } from "vitest";

import { AppContextRail } from "@/components/layout/AppContextRail";

function renderWith(initialPath: string) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AppContextRail />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AppContextRail", () => {
  test("renders a nav focus indicator on the active route", () => {
    renderWith("/dashboard");
    expect(screen.getByTestId("nav-focus-indicator")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/layout/AppContextRail.test.tsx
```

- [ ] **Step 3: Update `AppContextRail.tsx`**

Replace `frontend/src/components/layout/AppContextRail.tsx` with:

```tsx
import { useQueryClient } from "@tanstack/react-query";
import { motion, LayoutGroup } from "framer-motion";
import { NavLink } from "react-router-dom";

import { TenantSwitcher } from "@/components/layout/TenantSwitcher";
import { UserMenu } from "@/components/layout/UserMenu";
import {
  prefetchWorkspaceRoute,
  workspaceNavGroups,
} from "@/components/layout/TopNav";
import { cn } from "@/lib/utils";

export function AppContextRail() {
  const queryClient = useQueryClient();

  return (
    <aside className="sticky top-0 z-10 hidden h-screen w-[16.5rem] shrink-0 flex-col border-r border-[color:var(--vz-hair)] bg-[linear-gradient(180deg,rgba(8,12,18,0.98),rgba(12,16,23,0.95))] px-4 py-4 lg:flex xl:w-[17.5rem]">
      <LayoutGroup id="nav-focus-group">
        <div className="flex flex-1 flex-col gap-5">
          {workspaceNavGroups.map((group) => (
            <nav key={group.label} aria-label={group.label}>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--vz-text-muted)]">
                {group.label}
              </p>
              <div className="mt-3 space-y-1.5">
                {group.items.map((item) => (
                  <NavLink
                    key={item.label}
                    to={item.to}
                    onFocus={() => prefetchWorkspaceRoute(item.to, queryClient)}
                    onMouseEnter={() =>
                      prefetchWorkspaceRoute(item.to, queryClient)
                    }
                    onPointerDown={() =>
                      prefetchWorkspaceRoute(item.to, queryClient)
                    }
                    className={({ isActive }) =>
                      cn(
                        "relative flex items-center gap-3 rounded-[var(--vz-r-md)] border px-3 py-2.5 text-sm font-medium transition duration-200",
                        isActive
                          ? "border-[color:var(--vz-hair-focus)] bg-[linear-gradient(90deg,rgba(110,189,255,0.16),transparent_80%)] text-[var(--vz-text-primary)]"
                          : "border-[color:var(--vz-hair)] bg-white/[0.025] text-[var(--vz-text-secondary)] hover:border-[color:var(--vz-hair-strong)] hover:text-[var(--vz-text-primary)]",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive ? (
                          <motion.span
                            layoutId="nav-focus"
                            data-testid="nav-focus-indicator"
                            className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-[3px] rounded-full bg-[var(--vz-lens-cerulean)] shadow-[0_0_18px_rgba(118,224,255,0.55)]"
                            transition={{
                              type: "spring",
                              stiffness: 480,
                              damping: 38,
                            }}
                          />
                        ) : null}
                        <item.icon
                          className="size-4 shrink-0 opacity-80"
                          aria-hidden="true"
                        />
                        <span>{item.label}</span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </nav>
          ))}
        </div>
      </LayoutGroup>

      <div className="mt-4 space-y-3 border-t border-[color:var(--vz-hair)] pt-4">
        <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--vz-text-muted)]">
            Workspace
          </p>
          <p className="mt-2 text-sm font-medium text-[var(--vz-text-secondary)]">
            OmniSight control layer
          </p>
        </div>
        <TenantSwitcher />
        <UserMenu />
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Run tests, lint, dev smoke**

```bash
pnpm --dir frontend exec vitest run src/components/layout/AppContextRail.test.tsx
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend dev
# Click between /dashboard, /live, /history
# Confirm: a 3px cerulean shaft slides between active nav items
# Stop dev
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/AppContextRail.tsx frontend/src/components/layout/AppContextRail.test.tsx
git commit -m "feat(nav): sliding cerulean focus shaft between active routes"
```

---

## Task 4: Evidence selection slide-fade

**Files:**
- Modify: `frontend/src/pages/Incidents.tsx`

- [ ] **Step 1: Wrap the evidence-media region in `AnimatePresence` keyed on incident id**

In `frontend/src/pages/Incidents.tsx`, find the `selectedIncident` render block (around lines 181–199 — currently:

```tsx
<IncidentEvidenceHero
  incident={selectedIncident}
  cameraName={cameraNameFor(selectedIncident, cameraNamesById)}
  reviewMutation={reviewMutation}
/>
```

Wrap it with:

```tsx
<AnimatePresence mode="wait" initial={false}>
  <motion.div
    key={selectedIncident.id}
    {...useReducedMotionSafe("evidenceSwap")}
    className="min-w-0"
  >
    <IncidentEvidenceHero
      incident={selectedIncident}
      cameraName={cameraNameFor(selectedIncident, cameraNamesById)}
      reviewMutation={reviewMutation}
    />
  </motion.div>
</AnimatePresence>
```

Add at the top of the file:

```tsx
import { AnimatePresence, motion } from "framer-motion";

import { useReducedMotionSafe } from "@/lib/motion";
```

- [ ] **Step 2: Run Incidents test**

```bash
pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: green. The existing tests render a single selected incident and don't depend on motion timing.

- [ ] **Step 3: Dev smoke**

```bash
pnpm --dir frontend dev
# /incidents — click between two queue rows; the media area slides in from the right with fade
```

- [ ] **Step 4: Lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/pages/Incidents.tsx
git commit -m "feat(evidence): animate selected media swap with slide+fade"
```

---

## Task 5: Patterns bucket-selection animated shaft

**Files:**
- Modify: `frontend/src/components/history/HistoryTrendPanel.tsx`

The current component already accepts a `selectedBucket`. Spec §7.4 calls for the selected bucket to render a 100%-height shaft in cerulean at 18% opacity + 1px center line. Render it as a `motion.div` keyed on the bucket label so it slides between buckets rather than re-mounting.

- [ ] **Step 1: Read the existing component**

```bash
sed -n '1,80p' /Users/yann.moren/vision/frontend/src/components/history/HistoryTrendPanel.tsx
```

Identify how the chart renders the X axis and where the `selectedBucket` is read.

- [ ] **Step 2: Add the animated shaft overlay**

Inside `HistoryTrendPanel`, locate the chart container `<div>`. As a sibling overlay (positioned absolutely over the chart canvas), insert:

```tsx
{series.selectedBucket ? (
  <motion.div
    aria-hidden="true"
    layoutId="history-bucket-shaft"
    className="pointer-events-none absolute top-0 bottom-0 w-[2.4%] bg-[rgba(110,189,255,0.18)]"
    style={{
      left: bucketLeftPercent(series.points, series.selectedBucket),
    }}
    transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
  >
    <span className="absolute left-1/2 top-0 bottom-0 w-px -translate-x-1/2 bg-[var(--vz-lens-cerulean)] opacity-70" />
  </motion.div>
) : null}
```

Add at the top of the file:

```tsx
import { motion } from "framer-motion";
```

Add this helper near the bottom of the file:

```tsx
function bucketLeftPercent(
  points: ReadonlyArray<{ bucket: string }>,
  selected: string,
): string {
  const idx = points.findIndex((p) => p.bucket === selected);
  if (idx < 0 || points.length <= 1) return "0%";
  return `${(idx / (points.length - 1)) * 100}%`;
}
```

(If a Y-percent helper already exists, reuse it. Do not duplicate.)

- [ ] **Step 3: Tests**

If `HistoryTrendPanel.test.tsx` exists, ensure it still passes. If it does not, create a minimal one:

```tsx
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { HistoryTrendPanel } from "@/components/history/HistoryTrendPanel";

describe("HistoryTrendPanel", () => {
  test("renders with selectedBucket without crashing", () => {
    expect(() =>
      render(
        <HistoryTrendPanel
          series={{
            classNames: ["person"],
            points: [
              { bucket: "2026-04-30T00:00:00Z", values: { person: 1 } },
              { bucket: "2026-04-30T01:00:00Z", values: { person: 2 } },
            ],
            includeSpeed: false,
            speedThreshold: null,
            speedClassesUsed: null,
            selectedBucket: "2026-04-30T01:00:00Z",
          }}
          metric="occupancy"
          granularity="1h"
          coverage={null}
          onBucketSelect={() => {}}
        />,
      ),
    ).not.toThrow();
  });
});
```

- [ ] **Step 4: Run + lint + commit**

```bash
pnpm --dir frontend exec vitest run src/components/history/HistoryTrendPanel.test.tsx
pnpm --dir frontend test
pnpm --dir frontend lint
git add frontend/src/components/history/HistoryTrendPanel.tsx frontend/src/components/history/HistoryTrendPanel.test.tsx
git commit -m "feat(history): animated bucket-selection shaft"
```

---

## Task 6: Toast primitive + provider + `useToast`

**Files:**
- Create: `frontend/src/components/feedback/Toast.tsx`
- Create: `frontend/src/components/feedback/ToastProvider.tsx`
- Create: `frontend/src/hooks/use-toast.ts`
- Create: `frontend/src/components/feedback/Toast.test.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Write a failing test**

Create `frontend/src/components/feedback/Toast.test.tsx`:

```tsx
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import { ToastProvider } from "@/components/feedback/ToastProvider";
import { useToast } from "@/hooks/use-toast";

function Trigger() {
  const toast = useToast();
  return (
    <button
      type="button"
      onClick={() => toast.show({ tone: "healthy", message: "Saved" })}
    >
      Trigger
    </button>
  );
}

describe("Toast", () => {
  test("shows a toast on demand and auto-dismisses after timeout", async () => {
    vi.useFakeTimers();
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );

    await userEvent.setup({ advanceTimers: vi.advanceTimersByTime }).click(
      screen.getByRole("button", { name: /trigger/i }),
    );
    expect(screen.getByText("Saved")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(screen.queryByText("Saved")).toBeNull();
    vi.useRealTimers();
  });
});
```

Add at the top:

```tsx
import { vi } from "vitest";
```

- [ ] **Step 2: Run, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/feedback/Toast.test.tsx
```

- [ ] **Step 3: Create the toast primitive**

`frontend/src/components/feedback/Toast.tsx`:

```tsx
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type ToastTone = "healthy" | "attention" | "danger" | "accent";

const toneStripe: Record<ToastTone, string> = {
  healthy: "bg-[var(--vz-state-healthy)]",
  attention: "bg-[var(--vz-state-attention)]",
  danger: "bg-[var(--vz-state-risk)]",
  accent: "bg-[var(--vz-lens-cerulean)]",
};

export type ToastSpec = {
  id: string;
  tone: ToastTone;
  message: string;
  description?: ReactNode;
};

export function Toast({ spec }: { spec: ToastSpec }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "relative flex max-w-sm overflow-hidden rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair-strong)] bg-[color:var(--vz-canvas-graphite-up)] shadow-[var(--vz-elev-3)]",
      )}
    >
      <span className={cn("w-1 shrink-0", toneStripe[spec.tone])} />
      <div className="px-4 py-3">
        <p className="text-sm font-semibold text-[var(--vz-text-primary)]">
          {spec.message}
        </p>
        {spec.description ? (
          <p className="mt-1 text-xs text-[var(--vz-text-secondary)]">
            {spec.description}
          </p>
        ) : null}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create provider + hook**

`frontend/src/components/feedback/ToastProvider.tsx`:

```tsx
import { AnimatePresence, motion } from "framer-motion";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

import { Toast, type ToastSpec } from "@/components/feedback/Toast";
import { useReducedMotionSafe } from "@/lib/motion";

type ShowInput = Omit<ToastSpec, "id"> & { durationMs?: number };

type ToastContextValue = {
  show: (input: ShowInput) => string;
  dismiss: (id: string) => void;
};

export const ToastContext = createContext<ToastContextValue | null>(null);

const DEFAULT_DURATION = 5000;

export function ToastProvider({ children }: PropsWithChildren) {
  const [items, setItems] = useState<ToastSpec[]>([]);
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
    const handle = timers.current.get(id);
    if (handle) {
      clearTimeout(handle);
      timers.current.delete(id);
    }
  }, []);

  const show = useCallback(
    (input: ShowInput) => {
      const id =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random()}`;
      const spec: ToastSpec = {
        id,
        tone: input.tone,
        message: input.message,
        description: input.description,
      };
      setItems((prev) => [...prev.slice(-2), spec]);
      const handle = setTimeout(
        () => dismiss(id),
        input.durationMs ?? DEFAULT_DURATION,
      );
      timers.current.set(id, handle);
      return id;
    },
    [dismiss],
  );

  const value = useMemo(() => ({ show, dismiss }), [show, dismiss]);
  const motionProps = useReducedMotionSafe("rise");

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex flex-col gap-2">
        <AnimatePresence>
          {items.map((spec) => (
            <motion.div
              key={spec.id}
              {...motionProps}
              exit={{ opacity: 0, y: 8 }}
              className="pointer-events-auto"
            >
              <Toast spec={spec} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToastContext() {
  const value = useContext(ToastContext);
  if (!value) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return value;
}
```

`frontend/src/hooks/use-toast.ts`:

```ts
import { useToastContext } from "@/components/feedback/ToastProvider";

export function useToast() {
  return useToastContext();
}
```

- [ ] **Step 5: Mount provider in `main.tsx`**

In `frontend/src/main.tsx`, wrap the existing root render with `<ToastProvider>` so it sits inside `<QueryClientProvider>` (or wherever the existing top-level providers live). Add the import:

```tsx
import { ToastProvider } from "@/components/feedback/ToastProvider";
```

Wrap:

```tsx
<ToastProvider>
  <App />
</ToastProvider>
```

- [ ] **Step 6: Run tests**

```bash
pnpm --dir frontend exec vitest run src/components/feedback/Toast.test.tsx
pnpm --dir frontend test
```

- [ ] **Step 7: Lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/components/feedback/Toast.tsx frontend/src/components/feedback/ToastProvider.tsx frontend/src/components/feedback/Toast.test.tsx frontend/src/hooks/use-toast.ts frontend/src/main.tsx
git commit -m "feat(feedback): toast primitive with auto-dismiss"
```

---

## Task 7: Wire toast to evidence review success/failure

**Files:**
- Modify: `frontend/src/pages/Incidents.tsx`

- [ ] **Step 1: Replace inline error paragraph with toast**

In `frontend/src/pages/Incidents.tsx`, locate `IncidentEvidenceHero` and the `mutationErrorMessage` rendering. Replace with a `useEffect` that calls `useToast` on `reviewMutation.isError` / `reviewMutation.isSuccess`:

```tsx
import { useEffect } from "react";

import { useToast } from "@/hooks/use-toast";

// inside IncidentEvidenceHero, before the return:
const toast = useToast();

useEffect(() => {
  if (reviewMutation.isSuccess) {
    toast.show({
      tone: "healthy",
      message: "Review state saved.",
    });
    reviewMutation.reset();
  }
}, [reviewMutation, toast]);

useEffect(() => {
  if (reviewMutation.isError) {
    toast.show({
      tone: "danger",
      message: "Failed to update review state.",
      description: reviewMutationErrorMessage(reviewMutation.error),
    });
  }
}, [reviewMutation.isError, reviewMutation.error, toast]);
```

Then delete the inline `mutationErrorMessage` paragraph (the existing `aria-live="polite"` block at the bottom of the component). The toast covers a11y.

- [ ] **Step 2: Update Incidents test**

Existing tests should still pass. Add one that asserts the toast shows on review success — but only if the test harness already drives `reviewMutation`. If not, leave this for a future test pass and do a dev smoke instead.

```bash
pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

- [ ] **Step 3: Dev smoke**

```bash
pnpm --dir frontend dev
# /incidents — click Review on a record; toast appears bottom-right and auto-dismisses
```

- [ ] **Step 4: Lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/pages/Incidents.tsx
git commit -m "feat(evidence): toast review success/failure"
```

---

## Task 8: WorkspaceTransition tightening

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/layout/WorkspaceTransition.tsx`

- [ ] **Step 1: Tighten the keyframe**

In `frontend/src/index.css`, locate `@keyframes workspace-enter` and replace with the new spec keyframe (no scale, smaller Y delta):

```css
@keyframes workspace-enter {
  from {
    opacity: 0;
    transform: translate3d(0, 6px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}
```

- [ ] **Step 2: Verify the WorkspaceTransition component uses the right duration**

Read `frontend/src/components/layout/WorkspaceTransition.tsx` and confirm it applies `animation: workspace-enter var(--vz-dur-base) var(--vz-ease-product) both;`. If it inlines a different duration, update to use the token.

- [ ] **Step 3: Test, lint, commit**

```bash
pnpm --dir frontend test
pnpm --dir frontend lint
git add frontend/src/index.css frontend/src/components/layout/WorkspaceTransition.tsx
git commit -m "feat(motion): tighten workspace-enter keyframe to spec"
```

---

## Task 9: Verify and document phase completion

- [ ] **Step 1: Full verification**

```bash
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

- [ ] **Step 2: Reduced-motion verification**

Browser → DevTools → Rendering → Emulate CSS media feature `prefers-reduced-motion: reduce`. Visit:
- `/dashboard` — transitions instant.
- `/signin` — lens does not breathe; pointer-tilt disabled.
- `/incidents` — selection swap is instantaneous.
- nav focus — slides in `~0ms`.

Restore `prefers-reduced-motion: no-preference`. Confirm the choreography returns.

- [ ] **Step 3: Append changelog**

`frontend/CHANGELOG.md`:

```markdown
## Unreleased — Phase 3 Motion Choreography

- Added Framer Motion + `motionPresets` + `useReducedMotionSafe`.
- Sliding cerulean focus indicator on the active nav route.
- Evidence selection cross-fade on `/incidents`.
- Animated bucket-selection shaft on `/history`.
- Token-driven `Toast` primitive with `useToast` hook; wired to evidence review.
- Tightened `WorkspaceTransition` keyframe.
```

- [ ] **Step 4: Commit**

```bash
git add frontend/CHANGELOG.md
git commit -m "docs: changelog for Phase 3 motion"
```

---

## Done criteria

Phase 3 is complete when:

1. `pnpm --dir frontend lint`, `test`, `build` all pass.
2. The active nav route shows a sliding 3px cerulean shaft.
3. Evidence selection animates a cross-fade.
4. Patterns chart shows an animated bucket-selection shaft.
5. Toast renders bottom-right with token-driven styling and auto-dismisses.
6. Every new motion respects `prefers-reduced-motion: reduce`.

Hand off to **Phase 4: Optional WebGL upgrade** (`docs/superpowers/plans/2026-04-30-omnisight-spec-phase-4-webgl.md`) only if leadership approves a 3D dependency.
