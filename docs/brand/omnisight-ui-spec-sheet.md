# Vezor / OmniSight — UI / UX Spec Sheet

Review basis: current Vezor product UI on `main`
Date: 2026-04-30
Purpose: best-in-class design recommendations for the Vezor product surface, in line with the OmniSight brand (premium, dark, vigilant, dimensional). Modern motion. 3D where the product earns it. No marketing-pastiche.

This sheet is prescriptive: every recommendation is paired with a token, a value, or a code shape that engineering can apply directly. It is scoped to the Vezor product UI; marketing/web are out of scope.

---

## 1. Executive Audit

### What is already strong in the current product UI
- Composition primitives exist: `WorkspaceBand`, `WorkspaceSurface`, `MediaSurface`, `InstrumentRail`, `StatusToneBadge` (`frontend/src/components/layout/workspace-surfaces.tsx`).
- `OmniSightField` parallaxes the 3D logo with three z-stacked layers, orbital rings, and a conic radar mask — good structural bones for a real spatial cockpit.
- Palette discipline (75/15/5/5) is already specified in the earlier OmniSight UI design spec.
- `prefers-reduced-motion` is honored at the CSS level (`frontend/src/index.css`).
- `/dashboard` is restored as a real overview, not a redirect.

### Where it still reads "generic dark SaaS"
1. **Surfaces are flat.** Every panel = same `bg + border-white/10 + radius-0.9rem`. No elevation system, no depth ladder. The shell, dashboard, live, and sites pages all carry the same visual weight.
2. **Motion is decorative drift.** The orbital rings and mark stack animate ambiently but never react to navigation, hover, selection, telemetry, or scroll. Motion is wallpaper, not signal.
3. **No real 3D.** The 3D logo is rendered as a 2D PNG drop-shadowed and stacked. There is no perspective, no parallax-on-pointer, no depth-on-scroll. The asset *promises* dimension; the UI does not deliver it.
4. **Typography is system-default ("Avenir Next" → Segoe UI fallback).** Brand spec calls for `Sora`/`Space Grotesk` wordmark + `Inter`/`Manrope`/`Plus Jakarta Sans` UI. The product currently uses neither.
5. **Sign-in lens uses a 20 MB MP4** (`logo-no-bg.mp4`) as the hero. Heavy, uncacheable, hidden in `prefers-reduced-motion`, and inconsistent across browsers. The design spec calls for a CSS-driven lens stage; we should use the MP4 as a fallback poster only.
6. **Buttons and badges are pill-shaped neutral grays** with no semantic shape language. The primary CTA has no clear "intelligence-light" identity.
7. **Charts and live tiles are not visually first-class.** They borrow generic surface chrome (white/8 border on graphite). For an intelligence product, the data plane should feel sharper than the chrome around it.
8. **The icon rail and context rail share visual weight** with the workspace stage — there is no clear "frame vs. content" hierarchy.

The remainder of this sheet treats those eight items as the editorial brief.

---

## 2. Brand Foundations

### 2.1 Palette tokens (canonical)

Add the following to `:root` in `frontend/src/index.css`. Where a token already exists, the new name is the recommended alias (deprecate the older `--argus-*` names in a later cleanup pass).

```css
/* Canvas */
--vz-canvas-void:        #03050a; /* pure cockpit void */
--vz-canvas-obsidian:    #07090f; /* page background */
--vz-canvas-graphite:    #0e131c; /* workflow surface base */
--vz-canvas-graphite-up: #131927; /* raised surface */
--vz-media-black:        #010306; /* video / evidence plate */

/* Lens — intelligence light */
--vz-lens-cerulean:      #6ebdff; /* primary intelligence */
--vz-lens-cerulean-deep: #2c8df0; /* pressed / active */
--vz-lens-aqua:          #76e0ff; /* live highlight */
--vz-lens-violet:        #7e53ff; /* secondary / perimeter */
--vz-lens-lilac:         #c7b8ff; /* hairline glow */

/* Operational status */
--vz-state-healthy:      #6fe0a3;
--vz-state-attention:    #f5c46a;
--vz-state-risk:         #f48ca6;
--vz-state-info:         #79b8ff;

/* Text */
--vz-text-primary:       #f4f7fb;
--vz-text-secondary:     #b8c6dc;
--vz-text-muted:         #8497b3;
--vz-text-subtle:        #5e6e88;

/* Lines */
--vz-hair:               rgba(206, 224, 255, 0.06);   /* default border  */
--vz-hair-strong:        rgba(206, 224, 255, 0.12);   /* divider         */
--vz-hair-focus:         rgba(118, 224, 255, 0.42);   /* keyboard focus  */
--vz-hair-active:        rgba(126, 83, 255, 0.42);    /* selected state  */
```

### 2.2 Color ratios per surface

Reaffirms the design spec, with concrete pixel-budget guidance:

| Zone                 | Neutral graphite/black | Cerulean | Violet | Status |
|----------------------|------------------------|----------|--------|--------|
| Sign-in stage        | 50%                    | 25%      | 20%    | 5%     |
| Dashboard cockpit    | 70%                    | 18%      | 6%     | 6%     |
| Live workspace       | 80% (incl. video)      | 12%      | 3%     | 5%     |
| Patterns workbench   | 80%                    | 14%      | 2%     | 4%     |
| Evidence desk        | 82% (media-first)      | 8%       | 2%     | 8%     |
| Scenes / Sites       | 78%                    | 14%      | 4%     | 4%     |
| Operations           | 78%                    | 10%      | 2%     | 10%    |

Rule: violet is *only* for the sign-in lens, sentiment chips when "AI-generated," and the active-nav focus halo. Never as a panel tint.

### 2.3 Typography

Replace the current `"Avenir Next", "Suisse Intl", "Poppins", "Segoe UI"` stack with a free, brand-aligned pair already endorsed by `docs/brand/logo-brand-spec.md`:

```css
/* Add to index.css */
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap");

:root {
  --vz-font-display: "Space Grotesk", "Sora", system-ui, sans-serif;
  --vz-font-body:    "Inter", "Manrope", system-ui, sans-serif;
  --vz-font-mono:    "JetBrains Mono", ui-monospace, "Menlo", monospace;
}

body { font-family: var(--vz-font-body); }
h1, h2, .vz-display, .vz-eyebrow { font-family: var(--vz-font-display); }
```

Why Space Grotesk: it gives Vezor a signature wordmark feel without licensing cost, has tabular figures (matters for telemetry and counts), and pairs cleanly with Inter for product text. Inter Variable for body keeps cost low and supports the existing weights used today.

#### Type scale
| Role            | Size / line-height | Weight | Tracking | Usage                                    |
|-----------------|--------------------|--------|----------|------------------------------------------|
| display-xl      | 56 / 60            | 700    | -1.5%    | Sign-in headline                         |
| display-lg      | 40 / 44            | 700    | -1%      | Dashboard hero, page heroes              |
| h1              | 28 / 34            | 600    | -0.5%    | `WorkspaceBand` title                    |
| h2              | 20 / 26            | 600    | normal   | Section titles in panels                 |
| h3              | 16 / 22            | 600    | normal   | Card titles                              |
| body-lg         | 15 / 24            | 400    | normal   | Long-form description                    |
| body            | 14 / 22            | 400    | normal   | Default UI                               |
| caption         | 12 / 18            | 500    | normal   | Secondary metadata                       |
| eyebrow         | 11 / 16            | 600    | +18%     | Eyebrows, key labels (uppercase)         |
| mono            | 12 / 18            | 500    | normal   | IDs, RTSP, telemetry numerics            |

Render tabular numbers in metric tiles with `font-variant-numeric: tabular-nums;`.

### 2.4 Voice signals embedded in UI copy

- "OmniSight" is the *layer*, "Vezor" is the *product*, "Scenes" is the unit.
- Status copy uses present-tense system voice: "Streams healthy", "3 direct streams unavailable", "telemetry stale".
- Empty states are operator-directed: "No deployment sites yet — add the first deployment location."

---

## 3. Dimensional Language

The brand asks for "dimension" without the gaming aesthetic. We stage that with a small, reusable set of spatial tokens.

### 3.1 Elevation ladder

Six surfaces, each a single shadow + border-light combination. Stack additively only where intentional.

```css
:root {
  /* depth = (border highlight) + (cast shadow) + (rim glow on focus) */
  --vz-elev-0: 0 0 0 1px var(--vz-hair);                      /* page surface */
  --vz-elev-1: 0 1px 0 0 rgba(255,255,255,0.04) inset,
               0 12px 32px -28px rgba(0,0,0,0.9),
               0 0 0 1px var(--vz-hair);                      /* default panel */
  --vz-elev-2: 0 1px 0 0 rgba(255,255,255,0.06) inset,
               0 18px 60px -34px rgba(0,0,0,0.95),
               0 0 0 1px var(--vz-hair-strong);               /* raised card */
  --vz-elev-3: 0 1px 0 0 rgba(255,255,255,0.08) inset,
               0 32px 90px -42px rgba(0,0,0,0.96),
               0 0 0 1px var(--vz-hair-strong);               /* dialog / panel */
  --vz-elev-glow-cerulean:
               0 0 0 1px var(--vz-hair-focus),
               0 28px 80px -38px rgba(110,189,255,0.55);      /* active scene */
  --vz-elev-glow-violet:
               0 0 0 1px var(--vz-hair-active),
               0 28px 80px -38px rgba(126,83,255,0.50);       /* sign-in lens */
}
```

Apply consistently:
- Workspace stage (page background): `elev-0`.
- `WorkspaceBand`, `WorkspaceSurface`, table containers: `elev-1`.
- Dashboard hero, hovered scene tile, selected evidence card: `elev-2`.
- Modals, command palette, toast, popovers: `elev-3`.
- Active live scene focus, dashboard pulse-card: `elev-glow-cerulean`.
- Sign-in panel + lens stage: `elev-glow-violet`.

### 3.2 Border-radius scale

| Token        | Value   | Used for                                 |
|--------------|---------|------------------------------------------|
| `--vz-r-pill`| 999px   | Buttons, badges, status chips            |
| `--vz-r-sm`  | 8px     | Inputs, table rows on hover              |
| `--vz-r-md`  | 12px    | Internal panels (filter bar, queue items)|
| `--vz-r-lg`  | 16px    | Workspace surfaces                       |
| `--vz-r-xl`  | 24px    | Hero stages, sign-in lens halo           |

Stop using arbitrary `0.85rem` / `0.9rem` / `0.95rem` / `1rem` / `1.15rem` like the current code. Pick from the scale.

### 3.3 3D depth tokens

We do **not** add a WebGL dependency. We get most of the way with CSS perspective + transform-style preserve-3d.

```css
:root {
  --vz-perspective: 1400px;       /* product-wide vanishing point */
  --vz-tilt-soft: 4deg;           /* hero hover */
  --vz-tilt-firm: 8deg;           /* sign-in lens */
  --vz-pop-z: 18px;               /* selected/active translateZ */
  --vz-rest-z: 0px;
  --vz-parallax-bg: -36px;        /* shell ambient layer */
  --vz-parallax-mid: -12px;
  --vz-parallax-fg: 0px;
}
```

Apply via container `transform: perspective(var(--vz-perspective))` and child `translate3d(_, _, var(--vz-pop-z))`. Combine with `will-change: transform` and `transform-style: preserve-3d` only on stages that need it (sign-in, dashboard hero, live tiles on hover). Wrapped in `@media (prefers-reduced-motion: no-preference)`.

### 3.4 Optional: real WebGL upgrade path

If, in a later phase, leadership approves a 3D dependency:

- **First choice:** `@react-three/fiber` + `@react-three/drei` to render the 3D logo as a real GLB on the sign-in stage and dashboard hero only. ~85 KB gzip; tree-shakable. Reuse the existing PNG as a fallback poster for `prefers-reduced-motion` and for first paint.
- **Second choice:** Spline export (`@splinetool/react-spline`) embeds the existing 3D mark with sub-pixel parallax and pointer-driven rotation. Fastest to ship; pays a runtime cost.
- **Third choice (lightest):** Lottie/dotLottie for a 200–600 KB looping mark animation. No real 3D math but faster than MP4 and respects color tokens.

Recommendation: ship Phase 1 with **CSS perspective only**, then if engagement metrics warrant it, add R3F for sign-in + dashboard hero.

---

## 4. Motion System

Motion exists to communicate **navigation**, **state change**, and **focus**. Decoration is a side effect, not the goal.

### 4.1 Easings & durations

```css
:root {
  --vz-ease-product: cubic-bezier(0.22, 1, 0.36, 1);     /* "lens snap" */
  --vz-ease-out:     cubic-bezier(0.16, 1, 0.3, 1);
  --vz-ease-in-out:  cubic-bezier(0.65, 0, 0.35, 1);
  --vz-ease-spring:  cubic-bezier(0.34, 1.56, 0.64, 1);  /* tile pop only */

  --vz-dur-instant: 90ms;   /* hover color, badge swap */
  --vz-dur-quick:   180ms;  /* toggles, focus rings */
  --vz-dur-base:    240ms;  /* page transitions, panel reveals */
  --vz-dur-soft:    320ms;  /* hero hand-off, modal */
  --vz-dur-ambient: 14s;    /* lens drift, orbital sweep */
}
```

Cap product-UI transitions at `--vz-dur-soft` (320ms). Anything longer must be ambient (sign-in / dashboard) and respect reduced-motion.

### 4.2 Motion choreography by surface

| Surface             | Motion                                                                  | Trigger                  | Duration / easing            |
|---------------------|-------------------------------------------------------------------------|--------------------------|------------------------------|
| Sign-in lens        | Lens float (Z-axis breathe), orbital ring sweep, glint drift, halo bloom on focus | mount, ambient, focus    | ambient + 320ms ease-product |
| Workspace transition| 8px Y rise + 0→1 opacity + subtle scale 0.997→1                          | route change             | 240ms ease-product           |
| Nav active state    | Cerulean focus dot slides between nav items, rest morphs                | nav click                | 220ms ease-product           |
| Dashboard hero      | Scene preview cycles via cross-dissolve every 6s, paused on hover/focus | mount + interval         | 800ms ease-in-out            |
| Live tile hover     | translateZ(18px) + ring goes cerulean + corner brackets stretch         | hover / focus            | 220ms ease-product           |
| Live tile telemetry | Sparkline reveal (left→right), latency pip pulse (1.6s loop, ≤3 pulses) | data update              | 320ms / ambient              |
| Evidence selection  | Selected queue row → media plane swap with slide-from-right + fade      | select                   | 280ms ease-product           |
| Patterns chart      | Bucket selection: y-axis line drops from 100% to bucket; selected bucket shaft glows | click                    | 240ms ease-product           |
| Sign-in success     | Lens collapses inward, dissolves to dashboard hero                      | post-auth                | 480ms ease-in-out            |
| Reduced motion      | All ambient motion off; only durations ≤180ms with opacity-only changes | OS pref                  | n/a                          |

### 4.3 Reusable React motion utility

Recommend Framer Motion for choreographed sequences (sign-in, evidence selection, dashboard hero). It is already React-friendly, ~30 KB gzipped, and supports reduced-motion natively via `useReducedMotion`. If we want zero deps, use the existing CSS keyframes — they are sufficient for everything except the cross-fade evidence transition.

```tsx
// useReducedMotionSafe.ts
import { useReducedMotion } from "framer-motion";

export function useMotionPreset(name: "rise" | "lensSnap" | "evidenceSwap") {
  const reduce = useReducedMotion();
  if (reduce) return { initial: false, animate: { opacity: 1 }, transition: { duration: 0 } };
  // …token-driven presets
}
```

### 4.4 Motion anti-patterns (do not do)

- No bounce easings on workflow controls.
- No infinite loop animation behind text or tables.
- No scroll-jacking. Never override native scroll.
- No simultaneous animation of more than two key elements per route.
- No animated background blur (very expensive on Intel macOS — see CLAUDE.md hardware notes).

---

## 5. Composition System (Spec)

The current primitives cover the right boxes. Extend the contract with explicit variants and required props.

### 5.1 `WorkspaceBand`
Compact intro band for workflow pages. Default tone: graphite.

```ts
interface WorkspaceBandProps {
  eyebrow: string;
  title: string;
  description?: string;
  density?: "compact" | "standard"; // default standard; "compact" for Sites/Settings/etc.
  accent?: "neutral" | "cerulean" | "violet"; // hairline rim only
  actions?: ReactNode;
}
```

Spec:
- `elev-1`. Background: `linear-gradient(180deg, var(--vz-canvas-graphite) 0%, var(--vz-canvas-graphite-up) 100%)`.
- 1px hairline border `--vz-hair`.
- 24px / 20px (`compact`) vertical padding.
- Title in `display` font, 28px.
- `accent` adds a 1.5px-wide cerulean/violet rim along the top edge only — never a tinted background.

### 5.2 `WorkspaceHero` *(new)*
For sign-in and dashboard only. Two slots: `lens` (right) + `body` (left).

- `elev-glow-violet` (sign-in) or `elev-glow-cerulean` (dashboard).
- Built on a `perspective: var(--vz-perspective)` root.
- Lens slot accepts `<OmniSightLens variant="…" />` — the upgraded mark stage (see §6.10).

### 5.3 `WorkspaceSurface`
Default panel.

- `elev-1`. Padding: 20px / 24px depending on density.
- On hover (interactive variant): `elev-2` + 1px cerulean rim. Cursor pointer.
- Disable hover effects on non-clickable surfaces — current `OverviewLink` over-applies hover state.

### 5.4 `MediaSurface`
Pure black plate for video and evidence imagery.

- Background: `var(--vz-media-black)`.
- Border: `--vz-hair-strong` only.
- Inner frame: 4-corner brackets in `--vz-lens-cerulean` at 60% opacity, 1px, 18px length. (See §6.6.)
- No gradient overlays at rest. Bottom info bar is a `linear-gradient(180deg, transparent, rgba(2,4,8,0.92))` *only when telemetry is present*.

### 5.5 `InstrumentRail`
Right-side metrics / facts rail.

- Width: 320px desktop, 360px on Patterns. Collapses to full-width on `< 1024px`.
- Internal sections separated by `divide-y border-color: var(--vz-hair)`.
- `role="complementary"` and `aria-label`.

### 5.6 `StatusToneBadge`
Already shipped. Extend tones:

| Tone        | Border / bg / text                                       | Use                           |
|-------------|----------------------------------------------------------|-------------------------------|
| `healthy`   | green border + 22% alpha bg + green text                 | live, OK                      |
| `attention` | amber                                                    | stale, pending                |
| `danger`    | rose                                                     | failed, destructive           |
| `accent`    | cerulean                                                 | metric callout                |
| `intent`    | violet                                                   | AI-resolved query, model-tag  |
| `muted`     | hairline neutral                                         | metadata                      |

### 5.7 `Toolbar` *(new helper)*
Replaces the ad-hoc filter rows on Patterns, Cameras, and Incidents.

- Height: 56px.
- Left: filters as inline `<select>`s with the existing `Select` component.
- Right: actions (`Add scene`, `Download CSV`).
- Search input is sticky-left if present.
- Background: `--vz-canvas-graphite-up`. Bottom 1px hairline.

### 5.8 `KpiTile` *(new)*
Replace the inline `OverviewMetric` (Dashboard) with a token-driven primitive.

- Eyebrow + value + delta + sparkline slot.
- Pulse light: a 3px-tall cerulean line behind the value that animates `width: 0 → 100%` over 1.4s on mount.
- Tabular numerics.

---

## 6. Component Spec Sheet

### 6.1 Buttons (refresh)

Three variants. Pill-shape stays — distinctive on dark, distinctive vs. shadcn defaults.

| Variant   | Background                                                      | Border                          | Text          | Shadow                    |
|-----------|-----------------------------------------------------------------|---------------------------------|---------------|---------------------------|
| `primary` | `linear-gradient(135deg, #6ebdff 0%, #2c8df0 100%)`              | none                            | `#04101b`     | `0 14px 30px -18px rgba(110,189,255,0.6)` |
| `secondary` | `linear-gradient(180deg, #161c26, #0d121a)`                    | `1px var(--vz-hair-strong)`     | `--vz-text-primary` | `--vz-elev-1` |
| `ghost`   | transparent                                                     | `1px var(--vz-hair)`            | `--vz-text-secondary` | none |

Hover: brightness 1.06 + 1px cerulean rim. Active: scale 0.98. Disabled: 56% opacity, default cursor.

Add `loading` prop: shows a spinner *and* keeps the original label (no width-jump). Recommended spec already specified by `superpowers:loading-buttons`.

### 6.2 Inputs / Selects

- Height: 40px (matches `Button` total height).
- Background: `--vz-canvas-graphite-up`. Border: `--vz-hair-strong` at rest, `--vz-hair-focus` on focus + 2px outline `var(--vz-hair-focus)`.
- Placeholder: `--vz-text-muted`. Filled value: `--vz-text-primary`.
- Multi-select: replace native `<select multiple>` (used in `History.tsx`) with a token-driven combobox in a follow-up pass.

### 6.3 Badges (`Badge` component)

Square-rounded 8px by default for badges that mark *attributes* (tracker types, IDs); pill for *states* (`StatusToneBadge`). Today the codebase mixes these — pick one rule:
- Attribute (object): rounded-md.
- State (verb / status): pill.

### 6.4 Tables

Today: dense `Table` component with hardcoded `bg-[#0b1320]`. Replace with token-driven styles.

- Container: `WorkspaceSurface` + `overflow: hidden`.
- Header: `bg: var(--vz-canvas-graphite-up)`, eyebrow type style.
- Row hover: `bg: rgba(110,189,255,0.04)` + cursor-pointer if row click is wired.
- Selected row: 3px inset cerulean shaft on the left edge.
- Empty state lives inside a `<TR><TD colSpan="…">` — keep, but center the message and add a subtle illustration or icon (Lucide `MonitorOff`, `MapPinOff`).

### 6.5 Charts (Patterns)

- Library stays as the existing internal one.
- Series: cerulean `--vz-lens-cerulean` for primary; for multi-series, alternate cerulean → aqua `--vz-lens-aqua` → violet `--vz-lens-violet` → muted `#8ea8cf`. Avoid hue-spam (no random rainbow).
- Selected bucket: 100%-height vertical shaft in `--vz-lens-cerulean` at 18% opacity + 1px center line at 70%.
- Hover: tooltip uses `elev-3`, body font, tabular nums.
- Speed overlay: dashed `--vz-lens-violet`. Confidence band uses 12% alpha.
- Reference line for "now": 1px solid `--vz-state-info`, label "now" in caption type.

### 6.6 Live scene tile (`scene-portal`)

This is the most important card in the product. Spec:

```
+----------------------------------------------------+
|  [eyebrow] SCENE NAME       [live badge] [tracker] |
|  description (mode • profile)                      |
+====================================================+
|  ◰ video plate (MediaSurface)                       |
|     • corner brackets cerulean 60%                  |
|     • TelemetryCanvas overlay                       |
|     • bottom info gradient                          |
|     • bottom-left: heartbeat + visible-now          |
|     • bottom-right: stream mode pip                 |
+====================================================+
|  sparkline strip                                    |
+----------------------------------------------------+
```

- Tile root: `elev-1` at rest → `elev-glow-cerulean` on hover/focus. `translateZ(--vz-pop-z)` on hover.
- 4-corner brackets are `::before/::after` pseudo elements — pure CSS, no SVG dependency:
  ```css
  .scene-portal-media::before,
  .scene-portal-media::after {
    content: ""; position: absolute; width: 18px; height: 18px;
    border: 1px solid rgba(110,189,255,0.6);
  }
  /* place top-left, top-right, bottom-left, bottom-right with corner combos */
  ```
- Latency pip (top-right of media): 6px dot, color = healthy/attention/danger from `tone-by-heartbeat`. Pulse loop limited to **3 cycles** then stops; restarts on heartbeat change.
- Sparkline always anchors to **same Y baseline** across tiles — visual consistency over per-tile auto-scale.
- "Direct stream unavailable" note: move to the bottom-info bar, behind a `StatusToneBadge` instead of a free-floating warning paragraph.

### 6.7 Evidence card (queue row)

- 64px row height, vertical padding 12px.
- Left edge: 4px tall scene-color stripe (deterministic by camera id hash → 6 brand-aligned hues).
- Selected state: gradient already used in code — keep, but raise to `elev-2`.
- Selected indicator should be `aria-current="true"` not `aria-pressed`.

### 6.8 Sign-in lens stage (`OmniSightLens` upgrade)

Replace the current MP4 hero with a CSS-only lens stage. Asset use:
- `2d_logo_no_ring.png` is **not** used on sign-in.
- `3d_logo_no_bg.png` is the **only** image asset, used as a poster fallback and for `prefers-reduced-motion`.
- `logo-no-bg.mp4` (20 MB) is **deprecated** as the primary hero — keep cached for users who explicitly opt in to "high motion." Actually consider serving it from a CDN, in WEBM (~3 MB) and HEVC, only for users with `prefers-reduced-motion: no-preference` and `prefers-reduced-data: no-preference`.

Composition (12-col grid, desktop):

```
col 1-5  : headline + body + 3 proof signals
col 7-12 : lens stage (perspective: 1400px)
              - background: 2 orbital rings (CSS-only) on Y-tilted plane
              - mid:        conic radar mask
              - foreground: 3D logo (PNG) on transform-style: preserve-3d
                             → translateZ(40px) at rest
                             → drift Y/Z over 14s (already coded as `omnisight-mark-drift`)
                             → on pointer move, rotateX(-mouseY * 6deg) rotateY(mouseX * 6deg)
              - halo:       elev-glow-violet
sign-in panel : col 7-10, vertically centered, elev-glow-violet
```

Pointer-driven rotation is the most distinctive feature. Implement with `requestAnimationFrame` throttled to 60fps, no library required.

```ts
function useLensTilt(ref: RefObject<HTMLElement>) {
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width  - 0.5;  // -0.5..0.5
      const y = (e.clientY - r.top)  / r.height - 0.5;
      el.style.setProperty("--lens-rx", `${ -y * 8 }deg`);
      el.style.setProperty("--lens-ry", `${  x * 8 }deg`);
    };
    el.addEventListener("pointermove", onMove);
    return () => el.removeEventListener("pointermove", onMove);
  }, [ref]);
}
```

CSS:
```css
.lens-stage { perspective: var(--vz-perspective); }
.lens-mark  { transform-style: preserve-3d;
              transform: rotateX(var(--lens-rx, 0)) rotateY(var(--lens-ry, 0))
                         translate3d(0,0,40px); }
```

Disable in `prefers-reduced-motion`.

### 6.9 Nav rail (icon + context)

Today: two distinct rails. Keep that. Recommendations:

- **Icon rail** width: 60px. Active item gets a left-edge 2px cerulean shaft + 6px diameter dot at vertical center. Hover: subtle backdrop-filter blur + 1.04 scale on the icon (transform-only; layout doesn't shift).
- **Context rail** width: 264px / 280px (xl). Today's `[16.5rem_17.5rem]` is fine; rename to tokens.
- Active context-rail item: replace the existing `bg: rgba(30,46,71,0.56)` with `linear-gradient(90deg, rgba(110,189,255,0.16), transparent 80%)` + 2px cerulean rim on the left.
- Add a "lens focus" animated dot that slides between active items on route change (Framer Motion `layoutId="nav-focus"`). This is the single best motion upgrade for product feel and costs ≤30 lines.

### 6.10 Workspace transition

Keep the existing `WorkspaceTransition` component. Tighten the keyframe:

```css
@keyframes workspace-enter {
  from { opacity: 0; transform: translate3d(0, 6px, 0); }
  to   { opacity: 1; transform: translate3d(0, 0,    0); }
}
.workspace-enter { animation: workspace-enter var(--vz-dur-base) var(--vz-ease-product) both; }
```

No scale change. No filter blur. Smaller Y delta.

### 6.11 Toast / Notification (new spec)

The product currently lacks a toast surface. Design:
- Position: bottom-right, 24px gutter.
- Width: 360px max.
- `elev-3`. 12px radius. Left-edge 4px tone shaft (healthy/attention/danger/accent).
- Auto-dismiss: 5s default, pause on hover. Pre-dismiss progress shaft animates `width: 100% → 0` (only motion in the toast).
- Stack: max 3 visible, FIFO, with stagger 60ms enter.

### 6.12 Command palette (new, optional Phase 2)

Operators in a cockpit deserve a `⌘K` jump bar. Shortlist:
- Search scenes, sites, evidence, ops commands.
- Recently visited routes.
- "Ask Vezor" inline as a fallback when no command matches.
- Surface = `elev-3` floating panel with backdrop dim 60%.

---

## 7. Page-level recommendations

### 7.1 Sign-in (`/signin`)

Issues today:
1. The `<video>` autoplays and is the same z-layer as the H1 — at 1280px viewport the 3D logo overlaps the headline.
2. `elev-glow-violet` is approximated as a single shadow on the auth panel; the lens has no glow ring of its own.
3. No proof signals beyond three ALL-CAPS labels.

Required changes:
- Adopt `WorkspaceHero` with the `OmniSightLens` (§6.8). Drop the MP4 from the default render.
- Two-column grid breakpoint `lg:grid-cols-[7fr_5fr]`. Lens lives in the right column from 1024px+. Below 1024px, lens stacks above headline at 240px tall.
- Top-left lockup: 32px tall. Subdescriptor "Spatial intelligence layer" as an `eyebrow` in `--vz-text-muted`.
- Headline: "OmniSight for every live environment." Rendered in display-xl, max-width 18ch.
- Body: 56ch max.
- Proof signals: 3 chips with Lucide icons (`Camera`, `ScanEye`, `Cpu`) + 11px eyebrow + 13px caption. Outline style, not solid.
- Auth panel: 360px wide, `elev-glow-violet`. SSO button is `primary`. Add a "secured by SSO" footer line referencing the IdP.
- Remove the right-side glint.
- Footer: single line, justified, 12px caption type.

### 7.2 Dashboard (`/dashboard`)

Today: 3-tile metric strip + 6 link cards. Functional but not a cockpit.

Required changes:
- Replace top section with a `WorkspaceHero` carrying:
  - Left: live "intelligence summary" (3 KPI tiles using `KpiTile`: Live scenes, Pending evidence, Edge workers running).
  - Right: live preview tile cycling through up to 4 scene thumbnails (cross-dissolve, 6s interval, paused on hover/focus). Click → `/live#camera-id`.
- Add a `Patterns trend` row beneath the hero — 7-day occupancy line chart (single series), 96px tall, full width. This is the dashboard's *intelligence* moment.
- Replace the 6 `OverviewLink` cards with 3 large action surfaces ("Watch", "Investigate", "Operate") + secondary text links. Reduce decision count by half.
- Right rail: `InstrumentRail` with: site count, fleet status, "what changed in the last 24h" feed (3 entries max).

### 7.3 Live (`/live`)

Today: filter-less 2-column scene grid + spatial instrument rail.

Required changes:
- Promote `AgentInput` to a sticky command strip at the top of the workspace, full width, with `placeholder="Ask Vezor — e.g. 'show forklifts on aisle 2'"`. Sticky offset = `WorkspaceBand` height.
- Scene tiles upgraded per §6.6 (corner brackets, latency pip, hover Z-pop, telemetry sparkline anchored).
- Add a "wall mode" toggle (top-right of `WorkspaceBand`) that hides the rail and renders a 3- or 4-column tile wall. Useful for control-room demos.
- Move "diagnostics" (e.g. native unavailable) into a tile foot strip behind a single `StatusToneBadge`.
- Empty state shows a 256px illustration of the Vezor mark inside an empty radar ring with copy "No connected scenes yet — add your first scene in Setup."

### 7.4 Patterns (`/history`)

Today: filter rail competes with the chart for attention; export panel is featured at the top.

Required changes:
- Reduce export to a small icon-only `Download` button group in the toolbar (top-right). It is a utility.
- Filter rail moves to a 56px-tall toolbar above the chart, *not* a side panel. Side rail becomes "Bucket detail" only.
- Chart: full-bleed (no inner padding around the canvas). Reference lines: now (info), threshold (attention), zero (hairline).
- Bucket selection scrolls the rail to the bucket detail with a 240ms ease-product slide-from-right.
- Granularity bumped / speed capped messages: combine into a single "advisory bar" component above the chart, not stacked toasts.

### 7.5 Evidence (`/incidents`)

Today: 3-column queue / media / facts. Already strong. Refinements:

- Make the media plane true black (`--vz-media-black`) and stretch edge-to-edge inside its panel.
- Selected queue row keeps the gradient highlight, but the right-edge stripe should be cerulean, not the existing inset shadow.
- Add a "review" command bar overlay on the media: `Reviewed`, `Reopen`, `Open clip`, `Copy link`. Fades in on focus/hover. (Replaces the bottom utility row.)
- Facts rail (`InstrumentRail`) gets a top-of-rail mini-map: scene location dot (later phase, when we have site coordinates).

### 7.6 Scenes (`/cameras`)

Today: dense 5-step strip + table.

Required changes:
- Convert the 5-step strip into a horizontal *progress* artifact: each step is a card with a 1px hairline; the active step earns a cerulean rim.
- Table stays. Replace the per-row `Edit` / `Delete` buttons with a single overflow menu (Lucide `MoreVertical`) — reduces row noise and matches operator expectations.
- Wizard launch button moves into the toolbar pattern.

### 7.7 Sites (`/sites`)

Today: card grid + duplicate table. Both shipped in the current UI; one of them has to lose.

Required changes:
- **Drop the table entirely** when there are ≥ 1 site cards. Cards are richer (scene count, time zone, description) and the table adds no information density.
- Empty state replaces both: a 240px hero placeholder + `Add site` primary CTA + 3 inline tips ("Scenes connect to a Site for time zone and fleet").
- Card hover: `elev-2` + 1px cerulean rim. Click → `/sites/:id` (route to design later).
- Each card shows: site name, time zone (caption + `world clock` icon), scene count, edge status pip (when available), description.

### 7.8 Operations / Settings (`/settings`)

Today: dense single page.

Required changes:
- Top-level tabs (`Fleet`, `Workers`, `Bootstrap`, `Streams`, `Diagnostics`) using shadcn-style segmented control sized to 36px. Each tab routes to a sub-anchor.
- Distinguish "command blocks" from "config panels":
  - Command (read-only mono): `--vz-canvas-void` plate, mono font, copy-to-clipboard button.
  - Config (editable): `WorkspaceSurface`.
- Status colors are *only* used in this page where they map to fleet state — currently fine.

### 7.9 App shell

- The shell `OmniSightField` ambient field stays, but at `opacity: 0.06` (currently 0.85 with class default `0.08` for shell). Even at 8% it is heavy on Intel macOS — confirm with a quick FPS check.
- Shell background: trade the multi-radial gradient for a single linear `#03050a → #07090f` plus a single `radial-gradient(60% 60% at 70% 0%, rgba(110,189,255,0.10), transparent 60%)`. Less expensive to repaint.
- Add a 1px hairline below the icon-rail / context-rail transition for a sharper "frame vs. content" hierarchy.

---

## 8. Iconography & Imagery

### 8.1 Icons
- Lucide React (already imported). Forbid emoji, forbid Heroicons mixing.
- Default size: 16 (controls), 18 (nav), 24 (heroes). Stroke 1.5px on dark.
- Color: `currentColor`. Active states swap text color, not icon.

### 8.2 Brand mark usage in product
- `2d_logo_no_ring.png` → product lockup top-left of icon rail and sign-in.
- `3d_logo_no_bg.png` → lens-stage hero (sign-in, dashboard hero).
- Never use the 3D logo decoratively in workflow pages. It is a brand object, not wallpaper. The `OmniSightField` ambient field is fine because it is heavily faded (≤ 8% opacity).

### 8.3 Empty-state illustrations
- One illustration system: a 256px wide, 1px-line drawing that uses cerulean + violet hairlines on a transparent background. Topics: "no scenes," "no sites," "no evidence." Can be authored as inline SVG in `frontend/src/components/empty/` to keep them token-driven.

---

## 9. Accessibility & Responsive

### 9.1 Hard requirements (keep / verify)
- Color contrast 4.5:1 for body text and 3:1 for large display text. Sample the worst offenders: `#8ea8cf` on `var(--vz-canvas-graphite)` is **3.6:1** — fine for caption, **not** for body. Promote body to `--vz-text-secondary` (`#b8c6dc` → 5.6:1).
- Visible focus on every interactive element: 2px outline `var(--vz-hair-focus)` + 2px offset.
- `prefers-reduced-motion`: turn off ambient + cap durations to ≤ 180ms with opacity-only changes. (Already in CSS — extend to the new motion presets.)
- All tile / queue rows are `<button type="button">` with `aria-current` for selection — current code uses `aria-pressed` on a non-toggle, change to `aria-current="true"`.
- Live regions: the connection state pill should be inside `aria-live="polite"`.

### 9.2 Breakpoints

| Token   | px        | Behavior                                                  |
|---------|-----------|-----------------------------------------------------------|
| `xs`    | 375       | Mobile minimum. No horizontal scroll. Ambient field hidden.|
| `sm`    | 640       | One-column. Lens stacks above headline on sign-in.        |
| `md`    | 768       | Two-column on sign-in. Tile grid 1-up.                    |
| `lg`    | 1024      | Three-column on Evidence. Tile grid 2-up.                 |
| `xl`    | 1280      | Hero grids open up. Sign-in 7/5 split.                    |
| `2xl`   | 1536      | Live "wall mode" 4-up. Dashboard 3-up KPIs.               |

### 9.3 Reduced data
- `prefers-reduced-data: reduce` (where supported): swap the lens video for the static PNG, drop the dashboard scene cycle, throttle telemetry updates to 1 Hz.

---

## 10. Performance budgets

| Page         | First paint | TTI    | Hero animation FPS | Notes                                       |
|--------------|-------------|--------|--------------------|---------------------------------------------|
| Sign-in      | < 1.0s      | < 1.6s | ≥ 50 FPS           | drop the 20 MB MP4 from default render      |
| Dashboard    | < 1.2s      | < 2.2s | ≥ 50 FPS hero      | scene preview lazy-loaded behind IO         |
| Live         | < 1.4s      | < 2.6s | ≥ 24 FPS per tile  | telemetry canvas throttled to RAF           |
| Patterns     | < 1.4s      | < 2.4s | n/a                | chart canvas memoized                       |
| Evidence     | < 1.2s      | < 2.0s | n/a                | snapshot images use `loading="lazy"`        |

Operational: keep total CSS animation count per route ≤ 4. Use `will-change: transform, opacity` only on animated elements that are visible.

---

## 11. Implementation Roadmap

Phased to land discrete value without long-running branches.

### Phase 1 — Foundations (1-2 days)
1. Add new `--vz-*` palette and elevation tokens to `frontend/src/index.css`. Keep old `--argus-*` aliases.
2. Add Space Grotesk + Inter via `@import url(...)` and update `body`/`h1` font-family.
3. Refactor `Button`, `WorkspaceBand`, `WorkspaceSurface`, `MediaSurface`, `InstrumentRail` to consume the new tokens.
4. Replace shell ambient gradient with the lighter version.

**Deliverable:** every existing page renders without visual regression beyond the typography swap. Tests should pass after `pnpm vitest run` snapshot updates.

### Phase 2 — Spatial cockpit (2-3 days)
5. Build `OmniSightLens` (CSS-perspective, pointer-tilt). Replace MP4 hero on `SignInPage`.
6. Add `WorkspaceHero` and ship the upgraded Dashboard.
7. Apply scene-portal upgrades on `LivePage` (corner brackets, latency pip, Z-pop hover, sticky `AgentInput`).
8. Apply Sites upgrade (drop dup table, polish empty state).

**Deliverable:** sign-in and dashboard feel like Vezor; Live tile feels like a portal.

### Phase 3 — Motion choreography (1-2 days)
9. Add Framer Motion. Implement nav active-dot (`layoutId="nav-focus"`).
10. Evidence selection cross-fade.
11. Patterns bucket selection slide.
12. Toast component + first uses (review-success, export-failed).

**Deliverable:** routes feel connected; state changes are confirmed visually.

### Phase 4 — (optional, gated) WebGL upgrade
13. Add `@react-three/fiber` + the existing 3D mark as a GLB on sign-in + dashboard hero. Falls back to Phase-2 CSS lens. Behind a feature flag (`VITE_FEATURE_WEBGL_LENS`) so we can A/B.

---

## 12. Pre-delivery checklist

Apply to every PR that touches UI:

- [ ] No emoji as icon
- [ ] No arbitrary hex outside the `--vz-*` token set
- [ ] No raw `radius: 0.85rem`-style values — use `--vz-r-*`
- [ ] Buttons / cards / tile-rows have `cursor-pointer` if clickable
- [ ] Hover states do not shift layout (no width/height transitions; transform/opacity only)
- [ ] Focus visible on all interactive elements (2px ring, 2px offset)
- [ ] `prefers-reduced-motion` disables every new animation
- [ ] All ambient animations cap at `--vz-dur-soft` (320ms) for product UI, `--vz-dur-ambient` (14s) for sign-in/dashboard
- [ ] Tabular numerics on every metric (font-feature-settings)
- [ ] Verified at 375 / 768 / 1024 / 1440
- [ ] Light-on-dark contrast ≥ 4.5:1 for body, ≥ 3:1 for display
- [ ] No `bg-white/10` borders on light surfaces (we are dark-only, but principle still applies — borders must be visible)
- [ ] No new heavy assets > 1 MB without CDN + format negotiation (WebP/HEVC/WebM)
- [ ] React rules: `aria-current` for nav/queue selection, not `aria-pressed`

---

## 13. Open questions for product

1. Is a WebGL dependency acceptable in Phase 4? If not, the CSS-perspective lens is the final form.
2. Do we want Vezor-themed empty-state illustrations as inline SVG (free, owned) or commission a small set?
3. Should the `wall mode` on Live be a per-user preference (persisted) or just session-scoped?
4. Command palette (⌘K) — do we ship in this design pass or split it out as a follow-up?
5. The 3D logo PNG is rendered at 19vw (≈ 380px on a 2K display). At that size, the existing PNG starts to soft-pixelate. Do we upgrade to an SVG (per `docs/brand/logo-brand-spec.md` deliverable list) or accept a higher-res PNG?
