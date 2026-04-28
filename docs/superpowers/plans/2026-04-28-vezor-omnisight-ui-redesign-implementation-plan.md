# Vezor OmniSight UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Vezor frontend so it reads as an OmniSight spatial intelligence platform, with a bold branded entry experience, a faint living lens field in the app shell, calmer operational workflows, and product-neutral language.

**Architecture:** Implement the redesign as reusable visual primitives first, then apply them to the shell and pages. Keep routes and backend behavior stable in the first pass; change labels, copy, surfaces, and motion without changing API contracts. The OmniSight lens field should be a reusable component with `entry`, `overview`, `shell`, and `quiet` variants so dense workflows can opt into only the faint background hint.

**Tech Stack:** React 19, React Router, Tailwind utility classes, CSS variables in `frontend/src/index.css`, Vitest + Testing Library, existing local UI components, no new runtime dependency in the first implementation pass.

---

## Source Spec

Implement from:

- `docs/superpowers/specs/2026-04-28-vezor-omnisight-ui-redesign-design.md`

Use these defaults from the spec:

- Do not add a dedicated `/overview` route in this implementation pass.
- Use `History & Patterns` before moving all the way to `Patterns`.
- Use `Scenes` in navigation and `Scene Setup` as the page title; keep the `/cameras` route only as internal routing plumbing.
- Build the OmniSight field with CSS/HTML first. Do not add Three.js in this pass.
- Preserve honest runtime state. Never imply a worker is running unless the data reports it.

## File Map

Create:

- `frontend/src/components/brand/OmniSightField.tsx`
  - Owns the code-native lens/orbital field.
  - Exposes `variant` and `className` props.
  - Renders `aria-hidden="true"` decoration only.
- `frontend/src/components/brand/OmniSightField.test.tsx`
  - Verifies variants, decorative semantics, and stable class hooks.
- `frontend/src/components/layout/WorkspaceTransition.tsx`
  - Wraps routed page content with a location-keyed transition surface.
  - Keeps markup simple and compatible with reduced motion.
- `frontend/src/components/layout/WorkspaceTransition.test.tsx`
  - Verifies content renders and location-specific key/class hooks are present.
- `frontend/src/copy/omnisight.ts`
  - Centralizes high-level product labels used by nav, page titles, empty states, and command labels.
- `frontend/src/copy/omnisight.test.ts`
  - Verifies key labels remain product-neutral.

Modify:

- `frontend/src/index.css`
  - Add Vezor visual tokens, OmniSight field classes, motion utilities, reduced-motion rules.
- `frontend/src/pages/SignIn.tsx`
  - Rebuild entry page around the bold OmniSight field and broader OmniSight copy.
- `frontend/src/pages/SignIn.test.tsx`
  - Update assertions for broad platform copy.
- `frontend/src/App.test.tsx`
  - Update branded sign-in assertions.
- `frontend/src/components/layout/AppShell.tsx`
  - Add subtle shell field and route transition wrapper.
- `frontend/src/components/layout/AppIconRail.tsx`
  - Add active lens-light treatment and refined rail classes.
- `frontend/src/components/layout/AppContextRail.tsx`
  - Use product-neutral nav copy from `omnisight.ts`.
- `frontend/src/components/layout/TopNav.tsx`
  - Update nav labels while preserving routes; `Cameras` must not remain a user-facing nav item.
- `frontend/src/components/layout/AppShell.test.tsx`
  - Update nav and shell assertions.
- `frontend/src/components/layout/PageHeader.tsx`
  - Tune shared page header classes for the new visual system.
- `frontend/src/components/layout/PageUtilityBar.tsx`
  - Tune shared utility surface classes.
- `frontend/src/components/layout/InspectorPanel.tsx`
  - Tune shared inspector surface classes.
- `frontend/src/components/ui/button.tsx`
  - Refine default button treatment without changing API.
- `frontend/src/components/ui/badge.tsx`
  - Refine default badge treatment without changing API.
- `frontend/src/pages/Live.tsx`
  - Rename to Live Intelligence, Ask Vezor, Signals in View, Resolved Intent.
- `frontend/src/pages/Live.test.tsx`
  - Update assertions for copy and truthful status labels.
- `frontend/src/components/live/AgentInput.tsx`
  - Rename command input copy and example text.
- `frontend/src/components/live/AgentInput.test.tsx`
  - Update labels and example expectations.
- `frontend/src/components/live/DynamicStats.tsx`
  - Rename panel and empty-state copy.
- `frontend/src/components/live/LiveSparkline.tsx`
  - Minor visual class tuning only.
- `frontend/src/pages/History.tsx`
  - Rename page copy to History & Patterns and demote count/speed specifics.
- `frontend/src/pages/History.test.tsx`
  - Update page and toolbar copy assertions.
- `frontend/src/components/history/HistoryToolbar.tsx`
  - Update label text while preserving filter behavior.
- `frontend/src/components/history/HistoryTrendPanel.tsx`
  - Update empty/loading copy and surface classes.
- `frontend/src/pages/Incidents.tsx`
  - Keep Evidence Desk as product-facing name; improve queue/evidence/facts wording.
- `frontend/src/pages/Incidents.test.tsx`
  - Update Evidence Desk assertions.
- `frontend/src/pages/Cameras.tsx`
  - Reframe page title to Scene Setup while keeping camera-specific fields.
- `frontend/src/pages/Cameras.test.tsx`
  - Update page title and empty-state assertions.
- `frontend/src/components/cameras/CameraWizard.tsx`
  - Rename count boundaries to event boundaries in user-facing copy.
- `frontend/src/components/cameras/CameraWizard.test.tsx`
  - Update event-boundary and example text assertions.
- `frontend/src/pages/Settings.tsx`
  - Rename user-facing Operations copy and stream diagnostics language.
- `frontend/src/pages/Settings.test.tsx`
  - Update Operations copy assertions.
- `frontend/src/components/layout/UserMenu.tsx`
  - Replace `Unknown user` with more polished neutral copy.
- `frontend/src/components/sites/SiteDialog.tsx`
  - Review example text for product-neutral language; keep practical examples.

Do not modify generated API types or backend files for this redesign pass.

---

## Task 1: Centralize OmniSight Product Copy

**Files:**

- Create: `frontend/src/copy/omnisight.ts`
- Create: `frontend/src/copy/omnisight.test.ts`
- Modify: `frontend/src/components/layout/TopNav.tsx`

- [ ] **Step 1: Write the failing copy tests**

Create `frontend/src/copy/omnisight.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import {
  omniEmptyStates,
  omniLabels,
  omniNavGroups,
  omniPlaceExamples,
} from "@/copy/omnisight";

describe("omnisight copy", () => {
  test("uses broad product labels instead of traffic-specific framing", () => {
    expect(omniLabels.liveTitle).toBe("Live Intelligence");
    expect(omniLabels.historyTitle).toBe("History & Patterns");
    expect(omniLabels.evidenceTitle).toBe("Evidence Desk");
    expect(omniLabels.sceneSetupTitle).toBe("Scene Setup");
    expect(omniLabels.operationsTitle).toBe("Operations");
  });

  test("keeps navigation broad while preserving existing route paths", () => {
    expect(omniNavGroups).toEqual([
      {
        label: "Intelligence",
        items: [
          { label: "Live", to: "/live" },
          { label: "History", to: "/history" },
          { label: "Evidence", to: "/incidents" },
        ],
      },
      {
        label: "Control",
        items: [
          { label: "Sites", to: "/sites" },
          { label: "Scenes", to: "/cameras" },
          { label: "Operations", to: "/settings" },
        ],
      },
    ]);
  });

  test("uses product-neutral empty states and examples", () => {
    expect(omniEmptyStates.noScenes).toBe("No scenes are connected yet.");
    expect(omniEmptyStates.noSignals).toBe(
      "Live telemetry has not produced visible signals yet.",
    );
    expect(omniPlaceExamples.askVezor).toBe("show people near restricted zones");
  });
});
```

- [ ] **Step 2: Run the failing copy tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/copy/omnisight.test.ts
```

Expected: FAIL because `@/copy/omnisight` does not exist.

- [ ] **Step 3: Implement the copy module**

Create `frontend/src/copy/omnisight.ts`:

```ts
export const omniLabels = {
  liveTitle: "Live Intelligence",
  historyTitle: "History & Patterns",
  evidenceTitle: "Evidence Desk",
  sceneSetupTitle: "Scene Setup",
  operationsTitle: "Operations",
  askVezorTitle: "Ask Vezor",
  resolvedIntentTitle: "Resolved Intent",
  signalsInViewTitle: "Signals in View",
  streamDiagnosticsTitle: "Stream diagnostics",
  reviewQueueTitle: "Review Queue",
  evidenceMediaTitle: "Evidence",
  factsTitle: "Facts",
} as const;

export const omniEmptyStates = {
  noScenes: "No scenes are connected yet.",
  noSignals: "Live telemetry has not produced visible signals yet.",
  noEvidence: "No evidence records match the current filters.",
  noSites: "No sites are configured yet.",
} as const;

export const omniPlaceExamples = {
  askVezor: "show people near restricted zones",
  runtimeVocabulary: "person, forklift, safety vest",
  eventClasses: "person, vehicle",
  siteName: "HQ",
  siteDescription: "Main campus or operating zone",
  timezone: "Europe/Zurich",
  edgeHostname: "edge-kit-01",
  rtspUrl: "rtsp://camera.local/live",
} as const;

export const omniNavGroups = [
  {
    label: "Intelligence",
    items: [
      { label: "Live", to: "/live" },
      { label: "History", to: "/history" },
      { label: "Evidence", to: "/incidents" },
    ],
  },
  {
    label: "Control",
    items: [
      { label: "Sites", to: "/sites" },
      { label: "Scenes", to: "/cameras" },
      { label: "Operations", to: "/settings" },
    ],
  },
] as const;
```

- [ ] **Step 4: Wire nav labels to copy module**

Modify `frontend/src/components/layout/TopNav.tsx`.

Add import:

```ts
import { omniNavGroups } from "@/copy/omnisight";
```

Replace `workspaceNavGroups` with:

```ts
export const workspaceNavGroups = omniNavGroups.map((group) => ({
  label: group.label,
  items: group.items.map((item) => ({
    ...item,
    icon:
      item.to === "/live"
        ? Radio
        : item.to === "/history"
          ? Clock3
          : item.to === "/incidents"
            ? ShieldAlert
            : item.to === "/sites"
              ? MapPinned
              : item.to === "/cameras"
                ? Video
                : Settings2,
  })),
})) as readonly WorkspaceNavGroup[];
```

Keep route paths unchanged. The `/cameras` route remains an implementation detail, but the user-facing nav label must be `Scenes`.

- [ ] **Step 5: Run copy and shell tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/copy/omnisight.test.ts src/components/layout/AppShell.test.tsx
```

Expected: copy tests PASS; AppShell tests may FAIL where they assert old group names. Update those assertions to expect `Intelligence` and `Control`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/copy/omnisight.ts frontend/src/copy/omnisight.test.ts frontend/src/components/layout/TopNav.tsx frontend/src/components/layout/AppShell.test.tsx
git commit -m "feat: centralize omnisight product copy"
```

---

## Task 2: Add Visual Tokens and Surface Defaults

**Files:**

- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/components/ui/badge.tsx`
- Modify: `frontend/src/components/layout/PageHeader.tsx`
- Modify: `frontend/src/components/layout/PageUtilityBar.tsx`
- Modify: `frontend/src/components/layout/InspectorPanel.tsx`

- [ ] **Step 1: Write a style-token test**

Create or extend `frontend/src/brand/product-assets.test.ts` with:

```ts
import { describe, expect, test } from "vitest";

import fs from "node:fs/promises";
import path from "node:path";

describe("Vezor visual system tokens", () => {
  test("defines OmniSight lens color tokens and field motion classes", async () => {
    const css = await fs.readFile(path.join(process.cwd(), "src/index.css"), "utf8");

    expect(css).toContain("--vezor-lens-cerulean");
    expect(css).toContain("--vezor-lens-violet");
    expect(css).toContain("--vezor-surface-depth");
    expect(css).toContain(".omnisight-field");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
```

If `product-assets.test.ts` already imports `fs` and `path`, add only the test body and avoid duplicate imports.

- [ ] **Step 2: Run the failing token test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts -t "Vezor visual system tokens"
```

Expected: FAIL because the new tokens and classes do not exist.

- [ ] **Step 3: Add tokens and base classes**

Modify `frontend/src/index.css` inside `:root`:

```css
  --vezor-lens-cerulean: #6ebdff;
  --vezor-lens-violet: #7e53ff;
  --vezor-lens-aqua: #76e0ff;
  --vezor-success: #72e3a6;
  --vezor-attention: #f2bd5c;
  --vezor-risk: #f08aa2;
  --vezor-surface-depth: rgba(9, 14, 23, 0.82);
  --vezor-surface-raised: rgba(13, 20, 32, 0.92);
  --vezor-shadow-depth: 0 28px 80px -54px rgba(63, 121, 255, 0.68);
```

Append these classes near the end of `frontend/src/index.css`:

```css
.omnisight-field {
  pointer-events: none;
  position: absolute;
  inset: 0;
  overflow: hidden;
  isolation: isolate;
}

.omnisight-field__lens {
  position: absolute;
  border-radius: 9999px;
  background:
    radial-gradient(circle at 35% 30%, rgba(224, 247, 255, 0.96) 0 8%, transparent 9%),
    radial-gradient(circle at 44% 42%, var(--vezor-lens-cerulean) 0 24%, var(--vezor-lens-violet) 58%, rgba(34, 18, 71, 0.7) 82%);
  box-shadow:
    0 0 44px rgba(112, 177, 255, 0.42),
    0 0 120px rgba(105, 87, 255, 0.24);
}

.omnisight-field__ring {
  position: absolute;
  border-radius: 9999px;
  border: 1px solid rgba(218, 239, 255, 0.16);
  transform: rotateX(64deg) rotateZ(-18deg);
}

.omnisight-field__surface {
  position: absolute;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(8, 13, 22, 0.68);
  box-shadow: 0 22px 56px -44px rgba(0, 0, 0, 0.95);
  backdrop-filter: blur(10px);
}

.omnisight-field--entry .omnisight-field__lens {
  width: 13rem;
  height: 13rem;
  left: calc(50% - 6.5rem);
  top: 18%;
}

.omnisight-field--shell .omnisight-field__lens {
  width: 4.75rem;
  height: 4.75rem;
  right: 4rem;
  top: 2rem;
  opacity: 0.22;
}

.omnisight-field--quiet .omnisight-field__lens {
  width: 3rem;
  height: 3rem;
  right: 1.5rem;
  top: 1.25rem;
  opacity: 0.12;
}

@media (prefers-reduced-motion: no-preference) {
  .omnisight-field__ring {
    animation: omnisight-orbit 18s ease-in-out infinite alternate;
  }
}

@media (prefers-reduced-motion: reduce) {
  .omnisight-field__ring {
    animation: none;
  }
}

@keyframes omnisight-orbit {
  from {
    transform: rotateX(64deg) rotateZ(-18deg) translate3d(0, 0, 0);
  }
  to {
    transform: rotateX(64deg) rotateZ(12deg) translate3d(0.4rem, -0.2rem, 0);
  }
}
```

- [ ] **Step 4: Refine UI primitives**

Modify `frontend/src/components/ui/button.tsx` default classes to:

```ts
"inline-flex items-center justify-center rounded-[0.95rem] border border-[color:var(--argus-border-strong)] bg-[linear-gradient(180deg,rgba(29,43,65,0.98),rgba(15,22,35,0.98))] px-4 py-2.5 text-sm font-medium text-[var(--argus-text)] shadow-[0_16px_32px_-24px_rgba(63,121,255,0.58)] transition duration-200 hover:border-[color:var(--argus-border-highlight)] hover:bg-[linear-gradient(180deg,rgba(39,57,84,0.98),rgba(19,29,45,0.98))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--argus-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--argus-canvas)] disabled:cursor-not-allowed disabled:opacity-60"
```

Modify `frontend/src/components/ui/badge.tsx` default classes to:

```ts
"inline-flex items-center rounded-[0.7rem] border border-[color:var(--argus-border)] bg-[color:var(--argus-surface-soft)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--argus-text-muted)]"
```

Modify shared layout surfaces:

`PageHeader.tsx` header classes:

```ts
"flex flex-col gap-4 border-b border-white/[0.07] pb-5 sm:flex-row sm:items-end sm:justify-between"
```

`PageUtilityBar.tsx` section classes:

```ts
"rounded-[1.1rem] border border-white/[0.08] bg-[color:var(--vezor-surface-depth)] px-4 py-3 shadow-[var(--vezor-shadow-depth)] backdrop-blur-md"
```

`InspectorPanel.tsx` aside classes:

```ts
"rounded-[1.1rem] border border-white/[0.08] bg-[color:var(--vezor-surface-depth)] px-4 py-4 shadow-[var(--vezor-shadow-depth)]"
```

- [ ] **Step 5: Run tests and build**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts src/components/ui/calendar.test.tsx
corepack pnpm --dir frontend build
```

Expected: PASS. The build must not report TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/index.css frontend/src/brand/product-assets.test.ts frontend/src/components/ui/button.tsx frontend/src/components/ui/badge.tsx frontend/src/components/layout/PageHeader.tsx frontend/src/components/layout/PageUtilityBar.tsx frontend/src/components/layout/InspectorPanel.tsx
git commit -m "style: add omnisight visual tokens"
```

---

## Task 3: Build the OmniSight Field Component

**Files:**

- Create: `frontend/src/components/brand/OmniSightField.tsx`
- Create: `frontend/src/components/brand/OmniSightField.test.tsx`

- [ ] **Step 1: Write the failing component tests**

Create `frontend/src/components/brand/OmniSightField.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { OmniSightField } from "@/components/brand/OmniSightField";

describe("OmniSightField", () => {
  test("renders decorative entry variant with stable lens hooks", () => {
    render(<OmniSightField variant="entry" />);

    const field = screen.getByTestId("omnisight-field");
    expect(field).toHaveAttribute("aria-hidden", "true");
    expect(field).toHaveClass("omnisight-field--entry");
    expect(field.querySelector(".omnisight-field__lens")).not.toBeNull();
    expect(field.querySelectorAll(".omnisight-field__ring")).toHaveLength(2);
    expect(field.querySelectorAll(".omnisight-field__surface").length).toBeGreaterThan(0);
  });

  test("renders quiet variant without overview surfaces", () => {
    render(<OmniSightField variant="quiet" />);

    const field = screen.getByTestId("omnisight-field");
    expect(field).toHaveClass("omnisight-field--quiet");
    expect(field.querySelector(".omnisight-field__lens")).not.toBeNull();
    expect(field.querySelectorAll(".omnisight-field__surface")).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run the failing component tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/brand/OmniSightField.test.tsx
```

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/brand/OmniSightField.tsx`:

```tsx
import { cn } from "@/lib/utils";

type OmniSightFieldVariant = "entry" | "overview" | "shell" | "quiet";

type OmniSightFieldProps = {
  variant?: OmniSightFieldVariant;
  className?: string;
};

const overviewSurfaces = [
  { label: "Live Scenes", className: "left-[9%] top-[16%] h-16 w-36 rounded-[1rem]" },
  { label: "Evidence", className: "right-[7%] top-[18%] h-20 w-40 rounded-[1rem]" },
  { label: "Patterns", className: "left-[18%] bottom-[16%] h-20 w-44 rounded-[1rem]" },
  { label: "Edge Fleet", className: "right-[13%] bottom-[18%] h-16 w-36 rounded-[1rem]" },
];

export function OmniSightField({
  variant = "shell",
  className,
}: OmniSightFieldProps) {
  const showSurfaces = variant === "entry" || variant === "overview";

  return (
    <div
      aria-hidden="true"
      data-testid="omnisight-field"
      className={cn("omnisight-field", `omnisight-field--${variant}`, className)}
    >
      <div className="omnisight-field__ring left-[calc(50%-11rem)] top-[18%] h-40 w-[22rem]" />
      <div className="omnisight-field__ring left-[calc(50%-10rem)] top-[22%] h-36 w-80 rotate-[25deg] opacity-60" />
      <div className="omnisight-field__lens" />
      {showSurfaces
        ? overviewSurfaces.map((surface) => (
            <div
              key={surface.label}
              className={cn("omnisight-field__surface", surface.className)}
            >
              <span className="sr-only">{surface.label}</span>
            </div>
          ))
        : null}
    </div>
  );
}
```

- [ ] **Step 4: Run component tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/brand/OmniSightField.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/brand/OmniSightField.tsx frontend/src/components/brand/OmniSightField.test.tsx
git commit -m "feat: add omnisight field component"
```

---

## Task 4: Redesign the Sign-In Entry Surface

**Files:**

- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/pages/SignIn.test.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing sign-in assertions**

Modify `frontend/src/pages/SignIn.test.tsx` to assert the new product promise:

```tsx
expect(
  screen.getByRole("heading", { name: /omnisight for every live environment/i }),
).toBeInTheDocument();
expect(
  screen.getByText(/connects scenes, models, events, evidence, and edge operations/i),
).toBeInTheDocument();
expect(screen.getByTestId("omnisight-field")).toHaveClass("omnisight-field--entry");
```

Modify `frontend/src/App.test.tsx` to assert:

```tsx
expect(
  screen.getByRole("heading", { name: /omnisight for every live environment/i }),
).toBeInTheDocument();
```

- [ ] **Step 2: Run failing sign-in tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx src/App.test.tsx
```

Expected: FAIL because the old headline remains.

- [ ] **Step 3: Implement the new sign-in layout**

Modify `frontend/src/pages/SignIn.tsx`.

Add import:

```ts
import { OmniSightField } from "@/components/brand/OmniSightField";
```

Replace the returned JSX with:

```tsx
return (
  <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_50%_20%,rgba(110,189,255,0.22),transparent_28%),linear-gradient(180deg,var(--argus-canvas)_0%,var(--argus-canvas-raise)_48%,#121927_100%)] px-6 py-10 text-[var(--argus-text)]">
    <OmniSightField variant="entry" className="opacity-95" />
    <div className="relative z-10 mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-10 lg:grid-cols-[minmax(0,1.08fr)_minmax(340px,408px)]">
      <section className="max-w-2xl space-y-7">
        <ProductLockup className="h-14 w-auto" />
        <div className="space-y-5">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--argus-text-muted)]">
            {productBrand.descriptor}
          </p>
          <h1 className="text-4xl font-semibold tracking-[0.01em] text-[var(--argus-text)] sm:text-6xl">
            OmniSight for every live environment.
          </h1>
          <p className="max-w-xl text-lg leading-8 text-[var(--argus-text-muted)]">
            {brandName} connects scenes, models, events, evidence, and edge operations
            into one spatial intelligence layer.
          </p>
        </div>
      </section>
      <section className="w-full rounded-[1.35rem] border border-[color:var(--argus-border-strong)] bg-[color:var(--vezor-surface-depth)] p-6 text-[var(--argus-text)] shadow-[var(--vezor-shadow-depth)] backdrop-blur-xl sm:p-7">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--argus-text-muted)]">
          Secure entry
        </p>
        <h2 className="mt-4 text-2xl font-semibold text-[var(--argus-text)]">Sign in</h2>
        <p className="mt-2 text-sm text-[var(--argus-text-muted)]">
          Use your {brandName} identity provider account to continue.
        </p>
        <Button
          className="mt-6 w-full border-transparent bg-[linear-gradient(135deg,var(--vezor-lens-cerulean)_0%,var(--vezor-lens-violet)_100%)] text-[#06111a] shadow-[0_18px_38px_-24px_rgba(53,184,255,0.55)] hover:border-transparent hover:brightness-110"
          onClick={() => void signIn()}
        >
          Sign in
        </Button>
      </section>
    </div>
  </main>
);
```

- [ ] **Step 4: Run sign-in tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SignIn.tsx frontend/src/pages/SignIn.test.tsx frontend/src/App.test.tsx
git commit -m "feat: redesign omnisight sign-in"
```

---

## Task 5: Add the Living Shell Background and Route Transition Wrapper

**Files:**

- Create: `frontend/src/components/layout/WorkspaceTransition.tsx`
- Create: `frontend/src/components/layout/WorkspaceTransition.test.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/components/layout/AppIconRail.tsx`
- Modify: `frontend/src/components/layout/AppContextRail.tsx`
- Modify: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: Write failing transition tests**

Create `frontend/src/components/layout/WorkspaceTransition.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { WorkspaceTransition } from "@/components/layout/WorkspaceTransition";

describe("WorkspaceTransition", () => {
  test("wraps routed content with a transition surface", () => {
    render(
      <MemoryRouter initialEntries={["/live"]}>
        <WorkspaceTransition>
          <h1>Live Intelligence</h1>
        </WorkspaceTransition>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /live intelligence/i })).toBeInTheDocument();
    expect(screen.getByTestId("workspace-transition")).toHaveAttribute(
      "data-route",
      "/live",
    );
  });
});
```

- [ ] **Step 2: Update shell test expectations before implementation**

Modify `frontend/src/components/layout/AppShell.test.tsx`:

```tsx
expect(screen.getByTestId("omnisight-field")).toHaveClass("omnisight-field--shell");
expect(screen.getByTestId("workspace-transition")).toBeInTheDocument();
expect(screen.getByRole("navigation", { name: /intelligence/i })).toBeInTheDocument();
expect(screen.getByRole("navigation", { name: /control/i })).toBeInTheDocument();
```

- [ ] **Step 3: Run failing shell tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/WorkspaceTransition.test.tsx src/components/layout/AppShell.test.tsx
```

Expected: FAIL because `WorkspaceTransition` does not exist and AppShell does not render `OmniSightField`.

- [ ] **Step 4: Implement WorkspaceTransition**

Create `frontend/src/components/layout/WorkspaceTransition.tsx`:

```tsx
import { type PropsWithChildren } from "react";
import { useLocation } from "react-router-dom";

export function WorkspaceTransition({ children }: PropsWithChildren) {
  const location = useLocation();

  return (
    <div
      key={location.pathname}
      data-route={location.pathname}
      data-testid="workspace-transition"
      className="animate-[workspace-enter_220ms_ease-out] motion-reduce:animate-none"
    >
      {children}
    </div>
  );
}
```

Append to `frontend/src/index.css`:

```css
@keyframes workspace-enter {
  from {
    opacity: 0;
    transform: translate3d(0, 0.35rem, 0) scale(0.997);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
  }
}
```

- [ ] **Step 5: Add shell field and transition wrapper**

Modify `frontend/src/components/layout/AppShell.tsx`.

Add imports:

```ts
import { OmniSightField } from "@/components/brand/OmniSightField";
import { WorkspaceTransition } from "@/components/layout/WorkspaceTransition";
```

Replace the main return with:

```tsx
return (
  <main className="relative min-h-screen overflow-hidden bg-[#080c12] text-[#eef4ff]">
    <OmniSightField variant="shell" className="opacity-80" />
    <div
      className={cn(
        "relative z-10 grid min-h-screen grid-cols-[4.75rem_minmax(0,1fr)]",
        isContextRailExpanded &&
          "lg:grid-cols-[4.75rem_16.5rem_minmax(0,1fr)] xl:grid-cols-[4.75rem_17.5rem_minmax(0,1fr)]",
      )}
    >
      <AppIconRail
        contextRailExpanded={isContextRailExpanded}
        onToggleContextRail={toggleContextRail}
      />
      {isContextRailExpanded ? <AppContextRail /> : null}
      <section className="min-w-0 px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
        <div className="min-h-[calc(100vh-2rem)] rounded-[1.25rem] border border-white/[0.07] bg-[rgba(8,12,18,0.74)] shadow-[0_28px_86px_-60px_rgba(0,0,0,0.94)] backdrop-blur-xl">
          <WorkspaceTransition>{children}</WorkspaceTransition>
        </div>
      </section>
    </div>
  </main>
);
```

- [ ] **Step 6: Refine rails**

In `AppIconRail.tsx`, change active nav classes to include a lens glow:

```ts
isActive
  ? "border-[rgba(118,224,255,0.42)] bg-[linear-gradient(135deg,rgba(110,189,255,0.22),rgba(126,83,255,0.18))] text-[#eef4ff] shadow-[0_0_28px_-14px_rgba(110,189,255,0.8)]"
  : "border-white/[0.06] bg-white/[0.03] text-[#9fb0c9] hover:border-[#35598d] hover:bg-white/[0.06] hover:text-[#eef4ff]"
```

In `AppContextRail.tsx`, keep behavior but rely on updated nav group labels from Task 1. Keep `aria-label={group.label}` so tests can find `Intelligence` and `Control`.

- [ ] **Step 7: Run shell tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/WorkspaceTransition.test.tsx src/components/layout/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/layout/WorkspaceTransition.tsx frontend/src/components/layout/WorkspaceTransition.test.tsx frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/AppIconRail.tsx frontend/src/components/layout/AppContextRail.tsx frontend/src/components/layout/AppShell.test.tsx frontend/src/index.css
git commit -m "feat: add omnisight shell motion"
```

---

## Task 6: Update Live Intelligence Copy and Surfaces

**Files:**

- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`
- Modify: `frontend/src/components/live/AgentInput.tsx`
- Modify: `frontend/src/components/live/AgentInput.test.tsx`
- Modify: `frontend/src/components/live/DynamicStats.tsx`
- Modify: `frontend/src/components/live/LiveSparkline.tsx`

- [ ] **Step 1: Write failing Live tests**

Update `frontend/src/pages/Live.test.tsx` assertions:

```tsx
expect(await screen.findByRole("heading", { name: /live intelligence/i })).toBeInTheDocument();
expect(screen.getByText(/signals in view/i)).toBeInTheDocument();
expect(screen.getByText(/resolved intent/i)).toBeInTheDocument();
expect(screen.queryByText(/live command surface/i)).not.toBeInTheDocument();
```

Update `frontend/src/components/live/AgentInput.test.tsx` assertions:

```tsx
expect(screen.getByText(/ask vezor/i)).toBeInTheDocument();
expect(screen.getByLabelText(/ask vezor/i)).toHaveAttribute(
  "placeholder",
  "show people near restricted zones",
);
expect(screen.getByRole("button", { name: /apply/i })).toBeInTheDocument();
```

- [ ] **Step 2: Run failing Live tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/components/live/AgentInput.test.tsx
```

Expected: FAIL because old copy remains.

- [ ] **Step 3: Update Live page copy**

Modify `frontend/src/pages/Live.tsx`.

Add import:

```ts
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
```

Replace PageHeader props:

```tsx
<PageHeader
  eyebrow="Live"
  title={omniLabels.liveTitle}
  description="Watch scenes, signals, and operator intent converge in one live spatial intelligence layer."
  actions={...}
/>
```

Replace utility bar title and description:

```tsx
title="Ask Vezor without leaving the live wall"
description={
  isLoading
    ? "Loading connected scenes."
    : "Resolved intent narrows the operator view while telemetry remains truthful."
}
```

Replace loading and empty states:

```tsx
Loading connected scenes...
```

```tsx
{omniEmptyStates.noScenes}
```

Replace InspectorPanel:

```tsx
<InspectorPanel
  title={omniLabels.resolvedIntentTitle}
  description="Selection-aware interpretation for the current live view."
  ...
>
```

Replace no-query copy:

```tsx
No intent is active. Operators are seeing the current signal set from each live scene.
```

- [ ] **Step 4: Update AgentInput copy**

Modify `frontend/src/components/live/AgentInput.tsx`.

Add import:

```ts
import { omniLabels, omniPlaceExamples } from "@/copy/omnisight";
```

Replace section copy:

```tsx
<p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">
  {omniLabels.askVezorTitle}
</p>
<h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">
  Resolve operator intent across live scenes.
</h3>
<p className="mt-2 text-sm text-[#8ca2c5]">
  Ask {brandName} for the signals you need, then keep the live wall focused
  while the underlying telemetry remains unchanged.
</p>
```

Replace labels:

```tsx
Scope
Ask Vezor
```

Replace input:

```tsx
aria-label={omniLabels.askVezorTitle}
placeholder={omniPlaceExamples.askVezor}
```

Replace button text:

```tsx
{isSubmitting ? "Resolving..." : "Apply"}
```

- [ ] **Step 5: Update DynamicStats copy**

Modify `frontend/src/components/live/DynamicStats.tsx`.

Add import:

```ts
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
```

Replace header:

```tsx
{omniLabels.signalsInViewTitle}
```

Replace subheading:

```tsx
Live signals in view.
```

Replace empty state:

```tsx
{omniEmptyStates.noSignals}
```

- [ ] **Step 6: Run Live tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/components/live/AgentInput.test.tsx src/components/live/LiveSparkline.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx frontend/src/components/live/AgentInput.tsx frontend/src/components/live/AgentInput.test.tsx frontend/src/components/live/DynamicStats.tsx frontend/src/components/live/LiveSparkline.tsx
git commit -m "feat: reframe live as intelligence"
```

---

## Task 7: Update History, Evidence, Scene Setup, and Operations Language

**Files:**

- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/History.test.tsx`
- Modify: `frontend/src/components/history/HistoryToolbar.tsx`
- Modify: `frontend/src/components/history/HistoryTrendPanel.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Incidents.test.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Cameras.test.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`

- [ ] **Step 1: Write failing broad-copy tests**

Update tests to assert new labels:

`frontend/src/pages/History.test.tsx`:

```tsx
expect(await screen.findByRole("heading", { name: /history & patterns/i })).toBeInTheDocument();
expect(screen.queryByText(/as .* buckets/i)).not.toBeInTheDocument();
```

`frontend/src/pages/Incidents.test.tsx`:

```tsx
expect(await screen.findByRole("heading", { name: /evidence desk/i })).toBeInTheDocument();
expect(screen.getByRole("heading", { name: /review queue/i })).toBeInTheDocument();
expect(screen.getByRole("heading", { name: /facts/i })).toBeInTheDocument();
```

`frontend/src/pages/Cameras.test.tsx`:

```tsx
expect(await screen.findByRole("heading", { name: /scene setup/i })).toBeInTheDocument();
expect(screen.queryByText(/no cameras yet/i)).not.toBeInTheDocument();
```

`frontend/src/pages/Settings.test.tsx`:

```tsx
expect(await screen.findByRole("heading", { name: /operations/i })).toBeInTheDocument();
expect(screen.getByText(/stream diagnostics/i)).toBeInTheDocument();
expect(screen.queryByText(/delivery truth/i)).not.toBeInTheDocument();
```

`frontend/src/components/cameras/CameraWizard.test.tsx`:

```tsx
expect(screen.getByText(/event boundaries/i)).toBeInTheDocument();
expect(screen.queryByText(/count boundaries/i)).not.toBeInTheDocument();
```

- [ ] **Step 2: Run failing page tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx src/pages/Incidents.test.tsx src/pages/Cameras.test.tsx src/pages/Settings.test.tsx src/components/cameras/CameraWizard.test.tsx
```

Expected: FAIL where old copy remains.

- [ ] **Step 3: Update History copy**

Modify `frontend/src/pages/History.tsx`.

Add import:

```ts
import { omniLabels } from "@/copy/omnisight";
```

If there is no `PageHeader`, add a compact header above `HistoryToolbar`:

```tsx
<PageHeader
  eyebrow="History"
  title={omniLabels.historyTitle}
  description="Explore how signals, events, and scene patterns change over time."
/>
```

Update export text:

```tsx
<p className="mt-1">
  Export the current pattern view at {state.granularity} granularity.
</p>
```

Do not rename metric values or API fields.

- [ ] **Step 4: Update Evidence Desk copy**

Modify `frontend/src/pages/Incidents.tsx`.

Add import:

```ts
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
```

Replace existing page description:

```tsx
Review evidence records, confirm state, and move from signal to decision without leaving the desk.
```

Rename queue heading:

```tsx
<h3 className="text-lg font-semibold text-[#eef4ff]">{omniLabels.reviewQueueTitle}</h3>
```

Rename facts panel heading to:

```tsx
{omniLabels.factsTitle}
```

Replace empty evidence copy:

```tsx
{omniEmptyStates.noEvidence}
```

- [ ] **Step 5: Update Scene Setup copy**

Modify `frontend/src/pages/Cameras.tsx`.

Add import:

```ts
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
```

Replace heading:

```tsx
{omniLabels.sceneSetupTitle}
```

Replace description:

```tsx
Scene setup connects source streams, models, privacy rules, event boundaries, and calibration so Vezor can understand each environment.
```

Replace empty state:

```tsx
{omniEmptyStates.noScenes}
```

Keep table column `Name`, `Site`, `Mode`, `Delivery`, `Tracker`, `Actions` in this pass.

- [ ] **Step 6: Update CameraWizard copy**

Modify `frontend/src/components/cameras/CameraWizard.tsx`.

Replace user-facing phrases:

```tsx
Count boundaries
```

with:

```tsx
Event boundaries
```

Replace:

```tsx
No boundaries configured yet. Add a line for pass-by counting or a polygon for occupancy.
```

with:

```tsx
No event boundaries configured yet. Add a line for crossing events or a zone for enter and exit events.
```

Replace:

```tsx
Polygons count entries and exits whenever the tracked footpoint crosses the zone edge.
```

with:

```tsx
Zones create enter and exit events whenever the tracked footpoint crosses the boundary.
```

Replace example classes:

```tsx
placeholder="person,car"
```

with:

```tsx
placeholder={omniPlaceExamples.eventClasses}
```

Add `omniPlaceExamples` import if needed.

- [ ] **Step 7: Update Operations copy**

Modify `frontend/src/pages/Settings.tsx`.

Add import:

```ts
import { omniLabels, omniPlaceExamples } from "@/copy/omnisight";
```

Replace page title:

```tsx
{omniLabels.operationsTitle}
```

Replace description:

```tsx
Monitor planned workers, runtime reports, bootstrap material, and stream diagnostics for the fleet.
```

Replace tile label:

```tsx
Planned workers
```

Replace panel title:

```tsx
<Panel title={omniLabels.streamDiagnosticsTitle} icon={<Copy className="size-4" />}>
```

Replace input example:

```tsx
placeholder={omniPlaceExamples.edgeHostname}
```

Replace `source unknown` with:

```ts
return "source not reported";
```

Replace `unknown` reason fallback with:

```ts
return (reason ?? "not reported").replaceAll("_", " ");
```

- [ ] **Step 8: Run page tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx src/pages/Incidents.test.tsx src/pages/Cameras.test.tsx src/pages/Settings.test.tsx src/components/cameras/CameraWizard.test.tsx
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/History.tsx frontend/src/pages/History.test.tsx frontend/src/components/history/HistoryToolbar.tsx frontend/src/components/history/HistoryTrendPanel.tsx frontend/src/pages/Incidents.tsx frontend/src/pages/Incidents.test.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Cameras.test.tsx frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx
git commit -m "feat: update omnisight workspace language"
```

---

## Task 8: Apply Workflow Visual Polish Without Hiding Data

**Files:**

- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/components/history/HistoryTrendPanel.tsx`
- Modify: `frontend/src/components/live/VideoStream.tsx`
- Modify: `frontend/src/components/live/TelemetryCanvas.tsx`

- [ ] **Step 1: Add a test that evidence and live media remain inspectable**

Update `frontend/src/pages/Live.test.tsx`:

```tsx
expect(screen.getByLabelText(/video stream/i)).toBeInTheDocument();
expect(screen.getByLabelText(/telemetry overlay/i)).toBeInTheDocument();
```

Update `frontend/src/pages/Incidents.test.tsx`:

```tsx
expect(screen.getByRole("img", { name: /incident evidence/i })).toBeInTheDocument();
```

Use the existing accessible names in the components. If the current names differ, assert the existing media elements and update names only if that improves accessibility.

- [ ] **Step 2: Run media accessibility tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/pages/Incidents.test.tsx
```

Expected: FAIL only if accessible names need refinement.

- [ ] **Step 3: Refine page containers**

For each page root, prefer:

```tsx
<div className="space-y-5 p-5 sm:p-6">
```

or grid equivalents with page padding inside the shell. Avoid wrapping the whole page in another large rounded card unless it is a specific repeated item, modal, or tool surface.

Apply this pattern:

- Live: keep scene cards, no all-page card.
- History: toolbar and chart panels are separate surfaces.
- Evidence: queue, evidence, and facts are the main surfaces.
- Scene Setup: table panel plus wizard when open.
- Operations: summary strip plus panels.

- [ ] **Step 4: Add quiet field only to spacious page headers**

Where a page has a broad header band, add:

```tsx
<OmniSightField variant="quiet" className="opacity-60" />
```

Place it in a `relative overflow-hidden` header container and keep it behind content:

```tsx
<section className="relative overflow-hidden rounded-[1.1rem] border border-white/10 bg-[color:var(--vezor-surface-depth)] px-5 py-5">
  <OmniSightField variant="quiet" className="opacity-50" />
  <div className="relative z-10">...</div>
</section>
```

Do not place this inside tables, media frames, calibration canvases, or command output.

- [ ] **Step 5: Tune live scene card classes**

In `frontend/src/pages/Live.tsx`, update scene card class to:

```tsx
"overflow-hidden rounded-[1.1rem] border border-white/10 bg-[linear-gradient(180deg,rgba(10,16,26,0.96),rgba(5,8,13,0.98))] shadow-[0_22px_56px_-44px_rgba(63,121,255,0.52)] transition duration-200 hover:border-[rgba(118,224,255,0.28)] hover:shadow-[0_28px_70px_-50px_rgba(63,121,255,0.72)]"
```

- [ ] **Step 6: Tune evidence queue selected state**

In `frontend/src/pages/Incidents.tsx`, update selected queue item class:

```tsx
selected
  ? "bg-[linear-gradient(135deg,rgba(110,189,255,0.16),rgba(126,83,255,0.14))] text-white shadow-[inset_3px_0_0_rgba(118,224,255,0.72)]"
  : "text-[#c5d3ea] hover:bg-white/[0.04]"
```

- [ ] **Step 7: Run focused workflow tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/pages/History.test.tsx src/pages/Incidents.test.tsx src/pages/Cameras.test.tsx src/pages/Settings.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/Live.tsx frontend/src/pages/History.tsx frontend/src/pages/Incidents.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Settings.tsx frontend/src/components/history/HistoryTrendPanel.tsx frontend/src/components/live/VideoStream.tsx frontend/src/components/live/TelemetryCanvas.tsx frontend/src/pages/Live.test.tsx frontend/src/pages/Incidents.test.tsx
git commit -m "style: add omnisight workflow depth"
```

---

## Task 9: Browser Visual Verification and Responsive Pass

**Files:**

- Modify only files required by findings from browser verification.

- [ ] **Step 1: Start the frontend**

Run:

```bash
corepack pnpm --dir frontend dev
```

Expected: Vite serves the app on `http://localhost:3000`. If port 3000 is occupied, use the printed alternative URL.

- [ ] **Step 2: Verify sign-in visually**

Open `/signin`.

Check:

- Bold OmniSight lens is visible.
- Product promise says broad live-environment intelligence.
- Sign-in panel is readable.
- No traffic/counting-specific language appears.
- Mobile width keeps the sign-in panel below the brand message without overlap.

- [ ] **Step 3: Verify shell visually**

Sign in with the dev auth flow or use the existing app test setup if running locally with auth.

Check `/live`, `/history`, `/incidents`, `/cameras`, `/settings`.

For each route:

- Faint OmniSight field is visible in the shell but does not sit under dense text.
- Left rail remains stable.
- Active nav state is clear.
- Route transition is subtle and does not cause layout shift.
- Page content remains readable.

- [ ] **Step 4: Verify workflow interactions**

Click through:

- Live: resolve a query in Ask Vezor if backend is running; otherwise verify disabled/empty states.
- Live: hover scene cards and confirm depth change is subtle.
- History: adjust time range and metric filters.
- Evidence Desk: select records in Review Queue.
- Scene Setup: open create wizard and reach Calibration/Event boundaries.
- Operations: copy dev worker command and inspect stream diagnostics.

Expected: Controls remain usable; no text is obscured; no runtime state is invented.

- [ ] **Step 5: Capture issues in code comments or plan notes**

If visual issues appear, write concise local notes in the implementation thread, not in the repo, unless the issue requires code changes. For code changes, add the smallest focused patch and rerun the route that exposed the issue.

- [ ] **Step 6: Run full frontend verification**

Run:

```bash
corepack pnpm --dir frontend exec eslint .
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
```

Expected:

- `eslint .` exits 0. Existing warnings are acceptable only if no new errors appear.
- Vitest passes.
- Build passes.

- [ ] **Step 7: Commit final polish fixes**

If Step 5 required code changes:

```bash
git add frontend/src
git commit -m "fix: polish omnisight responsive ui"
```

If no code changes were required, do not create an empty commit.

---

## Task 10: Final Repository Verification

**Files:**

- No planned code changes.

- [ ] **Step 1: Run repository diff check**

Run:

```bash
git diff --check
```

Expected: no output and exit 0.

- [ ] **Step 2: Run frontend verification**

Run:

```bash
corepack pnpm --dir frontend exec eslint .
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
```

Expected: eslint exits 0, tests pass, build passes.

- [ ] **Step 3: Run backend smoke checks only if backend files changed**

If no backend files changed, skip this step and state that backend was not touched.

If backend files changed unexpectedly, run:

```bash
python3 -m uv run ruff check .
python3 -m uv run mypy --strict src
python3 -m uv run pytest
```

from `backend/`.

Expected: all pass.

- [ ] **Step 4: Review final copy against product scope**

Run:

```bash
rg -n "car counting|traffic analytics|delivery truth|Dynamic stats|Live command surface|raw scene|Native unavailable|desired state|No cameras yet|Count boundaries" frontend/src
```

Expected: no user-facing occurrences. Test fixtures may contain old strings only when explicitly asserting absence.

- [ ] **Step 5: Review final status**

Run:

```bash
git status --short --branch
```

Expected: only intended redesign files are modified, with no scratch visual companion files staged.

- [ ] **Step 6: Commit if needed**

If Task 10 found and fixed issues:

```bash
git add frontend/src
git commit -m "fix: finalize omnisight ui redesign"
```

If no changes were made, do not create a commit.

---

## Self-Review Notes

Spec coverage:

- Broad OmniSight product framing: Tasks 1, 4, 6, 7, 10.
- Bold entry and subtle living shell background: Tasks 2, 3, 4, 5.
- Dynamic browsing and route motion: Task 5 and Task 9.
- Page-by-page copy and hierarchy: Tasks 6, 7, 8.
- Runtime truth: Tasks 7, 9, 10 preserve reported worker state and avoid invented status.
- Accessibility and performance: Tasks 2, 3, 5, 8, 9 include reduced motion, decorative semantics, and media readability checks.

Intentional deferrals:

- No dedicated `/overview` route in this implementation pass.
- No Three.js dependency in this implementation pass.
- No backend API or generated API type changes.
- No route path rename from `/settings` to `/operations` or `/cameras` to `/scenes`; labels change first, and navigation must expose `Scenes` instead of `Cameras`.
