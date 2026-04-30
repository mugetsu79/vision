# OmniSight UI Distinctiveness Follow-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current OmniSight UI feel distinctive rather than generic by rebuilding the sign-in stage, restoring a real dashboard overview, differentiating page compositions, and enforcing the requested palette discipline.

**Architecture:** Add small shared composition primitives and palette/tone tokens first, then use them to rebuild sign-in, dashboard, Sites, and the workflow page frames. Keep backend APIs, auth behavior, and existing route paths stable; this is a UI composition and motion pass. Use the official 2D/3D logo assets already in `frontend/public/brand/`, with CSS motion only unless a later spec approves a rendering dependency.

**Tech Stack:** React 19, React Router, TypeScript, Tailwind v4 utility classes, CSS variables in `frontend/src/index.css`, Vitest + Testing Library, existing Playwright E2E harness.

---

## Source Spec

Implement from:

- `docs/superpowers/specs/2026-04-30-omnisight-ui-distinctiveness-followup-design.md`

Keep these constraints:

- Keep the Vezor palette, but enforce the approximate ratio: 75% neutral dark, 15% cerulean, 5% violet, 5% status colors.
- Violet is a brand/entry accent, not a default dashboard wash.
- No backend API changes.
- No auth flow changes.
- No new 3D/Three.js dependency in this pass.
- `/dashboard` must become a real route again.

## File Map

Create:

- `frontend/src/components/layout/workspace-surfaces.tsx`
  - Shared composition primitives: `WorkspaceBand`, `WorkspaceSurface`, `MediaSurface`, `InstrumentRail`, `StatusToneBadge`.
- `frontend/src/components/layout/workspace-surfaces.test.tsx`
  - Unit tests for semantic tone classes and primitive rendering.
- `frontend/src/pages/Dashboard.tsx`
  - Restored OmniSight cockpit page.
- `frontend/src/pages/Dashboard.test.tsx`
  - Tests for dashboard route content and overview links.

Modify:

- `frontend/src/index.css`
  - Add stricter palette variables, sign-in stage motion, reduced-motion coverage, and neutral surface helpers.
- `frontend/src/components/brand/OmniSightField.tsx`
  - Add a deliberate `stage` or `dashboard` variant if needed; reduce workflow-page visual wash.
- `frontend/src/components/brand/OmniSightField.test.tsx`
  - Cover new variant and decorative semantics.
- `frontend/src/pages/SignIn.tsx`
  - Rebuild as a deliberate 3D lens stage.
- `frontend/src/pages/SignIn.test.tsx`
  - Assert no generic old structure and presence of stage hooks.
- `frontend/src/app/router.tsx`
  - Replace `/dashboard` redirect with lazy `DashboardPage`.
- `frontend/src/components/layout/TopNav.tsx`
  - Restore Dashboard nav item if product navigation should expose it.
- `frontend/src/components/layout/AppIconRail.tsx`
  - Keep active nav lens treatment, add dashboard icon if route is exposed.
- `frontend/src/components/layout/AppContextRail.tsx`
  - Avoid generic “All systems operational” if not API-backed; keep it as a muted label or remove.
- `frontend/src/pages/Live.tsx`
  - Change from generic header-card to live portal composition using shared primitives.
- `frontend/src/components/live/AgentInput.tsx`
  - Convert to compact command strip or dock style.
- `frontend/src/components/live/DynamicStats.tsx`
  - Convert to instrument rail styling.
- `frontend/src/pages/History.tsx`
  - Reduce duplicated side filters and generic export prominence.
- `frontend/src/components/history/HistoryToolbar.tsx`
  - Use workbench toolbar styling.
- `frontend/src/components/history/HistoryTrendPanel.tsx`
  - Use chart-first media/workbench surface.
- `frontend/src/pages/Incidents.tsx`
  - Make media black zones stronger and semantic review state clearer.
- `frontend/src/pages/Cameras.tsx`
  - Add scene setup summary/topology band above the table.
- `frontend/src/pages/Sites.tsx`
  - Rework from placeholder table into deployment-context surface.
- `frontend/src/pages/Settings.tsx`
  - Apply composition/tone primitives to reduce repeated panel styling.
- Relevant page tests:
  - `frontend/src/pages/Live.test.tsx`
  - `frontend/src/pages/History.test.tsx`
  - `frontend/src/pages/Incidents.test.tsx`
  - `frontend/src/pages/Cameras.test.tsx`
  - `frontend/src/pages/Sites.test.tsx`
  - `frontend/src/pages/Settings.test.tsx`
  - `frontend/src/components/layout/AppShell.test.tsx`

Do not modify generated API files unless API generation is explicitly run as part of normal verification.

---

## Task 1: Add Palette And Composition Primitives

**Files:**

- Modify: `frontend/src/index.css`
- Create: `frontend/src/components/layout/workspace-surfaces.tsx`
- Create: `frontend/src/components/layout/workspace-surfaces.test.tsx`

- [ ] **Step 1: Write primitive tests**

Create `frontend/src/components/layout/workspace-surfaces.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import {
  InstrumentRail,
  MediaSurface,
  StatusToneBadge,
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";

describe("workspace surfaces", () => {
  test("renders neutral workspace primitives", () => {
    render(
      <>
        <WorkspaceBand title="Live Intelligence" eyebrow="Live">
          <p>Signals converge here.</p>
        </WorkspaceBand>
        <WorkspaceSurface aria-label="Surface">Surface body</WorkspaceSurface>
        <MediaSurface aria-label="Media">Media body</MediaSurface>
        <InstrumentRail aria-label="Rail">Rail body</InstrumentRail>
      </>,
    );

    expect(screen.getByRole("heading", { name: "Live Intelligence" })).toBeInTheDocument();
    expect(screen.getByLabelText("Surface")).toHaveClass("bg-[color:var(--vezor-surface-neutral)]");
    expect(screen.getByLabelText("Media")).toHaveClass("bg-[color:var(--vezor-media-black)]");
    expect(screen.getByLabelText("Rail")).toHaveClass("bg-[color:var(--vezor-surface-rail)]");
  });

  test("maps status tones to semantic classes", () => {
    render(
      <>
        <StatusToneBadge tone="healthy">Live</StatusToneBadge>
        <StatusToneBadge tone="attention">Pending</StatusToneBadge>
        <StatusToneBadge tone="danger">Failed</StatusToneBadge>
        <StatusToneBadge tone="accent">Selected</StatusToneBadge>
      </>,
    );

    expect(screen.getByText("Live")).toHaveClass("text-[var(--vezor-success)]");
    expect(screen.getByText("Pending")).toHaveClass("text-[var(--vezor-attention)]");
    expect(screen.getByText("Failed")).toHaveClass("text-[var(--vezor-risk)]");
    expect(screen.getByText("Selected")).toHaveClass("text-[var(--vezor-lens-cerulean)]");
  });
});
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/workspace-surfaces.test.tsx
```

Expected: FAIL because `workspace-surfaces.tsx` does not exist.

- [ ] **Step 3: Add palette variables**

In `frontend/src/index.css`, extend `:root` with these variables near the existing Vezor tokens:

```css
  --vezor-canvas-obsidian: #03050a;
  --vezor-canvas-ink: #05080d;
  --vezor-graphite: #10151d;
  --vezor-graphite-raised: #151b25;
  --vezor-surface-neutral: rgba(13, 18, 27, 0.94);
  --vezor-surface-rail: rgba(8, 12, 18, 0.88);
  --vezor-media-black: #010307;
  --vezor-border-neutral: rgba(176, 197, 226, 0.1);
  --vezor-border-focus: rgba(118, 224, 255, 0.38);
```

Keep existing `--vezor-lens-cerulean`, `--vezor-lens-violet`, `--vezor-success`, `--vezor-attention`, and `--vezor-risk`.

- [ ] **Step 4: Implement primitives**

Create `frontend/src/components/layout/workspace-surfaces.tsx`:

```tsx
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type WorkspaceBandProps = HTMLAttributes<HTMLElement> & {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
};

type Tone = "healthy" | "attention" | "danger" | "muted" | "accent";

const toneClasses: Record<Tone, string> = {
  healthy: "border-[rgba(114,227,166,0.24)] bg-[rgba(10,35,24,0.72)] text-[var(--vezor-success)]",
  attention: "border-[rgba(242,189,92,0.26)] bg-[rgba(42,31,10,0.72)] text-[var(--vezor-attention)]",
  danger: "border-[rgba(240,138,162,0.28)] bg-[rgba(45,14,24,0.72)] text-[var(--vezor-risk)]",
  muted: "border-white/10 bg-white/[0.035] text-[#9db0cc]",
  accent: "border-[rgba(118,224,255,0.26)] bg-[rgba(23,52,70,0.56)] text-[var(--vezor-lens-cerulean)]",
};

export function WorkspaceBand({
  eyebrow,
  title,
  description,
  actions,
  className,
  children,
  ...props
}: WorkspaceBandProps) {
  return (
    <section
      className={cn(
        "rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-neutral)] px-5 py-5",
        className,
      )}
      {...props}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8fa4c4]">
            {eyebrow}
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-normal text-[#f4f8ff] sm:text-3xl">
            {title}
          </h1>
          {description ? (
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[#9eb0cb]">
              {description}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {children ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}

export function WorkspaceSurface({
  className,
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn(
        "rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-neutral)]",
        className,
      )}
      {...props}
    />
  );
}

export function MediaSurface({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[0.9rem] border border-white/10 bg-[color:var(--vezor-media-black)]",
        className,
      )}
      {...props}
    />
  );
}

export function InstrumentRail({
  className,
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <aside
      className={cn(
        "rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-rail)]",
        className,
      )}
      {...props}
    />
  );
}

export function StatusToneBadge({
  tone = "muted",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em]",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
```

- [ ] **Step 5: Run primitive tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/workspace-surfaces.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/index.css frontend/src/components/layout/workspace-surfaces.tsx frontend/src/components/layout/workspace-surfaces.test.tsx
git commit -m "feat: add omnisight workspace surface primitives"
```

---

## Task 2: Rebuild Sign-In As A Deliberate Lens Stage

**Files:**

- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/brand/OmniSightField.tsx`
- Modify: `frontend/src/components/brand/OmniSightField.test.tsx`
- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/pages/SignIn.test.tsx`

- [ ] **Step 1: Write sign-in stage test**

Update `frontend/src/pages/SignIn.test.tsx` with assertions like:

```tsx
expect(screen.getByTestId("signin-lens-stage")).toBeInTheDocument();
expect(screen.getByTestId("signin-auth-panel")).toBeInTheDocument();
expect(screen.getByRole("heading", { name: /OmniSight for every live environment/i })).toBeInTheDocument();
expect(screen.getByText(/Vezor connects scenes, models, events, evidence, and edge operations/i)).toBeInTheDocument();
```

If the test currently asserts the old `signin-spatial-stage` or `signin-orbit-auth` names, replace those with the new test ids above.

- [ ] **Step 2: Run sign-in test to verify failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx
```

Expected: FAIL because the new stage hooks do not exist yet.

- [ ] **Step 3: Add an entry-stage field variant**

In `frontend/src/components/brand/OmniSightField.tsx`, extend the type:

```ts
type OmniSightFieldVariant = "entry" | "stage" | "dashboard" | "overview" | "shell" | "quiet";
```

Keep the component decorative with `aria-hidden="true"`.

Update `showNodes`:

```ts
const showNodes = variant === "overview" || variant === "dashboard" || variant === "shell";
```

- [ ] **Step 4: Add CSS for the sign-in lens stage**

In `frontend/src/index.css`, add these classes after the existing `.omnisight-field--entry` rules:

```css
.omnisight-field--stage .omnisight-field__mark-stack {
  width: clamp(17rem, 34vw, 31rem);
  right: clamp(1rem, 7vw, 7rem);
  top: 48%;
  opacity: 0.96;
  transform: translate3d(0, -50%, 0);
}

.omnisight-field--stage .omnisight-field__orbital-map {
  inset: 10% 4% 8% auto;
  width: min(54vw, 44rem);
  opacity: 0.5;
}

.omnisight-field--stage .omnisight-field__ring--primary {
  right: clamp(0rem, 8vw, 8rem);
  top: calc(50% - 7rem);
  width: clamp(19rem, 39vw, 36rem);
  height: clamp(9rem, 17vw, 16rem);
}

.omnisight-field--stage .omnisight-field__ring--secondary {
  right: clamp(-1rem, 6vw, 6rem);
  top: calc(50% - 8rem);
  width: clamp(22rem, 43vw, 40rem);
  height: clamp(10rem, 19vw, 18rem);
}

.signin-lens-glint {
  background: radial-gradient(circle, rgba(118, 224, 255, 0.75), transparent 58%);
  filter: blur(14px);
}

@media (max-width: 900px) {
  .omnisight-field--stage .omnisight-field__mark-stack {
    width: clamp(10rem, 54vw, 15rem);
    left: 50%;
    right: auto;
    top: 10.5rem;
    opacity: 0.82;
    transform: translate3d(-50%, -50%, 0);
  }

  .omnisight-field--stage .omnisight-field__ring--primary,
  .omnisight-field--stage .omnisight-field__ring--secondary {
    left: 50%;
    right: auto;
    translate: -50% 0;
  }
}
```

Inside the existing `@media (prefers-reduced-motion: no-preference)`, add:

```css
  .signin-lens-glint {
    animation: signin-glint 4.8s ease-in-out infinite alternate;
  }
```

Inside `@media (prefers-reduced-motion: reduce)`, add:

```css
  .signin-lens-glint {
    animation: none;
  }
```

Add keyframes:

```css
@keyframes signin-glint {
  from {
    opacity: 0.26;
    transform: translate3d(-0.5rem, 0.2rem, 0) scale(0.92);
  }
  to {
    opacity: 0.68;
    transform: translate3d(0.7rem, -0.3rem, 0) scale(1.08);
  }
}
```

- [ ] **Step 5: Rebuild SignIn layout**

In `frontend/src/pages/SignIn.tsx`, structure the return as:

```tsx
return (
  <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_74%_42%,rgba(110,189,255,0.18),transparent_28%),linear-gradient(180deg,var(--vezor-canvas-obsidian)_0%,#080d15_52%,#10141d_100%)] px-6 py-8 text-[var(--argus-text)]">
    <div className="absolute inset-0" data-testid="signin-lens-stage">
      <OmniSightField variant="stage" className="opacity-95" />
      <div className="signin-lens-glint pointer-events-none absolute right-[18%] top-[38%] h-28 w-28 rounded-full" />
    </div>

    <div className="relative z-10 mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl grid-rows-[auto_1fr_auto] gap-8">
      <header className="flex items-center justify-between">
        <ProductLockup className="h-12 w-auto" />
        <p className="hidden text-[11px] font-semibold uppercase tracking-[0.24em] text-[#7f94b5] sm:block">
          Spatial intelligence layer
        </p>
      </header>

      <section className="grid items-center gap-8 lg:grid-cols-[minmax(0,0.84fr)_minmax(360px,0.72fr)]">
        <div className="max-w-2xl space-y-6 lg:pb-20">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--argus-text-muted)]">
            {productBrand.descriptor}
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-normal text-[var(--argus-text)] sm:text-6xl lg:text-7xl">
            OmniSight for every live environment.
          </h1>
          <p className="max-w-xl text-lg leading-8 text-[var(--argus-text-muted)]">
            {brandName} connects scenes, models, events, evidence, and edge
            operations into one spatial intelligence layer.
          </p>
          <ul className="grid max-w-xl gap-3 text-sm text-[#dbe8fb] sm:grid-cols-3">
            {["Scenes", "Evidence", "Operations"].map((label) => (
              <li key={label} className="flex items-center gap-3">
                <span className="h-2 w-2 rounded-full bg-[var(--vezor-lens-aqua)] shadow-[0_0_18px_rgba(118,224,255,0.62)]" />
                <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#9db7dc]">
                  {label}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <section
          data-testid="signin-auth-panel"
          className="ml-auto mt-28 w-full max-w-[25rem] rounded-[0.95rem] border border-white/[0.12] bg-[linear-gradient(180deg,rgba(10,15,25,0.94),rgba(5,8,14,0.92))] p-6 text-[var(--argus-text)] shadow-[0_32px_90px_-62px_rgba(73,126,255,0.72)] backdrop-blur-xl sm:p-7 lg:mt-64"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--argus-text-muted)]">
            Secure entry
          </p>
          <h2 className="mt-4 text-2xl font-semibold text-[var(--argus-text)]">
            Sign in
          </h2>
          <p className="mt-2 text-sm text-[var(--argus-text-muted)]">
            Use your {brandName} identity provider account to continue.
          </p>
          <Button
            className="mt-6 w-full border-transparent bg-[linear-gradient(135deg,var(--vezor-lens-cerulean)_0%,#79a7ff_100%)] text-[#06111a] shadow-[0_18px_38px_-24px_rgba(53,184,255,0.55)] hover:border-transparent hover:brightness-110"
            onClick={() => void signIn()}
          >
            Sign in
          </Button>
        </section>
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-[#8397b8]">
        <span>Secure, private, and compliant.</span>
        <span>Your data stays protected.</span>
      </footer>
    </div>
  </main>
);
```

Adjust spacing if browser screenshots show overlap at 768px or 1024px.

- [ ] **Step 6: Run sign-in tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx src/components/brand/OmniSightField.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Browser-check sign-in**

Run the dev server if needed:

```bash
corepack pnpm --dir frontend dev
```

Open `/signin` and verify:

- desktop `1440x900`: 3D lens does not sit under H1 text
- tablet `768x900`: no overlap
- mobile `375x812`: no horizontal overflow, readable lockup, usable sign-in button
- reduced motion: no ambient animation

- [ ] **Step 8: Commit**

```bash
git add frontend/src/index.css frontend/src/components/brand/OmniSightField.tsx frontend/src/components/brand/OmniSightField.test.tsx frontend/src/pages/SignIn.tsx frontend/src/pages/SignIn.test.tsx
git commit -m "feat: rebuild signin as omnisight lens stage"
```

---

## Task 3: Restore Dashboard As OmniSight Overview

**Files:**

- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/Dashboard.test.tsx`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/components/layout/TopNav.tsx`
- Modify: `frontend/src/components/layout/AppIconRail.tsx`
- Modify: `frontend/src/components/layout/AppContextRail.tsx`

- [ ] **Step 1: Write Dashboard tests**

Create `frontend/src/pages/Dashboard.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import { DashboardPage } from "@/pages/Dashboard";

vi.mock("@/hooks/use-cameras", () => ({
  useCameras: () => ({
    data: [
      { id: "camera-1", name: "North Gate", site_id: "site-1" },
      { id: "camera-2", name: "Depot Yard", site_id: "site-1" },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-incidents", () => ({
  useIncidents: () => ({
    data: [
      { id: "incident-1", review_status: "pending", type: "ppe-missing" },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-sites", () => ({
  useSites: () => ({
    data: [{ id: "site-1", name: "HQ", tz: "Europe/Zurich" }],
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: {
      summary: {
        desired_workers: 2,
        running_workers: 1,
        stale_nodes: 0,
        offline_nodes: 0,
        native_unavailable_cameras: 1,
      },
    },
    isLoading: false,
    isError: false,
  }),
}));

describe("DashboardPage", () => {
  test("renders an OmniSight overview cockpit", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "OmniSight Overview" })).toBeInTheDocument();
    expect(screen.getByText("2 live scenes")).toBeInTheDocument();
    expect(screen.getByText("1 pending evidence record")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Live Intelligence/i })).toHaveAttribute("href", "/live");
    expect(screen.getByRole("link", { name: /Review Evidence/i })).toHaveAttribute("href", "/incidents");
  });
});
```

- [ ] **Step 2: Run Dashboard test to verify failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Dashboard.test.tsx
```

Expected: FAIL because `Dashboard.tsx` does not exist.

- [ ] **Step 3: Implement Dashboard page**

Create `frontend/src/pages/Dashboard.tsx`:

```tsx
import { Link } from "react-router-dom";

import { OmniSightField } from "@/components/brand/OmniSightField";
import {
  InstrumentRail,
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { useCameras } from "@/hooks/use-cameras";
import { useIncidents } from "@/hooks/use-incidents";
import { useFleetOverview } from "@/hooks/use-operations";
import { useSites } from "@/hooks/use-sites";

export function DashboardPage() {
  const { data: cameras = [] } = useCameras();
  const { data: sites = [] } = useSites();
  const { data: incidents = [] } = useIncidents({
    cameraId: null,
    incidentType: null,
    reviewStatus: "pending",
    limit: 12,
  });
  const fleet = useFleetOverview();

  const runningWorkers = fleet.data?.summary.running_workers ?? 0;
  const desiredWorkers = fleet.data?.summary.desired_workers ?? 0;
  const directUnavailable = fleet.data?.summary.native_unavailable_cameras ?? 0;

  return (
    <div data-testid="omnisight-overview" className="grid gap-5 p-4 sm:p-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="relative min-h-[22rem] overflow-hidden rounded-[1rem] border border-white/10 bg-[linear-gradient(135deg,rgba(9,14,23,0.98),rgba(7,10,16,0.96))] px-5 py-5">
        <OmniSightField variant="dashboard" className="opacity-80" />
        <div className="relative z-10 max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8fa4c4]">
            Dashboard
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-normal text-[#f4f8ff] sm:text-5xl">
            OmniSight Overview
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[#9eb0cb]">
            A connected view of live scenes, evidence, patterns, deployment
            context, and edge operations.
          </p>
        </div>
        <div className="relative z-10 mt-8 grid gap-3 sm:grid-cols-3">
          <OverviewMetric label="Live scenes" value={`${cameras.length} live scenes`} />
          <OverviewMetric label="Evidence queue" value={`${incidents.length} pending evidence ${incidents.length === 1 ? "record" : "records"}`} />
          <OverviewMetric label="Edge workers" value={`${runningWorkers}/${desiredWorkers} running`} />
        </div>
      </section>

      <InstrumentRail aria-label="Overview instruments" className="space-y-3 p-4">
        <StatusToneBadge tone={directUnavailable > 0 ? "attention" : "healthy"}>
          {directUnavailable > 0 ? `${directUnavailable} direct streams unavailable` : "Streams healthy"}
        </StatusToneBadge>
        <p className="text-sm text-[#9eb0cb]">
          {sites.length} deployment {sites.length === 1 ? "site" : "sites"} configured.
        </p>
      </InstrumentRail>

      <section className="grid gap-4 xl:col-span-2 lg:grid-cols-3">
        <OverviewLink
          title="Live Intelligence"
          copy="Open the portal wall and inspect active scene signals."
          href="/live"
          action="Open Live Intelligence"
        />
        <OverviewLink
          title="Patterns"
          copy="Explore time windows, buckets, speed, and event trends."
          href="/history"
          action="Explore Patterns"
        />
        <OverviewLink
          title="Evidence"
          copy="Review pending records and move evidence to a decision."
          href="/incidents"
          action="Review Evidence"
        />
        <OverviewLink
          title="Scenes"
          copy="Configure source streams, models, privacy, boundaries, and calibration."
          href="/cameras"
          action="Set Up Scenes"
        />
        <OverviewLink
          title="Sites"
          copy="Manage deployment locations and their scene context."
          href="/sites"
          action="Open Sites"
        />
        <OverviewLink
          title="Operations"
          copy="Inspect workers, bootstrap material, and stream diagnostics."
          href="/settings"
          action="Open Operations"
        />
      </section>
    </div>
  );
}

function OverviewMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[0.85rem] border border-white/10 bg-black/25 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7f96b8]">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold text-[#f4f8ff]">{value}</p>
    </div>
  );
}

function OverviewLink({
  title,
  copy,
  href,
  action,
}: {
  title: string;
  copy: string;
  href: string;
  action: string;
}) {
  return (
    <WorkspaceSurface className="p-4 transition duration-200 hover:border-[color:var(--vezor-border-focus)] hover:bg-[rgba(17,24,34,0.96)]">
      <h2 className="text-lg font-semibold text-[#f4f8ff]">{title}</h2>
      <p className="mt-2 min-h-12 text-sm leading-6 text-[#9eb0cb]">{copy}</p>
      <Link
        to={href}
        className="mt-4 inline-flex text-sm font-semibold text-[var(--vezor-lens-cerulean)] transition hover:text-white"
      >
        {action}
      </Link>
    </WorkspaceSurface>
  );
}
```

- [ ] **Step 4: Restore Dashboard routing**

In `frontend/src/app/router.tsx`, replace:

```tsx
{ index: true, element: <Navigate to="live" replace /> },
{ path: "dashboard", element: <Navigate to="/live" replace /> },
```

with:

```tsx
{ index: true, element: <Navigate to="dashboard" replace /> },
{
  path: "dashboard",
  lazy: async () => ({
    Component: (await import("@/pages/Dashboard")).DashboardPage,
  }),
},
```

- [ ] **Step 5: Restore Dashboard in nav**

In `frontend/src/components/layout/TopNav.tsx`, add Dashboard to the Intelligence group before Live:

```ts
{ label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
```

Keep the rest of the current OmniSight labels.

- [ ] **Step 6: Remove unbacked platform status copy**

In `frontend/src/components/layout/AppContextRail.tsx`, either remove the hardcoded “All systems operational” block or change it to a neutral product label:

```tsx
<div className="rounded-[1rem] border border-white/[0.08] bg-white/[0.025] px-3 py-3">
  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8fa2be]">
    Workspace
  </p>
  <p className="mt-2 text-sm font-medium text-[#bfd0e6]">
    OmniSight control layer
  </p>
</div>
```

- [ ] **Step 7: Run routing and dashboard tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Dashboard.test.tsx src/components/layout/AppShell.test.tsx
```

Expected: PASS after updating any nav assertions from previous redirect behavior.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx frontend/src/app/router.tsx frontend/src/components/layout/TopNav.tsx frontend/src/components/layout/AppIconRail.tsx frontend/src/components/layout/AppContextRail.tsx frontend/src/components/layout/AppShell.test.tsx
git commit -m "feat: restore omnisight dashboard overview"
```

---

## Task 4: Differentiate Workflow Page Compositions

**Files:**

- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/components/live/AgentInput.tsx`
- Modify: `frontend/src/components/live/DynamicStats.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/components/history/HistoryToolbar.tsx`
- Modify: `frontend/src/components/history/HistoryTrendPanel.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: corresponding tests

- [ ] **Step 1: Update page tests for differentiated surfaces**

Add or update assertions:

`frontend/src/pages/Live.test.tsx`:

```tsx
expect(screen.getByTestId("scene-portal-grid")).toBeInTheDocument();
expect(screen.getByTestId("ask-vezor-dock")).toBeInTheDocument();
```

`frontend/src/pages/History.test.tsx`:

```tsx
expect(screen.getByTestId("patterns-workbench-toolbar")).toBeInTheDocument();
expect(screen.getByTestId("pattern-trend-panel")).toBeInTheDocument();
```

`frontend/src/pages/Incidents.test.tsx`:

```tsx
expect(screen.getByTestId("review-queue")).toBeInTheDocument();
expect(screen.getByTestId("evidence-media")).toHaveClass("bg-[color:var(--vezor-media-black)]");
expect(screen.getByTestId("facts-rail")).toBeInTheDocument();
```

- [ ] **Step 2: Run workflow tests to verify current gaps**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/pages/History.test.tsx src/pages/Incidents.test.tsx
```

Expected: FAIL for any missing new test ids or class expectations.

- [ ] **Step 3: Refactor Live composition**

In `frontend/src/pages/Live.tsx`:

- Replace the top generic header card with `WorkspaceBand`.
- Make `AgentInput` appear as a compact command dock directly under the band.
- Keep scene tiles as the dominant visual center.
- Use `MediaSurface` semantics/classes for the video area.
- Use `InstrumentRail` for `DynamicStats` and resolved intent.

Concrete top structure:

```tsx
<WorkspaceBand
  eyebrow="Live"
  title={omniLabels.liveTitle}
  description="Watch scenes, signals, and operator intent converge in one live spatial intelligence layer."
  actions={...}
/>
```

For scene articles, reduce blue/violet gradient wash:

```tsx
className="overflow-hidden rounded-[0.9rem] border border-white/10 bg-[color:var(--vezor-surface-neutral)] shadow-[0_20px_56px_-48px_rgba(0,0,0,0.92)] transition duration-200 hover:border-[color:var(--vezor-border-focus)]"
```

For the media div:

```tsx
<div className="relative aspect-video bg-[color:var(--vezor-media-black)]">
```

- [ ] **Step 4: Refactor AgentInput into a dock**

In `frontend/src/components/live/AgentInput.tsx`, keep behavior but reduce the large card feel:

```tsx
<section
  data-testid="ask-vezor-dock"
  className="rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-rail)] px-4 py-4"
>
```

Use a compact heading row and keep labels visible.

- [ ] **Step 5: Refactor History composition**

In `frontend/src/components/history/HistoryToolbar.tsx`, set:

```tsx
<section
  data-testid="patterns-workbench-toolbar"
  className="rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-neutral)] p-4"
>
```

In `frontend/src/components/history/HistoryTrendPanel.tsx`, set:

```tsx
<section
  data-testid="pattern-trend-panel"
  className="overflow-hidden rounded-[0.9rem] border border-white/10 bg-[color:var(--vezor-surface-neutral)] shadow-[0_22px_56px_-48px_rgba(0,0,0,0.92)]"
>
```

In `frontend/src/pages/History.tsx`, make export quieter:

```tsx
className="rounded-[0.85rem] border border-white/8 bg-white/[0.025] p-4"
```

- [ ] **Step 6: Refactor Evidence media**

In `frontend/src/pages/Incidents.tsx`, change the selected evidence container class to include:

```tsx
className="min-w-0 overflow-hidden rounded-[0.9rem] border border-white/10 bg-[color:var(--vezor-media-black)]"
```

Use `StatusToneBadge` for review status:

```tsx
<StatusToneBadge tone={incident.review_status === "pending" ? "attention" : "healthy"}>
  {incident.review_status}
</StatusToneBadge>
```

- [ ] **Step 7: Run workflow tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/pages/History.test.tsx src/pages/Incidents.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/Live.tsx frontend/src/components/live/AgentInput.tsx frontend/src/components/live/DynamicStats.tsx frontend/src/pages/History.tsx frontend/src/components/history/HistoryToolbar.tsx frontend/src/components/history/HistoryTrendPanel.tsx frontend/src/pages/Incidents.tsx frontend/src/pages/Live.test.tsx frontend/src/pages/History.test.tsx frontend/src/pages/Incidents.test.tsx
git commit -m "feat: differentiate omnisight workflow compositions"
```

---

## Task 5: Rework Sites And Scene Setup Context

**Files:**

- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/pages/Sites.test.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Cameras.test.tsx`

- [ ] **Step 1: Update Sites tests**

In `frontend/src/pages/Sites.test.tsx`, add assertions for deployment context:

```tsx
expect(screen.getByRole("heading", { name: "Deployment Sites" })).toBeInTheDocument();
expect(screen.getByTestId("site-context-grid")).toBeInTheDocument();
expect(screen.getByText(/deployment location/i)).toBeInTheDocument();
```

If the test mocks cameras, include at least one camera with a `site_id` matching a site so scene counts can be verified:

```tsx
expect(screen.getByText("1 scene")).toBeInTheDocument();
```

- [ ] **Step 2: Run Sites test to verify failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Sites.test.tsx
```

Expected: FAIL because current page repeats `Sites` and lacks `site-context-grid`.

- [ ] **Step 3: Implement deployment context grid**

In `frontend/src/pages/Sites.tsx`, import `useCameras` and shared primitives:

```tsx
import { WorkspaceBand, WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { useCameras } from "@/hooks/use-cameras";
```

Build scene counts:

```tsx
const { data: cameras = [] } = useCameras();
const sceneCountBySite = new Map<string, number>();
for (const camera of cameras) {
  sceneCountBySite.set(camera.site_id, (sceneCountBySite.get(camera.site_id) ?? 0) + 1);
}
```

Replace the header with:

```tsx
<WorkspaceBand
  eyebrow="Sites"
  title="Deployment Sites"
  description={`Sites anchor deployment locations, time zones, scene context, and edge fleet planning across ${brandName}.`}
  actions={<Button onClick={() => setDialogOpen(true)}>Add site</Button>}
/>
```

Before the table, add:

```tsx
<section data-testid="site-context-grid" className="grid gap-4 lg:grid-cols-3">
  {sites.map((site) => {
    const sceneCount = sceneCountBySite.get(site.id) ?? 0;
    return (
      <WorkspaceSurface key={site.id} className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
          Deployment location
        </p>
        <h2 className="mt-2 text-xl font-semibold text-[#f4f8ff]">{site.name}</h2>
        <p className="mt-2 text-sm text-[#9eb0cb]">{site.tz}</p>
        <p className="mt-3 text-sm font-medium text-[#dce6f7]">
          {sceneCount} {sceneCount === 1 ? "scene" : "scenes"}
        </p>
        {site.description ? (
          <p className="mt-2 text-sm text-[#8fa4c4]">{site.description}</p>
        ) : null}
      </WorkspaceSurface>
    );
  })}
</section>
```

Keep the table below as a scan-friendly secondary view.

- [ ] **Step 4: Update Scene Setup tests**

In `frontend/src/pages/Cameras.test.tsx`, add:

```tsx
expect(screen.getByTestId("scene-setup-sequence")).toBeInTheDocument();
expect(screen.getByText("Source")).toBeInTheDocument();
expect(screen.getByText("Model")).toBeInTheDocument();
expect(screen.getByText("Privacy")).toBeInTheDocument();
expect(screen.getByText("Boundaries")).toBeInTheDocument();
expect(screen.getByText("Calibration")).toBeInTheDocument();
```

- [ ] **Step 5: Implement Scene Setup sequence band**

In `frontend/src/pages/Cameras.tsx`, below the `WorkspaceBand`/header and above the table, add:

```tsx
<section
  data-testid="scene-setup-sequence"
  className="grid gap-3 rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-rail)] p-4 sm:grid-cols-5"
>
  {["Source", "Model", "Privacy", "Boundaries", "Calibration"].map((step, index) => (
    <div key={step} className="rounded-[0.75rem] border border-white/8 bg-black/20 px-3 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7f96b8]">
        Step {index + 1}
      </p>
      <p className="mt-2 text-sm font-semibold text-[#f4f8ff]">{step}</p>
    </div>
  ))}
</section>
```

- [ ] **Step 6: Run Sites and Scenes tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Sites.test.tsx src/pages/Cameras.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Sites.tsx frontend/src/pages/Sites.test.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Cameras.test.tsx
git commit -m "feat: rework sites and scene setup context"
```

---

## Task 6: Apply Palette Discipline To Operations And Remaining Surfaces

**Files:**

- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`
- Modify: `frontend/src/components/ui/badge.tsx`
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/components/layout/PageHeader.tsx`
- Modify: `frontend/src/components/layout/PageUtilityBar.tsx`
- Modify: `frontend/src/components/layout/InspectorPanel.tsx`

- [ ] **Step 1: Update Settings tests for semantic tones**

In `frontend/src/pages/Settings.test.tsx`, assert Operations still renders and stream diagnostics remain visible:

```tsx
expect(screen.getByRole("heading", { name: "Operations" })).toBeInTheDocument();
expect(screen.getByTestId("edge-fleet-grid")).toBeInTheDocument();
expect(screen.getByTestId("stream-diagnostics-rail")).toBeInTheDocument();
```

- [ ] **Step 2: Refactor Settings panels**

In `frontend/src/pages/Settings.tsx`:

- Use `WorkspaceBand` for the top section.
- Use `WorkspaceSurface` for neutral sections.
- Use `InstrumentRail` where a rail layout is appropriate.
- Use `StatusToneBadge` for runtime statuses if values are simple strings.
- Keep command blocks black and legible.

Update `SummaryTile`:

```tsx
function SummaryTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[0.75rem] border border-white/10 bg-black/25 px-4 py-3">
      <p className="text-xs text-[#93a7c5]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[#f4f8ff]">{value}</p>
    </div>
  );
}
```

Update `Panel`:

```tsx
className="rounded-[0.9rem] border border-[color:var(--vezor-border-neutral)] bg-[color:var(--vezor-surface-neutral)] p-4"
```

- [ ] **Step 3: Tune shared UI defaults**

In `frontend/src/components/ui/button.tsx`, keep the API and make the default more neutral:

```tsx
"inline-flex items-center justify-center rounded-full border border-[color:var(--vezor-border-neutral)] bg-[linear-gradient(180deg,rgba(22,28,38,0.98),rgba(12,17,25,0.98))] px-4 py-2.5 text-sm font-medium text-[var(--argus-text)] shadow-[0_12px_28px_-24px_rgba(0,0,0,0.88)] transition duration-200 hover:border-[color:var(--vezor-border-focus)] hover:bg-[rgba(20,28,39,0.98)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--argus-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--argus-canvas)] disabled:cursor-not-allowed disabled:opacity-60"
```

In `frontend/src/components/ui/badge.tsx`, reduce blue by default:

```tsx
"inline-flex items-center rounded-full border border-white/10 bg-white/[0.035] px-2.5 py-1 text-xs font-medium text-[#c8d6ea]"
```

- [ ] **Step 4: Run shared UI and Settings tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx src/components/ui/calendar.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx frontend/src/components/ui/badge.tsx frontend/src/components/ui/button.tsx frontend/src/components/layout/PageHeader.tsx frontend/src/components/layout/PageUtilityBar.tsx frontend/src/components/layout/InspectorPanel.tsx
git commit -m "style: enforce omnisight palette discipline"
```

---

## Task 7: Verification And Visual QA

**Files:**

- Modify test files only if verification exposes stale expectations.

- [ ] **Step 1: Run focused frontend tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/components/layout/workspace-surfaces.test.tsx \
  src/components/brand/OmniSightField.test.tsx \
  src/pages/SignIn.test.tsx \
  src/pages/Dashboard.test.tsx \
  src/pages/Live.test.tsx \
  src/pages/History.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Cameras.test.tsx \
  src/pages/Sites.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run full frontend verification**

Run:

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec eslint .
git diff --check
```

Expected:

- tests pass
- build passes
- ESLint has 0 errors; known warnings may remain if unchanged
- diff whitespace check passes

- [ ] **Step 3: Browser visual check**

With a dev server running, check:

- `/signin`
- `/dashboard`
- `/live`
- `/history`
- `/incidents`
- `/cameras`
- `/sites`
- `/settings`

Viewport checks:

- 375px wide mobile
- 768px tablet
- 1024px laptop
- 1440px desktop

Acceptance checks:

- Sign-in lens never overlaps the H1 or sign-in controls.
- `/dashboard` is not a redirect.
- Authenticated pages are not all identical header-card layouts.
- Violet appears primarily in sign-in/dashboard accents, not every panel.
- Video and evidence zones use near-black media surfaces.
- Sites presents deployment context before any table.
- No horizontal overflow.

- [ ] **Step 4: Commit any test expectation fixes**

Only if needed:

```bash
git add frontend/src/**/*.test.ts frontend/src/**/*.test.tsx frontend/e2e/*.spec.ts
git commit -m "test: align ui distinctiveness expectations"
```

---

## Self-Review Checklist

- Spec coverage:
  - Sign-in stage: Task 2.
  - Dashboard overview: Task 3.
  - Distinct workflow compositions: Task 4.
  - Palette discipline: Tasks 1 and 6.
  - Sites rework: Task 5.
  - Accessibility/reduced motion: Tasks 2 and 7.
- No backend API changes are required.
- No new runtime dependency is introduced.
- Each task has focused tests and a commit.
- The plan preserves route paths except restoring `/dashboard` behavior.

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-04-30-omnisight-ui-distinctiveness-followup-implementation-plan.md`. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.
