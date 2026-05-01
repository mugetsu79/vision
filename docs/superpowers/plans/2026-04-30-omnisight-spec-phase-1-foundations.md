# OmniSight Spec — Phase 1: Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the design-token, typography, and primitive-component foundations from `docs/brand/omnisight-ui-spec-sheet.md` (sections 2, 3.1, 3.2, 5.1–5.5, 6.1) so later phases (cockpit, motion, WebGL) can build on a single source of truth.

**Architecture:** Pure CSS / TypeScript refactor scoped to `frontend/src/`. Adds a `--vz-*` token namespace alongside the existing `--vezor-*` / `--argus-*` namespaces (keep aliases — do not break consumers). Updates the `body`/`h1` font-family stack to brand fonts. Refactors `Button`, `WorkspaceBand`, `WorkspaceSurface`, `MediaSurface`, `InstrumentRail` to consume the new tokens. No new runtime dependencies.

**Tech Stack:** React 19, Vite 6, Tailwind v4 (`@tailwindcss/vite`), Vitest 2 + `@testing-library/react`, ESLint 9, TypeScript 5.7. Frontend root: `/Users/yann.moren/vision/frontend`. Branch: `codex/omnisight-ui-distinctiveness-followup`.

**Spec source:** `/Users/yann.moren/vision/docs/brand/omnisight-ui-spec-sheet.md`

---

## Pre-flight

Run from repo root unless otherwise stated:

```bash
cd /Users/yann.moren/vision
git status                          # confirm clean tree
git rev-parse --abbrev-ref HEAD     # confirm: codex/omnisight-ui-distinctiveness-followup
pnpm --dir frontend install         # ensure deps installed
pnpm --dir frontend test            # ensure baseline is green
pnpm --dir frontend lint            # ensure baseline is clean
pnpm --dir frontend build           # ensure baseline builds
```

If anything is red before starting: stop and triage. Do not begin Phase 1 on a broken baseline.

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `frontend/src/index.css` | modify | add `--vz-*` tokens, `@import` brand fonts, swap shell gradient, keep existing tokens as aliases |
| `frontend/src/components/ui/button.tsx` | modify | add `variant` prop (`primary` \| `secondary` \| `ghost`), wire to tokens |
| `frontend/src/components/ui/button.test.tsx` | create | TDD tests for variants and disabled/loading state |
| `frontend/src/components/layout/workspace-surfaces.tsx` | modify | consume new `--vz-elev-*` and `--vz-r-*` tokens; add `density` and `accent` props on `WorkspaceBand` |
| `frontend/src/components/layout/workspace-surfaces.test.tsx` | modify | extend tests for new variants |
| `frontend/src/components/layout/AppShell.tsx` | modify | replace heavy shell gradient with the lighter token-driven one |
| `frontend/src/components/layout/AppShell.test.tsx` | modify (only if asserting class names) | keep existing assertions passing |

No new files outside that table.

---

## Task 1: Add `--vz-*` palette and elevation tokens to `index.css`

**Files:**
- Modify: `frontend/src/index.css` (after line 53, inside the existing `:root` block — append a block; do not delete the `--argus-*` / `--vezor-*` tokens)
- Modify: `frontend/src/index.css` (append a new `@layer` or top-level rule for fonts at the top of the file)

- [ ] **Step 1: Read the current `:root` block**

```bash
sed -n '1,60p' /Users/yann.moren/vision/frontend/src/index.css
```

Expected: confirm `:root { ... }` ends near line 53 with `color-scheme: dark;`.

- [ ] **Step 2: Add the new tokens at the end of the existing `:root` block**

In `frontend/src/index.css`, locate the line `  color-scheme: dark;` inside `:root`. Immediately **before** the closing `}` of `:root` (currently line 53), insert this block:

```css
  /* --- Vezor v2 token namespace (keep --argus-*/--vezor-* as aliases) --- */
  /* Canvas */
  --vz-canvas-void: #03050a;
  --vz-canvas-obsidian: #07090f;
  --vz-canvas-graphite: #0e131c;
  --vz-canvas-graphite-up: #131927;
  --vz-media-black: #010306;

  /* Lens */
  --vz-lens-cerulean: #6ebdff;
  --vz-lens-cerulean-deep: #2c8df0;
  --vz-lens-aqua: #76e0ff;
  --vz-lens-violet: #7e53ff;
  --vz-lens-lilac: #c7b8ff;

  /* Status */
  --vz-state-healthy: #6fe0a3;
  --vz-state-attention: #f5c46a;
  --vz-state-risk: #f48ca6;
  --vz-state-info: #79b8ff;

  /* Text */
  --vz-text-primary: #f4f7fb;
  --vz-text-secondary: #b8c6dc;
  --vz-text-muted: #8497b3;
  --vz-text-subtle: #5e6e88;

  /* Hairlines */
  --vz-hair: rgba(206, 224, 255, 0.06);
  --vz-hair-strong: rgba(206, 224, 255, 0.12);
  --vz-hair-focus: rgba(118, 224, 255, 0.42);
  --vz-hair-active: rgba(126, 83, 255, 0.42);

  /* Radii */
  --vz-r-pill: 999px;
  --vz-r-sm: 8px;
  --vz-r-md: 12px;
  --vz-r-lg: 16px;
  --vz-r-xl: 24px;

  /* Elevation */
  --vz-elev-0: 0 0 0 1px var(--vz-hair);
  --vz-elev-1: 0 1px 0 0 rgba(255, 255, 255, 0.04) inset,
    0 12px 32px -28px rgba(0, 0, 0, 0.9), 0 0 0 1px var(--vz-hair);
  --vz-elev-2: 0 1px 0 0 rgba(255, 255, 255, 0.06) inset,
    0 18px 60px -34px rgba(0, 0, 0, 0.95), 0 0 0 1px var(--vz-hair-strong);
  --vz-elev-3: 0 1px 0 0 rgba(255, 255, 255, 0.08) inset,
    0 32px 90px -42px rgba(0, 0, 0, 0.96), 0 0 0 1px var(--vz-hair-strong);
  --vz-elev-glow-cerulean: 0 0 0 1px var(--vz-hair-focus),
    0 28px 80px -38px rgba(110, 189, 255, 0.55);
  --vz-elev-glow-violet: 0 0 0 1px var(--vz-hair-active),
    0 28px 80px -38px rgba(126, 83, 255, 0.5);

  /* Motion */
  --vz-ease-product: cubic-bezier(0.22, 1, 0.36, 1);
  --vz-ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --vz-ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --vz-ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --vz-dur-instant: 90ms;
  --vz-dur-quick: 180ms;
  --vz-dur-base: 240ms;
  --vz-dur-soft: 320ms;
  --vz-dur-ambient: 14s;

  /* Perspective / 3D */
  --vz-perspective: 1400px;
  --vz-tilt-soft: 4deg;
  --vz-tilt-firm: 8deg;
  --vz-pop-z: 18px;
  --vz-rest-z: 0px;
```

- [ ] **Step 3: Verify the file still parses by running the build**

```bash
pnpm --dir frontend build
```

Expected: `vite build` completes without CSS errors. `dist/` is generated.

- [ ] **Step 4: Run the existing tests**

```bash
pnpm --dir frontend test
```

Expected: all pre-existing tests pass (no behavior changed yet).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): add --vz-* design token namespace"
```

---

## Task 2: Add Space Grotesk + Inter brand fonts

**Files:**
- Modify: `frontend/src/index.css` (top of file, before `@import "tailwindcss";`)
- Modify: `frontend/src/index.css` (inside `:root`, font-family stack)

- [ ] **Step 1: Add `@import` for Google Fonts at the very top of `index.css`**

Insert as the **first line** of `frontend/src/index.css`, above the existing `@import "tailwindcss";`:

```css
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap");
```

- [ ] **Step 2: Add font-family tokens to `:root`**

Inside the same `:root` block (anywhere after the new `--vz-*` tokens added in Task 1), add:

```css
  --vz-font-display: "Space Grotesk", "Sora", system-ui, sans-serif;
  --vz-font-body: "Inter", "Manrope", system-ui, sans-serif;
  --vz-font-mono: "JetBrains Mono", ui-monospace, "Menlo", monospace;
```

- [ ] **Step 3: Update `body` font-family inside `:root`**

In `frontend/src/index.css`, find the existing line:

```css
  font-family: "Avenir Next", "Suisse Intl", "Poppins", "Segoe UI", sans-serif;
```

Replace with:

```css
  font-family: var(--vz-font-body);
```

- [ ] **Step 4: Add a global rule that maps headings to the display font**

After the existing `body { ... }` rule (around line 65), append:

```css
h1,
h2,
.vz-display {
  font-family: var(--vz-font-display);
  letter-spacing: -0.005em;
}
```

- [ ] **Step 5: Run build + tests**

```bash
pnpm --dir frontend build
pnpm --dir frontend test
```

Expected: build succeeds; all tests still pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): adopt Space Grotesk + Inter brand fonts"
```

---

## Task 3: Lighten the AppShell ambient background

**Files:**
- Modify: `frontend/src/components/layout/AppShell.tsx:34-36`

The current shell uses a heavy three-stop radial+linear gradient. Spec §7.9 swaps it for a single linear plus a single radial. This is a one-line replacement.

- [ ] **Step 1: Read the existing line**

Open `frontend/src/components/layout/AppShell.tsx`. Confirm line 35 reads:

```tsx
className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_55%_36%,rgba(74,121,211,0.16),transparent_30%),linear-gradient(180deg,#05080d_0%,#08101a_48%,#03050a_100%)] text-[#eef4ff]"
```

- [ ] **Step 2: Replace with token-driven gradient**

Replace that exact `className` value with:

```tsx
className="relative min-h-screen overflow-hidden bg-[radial-gradient(60%_60%_at_70%_0%,rgba(110,189,255,0.10),transparent_60%),linear-gradient(180deg,var(--vz-canvas-void)_0%,var(--vz-canvas-obsidian)_60%,var(--vz-canvas-void)_100%)] text-[var(--vz-text-primary)]"
```

- [ ] **Step 3: Soften the OmniSightField shell opacity**

In the same file, locate:

```tsx
<OmniSightField variant="shell" className="opacity-85" />
```

Replace with:

```tsx
<OmniSightField variant="shell" className="opacity-50" />
```

(Spec §7.9: the shell field is heavy on Intel macOS; reduce its weight.)

- [ ] **Step 4: Run shell test to confirm assertions still pass**

```bash
pnpm --dir frontend exec vitest run src/components/layout/AppShell.test.tsx
```

Expected: passes (the test asserts structure, not exact gradient).

- [ ] **Step 5: Smoke-test in the browser**

```bash
pnpm --dir frontend dev
```

Open `http://127.0.0.1:3000`. Sign in (or skip auth in dev) and confirm the shell still has visible depth but is darker and lighter on the GPU.

Stop dev server (Ctrl+C).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/layout/AppShell.tsx
git commit -m "feat(ui): lighten shell gradient using --vz-canvas tokens"
```

---

## Task 4: Refactor `Button` component with variant prop

**Files:**
- Modify: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/button.test.tsx`

The current `Button` is a single hard-coded style. Spec §6.1 defines three variants.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/button.test.tsx` with:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { Button } from "@/components/ui/button";

describe("Button", () => {
  test("primary variant renders with cerulean gradient class", () => {
    render(<Button variant="primary">Sign in</Button>);
    const btn = screen.getByRole("button", { name: /sign in/i });
    expect(btn.className).toContain("from-[var(--vz-lens-cerulean)]");
  });

  test("secondary is the default variant", () => {
    render(<Button>Cancel</Button>);
    const btn = screen.getByRole("button", { name: /cancel/i });
    expect(btn.className).toContain("bg-[linear-gradient(180deg,#161c26,#0d121a)]");
  });

  test("ghost variant has transparent background", () => {
    render(<Button variant="ghost">Skip</Button>);
    const btn = screen.getByRole("button", { name: /skip/i });
    expect(btn.className).toContain("bg-transparent");
  });

  test("renders type=button by default to avoid accidental form submits", () => {
    render(<Button>Click</Button>);
    expect(screen.getByRole("button", { name: /click/i })).toHaveAttribute(
      "type",
      "button",
    );
  });

  test("disabled prop applies disabled styling", () => {
    render(<Button disabled>Off</Button>);
    const btn = screen.getByRole("button", { name: /off/i });
    expect(btn).toBeDisabled();
    expect(btn.className).toContain("disabled:opacity-60");
  });
});
```

- [ ] **Step 2: Run the test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/ui/button.test.tsx
```

Expected: at least one of the variant tests fails (component does not yet accept a `variant` prop).

- [ ] **Step 3: Replace `button.tsx` implementation**

Overwrite `frontend/src/components/ui/button.tsx` with:

```tsx
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const baseClasses =
  "inline-flex items-center justify-center rounded-full px-4 py-2.5 text-sm font-medium transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--vz-hair-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--vz-canvas-obsidian)] disabled:cursor-not-allowed disabled:opacity-60";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border-0 bg-[linear-gradient(135deg,var(--vz-lens-cerulean)_0%,var(--vz-lens-cerulean-deep)_100%)] from-[var(--vz-lens-cerulean)] to-[var(--vz-lens-cerulean-deep)] text-[#04101b] shadow-[0_14px_30px_-18px_rgba(110,189,255,0.6)] hover:brightness-110",
  secondary:
    "border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,#161c26,#0d121a)] text-[var(--vz-text-primary)] shadow-[var(--vz-elev-1)] hover:border-[color:var(--vz-hair-focus)]",
  ghost:
    "border border-[color:var(--vz-hair)] bg-transparent text-[var(--vz-text-secondary)] hover:border-[color:var(--vz-hair-strong)] hover:text-[var(--vz-text-primary)]",
};

export function Button({
  className,
  type = "button",
  variant = "secondary",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(baseClasses, variantClasses[variant], className)}
      {...props}
    />
  );
}
```

- [ ] **Step 4: Run the new test**

```bash
pnpm --dir frontend exec vitest run src/components/ui/button.test.tsx
```

Expected: all 5 tests pass.

- [ ] **Step 5: Run the full test suite to catch regressions**

```bash
pnpm --dir frontend test
```

Expected: green. If any existing test asserted the old button class string, update it to use `.toContain` against the new variant classes — only do this if the test was asserting cosmetic classes; do not weaken structural assertions.

- [ ] **Step 6: Lint**

```bash
pnpm --dir frontend lint
```

Expected: clean (no new warnings).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ui/button.tsx frontend/src/components/ui/button.test.tsx
git commit -m "feat(ui): add Button variants (primary/secondary/ghost) with token-driven styles"
```

---

## Task 5: Promote SignIn primary CTA to the new `primary` variant

**Files:**
- Modify: `frontend/src/pages/SignIn.tsx:80-86`

- [ ] **Step 1: Update the SSO `Button` in `SignIn.tsx`**

Find the `<Button>` element at lines 80–85. Replace its current `className` (the `bg-[linear-gradient...]` override) with the new `variant="primary"`:

```tsx
<Button
  variant="primary"
  className="mt-6 w-full"
  onClick={() => void signIn()}
>
  Sign in
</Button>
```

- [ ] **Step 2: Run the SignIn test**

```bash
pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx
```

Expected: passes (the existing test asserts the button's role and label, not its inline gradient).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SignIn.tsx
git commit -m "feat(ui): use primary Button variant on sign-in"
```

---

## Task 6: Refactor `WorkspaceBand` with `density` and `accent` props

**Files:**
- Modify: `frontend/src/components/layout/workspace-surfaces.tsx`
- Modify: `frontend/src/components/layout/workspace-surfaces.test.tsx`

Spec §5.1 adds `density` (`compact` | `standard`) and `accent` (`neutral` | `cerulean` | `violet`) to `WorkspaceBand`.

- [ ] **Step 1: Add a failing test for `accent="cerulean"` rim**

Open `frontend/src/components/layout/workspace-surfaces.test.tsx`. Inside the existing `describe("workspace surfaces", ...)` block, add **two** new tests at the bottom:

```tsx
test("WorkspaceBand applies cerulean rim when accent='cerulean'", () => {
  render(
    <WorkspaceBand
      eyebrow="Live"
      title="Live Intelligence"
      accent="cerulean"
    />,
  );

  const heading = screen.getByRole("heading", { name: "Live Intelligence" });
  const band = heading.closest("section");
  expect(band).not.toBeNull();
  expect(band?.className).toContain("border-t-[color:var(--vz-lens-cerulean)]");
});

test("WorkspaceBand compact density reduces vertical padding", () => {
  render(
    <WorkspaceBand
      eyebrow="Sites"
      title="Deployment Sites"
      density="compact"
    />,
  );

  const heading = screen.getByRole("heading", { name: "Deployment Sites" });
  const band = heading.closest("section");
  expect(band?.className).toContain("py-4");
});
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/layout/workspace-surfaces.test.tsx
```

Expected: the two new tests fail (props not supported yet).

- [ ] **Step 3: Update `WorkspaceBand` in `workspace-surfaces.tsx`**

Replace the existing `WorkspaceBand` definition with:

```tsx
type WorkspaceBandDensity = "standard" | "compact";
type WorkspaceBandAccent = "neutral" | "cerulean" | "violet";

type WorkspaceBandProps = HTMLAttributes<HTMLElement> & {
  eyebrow: string;
  title: string;
  description?: string;
  density?: WorkspaceBandDensity;
  accent?: WorkspaceBandAccent;
  actions?: ReactNode;
};

const accentClasses: Record<WorkspaceBandAccent, string> = {
  neutral: "",
  cerulean: "border-t-2 border-t-[color:var(--vz-lens-cerulean)]",
  violet: "border-t-2 border-t-[color:var(--vz-lens-violet)]",
};

const densityClasses: Record<WorkspaceBandDensity, string> = {
  standard: "px-5 py-5",
  compact: "px-5 py-4",
};

export function WorkspaceBand({
  eyebrow,
  title,
  description,
  density = "standard",
  accent = "neutral",
  actions,
  className,
  children,
  ...props
}: WorkspaceBandProps) {
  return (
    <section
      className={cn(
        "rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[linear-gradient(180deg,var(--vz-canvas-graphite)_0%,var(--vz-canvas-graphite-up)_100%)] shadow-[var(--vz-elev-1)]",
        densityClasses[density],
        accentClasses[accent],
        className,
      )}
      {...props}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
            {eyebrow}
          </p>
          <h1 className="mt-2 font-[family-name:var(--vz-font-display)] text-2xl font-semibold tracking-normal text-[var(--vz-text-primary)] sm:text-3xl">
            {title}
          </h1>
          {description ? (
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--vz-text-secondary)]">
              {description}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
      {children ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}
```

- [ ] **Step 4: Run the workspace-surfaces tests**

```bash
pnpm --dir frontend exec vitest run src/components/layout/workspace-surfaces.test.tsx
```

Expected: all tests in that file pass (existing 2 + new 2).

- [ ] **Step 5: Run full test suite**

```bash
pnpm --dir frontend test
```

Expected: green. If existing page tests assert the old `bg-[color:var(--vezor-surface-neutral)]` class on the band, update those tests to match the new gradient class — but only after confirming the page still renders correctly in `pnpm --dir frontend dev`.

- [ ] **Step 6: Lint**

```bash
pnpm --dir frontend lint
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/layout/workspace-surfaces.tsx frontend/src/components/layout/workspace-surfaces.test.tsx
git commit -m "feat(ui): add density and accent props to WorkspaceBand"
```

---

## Task 7: Migrate `WorkspaceSurface`, `MediaSurface`, `InstrumentRail` to new tokens

**Files:**
- Modify: `frontend/src/components/layout/workspace-surfaces.tsx`
- Modify: `frontend/src/components/layout/workspace-surfaces.test.tsx`

- [ ] **Step 1: Update existing assertions to the new tokens**

In `workspace-surfaces.test.tsx`, replace the original test that asserts the old token classes:

```tsx
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

  expect(
    screen.getByRole("heading", { name: "Live Intelligence" }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Surface").className).toContain(
    "bg-[color:var(--vz-canvas-graphite)]",
  );
  expect(screen.getByLabelText("Media").className).toContain(
    "bg-[color:var(--vz-media-black)]",
  );
  expect(screen.getByLabelText("Rail").className).toContain(
    "bg-[color:var(--vz-canvas-graphite)]",
  );
});
```

- [ ] **Step 2: Run the test, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/layout/workspace-surfaces.test.tsx
```

Expected: the surface assertion fails.

- [ ] **Step 3: Update the three primitives**

In `frontend/src/components/layout/workspace-surfaces.tsx`, replace `WorkspaceSurface`, `MediaSurface`, and `InstrumentRail` with:

```tsx
export function WorkspaceSurface({
  className,
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn(
        "rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite)] shadow-[var(--vz-elev-1)]",
        className,
      )}
      {...props}
    />
  );
}

export function MediaSurface({
  className,
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair-strong)] bg-[color:var(--vz-media-black)]",
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
        "rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite)] shadow-[var(--vz-elev-1)]",
        className,
      )}
      {...props}
    />
  );
}
```

- [ ] **Step 4: Update `StatusToneBadge` token references**

In the same file, replace the `toneClasses` map:

```tsx
const toneClasses: Record<Tone, string> = {
  healthy:
    "border-[rgba(111,224,163,0.28)] bg-[rgba(10,36,24,0.72)] text-[var(--vz-state-healthy)]",
  attention:
    "border-[rgba(245,196,106,0.28)] bg-[rgba(42,31,10,0.72)] text-[var(--vz-state-attention)]",
  danger:
    "border-[rgba(244,140,166,0.28)] bg-[rgba(45,14,24,0.72)] text-[var(--vz-state-risk)]",
  muted: "border-[color:var(--vz-hair)] bg-white/[0.035] text-[var(--vz-text-muted)]",
  accent:
    "border-[rgba(118,224,255,0.28)] bg-[rgba(23,52,70,0.56)] text-[var(--vz-lens-cerulean)]",
};
```

- [ ] **Step 5: Update the existing `StatusToneBadge` tone test in the same test file**

Replace the existing tone-mapping test with:

```tsx
test("maps status tones to semantic classes", () => {
  render(
    <>
      <StatusToneBadge tone="healthy">Live</StatusToneBadge>
      <StatusToneBadge tone="attention">Pending</StatusToneBadge>
      <StatusToneBadge tone="danger">Failed</StatusToneBadge>
      <StatusToneBadge tone="accent">Selected</StatusToneBadge>
    </>,
  );

  expect(screen.getByText("Live")).toHaveClass("text-[var(--vz-state-healthy)]");
  expect(screen.getByText("Pending")).toHaveClass(
    "text-[var(--vz-state-attention)]",
  );
  expect(screen.getByText("Failed")).toHaveClass("text-[var(--vz-state-risk)]");
  expect(screen.getByText("Selected")).toHaveClass(
    "text-[var(--vz-lens-cerulean)]",
  );
});
```

- [ ] **Step 6: Run tests**

```bash
pnpm --dir frontend exec vitest run src/components/layout/workspace-surfaces.test.tsx
```

Expected: all tests pass.

- [ ] **Step 7: Run full suite**

```bash
pnpm --dir frontend test
```

Expected: green. If page tests asserted old token names (e.g., `--vezor-surface-neutral` strings), keep them green by adding aliases in `index.css` rather than changing those tests. Add this in `:root` *after* the new `--vz-*` tokens:

```css
  /* Aliases — do not remove until all consumers migrate */
  --vezor-surface-neutral: var(--vz-canvas-graphite);
  --vezor-surface-rail: var(--vz-canvas-graphite);
  --vezor-media-black: var(--vz-media-black);
  --vezor-border-neutral: var(--vz-hair);
  --vezor-border-focus: var(--vz-hair-focus);
```

Re-run tests after adding aliases.

- [ ] **Step 8: Lint**

```bash
pnpm --dir frontend lint
```

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/layout/workspace-surfaces.tsx frontend/src/components/layout/workspace-surfaces.test.tsx frontend/src/index.css
git commit -m "feat(ui): migrate workspace primitives to --vz-* tokens with legacy aliases"
```

---

## Task 8: Verify and document phase completion

- [ ] **Step 1: Run full verification**

```bash
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

Expected: all three commands exit 0.

- [ ] **Step 2: Visual smoke test**

```bash
pnpm --dir frontend dev
```

Open `http://127.0.0.1:3000` and walk these routes (use any seeded local user, or skip auth as configured):

- `/signin` — confirm headline uses Space Grotesk; primary button has cerulean gradient; lens stage still renders.
- `/dashboard` — confirm hero band reads in display font; metrics readable.
- `/live` — confirm scenes render; band style consistent.
- `/sites` — confirm cards readable.

Stop dev server.

- [ ] **Step 3: Capture and commit a brief Phase 1 changelog entry**

Append to `frontend/CHANGELOG.md` (create the file if it does not exist):

```markdown
## Unreleased — Phase 1 Foundations

- Added `--vz-*` token namespace (palette, elevation, radius, motion, perspective).
- Adopted Space Grotesk + Inter as brand fonts.
- Refactored `Button` with `primary | secondary | ghost` variants.
- Migrated `WorkspaceBand`, `WorkspaceSurface`, `MediaSurface`, `InstrumentRail`, `StatusToneBadge` to new tokens; legacy `--vezor-*` / `--argus-*` names remain as aliases.
- Lightened `AppShell` ambient gradient.
```

- [ ] **Step 4: Commit changelog**

```bash
git add frontend/CHANGELOG.md
git commit -m "docs: changelog for Phase 1 foundations"
```

- [ ] **Step 5: Confirm commit graph**

```bash
git log --oneline -n 10
```

Expected: 7–8 new commits since the start of Phase 1 (one per task plus changelog).

---

## Done criteria

Phase 1 is complete when:

1. `pnpm --dir frontend test`, `lint`, and `build` all pass.
2. Every component now reachable from any of the 4 spec checklists (§2.1, §2.3, §3.1, §3.2, §6.1, §5.1–§5.6) consumes `--vz-*` tokens.
3. No new runtime dependency was added.
4. Existing pages render identically in structure (visual smoke test).
5. The branch contains discrete commits per task — Codex/reviewers can bisect cleanly.

After Phase 1 lands, hand off to **Phase 2: Spatial cockpit** (`docs/superpowers/plans/2026-04-30-omnisight-spec-phase-2-spatial-cockpit.md`).
