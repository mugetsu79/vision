# OmniSight Spec — Phase 4: Optional WebGL Lens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Behind a build-time feature flag, render the Vezor 3D mark as a real WebGL object on the Sign-In stage and Dashboard hero using `@react-three/fiber`. The CSS-perspective `OmniSightLens` from Phase 2 stays as the default + fallback for `prefers-reduced-motion`, `prefers-reduced-data`, and unsupported clients.

**Architecture:** A thin `OmniSightLensGL` wrapper lazy-loads `@react-three/fiber` and `@react-three/drei` only when `import.meta.env.VITE_FEATURE_WEBGL_LENS === "true"`. The mark is rendered from a GLB authored offline (initially the existing PNG mapped onto a billboard plane — upgrade to a true GLB later). The component falls back to the Phase-2 CSS lens whenever WebGL fails, the flag is off, the user prefers reduced motion, or the user prefers reduced data. No bundle bloat for the default flag-off build.

**Tech Stack:** React 19, Vite 6, Tailwind v4, Vitest 2, **@react-three/fiber 8**, **three 0.x**, **@react-three/drei 9**. Frontend root: `/Users/yann.moren/vision/frontend`. Branch: `codex/omnisight-ui-distinctiveness-followup`.

**Spec source:** `/Users/yann.moren/vision/docs/brand/omnisight-ui-spec-sheet.md` §3.4, §11 (Phase 4).

**Prerequisites:** Phases 1–3 merged. The CSS lens (`OmniSightLens`) and `useLensTilt` exist. Leadership has approved adding a WebGL dependency (per the spec's "Open questions" item 1).

---

## Pre-flight

```bash
cd /Users/yann.moren/vision
git status
git rev-parse --abbrev-ref HEAD
test -f frontend/src/components/brand/OmniSightLens.tsx && echo "Phase 2 OK"
grep -c "framer-motion" frontend/package.json   # ≥ 1, Phase 3 OK

pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```

If any check fails, do not proceed; resolve the missing prerequisite first.

## Approval gate

Before writing any code, confirm in the PR description / merge request:

- [ ] Leadership has approved adding `@react-three/fiber` + `three` (~85 KB gzip) as a dependency.
- [ ] The 3D asset has been chosen: either (a) an authored GLB (preferred) or (b) the existing PNG textured onto a billboard plane (fallback for this phase).
- [ ] An A/B / engagement-metric plan exists, or this ships behind a flag default-off.

If any of those is missing, **stop**. The CSS lens from Phase 2 already meets the spec.

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `frontend/package.json` | modify | add `three`, `@react-three/fiber`, `@react-three/drei` |
| `frontend/src/components/brand/OmniSightLensGL.tsx` | create | WebGL renderer (lazy-loaded) |
| `frontend/src/components/brand/OmniSightLensGL.test.tsx` | create | flag and fallback tests |
| `frontend/src/components/brand/OmniSightLensSwitch.tsx` | create | flag + capability check, picks GL or CSS variant |
| `frontend/src/components/brand/OmniSightLensSwitch.test.tsx` | create | tests |
| `frontend/src/lib/feature-flags.ts` | create or modify | `isWebglLensEnabled()` reads `import.meta.env.VITE_FEATURE_WEBGL_LENS` |
| `frontend/src/lib/feature-flags.test.ts` | create | tests |
| `frontend/src/pages/SignIn.tsx` | modify | swap `<OmniSightLens>` for `<OmniSightLensSwitch>` |
| `frontend/src/pages/Dashboard.tsx` | modify | same swap |
| `frontend/.env.example` | modify or create | document `VITE_FEATURE_WEBGL_LENS=false` |
| `frontend/public/brand/3d_logo.glb` | optional | authored GLB if available |

If a GLB is not provided, this phase ships a textured-plane fallback. The plan covers both.

---

## Task 1: Add the dependencies

- [ ] **Step 1: Install**

```bash
pnpm --dir frontend add three @react-three/fiber @react-three/drei
pnpm --dir frontend add -D @types/three
```

- [ ] **Step 2: Type-check**

```bash
pnpm --dir frontend exec tsc -b --noEmit
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore(frontend): add three + react-three-fiber + drei for WebGL lens"
```

---

## Task 2: Feature flag plumbing

**Files:**
- Create: `frontend/src/lib/feature-flags.ts`
- Create: `frontend/src/lib/feature-flags.test.ts`
- Modify: `frontend/.env.example` (create if missing)

- [ ] **Step 1: Write failing test**

`frontend/src/lib/feature-flags.test.ts`:

```ts
import { afterEach, describe, expect, test, vi } from "vitest";

import { isWebglLensEnabled } from "@/lib/feature-flags";

describe("feature flags", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  test("returns false when VITE_FEATURE_WEBGL_LENS is unset", () => {
    vi.stubEnv("VITE_FEATURE_WEBGL_LENS", "");
    expect(isWebglLensEnabled()).toBe(false);
  });

  test("returns true only for exactly 'true'", () => {
    vi.stubEnv("VITE_FEATURE_WEBGL_LENS", "true");
    expect(isWebglLensEnabled()).toBe(true);
  });

  test("returns false for '1' or 'TRUE'", () => {
    vi.stubEnv("VITE_FEATURE_WEBGL_LENS", "1");
    expect(isWebglLensEnabled()).toBe(false);
    vi.stubEnv("VITE_FEATURE_WEBGL_LENS", "TRUE");
    expect(isWebglLensEnabled()).toBe(false);
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
pnpm --dir frontend exec vitest run src/lib/feature-flags.test.ts
```

- [ ] **Step 3: Implement**

`frontend/src/lib/feature-flags.ts`:

```ts
export function isWebglLensEnabled(): boolean {
  const value = import.meta.env.VITE_FEATURE_WEBGL_LENS;
  return value === "true";
}
```

- [ ] **Step 4: Document the env var**

In `frontend/.env.example` (create if missing) add:

```env
# Feature flags
VITE_FEATURE_WEBGL_LENS=false
```

- [ ] **Step 5: Run + lint + commit**

```bash
pnpm --dir frontend exec vitest run src/lib/feature-flags.test.ts
pnpm --dir frontend lint
git add frontend/src/lib/feature-flags.ts frontend/src/lib/feature-flags.test.ts frontend/.env.example
git commit -m "feat(flags): add VITE_FEATURE_WEBGL_LENS gate"
```

---

## Task 3: Capability check helper

**Files:**
- Modify: `frontend/src/lib/feature-flags.ts` (add `hasWebglSupport`)
- Modify: `frontend/src/lib/feature-flags.test.ts`

- [ ] **Step 1: Add failing test**

Append to `frontend/src/lib/feature-flags.test.ts`:

```ts
import { hasWebglSupport } from "@/lib/feature-flags";

describe("hasWebglSupport", () => {
  test("returns false when WebGL is not available (jsdom)", () => {
    expect(hasWebglSupport()).toBe(false);
  });
});
```

- [ ] **Step 2: Implement**

Append to `frontend/src/lib/feature-flags.ts`:

```ts
export function hasWebglSupport(): boolean {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    const gl =
      canvas.getContext("webgl2") ||
      canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl");
    return Boolean(gl);
  } catch {
    return false;
  }
}

export function prefersReducedExperience(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return (
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
    window.matchMedia("(prefers-reduced-data: reduce)").matches
  );
}
```

- [ ] **Step 3: Test, lint, commit**

```bash
pnpm --dir frontend exec vitest run src/lib/feature-flags.test.ts
pnpm --dir frontend lint
git add frontend/src/lib/feature-flags.ts frontend/src/lib/feature-flags.test.ts
git commit -m "feat(flags): add hasWebglSupport + prefersReducedExperience"
```

---

## Task 4: Implement `OmniSightLensGL` (textured-plane variant)

**Files:**
- Create: `frontend/src/components/brand/OmniSightLensGL.tsx`
- Create: `frontend/src/components/brand/OmniSightLensGL.test.tsx`

The simplest viable WebGL hero: a pointer-reactive plane that holds the existing 3D PNG, lit and rotated subtly. Migrate to a true GLB once authored.

- [ ] **Step 1: Write a smoke test that does not require a GL context**

`frontend/src/components/brand/OmniSightLensGL.test.tsx`:

```tsx
import { describe, expect, test, vi } from "vitest";

vi.mock("@react-three/fiber", () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="r3f-canvas">{children}</div>
  ),
  useFrame: vi.fn(),
}));

vi.mock("@react-three/drei", () => ({
  useTexture: () => ({}),
  Float: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { render, screen } from "@testing-library/react";

import { OmniSightLensGL } from "@/components/brand/OmniSightLensGL";

describe("OmniSightLensGL", () => {
  test("mounts a Canvas root", () => {
    render(<OmniSightLensGL variant="signin" />);
    expect(screen.getByTestId("r3f-canvas")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/brand/OmniSightLensGL.test.tsx
```

- [ ] **Step 3: Implement the component**

`frontend/src/components/brand/OmniSightLensGL.tsx`:

```tsx
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, useTexture } from "@react-three/drei";
import { useRef } from "react";
import type { Mesh } from "three";

import { productBrand } from "@/brand/product";
import { cn } from "@/lib/utils";

type Variant = "signin" | "dashboard";

type Props = {
  variant?: Variant;
  className?: string;
};

const variantSizes: Record<Variant, string> = {
  signin: "w-[clamp(18rem,32vw,28rem)] aspect-square",
  dashboard: "w-[clamp(10rem,18vw,16rem)] aspect-square",
};

function MarkPlane() {
  const ref = useRef<Mesh>(null);
  const tex = useTexture(productBrand.runtimeAssets.logo3d);
  useFrame((state, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * 0.06;
  });
  return (
    <Float speed={0.6} rotationIntensity={0.2} floatIntensity={0.4}>
      <mesh ref={ref}>
        <planeGeometry args={[1.6, 1.6]} />
        <meshStandardMaterial map={tex} transparent metalness={0.2} roughness={0.55} />
      </mesh>
    </Float>
  );
}

export function OmniSightLensGL({ variant = "signin", className }: Props) {
  return (
    <div
      data-testid="omnisight-lens-gl"
      data-variant={variant}
      aria-hidden="true"
      className={cn("relative grid place-items-center", variantSizes[variant], className)}
    >
      <Canvas
        camera={{ position: [0, 0, 2.4], fov: 38 }}
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[1.4, 2, 2]} intensity={1.0} />
        <pointLight color="#7e53ff" intensity={1.2} position={[-1.6, 1, 1]} />
        <MarkPlane />
      </Canvas>
    </div>
  );
}
```

- [ ] **Step 4: Run test, lint**

```bash
pnpm --dir frontend exec vitest run src/components/brand/OmniSightLensGL.test.tsx
pnpm --dir frontend lint
```

Expected: green.

- [ ] **Step 5: Build with the flag enabled**

```bash
VITE_FEATURE_WEBGL_LENS=true pnpm --dir frontend build
```

Expected: builds successfully and emits a chunk that includes three.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/brand/OmniSightLensGL.tsx frontend/src/components/brand/OmniSightLensGL.test.tsx
git commit -m "feat(ui): WebGL lens via react-three-fiber (textured-plane variant)"
```

---

## Task 5: `OmniSightLensSwitch` — pick CSS or GL based on flag + capability

**Files:**
- Create: `frontend/src/components/brand/OmniSightLensSwitch.tsx`
- Create: `frontend/src/components/brand/OmniSightLensSwitch.test.tsx`

- [ ] **Step 1: Write the test**

`frontend/src/components/brand/OmniSightLensSwitch.test.tsx`:

```tsx
import { afterEach, describe, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/feature-flags", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/feature-flags")>(
      "@/lib/feature-flags",
    );
  return {
    ...actual,
    isWebglLensEnabled: vi.fn().mockReturnValue(false),
    hasWebglSupport: vi.fn().mockReturnValue(false),
    prefersReducedExperience: vi.fn().mockReturnValue(false),
  };
});

import {
  isWebglLensEnabled,
  hasWebglSupport,
  prefersReducedExperience,
} from "@/lib/feature-flags";
import { OmniSightLensSwitch } from "@/components/brand/OmniSightLensSwitch";

describe("OmniSightLensSwitch", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  test("renders the CSS lens by default (flag off)", () => {
    render(<OmniSightLensSwitch variant="signin" />);
    expect(screen.getByTestId("omnisight-lens")).toBeInTheDocument();
    expect(screen.queryByTestId("omnisight-lens-gl")).toBeNull();
  });

  test("renders the CSS lens when reduced motion / data is preferred", () => {
    vi.mocked(isWebglLensEnabled).mockReturnValue(true);
    vi.mocked(hasWebglSupport).mockReturnValue(true);
    vi.mocked(prefersReducedExperience).mockReturnValue(true);
    render(<OmniSightLensSwitch variant="signin" />);
    expect(screen.getByTestId("omnisight-lens")).toBeInTheDocument();
  });

  test("renders the GL lens when flag is on, support exists, and no reduced preference", async () => {
    vi.mocked(isWebglLensEnabled).mockReturnValue(true);
    vi.mocked(hasWebglSupport).mockReturnValue(true);
    vi.mocked(prefersReducedExperience).mockReturnValue(false);
    render(<OmniSightLensSwitch variant="signin" />);
    // GL lens is lazy; wait one tick
    expect(await screen.findByTestId("omnisight-lens-gl")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
pnpm --dir frontend exec vitest run src/components/brand/OmniSightLensSwitch.test.tsx
```

- [ ] **Step 3: Implement the switch**

`frontend/src/components/brand/OmniSightLensSwitch.tsx`:

```tsx
import { Suspense, lazy, useEffect, useState } from "react";

import { OmniSightLens } from "@/components/brand/OmniSightLens";
import {
  hasWebglSupport,
  isWebglLensEnabled,
  prefersReducedExperience,
} from "@/lib/feature-flags";

const OmniSightLensGL = lazy(() =>
  import("@/components/brand/OmniSightLensGL").then((m) => ({
    default: m.OmniSightLensGL,
  })),
);

type Props = {
  variant?: "signin" | "dashboard";
  className?: string;
};

export function OmniSightLensSwitch({ variant = "signin", className }: Props) {
  const [shouldUseGL, setShouldUseGL] = useState(false);

  useEffect(() => {
    if (!isWebglLensEnabled()) return;
    if (!hasWebglSupport()) return;
    if (prefersReducedExperience()) return;
    setShouldUseGL(true);
  }, []);

  if (!shouldUseGL) {
    return <OmniSightLens variant={variant} className={className} />;
  }

  return (
    <Suspense
      fallback={<OmniSightLens variant={variant} className={className} />}
    >
      <OmniSightLensGL variant={variant} className={className} />
    </Suspense>
  );
}
```

- [ ] **Step 4: Run + lint**

```bash
pnpm --dir frontend exec vitest run src/components/brand/OmniSightLensSwitch.test.tsx
pnpm --dir frontend lint
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/brand/OmniSightLensSwitch.tsx frontend/src/components/brand/OmniSightLensSwitch.test.tsx
git commit -m "feat(ui): OmniSightLensSwitch picks GL or CSS by capability + flag"
```

---

## Task 6: Adopt the switch on Sign-In and Dashboard

**Files:**
- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Replace the Phase-2 import on each page**

In `frontend/src/pages/SignIn.tsx`:

```tsx
- import { OmniSightLens } from "@/components/brand/OmniSightLens";
+ import { OmniSightLensSwitch } from "@/components/brand/OmniSightLensSwitch";
```

And the JSX:

```tsx
- lens={<OmniSightLens variant="signin" />}
+ lens={<OmniSightLensSwitch variant="signin" />}
```

In `frontend/src/pages/Dashboard.tsx`:

```tsx
- import { OmniSightLens } from "@/components/brand/OmniSightLens";
+ import { OmniSightLensSwitch } from "@/components/brand/OmniSightLensSwitch";

- lens={<OmniSightLens variant="dashboard" />}
+ lens={<OmniSightLensSwitch variant="dashboard" />}
```

- [ ] **Step 2: Update tests if they assert on `omnisight-lens`**

Existing `Dashboard.test.tsx` and `SignIn.test.tsx` both assert `omnisight-lens` test id. The switch defaults to the CSS lens when the flag is off, so those test ids still appear; tests should remain green. Verify:

```bash
pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx src/pages/Dashboard.test.tsx
```

If a test fails because the GL test id appears, ensure `VITE_FEATURE_WEBGL_LENS` is unset in vitest. Vitest does **not** load `.env` by default, so `import.meta.env.VITE_FEATURE_WEBGL_LENS` is `undefined`, which the flag treats as `false`. Confirm this assumption in the test environment by adding a guard test in `feature-flags.test.ts` if needed.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SignIn.tsx frontend/src/pages/Dashboard.tsx
git commit -m "feat(ui): use OmniSightLensSwitch on sign-in and dashboard"
```

---

## Task 7: Real GLB upgrade (optional within Phase 4)

If a designer-authored GLB exists in `docs/brand/assets/source/3d_logo.glb` (or similar):

- [ ] **Step 1: Copy the GLB to public**

```bash
cp docs/brand/assets/source/3d_logo.glb frontend/public/brand/3d_logo.glb
```

- [ ] **Step 2: Replace the textured-plane in `OmniSightLensGL`**

In `OmniSightLensGL.tsx`, replace the `MarkPlane` component with:

```tsx
import { useGLTF } from "@react-three/drei";

function MarkModel() {
  const { scene } = useGLTF("/brand/3d_logo.glb");
  const ref = useRef<Object3D>(null);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.08;
  });
  return <primitive ref={ref} object={scene} scale={0.85} />;
}

useGLTF.preload("/brand/3d_logo.glb");
```

Add the `Object3D` import: `import type { Object3D } from "three";`.

- [ ] **Step 3: Update the `MarkPlane` usage**

Inside `<Canvas>`, swap `<MarkPlane />` for:

```tsx
<Suspense fallback={null}>
  <Float speed={0.6} rotationIntensity={0.2} floatIntensity={0.4}>
    <MarkModel />
  </Float>
</Suspense>
```

Add `import { Suspense } from "react";` at the top.

- [ ] **Step 4: Build + visual smoke**

```bash
VITE_FEATURE_WEBGL_LENS=true pnpm --dir frontend dev
# /signin and /dashboard show the rotating GLB
# Pointer movement: use OrbitControls? No — we keep auto-rotate only
```

If no GLB is available, **skip Task 7** entirely; the textured-plane variant from Task 4 is the Phase-4 deliverable.

- [ ] **Step 5: Commit**

```bash
git add frontend/public/brand/3d_logo.glb frontend/src/components/brand/OmniSightLensGL.tsx
git commit -m "feat(ui): render real GLB on WebGL lens"
```

---

## Task 8: Bundle audit

- [ ] **Step 1: Build with flag off and inspect bundle size**

```bash
pnpm --dir frontend build
ls -lah frontend/dist/assets | head -20
```

Expected: no `three`-related chunk in the default build (the dynamic `import()` ensures lazy loading; only used if the switch goes GL). Confirm there is no top-level static import of `three` anywhere outside `OmniSightLensGL.tsx` and its dependencies.

```bash
grep -R "from \"three\"" frontend/src
grep -R "from '@react-three" frontend/src
```

Expected: only `OmniSightLensGL.tsx` matches.

- [ ] **Step 2: Build with flag on and capture sizes**

```bash
VITE_FEATURE_WEBGL_LENS=true pnpm --dir frontend build
ls -lah frontend/dist/assets | head -30
```

Note the additional chunk size. Add a line to the changelog with the measured number.

- [ ] **Step 3: Commit changelog**

`frontend/CHANGELOG.md`:

```markdown
## Unreleased — Phase 4 Optional WebGL

- Added `@react-three/fiber` + `@react-three/drei` + `three`. Lazy-loaded behind `VITE_FEATURE_WEBGL_LENS`.
- New `OmniSightLensSwitch` chooses CSS or GL based on flag, capability, and reduced-motion/data preferences.
- Default builds (`flag=false`) do not pay the WebGL bundle cost (verified via bundle audit).
- Bundle delta when flag is on: <RECORD MEASURED VALUE HERE> KB gzipped.
```

```bash
git add frontend/CHANGELOG.md
git commit -m "docs: changelog for Phase 4 WebGL lens"
```

---

## Task 9: Roll-out plan + verification

- [ ] **Step 1: Confirm zero-cost default**

The default `pnpm --dir frontend build` (flag unset) must produce identical UX to Phase 3. Run smoke tests:

```bash
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend dev
# /signin and /dashboard render the CSS lens (Phase 2 behavior)
```

- [ ] **Step 2: Confirm GL on**

```bash
VITE_FEATURE_WEBGL_LENS=true pnpm --dir frontend dev
# /signin and /dashboard render the GL lens; reduce-motion in DevTools must fall back to CSS
```

- [ ] **Step 3: Final lint + test**

```bash
pnpm --dir frontend lint
pnpm --dir frontend test
```

- [ ] **Step 4: Open the rollout PR**

The PR description should:

- State the bundle delta (measured in Task 8).
- State the default flag value (`false`).
- Document the rollout path (e.g., enable in staging via `VITE_FEATURE_WEBGL_LENS=true`, monitor FPS / errors, then promote).
- Include screenshots of `/signin` and `/dashboard` with the flag on and off.

---

## Done criteria

Phase 4 is complete when:

1. `pnpm --dir frontend lint`, `test`, and `build` all pass with the flag off.
2. The default build does **not** include `three` in any non-lazy chunk (verified by grep + dist inspection).
3. With `VITE_FEATURE_WEBGL_LENS=true`, `/signin` and `/dashboard` render the GL lens.
4. With reduced-motion or reduced-data, the switch falls back to the CSS lens, even with the flag on.
5. The CHANGELOG records the measured bundle delta.

If the bundle delta exceeds **120 KB gzipped**, stop and re-evaluate before merging — that is the agreed ceiling for the optional WebGL path. Use `webpack-bundle-analyzer` or `vite-bundle-visualizer` if more detail is needed.

This plan ends Phase 4. Future motion / 3D work (Spline-rendered hero, real-time scene volumetrics, etc.) belongs in a new spec.
