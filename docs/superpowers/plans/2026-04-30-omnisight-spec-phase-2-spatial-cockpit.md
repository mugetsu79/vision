# OmniSight Spec — Phase 2: Spatial Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the four most brand-defining surfaces feel spatial: a CSS-perspective `OmniSightLens` (replacing the 20 MB MP4), a `WorkspaceHero` primitive, upgraded Live scene tiles with corner brackets and Z-pop hover, and a Sites page that no longer duplicates a card grid above a table.

**Architecture:** Pure CSS + React. No new runtime dependency. Adds a new `OmniSightLens` component built from the existing `3d_logo_no_bg.png` and CSS `perspective`/`preserve-3d` plus a `useLensTilt` pointer hook. Adds a `WorkspaceHero` layout primitive consumed by `SignInPage` and `DashboardPage`. Reworks the live scene-portal CSS for elevation hover and CSS-only corner brackets. Drops the duplicate sites table.

**Tech Stack:** React 19, Vite 6, Tailwind v4, Vitest 2 + `@testing-library/react`, ESLint 9, TypeScript 5.7. Frontend root: `/Users/yann.moren/vision/frontend`. Branch: `codex/omnisight-ui-distinctiveness-followup`.

**Spec source:** `/Users/yann.moren/vision/docs/brand/omnisight-ui-spec-sheet.md` (sections 5.2, 6.6, 6.8, 7.1, 7.2, 7.3, 7.7).

**Prerequisite:** Phase 1 (`2026-04-30-omnisight-spec-phase-1-foundations.md`) must be merged. Do not start this phase if `--vz-*` tokens are not present in `frontend/src/index.css`.

---

## Pre-flight

```bash
cd /Users/yann.moren/vision
git status
git rev-parse --abbrev-ref HEAD     # codex/omnisight-ui-distinctiveness-followup
grep -c -- "--vz-perspective" frontend/src/index.css
# Expected: ≥ 1 (Phase 1 was merged)

pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
# All green before starting.
```

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `frontend/src/components/brand/OmniSightLens.tsx` | create | CSS-perspective 3D lens hero (sign-in + dashboard) |
| `frontend/src/components/brand/OmniSightLens.test.tsx` | create | unit tests |
| `frontend/src/components/brand/use-lens-tilt.ts` | create | pointer-driven `rotateX/Y` hook |
| `frontend/src/components/brand/use-lens-tilt.test.ts` | create | hook tests |
| `frontend/src/components/layout/workspace-surfaces.tsx` | modify | add `WorkspaceHero` primitive |
| `frontend/src/components/layout/workspace-surfaces.test.tsx` | modify | add `WorkspaceHero` test |
| `frontend/src/index.css` | modify | add `.lens-stage`, `.lens-mark`, `.scene-portal-media` corner-bracket CSS, `@keyframes lens-breathe` |
| `frontend/src/pages/SignIn.tsx` | modify | swap MP4 hero for `OmniSightLens` + `WorkspaceHero` layout |
| `frontend/src/pages/SignIn.test.tsx` | modify | drop MP4 assertions; assert lens stage and proof signals |
| `frontend/src/pages/Dashboard.tsx` | modify | wrap top section in `WorkspaceHero`; restyle `OverviewMetric` as `KpiTile` |
| `frontend/src/components/dashboard/KpiTile.tsx` | create | new primitive |
| `frontend/src/components/dashboard/KpiTile.test.tsx` | create | tests |
| `frontend/src/pages/Dashboard.test.tsx` | modify | assert new KPI structure |
| `frontend/src/pages/Live.tsx` | modify | add `data-scene-portal-media` for corner brackets; raise tile to `--vz-elev-glow-cerulean` on focus/hover |
| `frontend/src/pages/Sites.tsx` | modify | drop the duplicate `<Table>` block; promote `WorkspaceSurface` cards |
| `frontend/src/pages/Sites.test.tsx` | modify | drop table-row assertions, add card grid assertions |

---

## Task 1: Add CSS for lens stage and corner brackets

**Files:**
- Modify: `frontend/src/index.css` (append a new section after the existing `.omnisight-field--*` rules)

- [ ] **Step 1: Append the lens-stage rules**

At the end of `frontend/src/index.css`, append:

```css
/* --------------------------------------------------------- */
/* OmniSight Lens (Phase 2)                                  */
/* --------------------------------------------------------- */

.lens-stage {
  position: relative;
  perspective: var(--vz-perspective);
  transform-style: preserve-3d;
}

.lens-mark {
  position: relative;
  display: block;
  transform-style: preserve-3d;
  transform: rotateX(var(--lens-rx, 0deg)) rotateY(var(--lens-ry, 0deg))
    translate3d(0, 0, 40px);
  transition: transform 220ms var(--vz-ease-product);
  filter: drop-shadow(0 0 30px rgba(110, 189, 255, 0.32))
    drop-shadow(0 30px 80px rgba(63, 109, 255, 0.22));
  user-select: none;
}

.lens-halo {
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  pointer-events: none;
  background: radial-gradient(
    circle at center,
    rgba(126, 83, 255, 0.35) 0%,
    rgba(110, 189, 255, 0.18) 35%,
    transparent 65%
  );
  filter: blur(28px);
  opacity: 0.7;
}

@media (prefers-reduced-motion: no-preference) {
  .lens-mark {
    animation: lens-breathe 9s ease-in-out infinite alternate;
  }
}

@keyframes lens-breathe {
  from {
    transform: rotateX(var(--lens-rx, 0deg)) rotateY(var(--lens-ry, 0deg))
      translate3d(0, 0, 36px) scale(0.99);
  }
  to {
    transform: rotateX(var(--lens-rx, 0deg)) rotateY(var(--lens-ry, 0deg))
      translate3d(0, -8px, 48px) scale(1.01);
  }
}

/* --------------------------------------------------------- */
/* Scene portal media frame brackets (Phase 2 - Live tile)   */
/* --------------------------------------------------------- */

[data-scene-portal-media] {
  position: relative;
}

[data-scene-portal-media]::before,
[data-scene-portal-media]::after,
[data-scene-portal-media] > [data-bracket]::before,
[data-scene-portal-media] > [data-bracket]::after {
  content: "";
  position: absolute;
  width: 18px;
  height: 18px;
  border: 1px solid rgba(110, 189, 255, 0.6);
  pointer-events: none;
  transition: border-color 200ms var(--vz-ease-product);
}

[data-scene-portal-media]::before {
  top: 8px;
  left: 8px;
  border-right: 0;
  border-bottom: 0;
}

[data-scene-portal-media]::after {
  top: 8px;
  right: 8px;
  border-left: 0;
  border-bottom: 0;
}

[data-scene-portal-media] > [data-bracket]::before {
  bottom: 8px;
  left: 8px;
  border-right: 0;
  border-top: 0;
}

[data-scene-portal-media] > [data-bracket]::after {
  bottom: 8px;
  right: 8px;
  border-left: 0;
  border-top: 0;
}

[data-scene-portal-tile]:hover [data-scene-portal-media]::before,
[data-scene-portal-tile]:hover [data-scene-portal-media]::after,
[data-scene-portal-tile]:hover [data-scene-portal-media] > [data-bracket]::before,
[data-scene-portal-tile]:hover [data-scene-portal-media] > [data-bracket]::after,
[data-scene-portal-tile]:focus-within [data-scene-portal-media]::before,
[data-scene-portal-tile]:focus-within [data-scene-portal-media]::after,
[data-scene-portal-tile]:focus-within [data-scene-portal-media] > [data-bracket]::before,
[data-scene-portal-tile]:focus-within [data-scene-portal-media] > [data-bracket]::after {
  border-color: rgba(118, 224, 255, 1);
}
```

- [ ] **Step 2: Build to confirm CSS parses**

```bash
pnpm --dir frontend build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): add lens-stage and scene-portal bracket CSS"
```

---

## Task 2: Add `useLensTilt` hook

**Files:**
- Create: `frontend/src/components/brand/use-lens-tilt.ts`
- Create: `frontend/src/components/brand/use-lens-tilt.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/brand/use-lens-tilt.test.ts`:

```ts
import { act, render } from "@testing-library/react";
import { useRef } from "react";
import { describe, expect, test } from "vitest";

import { useLensTilt } from "@/components/brand/use-lens-tilt";

function Harness() {
  const ref = useRef<HTMLDivElement>(null);
  useLensTilt(ref);
  return (
    <div
      data-testid="harness"
      ref={ref}
      style={{ width: 200, height: 200 }}
    />
  );
}

describe("useLensTilt", () => {
  test("writes --lens-rx and --lens-ry on pointermove", () => {
    const { getByTestId } = render(<Harness />);
    const el = getByTestId("harness") as HTMLDivElement;

    Object.defineProperty(el, "getBoundingClientRect", {
      value: () => ({
        left: 0,
        top: 0,
        width: 200,
        height: 200,
        right: 200,
        bottom: 200,
        x: 0,
        y: 0,
        toJSON: () => "",
      }),
    });

    act(() => {
      el.dispatchEvent(
        new PointerEvent("pointermove", {
          clientX: 150,
          clientY: 50,
          bubbles: true,
        }),
      );
    });

    expect(el.style.getPropertyValue("--lens-ry")).toMatch(/deg$/);
    expect(el.style.getPropertyValue("--lens-rx")).toMatch(/deg$/);
  });

  test("clears tilt on pointerleave", () => {
    const { getByTestId } = render(<Harness />);
    const el = getByTestId("harness") as HTMLDivElement;

    Object.defineProperty(el, "getBoundingClientRect", {
      value: () => ({
        left: 0,
        top: 0,
        width: 200,
        height: 200,
        right: 200,
        bottom: 200,
        x: 0,
        y: 0,
        toJSON: () => "",
      }),
    });

    act(() => {
      el.dispatchEvent(
        new PointerEvent("pointermove", {
          clientX: 150,
          clientY: 50,
          bubbles: true,
        }),
      );
      el.dispatchEvent(new PointerEvent("pointerleave", { bubbles: true }));
    });

    expect(el.style.getPropertyValue("--lens-rx")).toBe("0deg");
    expect(el.style.getPropertyValue("--lens-ry")).toBe("0deg");
  });
});
```

- [ ] **Step 2: Run the test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/brand/use-lens-tilt.test.ts
```

Expected: fails (module not found).

- [ ] **Step 3: Write the hook**

Create `frontend/src/components/brand/use-lens-tilt.ts`:

```ts
import { useEffect, type RefObject } from "react";

const MAX_TILT_DEG = 8;

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function useLensTilt(ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReducedMotion()) return;

    let frame = 0;
    let nextX = 0;
    let nextY = 0;

    const flush = () => {
      frame = 0;
      el.style.setProperty("--lens-rx", `${-nextY * MAX_TILT_DEG}deg`);
      el.style.setProperty("--lens-ry", `${nextX * MAX_TILT_DEG}deg`);
    };

    const onMove = (event: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      nextX = (event.clientX - rect.left) / rect.width - 0.5;
      nextY = (event.clientY - rect.top) / rect.height - 0.5;
      if (frame === 0) {
        frame = window.requestAnimationFrame(flush);
      }
    };

    const onLeave = () => {
      if (frame !== 0) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
      el.style.setProperty("--lens-rx", "0deg");
      el.style.setProperty("--lens-ry", "0deg");
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onLeave);

    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      if (frame !== 0) window.cancelAnimationFrame(frame);
    };
  }, [ref]);
}
```

- [ ] **Step 4: Run test, expect pass**

```bash
pnpm --dir frontend exec vitest run src/components/brand/use-lens-tilt.test.ts
```

Expected: both tests pass. (Note: `requestAnimationFrame` resolves synchronously in jsdom only when manually flushed; the test triggers a single dispatch so the value is set on the next animation frame. If the assertion fails because `getPropertyValue` returns empty, wrap the dispatch in `await new Promise((r) => setTimeout(r, 0));` and add `async` to the test function.)

- [ ] **Step 5: Lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/components/brand/use-lens-tilt.ts frontend/src/components/brand/use-lens-tilt.test.ts
git commit -m "feat(ui): add useLensTilt pointer hook"
```

---

## Task 3: Create `OmniSightLens` component

**Files:**
- Create: `frontend/src/components/brand/OmniSightLens.tsx`
- Create: `frontend/src/components/brand/OmniSightLens.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/brand/OmniSightLens.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { OmniSightLens } from "@/components/brand/OmniSightLens";
import { productBrand } from "@/brand/product";

describe("OmniSightLens", () => {
  test("renders the 3D mark image as the lens hero", () => {
    render(<OmniSightLens variant="signin" />);
    const lens = screen.getByTestId("omnisight-lens");
    expect(lens).toBeInTheDocument();
    const img = lens.querySelector("img");
    expect(img).not.toBeNull();
    expect(img).toHaveAttribute("src", productBrand.runtimeAssets.logo3d);
    expect(img).toHaveAttribute("alt", "");
  });

  test("renders a halo and ring stack", () => {
    render(<OmniSightLens variant="signin" />);
    const lens = screen.getByTestId("omnisight-lens");
    expect(lens.querySelector("[data-lens-halo]")).not.toBeNull();
    expect(lens.querySelectorAll("[data-lens-ring]").length).toBeGreaterThanOrEqual(2);
  });

  test("variant=dashboard scales the lens down for cockpit context", () => {
    render(<OmniSightLens variant="dashboard" />);
    expect(screen.getByTestId("omnisight-lens")).toHaveAttribute(
      "data-variant",
      "dashboard",
    );
  });
});
```

- [ ] **Step 2: Run test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/brand/OmniSightLens.test.tsx
```

Expected: fails (component does not exist).

- [ ] **Step 3: Create the component**

Create `frontend/src/components/brand/OmniSightLens.tsx`:

```tsx
import { useRef } from "react";

import { productBrand } from "@/brand/product";
import { cn } from "@/lib/utils";

import { useLensTilt } from "./use-lens-tilt";

type OmniSightLensVariant = "signin" | "dashboard";

type OmniSightLensProps = {
  variant?: OmniSightLensVariant;
  className?: string;
};

const variantSizes: Record<OmniSightLensVariant, string> = {
  signin: "w-[clamp(18rem,32vw,28rem)] aspect-square",
  dashboard: "w-[clamp(10rem,18vw,16rem)] aspect-square",
};

export function OmniSightLens({
  variant = "signin",
  className,
}: OmniSightLensProps) {
  const stageRef = useRef<HTMLDivElement>(null);
  useLensTilt(stageRef);

  return (
    <div
      ref={stageRef}
      data-testid="omnisight-lens"
      data-variant={variant}
      aria-hidden="true"
      className={cn(
        "lens-stage relative grid place-items-center",
        variantSizes[variant],
        className,
      )}
    >
      <span data-lens-halo className="lens-halo" />
      <span
        data-lens-ring
        className="absolute inset-[6%] rounded-full border border-[rgba(118,224,255,0.22)]"
      />
      <span
        data-lens-ring
        className="absolute inset-[14%] rounded-full border border-[rgba(126,83,255,0.18)]"
      />
      <img
        alt=""
        draggable={false}
        src={productBrand.runtimeAssets.logo3d}
        className="lens-mark relative z-[1] w-[78%] object-contain"
      />
    </div>
  );
}
```

- [ ] **Step 4: Run test, expect pass**

```bash
pnpm --dir frontend exec vitest run src/components/brand/OmniSightLens.test.tsx
```

Expected: 3 tests pass.

- [ ] **Step 5: Lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/components/brand/OmniSightLens.tsx frontend/src/components/brand/OmniSightLens.test.tsx
git commit -m "feat(ui): add OmniSightLens CSS-3D hero component"
```

---

## Task 4: Add `WorkspaceHero` primitive

**Files:**
- Modify: `frontend/src/components/layout/workspace-surfaces.tsx`
- Modify: `frontend/src/components/layout/workspace-surfaces.test.tsx`

- [ ] **Step 1: Write the failing test**

Append to the existing `describe("workspace surfaces", ...)` block in `workspace-surfaces.test.tsx`:

```tsx
test("WorkspaceHero renders body and lens slot regions", () => {
  render(
    <WorkspaceHero
      eyebrow="Hero"
      title="Spatial cockpit"
      description="OmniSight for every live environment."
      lens={<div data-testid="lens-slot">lens</div>}
      body={<button type="button">Sign in</button>}
    />,
  );

  expect(screen.getByRole("heading", { name: /spatial cockpit/i })).toBeInTheDocument();
  expect(screen.getByTestId("lens-slot")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  expect(screen.getByTestId("workspace-hero")).toHaveAttribute(
    "data-tone",
    "neutral",
  );
});

test("WorkspaceHero accepts tone='violet' and exposes data-tone for styling", () => {
  render(
    <WorkspaceHero
      eyebrow="Sign in"
      title="OmniSight"
      tone="violet"
      lens={<span>lens</span>}
      body={<span>body</span>}
    />,
  );

  expect(screen.getByTestId("workspace-hero")).toHaveAttribute(
    "data-tone",
    "violet",
  );
});
```

Add `WorkspaceHero` to the existing import at the top of the test file:

```tsx
import {
  InstrumentRail,
  MediaSurface,
  StatusToneBadge,
  WorkspaceBand,
  WorkspaceHero,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
```

- [ ] **Step 2: Run test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/layout/workspace-surfaces.test.tsx
```

Expected: fails.

- [ ] **Step 3: Add `WorkspaceHero` to `workspace-surfaces.tsx`**

Append (do not replace anything) to `frontend/src/components/layout/workspace-surfaces.tsx`:

```tsx
type WorkspaceHeroTone = "neutral" | "cerulean" | "violet";

type WorkspaceHeroProps = {
  eyebrow: string;
  title: string;
  description?: string;
  tone?: WorkspaceHeroTone;
  body?: ReactNode;
  lens?: ReactNode;
  className?: string;
};

const heroToneClasses: Record<WorkspaceHeroTone, string> = {
  neutral: "shadow-[var(--vz-elev-1)]",
  cerulean: "shadow-[var(--vz-elev-glow-cerulean)]",
  violet: "shadow-[var(--vz-elev-glow-violet)]",
};

export function WorkspaceHero({
  eyebrow,
  title,
  description,
  tone = "neutral",
  body,
  lens,
  className,
}: WorkspaceHeroProps) {
  return (
    <section
      data-testid="workspace-hero"
      data-tone={tone}
      className={cn(
        "relative overflow-hidden rounded-[var(--vz-r-xl)] border border-[color:var(--vz-hair)] bg-[linear-gradient(135deg,var(--vz-canvas-graphite)_0%,var(--vz-canvas-obsidian)_100%)] px-6 py-7 sm:px-8 sm:py-8",
        heroToneClasses[tone],
        className,
      )}
      style={{ perspective: "var(--vz-perspective)" }}
    >
      <div className="grid items-center gap-8 lg:grid-cols-[7fr_5fr]">
        <div className="min-w-0 space-y-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--vz-text-muted)]">
            {eyebrow}
          </p>
          <h1 className="font-[family-name:var(--vz-font-display)] text-3xl font-semibold tracking-tight text-[var(--vz-text-primary)] sm:text-4xl lg:text-5xl">
            {title}
          </h1>
          {description ? (
            <p className="max-w-2xl text-base leading-7 text-[var(--vz-text-secondary)]">
              {description}
            </p>
          ) : null}
          {body ? <div className="pt-2">{body}</div> : null}
        </div>
        {lens ? (
          <div className="relative grid place-items-center">{lens}</div>
        ) : null}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Run test, expect pass**

```bash
pnpm --dir frontend exec vitest run src/components/layout/workspace-surfaces.test.tsx
```

Expected: green.

- [ ] **Step 5: Lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/components/layout/workspace-surfaces.tsx frontend/src/components/layout/workspace-surfaces.test.tsx
git commit -m "feat(ui): add WorkspaceHero primitive"
```

---

## Task 5: Replace SignIn MP4 hero with `OmniSightLens` + `WorkspaceHero`

**Files:**
- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/pages/SignIn.test.tsx`

- [ ] **Step 1: Update tests to reflect new SignIn structure**

Replace `frontend/src/pages/SignIn.test.tsx` with:

```tsx
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { productBrand } from "@/brand/product";

vi.mock("@/lib/auth", () => ({
  mapOidcUser: vi.fn(),
  oidcManager: {
    getUser: vi.fn(),
    signinRedirect: vi.fn(),
    signinRedirectCallback: vi.fn(),
    signoutRedirect: vi.fn(),
  },
}));

import { SignInPage } from "@/pages/SignIn";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("SignInPage", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  afterEach(() => {
    act(() => {
      useAuthStore.setState(initialAuthState, true);
    });
  });

  test("starts the OIDC login flow when the user clicks sign in", async () => {
    const user = userEvent.setup();
    const signIn = vi.fn().mockResolvedValue(undefined);
    useAuthStore.setState({ signIn });

    render(<SignInPage />);
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(signIn).toHaveBeenCalledTimes(1);
  });

  test("renders the lens hero and product lockup", () => {
    render(<SignInPage />);

    expect(
      screen.getByRole("group", {
        name: new RegExp(`${productBrand.name} product lockup`, "i"),
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: /omnisight for every live environment/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("omnisight-lens")).toBeInTheDocument();
    expect(screen.getByTestId("signin-auth-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("signin-animated-logo")).toBeNull();
  });

  test("renders three proof signals", () => {
    render(<SignInPage />);
    expect(screen.getByText(/scenes/i)).toBeInTheDocument();
    expect(screen.getByText(/evidence/i)).toBeInTheDocument();
    expect(screen.getByText(/operations/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx
```

Expected: fails (`omnisight-lens` not found, `signin-animated-logo` still present).

- [ ] **Step 3: Rewrite `SignInPage`**

Replace `frontend/src/pages/SignIn.tsx` with:

```tsx
import { Camera, Cpu, ScanEye } from "lucide-react";

import { OmniSightLens } from "@/components/brand/OmniSightLens";
import { ProductLockup } from "@/components/layout/ProductLockup";
import { WorkspaceHero } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { productBrand } from "@/brand/product";
import { useAuthStore } from "@/stores/auth-store";

const proofSignals = [
  { icon: Camera, label: "Scenes", caption: "Live spatial canvas" },
  { icon: ScanEye, label: "Evidence", caption: "Reviewed in seconds" },
  { icon: Cpu, label: "Operations", caption: "Edge-aware fleet" },
] as const;

export function SignInPage() {
  const signIn = useAuthStore((state) => state.signIn);
  const brandName = productBrand.name;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(60%_60%_at_75%_30%,rgba(126,83,255,0.18),transparent_60%),linear-gradient(180deg,var(--vz-canvas-void)_0%,var(--vz-canvas-obsidian)_100%)] px-6 py-8 text-[var(--vz-text-primary)]">
      <div className="relative z-10 mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl grid-rows-[auto_1fr_auto] gap-8">
        <header className="flex items-center justify-between">
          <ProductLockup className="h-12 w-auto" />
          <p className="hidden text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--vz-text-muted)] sm:block">
            Spatial intelligence layer
          </p>
        </header>

        <WorkspaceHero
          eyebrow={productBrand.descriptor}
          title="OmniSight for every live environment."
          description={`${brandName} connects scenes, models, events, evidence, and edge operations into one spatial intelligence layer.`}
          tone="violet"
          lens={<OmniSightLens variant="signin" />}
          body={
            <ul className="grid max-w-xl grid-cols-3 gap-3 text-sm">
              {proofSignals.map(({ icon: Icon, label, caption }) => (
                <li
                  key={label}
                  className="flex items-start gap-3 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite-up)] px-3 py-2.5"
                >
                  <Icon
                    className="mt-0.5 size-4 text-[var(--vz-lens-cerulean)]"
                    aria-hidden="true"
                  />
                  <span className="flex flex-col">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-secondary)]">
                      {label}
                    </span>
                    <span className="text-[12px] text-[var(--vz-text-muted)]">
                      {caption}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          }
        />

        <section
          data-testid="signin-auth-panel"
          className="ml-auto w-full max-w-[25rem] rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,rgba(10,15,25,0.94),rgba(5,8,14,0.92))] p-6 text-[var(--vz-text-primary)] shadow-[var(--vz-elev-glow-violet)] backdrop-blur-xl sm:p-7"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
            Secure entry
          </p>
          <h2 className="mt-4 font-[family-name:var(--vz-font-display)] text-2xl font-semibold text-[var(--vz-text-primary)]">
            Sign in
          </h2>
          <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
            Use your {brandName} identity provider account to continue.
          </p>
          <Button
            variant="primary"
            className="mt-6 w-full"
            onClick={() => void signIn()}
          >
            Sign in
          </Button>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-[var(--vz-text-muted)]">
          <span>Secure, private, and compliant.</span>
          <span>Your data stays protected.</span>
        </footer>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx
```

Expected: 3 tests pass.

- [ ] **Step 5: Run full suite**

```bash
pnpm --dir frontend test
```

Expected: green. If `OmniSightField.test.tsx` fails because the sign-in page no longer renders `OmniSightField`, that is correct — the test file targets `OmniSightField` directly with mounted variants, so it should still pass; only `SignIn.test.tsx` cared about the field on sign-in.

- [ ] **Step 6: Lint + browser smoke test**

```bash
pnpm --dir frontend lint
pnpm --dir frontend dev
# Visit http://127.0.0.1:3000/signin
# Verify: no MP4, lens stage tilts on pointer move, halo visible, headline does not overlap lens.
# Stop with Ctrl+C
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/SignIn.tsx frontend/src/pages/SignIn.test.tsx
git commit -m "feat(signin): replace MP4 hero with CSS-3D OmniSightLens stage"
```

---

## Task 6: Add `KpiTile` primitive

**Files:**
- Create: `frontend/src/components/dashboard/KpiTile.tsx`
- Create: `frontend/src/components/dashboard/KpiTile.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/dashboard/KpiTile.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { KpiTile } from "@/components/dashboard/KpiTile";

describe("KpiTile", () => {
  test("renders eyebrow, value, and caption", () => {
    render(
      <KpiTile
        eyebrow="Live scenes"
        value="12"
        caption="2 attention"
      />,
    );

    expect(screen.getByText("Live scenes")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("2 attention")).toBeInTheDocument();
  });

  test("uses tabular numerics for the value", () => {
    render(<KpiTile eyebrow="Workers" value="4/6" />);
    expect(screen.getByText("4/6")).toHaveClass("tabular-nums");
  });
});
```

- [ ] **Step 2: Run test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/dashboard/KpiTile.test.tsx
```

- [ ] **Step 3: Create the component**

Create `frontend/src/components/dashboard/KpiTile.tsx`:

```tsx
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type KpiTileProps = {
  eyebrow: string;
  value: ReactNode;
  caption?: ReactNode;
  className?: string;
};

export function KpiTile({ eyebrow, value, caption, className }: KpiTileProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite-up)] px-4 py-3 shadow-[var(--vz-elev-1)]",
        className,
      )}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--vz-text-muted)]">
        {eyebrow}
      </p>
      <p className="mt-2 font-[family-name:var(--vz-font-display)] text-2xl font-semibold tabular-nums text-[var(--vz-text-primary)]">
        {value}
      </p>
      {caption ? (
        <p className="mt-1 text-xs text-[var(--vz-text-secondary)]">
          {caption}
        </p>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Run + commit**

```bash
pnpm --dir frontend exec vitest run src/components/dashboard/KpiTile.test.tsx
pnpm --dir frontend lint
git add frontend/src/components/dashboard/KpiTile.tsx frontend/src/components/dashboard/KpiTile.test.tsx
git commit -m "feat(ui): add KpiTile primitive"
```

---

## Task 7: Refactor Dashboard hero to use `WorkspaceHero` + `OmniSightLens` + `KpiTile`

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Dashboard.test.tsx`

- [ ] **Step 1: Update tests**

Replace the `test("renders an OmniSight overview cockpit", ...)` body in `Dashboard.test.tsx` with:

```tsx
test("renders an OmniSight overview cockpit", () => {
  render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );

  expect(
    screen.getByRole("heading", { name: "OmniSight Overview" }),
  ).toBeInTheDocument();
  expect(screen.getByTestId("omnisight-lens")).toBeInTheDocument();
  expect(screen.getByText("Live scenes")).toBeInTheDocument();
  expect(screen.getByText("Evidence queue")).toBeInTheDocument();
  expect(screen.getByText("Edge workers")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /Open Live Intelligence/i }),
  ).toHaveAttribute("href", "/live");
  expect(
    screen.getByRole("link", { name: /Review Evidence/i }),
  ).toHaveAttribute("href", "/incidents");
});
```

- [ ] **Step 2: Run test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/pages/Dashboard.test.tsx
```

- [ ] **Step 3: Update `Dashboard.tsx`**

Replace `frontend/src/pages/Dashboard.tsx` with:

```tsx
import { Link } from "react-router-dom";

import { OmniSightLens } from "@/components/brand/OmniSightLens";
import { KpiTile } from "@/components/dashboard/KpiTile";
import {
  InstrumentRail,
  StatusToneBadge,
  WorkspaceHero,
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
  const directUnavailable =
    fleet.data?.summary.native_unavailable_cameras ?? 0;

  const evidenceCaption = `${incidents.length} pending evidence ${
    incidents.length === 1 ? "record" : "records"
  }`;

  return (
    <div
      data-testid="omnisight-overview"
      className="grid gap-5 p-4 sm:p-6 xl:grid-cols-[minmax(0,1fr)_340px]"
    >
      <WorkspaceHero
        eyebrow="Dashboard"
        title="OmniSight Overview"
        description="A connected view of live scenes, evidence, patterns, deployment context, and edge operations."
        tone="cerulean"
        lens={<OmniSightLens variant="dashboard" />}
        body={
          <div className="grid gap-3 sm:grid-cols-3">
            <KpiTile
              eyebrow="Live scenes"
              value={cameras.length}
              caption={`${cameras.length === 1 ? "scene" : "scenes"} streaming`}
            />
            <KpiTile
              eyebrow="Evidence queue"
              value={incidents.length}
              caption={evidenceCaption}
            />
            <KpiTile
              eyebrow="Edge workers"
              value={`${runningWorkers}/${desiredWorkers}`}
              caption="running / desired"
            />
          </div>
        }
      />

      <InstrumentRail aria-label="Overview instruments" className="space-y-3 p-4">
        <StatusToneBadge tone={directUnavailable > 0 ? "attention" : "healthy"}>
          {directUnavailable > 0
            ? `${directUnavailable} direct streams unavailable`
            : "Streams healthy"}
        </StatusToneBadge>
        <p className="text-sm text-[var(--vz-text-secondary)]">
          {sites.length} deployment {sites.length === 1 ? "site" : "sites"}{" "}
          configured.
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
    <WorkspaceSurface className="cursor-pointer p-4 transition duration-200 hover:border-[color:var(--vz-hair-focus)] hover:shadow-[var(--vz-elev-2)]">
      <h2 className="font-[family-name:var(--vz-font-display)] text-lg font-semibold text-[var(--vz-text-primary)]">
        {title}
      </h2>
      <p className="mt-2 min-h-12 text-sm leading-6 text-[var(--vz-text-secondary)]">
        {copy}
      </p>
      <Link
        to={href}
        className="mt-4 inline-flex text-sm font-semibold text-[var(--vz-lens-cerulean)] transition hover:text-[var(--vz-text-primary)]"
      >
        {action}
      </Link>
    </WorkspaceSurface>
  );
}
```

- [ ] **Step 4: Run tests + lint**

```bash
pnpm --dir frontend exec vitest run src/pages/Dashboard.test.tsx
pnpm --dir frontend test
pnpm --dir frontend lint
```

Expected: green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx
git commit -m "feat(dashboard): adopt WorkspaceHero, OmniSightLens, KpiTile"
```

---

## Task 8: Live tile — corner brackets + Z-pop hover

**Files:**
- Modify: `frontend/src/pages/Live.tsx`

- [ ] **Step 1: Annotate the scene-portal article and media plate**

In `frontend/src/pages/Live.tsx`, locate the `<article>` for each scene tile (currently around line 154–227). Update:

Replace the existing `<article ... data-testid="scene-portal" ...>` opening tag with:

```tsx
<article
  key={camera.id}
  data-testid="scene-portal"
  data-scene-portal-tile
  tabIndex={0}
  className="group relative overflow-hidden rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite)] shadow-[var(--vz-elev-1)] outline-none transition duration-200 hover:-translate-y-0.5 hover:shadow-[var(--vz-elev-glow-cerulean)] focus-within:shadow-[var(--vz-elev-glow-cerulean)]"
>
```

Replace the `<div className="relative aspect-video bg-[color:var(--vezor-media-black)]">` opener with:

```tsx
<div
  data-scene-portal-media
  className="relative aspect-video bg-[color:var(--vz-media-black)]"
>
  <span data-bracket aria-hidden="true" />
```

Make sure to **close** that `<span data-bracket>` immediately as a self-closing element by changing it to `<span data-bracket aria-hidden="true" />`. The `::before/::after` pseudo elements on the parent and on the `[data-bracket]` element render the four corners.

- [ ] **Step 2: Run Live test (it does not assert pixel positions)**

```bash
pnpm --dir frontend exec vitest run src/pages/Live.test.tsx 2>/dev/null || pnpm --dir frontend exec vitest run -t "live"
```

If no Live page test exists, that is fine — verify in dev.

```bash
pnpm --dir frontend dev
# Visit http://127.0.0.1:3000/live with seeded cameras
# Hover a tile — confirm the corner brackets light up cerulean
# Confirm the tile lifts ~2px and gains a cerulean glow
# Confirm there is no layout shift on hover
```

Stop dev.

- [ ] **Step 3: Run full suite + lint + commit**

```bash
pnpm --dir frontend test
pnpm --dir frontend lint
git add frontend/src/pages/Live.tsx
git commit -m "feat(live): scene-portal corner brackets and Z-pop hover"
```

---

## Task 9: Sites — drop duplicate table and improve empty state

**Files:**
- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/pages/Sites.test.tsx`

- [ ] **Step 1: Update tests**

In `frontend/src/pages/Sites.test.tsx`, drop or rewrite any test that asserts the table rendering. Add a test that asserts:
- An empty state appears when `sites.length === 0`.
- A `WorkspaceSurface` card appears for each site when `sites.length > 0`.
- The duplicate table is not present (no `<table>` in the DOM unless we keep it for ≥ 8 sites — but for Phase 2 we drop it entirely; the spec calls for cards).

Append:

```tsx
test("renders one card per site without a duplicate table", async () => {
  // Use existing test harness pattern in the file: mock useCameras / useSites
  // (See file head for the exact harness pattern; reuse it.)
  // After render:
  expect(screen.queryByRole("table")).toBeNull();
});

test("shows empty state when there are no sites", async () => {
  // override useSites mock to return data: []
  // Then render:
  expect(screen.getByText(/no deployment sites yet/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /add site/i })).toBeInTheDocument();
});
```

(If the existing `Sites.test.tsx` already provides a harness for mocking `useSites` and `useCameras`, follow that pattern; do **not** introduce new mocking style.)

- [ ] **Step 2: Run tests, expect failure**

```bash
pnpm --dir frontend exec vitest run src/pages/Sites.test.tsx
```

- [ ] **Step 3: Update `Sites.tsx` — remove the `<Table>` block and add a real empty state**

In `frontend/src/pages/Sites.tsx`, locate the second `<section className="overflow-hidden rounded-[0.9rem] ...">` block that renders the `<Table>`. Delete it entirely.

Replace the existing `<section data-testid="site-context-grid" ...>` block with:

```tsx
{isLoading ? (
  <p className="text-sm text-[var(--vz-text-secondary)]">Loading sites...</p>
) : sites.length === 0 ? (
  <section
    data-testid="sites-empty-state"
    className="rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite)] px-6 py-10 text-center shadow-[var(--vz-elev-1)]"
  >
    <p className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
      No deployment sites yet
    </p>
    <p className="mx-auto mt-2 max-w-md text-sm text-[var(--vz-text-secondary)]">
      Sites anchor scenes, time zones, and edge fleet planning across {brandName}.
      Add your first deployment location to start.
    </p>
    <Button
      variant="primary"
      className="mt-5"
      onClick={() => setDialogOpen(true)}
    >
      Add site
    </Button>
  </section>
) : (
  <section
    data-testid="site-context-grid"
    className="grid gap-4 lg:grid-cols-3"
  >
    {sites.map((site) => {
      const sceneCount = sceneCountBySite.get(site.id) ?? 0;
      return (
        <WorkspaceSurface
          key={site.id}
          className="cursor-pointer p-4 transition duration-200 hover:border-[color:var(--vz-hair-focus)] hover:shadow-[var(--vz-elev-2)]"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
            Deployment location
          </p>
          <h2 className="mt-2 font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
            {site.name}
          </h2>
          <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
            {site.tz}
          </p>
          <p className="mt-3 text-sm font-medium text-[var(--vz-text-primary)]">
            {sceneCount} {sceneCount === 1 ? "scene" : "scenes"}
          </p>
          {site.description ? (
            <p className="mt-2 text-sm text-[var(--vz-text-muted)]">
              {site.description}
            </p>
          ) : null}
        </WorkspaceSurface>
      );
    })}
  </section>
)}
```

Also remove the `Table, TBody, TD, TH, THead, TR` imports from the top of the file — they are no longer used.

- [ ] **Step 4: Run tests, lint, commit**

```bash
pnpm --dir frontend exec vitest run src/pages/Sites.test.tsx
pnpm --dir frontend test
pnpm --dir frontend lint
git add frontend/src/pages/Sites.tsx frontend/src/pages/Sites.test.tsx
git commit -m "feat(sites): drop duplicate table, add real empty state"
```

---

## Task 10: Verify and document phase completion

- [ ] **Step 1: Full verification**

```bash
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

- [ ] **Step 2: Browser smoke test all touched routes**

```bash
pnpm --dir frontend dev
# /signin    → CSS-3D lens, no MP4, headline reads cleanly, halo visible
# /dashboard → KPI tiles, dashboard lens (smaller), action cards
# /live      → Hover a tile: brackets glow cerulean, tile lifts, no layout shift
# /sites     → Cards only (no table). Visit with no sites → empty state CTA renders
# All 4 must respect prefers-reduced-motion when toggled at the OS level
```

- [ ] **Step 3: Append to changelog**

In `frontend/CHANGELOG.md` append:

```markdown
## Unreleased — Phase 2 Spatial Cockpit

- Replaced the 20 MB sign-in MP4 hero with a CSS-perspective `OmniSightLens`.
- Added `useLensTilt` pointer-driven rotation hook.
- Introduced `WorkspaceHero` and `KpiTile` primitives.
- Adopted them on `/signin` and `/dashboard`.
- Live scene tiles gained CSS-only corner brackets and Z-pop hover.
- Dropped the duplicate Sites table; replaced with cards + dedicated empty state.
```

- [ ] **Step 4: Commit changelog**

```bash
git add frontend/CHANGELOG.md
git commit -m "docs: changelog for Phase 2 spatial cockpit"
```

---

## Done criteria

Phase 2 is complete when:

1. `pnpm --dir frontend lint`, `test`, `build` all pass.
2. The sign-in MP4 (`signin-animated-logo`) is gone from default render. The `logo-no-bg.mp4` asset is **not** removed from `public/brand/` (Phase 4 may opt back in behind a flag).
3. `/signin` and `/dashboard` use `WorkspaceHero` + `OmniSightLens`; pointer movement over the lens produces visible tilt and is disabled under reduced-motion.
4. `/live` scene tiles lift on hover/focus with cerulean corner brackets, no layout shift.
5. `/sites` shows cards only; empty state shows a real CTA.

Hand off to **Phase 3: Motion choreography** (`docs/superpowers/plans/2026-04-30-omnisight-spec-phase-3-motion.md`).
