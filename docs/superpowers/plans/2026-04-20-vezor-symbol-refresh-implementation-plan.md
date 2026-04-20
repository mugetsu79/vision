# Vezor Symbol Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current in-product `Vezor` symbol with an SVG rebuild of the approved attached eye-and-radar mark, and propagate that rebuilt symbol through the product lockup and compatibility brand assets without changing asset wiring.

**Architecture:** Keep the existing frontend brand metadata and `ProductLockup` component untouched. Introduce canonical SVG source files under `docs/brand/assets/source/`, then copy those approved source assets into the runtime `frontend/public/brand/` files so the app keeps the same asset paths while the artwork changes underneath. Guard the change with an asset-structure regression test plus the existing lockup/component verification.

**Tech Stack:** SVG, React, Vite, Vitest, Testing Library, Playwright, Git

---

## File Structure Map

### New Files

- Create: `docs/brand/assets/source/vezor-symbol-product-ui.svg`
  - Canonical SVG source for the approved attached symbol rebuild.
- Create: `docs/brand/assets/source/vezor-lockup-product-ui.svg`
  - Canonical SVG source for the full in-product lockup that combines the rebuilt symbol with the existing `Vezor` wordmark and descriptor treatment.
- Create: `frontend/src/brand/product-assets.test.ts`
  - Regression test that reads the runtime SVG assets and asserts they contain the approved `Vezor` metadata and the new symbol structure identifiers.

### Existing Files To Modify

- Modify: `frontend/public/brand/product-symbol-ui.svg`
  - Runtime symbol asset used by the app in symbol-only placements.
- Modify: `frontend/public/brand/product-lockup-ui.svg`
  - Runtime full lockup asset used by the app in full lockup placements.
- Modify: `frontend/public/brand/argus-symbol-ui.svg`
  - Compatibility symbol asset that should stay visually aligned even though the filename remains legacy.
- Modify: `frontend/public/brand/argus-lockup-ui.svg`
  - Compatibility lockup asset that should stay visually aligned even though the filename remains legacy.

### Existing Files To Reuse Without Changes

- Reuse: `frontend/src/brand/product.ts`
  - Keeps the existing `Vezor` metadata and runtime asset paths unchanged.
- Reuse: `frontend/src/components/layout/ProductLockup.tsx`
  - Keeps the current lockup rendering logic unchanged.
- Reuse: `frontend/src/components/layout/ProductLockup.test.tsx`
  - Continues proving that the UI still points at the same runtime asset paths.

## Task 1: Add An SVG Asset Regression Test

**Files:**
- Create: `frontend/src/brand/product-assets.test.ts`
- Test: `frontend/src/brand/product-assets.test.ts`

- [ ] **Step 1: Write the failing asset regression test**

Create `frontend/src/brand/product-assets.test.ts` with:

```ts
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

function readBrandAsset(name: string): string {
  return readFileSync(resolve(process.cwd(), "frontend/public/brand", name), "utf8");
}

describe("product brand SVG assets", () => {
  test("product and compatibility symbol assets expose the rebuilt Vezor symbol structure", () => {
    const productSymbol = readBrandAsset("product-symbol-ui.svg");
    const compatibilitySymbol = readBrandAsset("argus-symbol-ui.svg");

    for (const svg of [productSymbol, compatibilitySymbol]) {
      expect(svg).toContain('aria-label="Vezor symbol"');
      expect(svg).toContain("<title>Vezor symbol</title>");
      expect(svg).toContain('id="vezor-symbol-mark"');
      expect(svg).toContain('id="symbol-ring"');
      expect(svg).toContain('id="symbol-eye"');
      expect(svg).toContain('id="symbol-core"');
      expect(svg).not.toContain(">Argus<");
    }
  });

  test("product and compatibility lockup assets embed the rebuilt symbol and Vezor lockup metadata", () => {
    const productLockup = readBrandAsset("product-lockup-ui.svg");
    const compatibilityLockup = readBrandAsset("argus-lockup-ui.svg");

    for (const svg of [productLockup, compatibilityLockup]) {
      expect(svg).toContain('aria-label="Vezor product lockup"');
      expect(svg).toContain("<title>Vezor product lockup</title>");
      expect(svg).toContain('id="vezor-symbol-mark"');
      expect(svg).toContain('id="symbol-ring"');
      expect(svg).toContain('id="symbol-eye"');
      expect(svg).toContain('id="symbol-core"');
      expect(svg).toContain(">Vezor<");
      expect(svg).toContain(">THE OMNISIGHT<");
      expect(svg).toContain(">PLATFORM<");
      expect(svg).not.toContain(">Argus<");
    }
  });
});
```

- [ ] **Step 2: Run the new regression test and verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts
```

Expected:

- FAIL because the current SVG files do not yet include the new `id="vezor-symbol-mark"`, `id="symbol-ring"`, `id="symbol-eye"`, and `id="symbol-core"` structure markers.

- [ ] **Step 3: Commit the failing-test checkpoint**

```bash
git add frontend/src/brand/product-assets.test.ts
git commit -m "test: add Vezor brand asset regression coverage"
```

## Task 2: Rebuild The Approved Symbol As The Canonical SVG Source

**Files:**
- Create: `docs/brand/assets/source/vezor-symbol-product-ui.svg`
- Modify: `frontend/public/brand/product-symbol-ui.svg`
- Modify: `frontend/public/brand/argus-symbol-ui.svg`
- Test: `frontend/src/brand/product-assets.test.ts`

- [ ] **Step 1: Create the canonical source SVG for the approved symbol**

Create `docs/brand/assets/source/vezor-symbol-product-ui.svg` with:

```svg
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Vezor symbol">
  <title>Vezor symbol</title>
  <desc>Approved eye-and-radar symbol for the Vezor platform, rebuilt as a crisp product SVG.</desc>
  <defs>
    <linearGradient id="ringGradient" x1="14%" y1="10%" x2="86%" y2="88%">
      <stop offset="0%" stop-color="#54d7ff"/>
      <stop offset="52%" stop-color="#5fb6ff"/>
      <stop offset="100%" stop-color="#a584ff"/>
    </linearGradient>
    <radialGradient id="coreGradient" cx="50%" cy="46%" r="56%">
      <stop offset="0%" stop-color="#baf1ff"/>
      <stop offset="38%" stop-color="#56d0ff"/>
      <stop offset="74%" stop-color="#3298ff"/>
      <stop offset="100%" stop-color="#8d72ff"/>
    </radialGradient>
    <filter id="symbolGlow" x="-24%" y="-24%" width="148%" height="148%">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feColorMatrix
        in="blur"
        type="matrix"
        values="1 0 0 0 0
                0 1 0 0 0
                0 0 1 0 0
                0 0 0 0.14 0"
      />
    </filter>
  </defs>

  <g id="vezor-symbol-mark" transform="translate(256 256)">
    <g id="symbol-ring" filter="url(#symbolGlow)">
      <circle
        cx="0"
        cy="0"
        r="162"
        fill="none"
        stroke="url(#ringGradient)"
        stroke-width="16"
        stroke-linecap="round"
        stroke-dasharray="94 24 58 24 94 24 58 24 94 24 58 24 94 24 58 24"
        opacity="0.86"
      />
    </g>

    <g id="symbol-eye">
      <path
        d="M-146 0c34-54 92-90 146-90s112 36 146 90c-34 54-92 90-146 90S-112 54-146 0Z"
        fill="none"
        stroke="url(#ringGradient)"
        stroke-width="16"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </g>

    <g id="symbol-blades" fill="url(#ringGradient)">
      <path d="M-32-210h22L1-116l-26 324h-22l15-324Z" opacity="0.98" />
      <path d="M146-132 164-114 46 10l-116 108-18-18L28-24 146-132Z" opacity="0.94" />
      <path d="M-166-118l18-18 118 112 116 124-18 18L-50 10-166-118Z" opacity="0.88" />
      <path d="M12-10c44 6 84 36 104 82l-28 11C72 47 42 25 7 21L12-10Z" opacity="0.9" />
    </g>

    <g id="symbol-core">
      <circle cx="18" cy="6" r="72" fill="url(#coreGradient)" />
      <circle cx="18" cy="6" r="33" fill="#0a111a" />
      <circle cx="2" cy="-14" r="11" fill="#effbff" opacity="0.9" />
    </g>
  </g>
</svg>
```

- [ ] **Step 2: Copy the canonical source SVG into the runtime symbol assets**

Run:

```bash
cp docs/brand/assets/source/vezor-symbol-product-ui.svg frontend/public/brand/product-symbol-ui.svg
cp docs/brand/assets/source/vezor-symbol-product-ui.svg frontend/public/brand/argus-symbol-ui.svg
```

- [ ] **Step 3: Run only the symbol-focused regression test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts -t "product and compatibility symbol assets expose the rebuilt Vezor symbol structure"
```

Expected:

- PASS for the symbol asset test.
- The lockup asset test may still fail because the lockup files have not been rebuilt yet.

- [ ] **Step 4: Commit the symbol rebuild checkpoint**

```bash
git add docs/brand/assets/source/vezor-symbol-product-ui.svg frontend/public/brand/product-symbol-ui.svg frontend/public/brand/argus-symbol-ui.svg
git commit -m "feat: rebuild the Vezor product symbol"
```

## Task 3: Rebuild The Product Lockup Around The Approved Symbol

**Files:**
- Create: `docs/brand/assets/source/vezor-lockup-product-ui.svg`
- Modify: `frontend/public/brand/product-lockup-ui.svg`
- Modify: `frontend/public/brand/argus-lockup-ui.svg`
- Test: `frontend/src/brand/product-assets.test.ts`
- Test: `frontend/src/components/layout/ProductLockup.test.tsx`

- [ ] **Step 1: Create the canonical source SVG for the full Vezor lockup**

Create `docs/brand/assets/source/vezor-lockup-product-ui.svg` with:

```svg
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" role="img" aria-label="Vezor product lockup">
  <title>Vezor product lockup</title>
  <desc>Approved Vezor product lockup that pairs the rebuilt eye-and-radar symbol with the existing wordmark and descriptor.</desc>
  <defs>
    <style>
      .word { font-family: "Avenir Next", "Inter", "Segoe UI", sans-serif; font-weight: 800; letter-spacing: -0.035em; }
      .tag { font-family: "Avenir Next", "Inter", "Segoe UI", sans-serif; font-weight: 500; letter-spacing: 0.18em; }
    </style>
    <linearGradient id="ringGradient" x1="14%" y1="10%" x2="86%" y2="88%">
      <stop offset="0%" stop-color="#54d7ff"/>
      <stop offset="52%" stop-color="#5fb6ff"/>
      <stop offset="100%" stop-color="#a584ff"/>
    </linearGradient>
    <linearGradient id="wordGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#fdfefe"/>
      <stop offset="100%" stop-color="#dbe3ef"/>
    </linearGradient>
    <linearGradient id="taglineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#94a3bb"/>
      <stop offset="100%" stop-color="#c2cddd"/>
    </linearGradient>
    <radialGradient id="coreGradient" cx="50%" cy="46%" r="56%">
      <stop offset="0%" stop-color="#baf1ff"/>
      <stop offset="38%" stop-color="#56d0ff"/>
      <stop offset="74%" stop-color="#3298ff"/>
      <stop offset="100%" stop-color="#8d72ff"/>
    </radialGradient>
    <filter id="symbolGlow" x="-24%" y="-24%" width="148%" height="148%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feColorMatrix
        in="blur"
        type="matrix"
        values="1 0 0 0 0
                0 1 0 0 0
                0 0 1 0 0
                0 0 0 0.12 0"
      />
    </filter>
  </defs>

  <g id="vezor-symbol-mark" transform="translate(180 180) scale(0.7)">
    <g id="symbol-ring" filter="url(#symbolGlow)">
      <circle
        cx="0"
        cy="0"
        r="162"
        fill="none"
        stroke="url(#ringGradient)"
        stroke-width="16"
        stroke-linecap="round"
        stroke-dasharray="94 24 58 24 94 24 58 24 94 24 58 24 94 24 58 24"
        opacity="0.86"
      />
    </g>

    <g id="symbol-eye">
      <path
        d="M-146 0c34-54 92-90 146-90s112 36 146 90c-34 54-92 90-146 90S-112 54-146 0Z"
        fill="none"
        stroke="url(#ringGradient)"
        stroke-width="16"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </g>

    <g id="symbol-blades" fill="url(#ringGradient)">
      <path d="M-32-210h22L1-116l-26 324h-22l15-324Z" opacity="0.98" />
      <path d="M146-132 164-114 46 10l-116 108-18-18L28-24 146-132Z" opacity="0.94" />
      <path d="M-166-118l18-18 118 112 116 124-18 18L-50 10-166-118Z" opacity="0.88" />
      <path d="M12-10c44 6 84 36 104 82l-28 11C72 47 42 25 7 21L12-10Z" opacity="0.9" />
    </g>

    <g id="symbol-core">
      <circle cx="18" cy="6" r="72" fill="url(#coreGradient)" />
      <circle cx="18" cy="6" r="33" fill="#0a111a" />
      <circle cx="2" cy="-14" r="11" fill="#effbff" opacity="0.9" />
    </g>
  </g>

  <g transform="translate(348 0)">
    <text x="0" y="193" class="word" font-size="126" fill="url(#wordGradient)">Vezor</text>
    <text x="350" y="195" class="tag" font-size="26" fill="#7e8ba2">|</text>
    <text x="392" y="168" class="tag" font-size="22" fill="url(#taglineGradient)">THE OMNISIGHT</text>
    <text x="392" y="208" class="tag" font-size="22" fill="url(#taglineGradient)">PLATFORM</text>
  </g>
</svg>
```

- [ ] **Step 2: Copy the canonical lockup SVG into the runtime lockup assets**

Run:

```bash
cp docs/brand/assets/source/vezor-lockup-product-ui.svg frontend/public/brand/product-lockup-ui.svg
cp docs/brand/assets/source/vezor-lockup-product-ui.svg frontend/public/brand/argus-lockup-ui.svg
```

- [ ] **Step 3: Run the full SVG regression test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts
```

Expected:

- PASS with `2 passed`.

- [ ] **Step 4: Run the existing lockup component test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/ProductLockup.test.tsx
```

Expected:

- PASS with `2 passed`.

- [ ] **Step 5: Commit the lockup rebuild checkpoint**

```bash
git add docs/brand/assets/source/vezor-lockup-product-ui.svg frontend/public/brand/product-lockup-ui.svg frontend/public/brand/argus-lockup-ui.svg frontend/src/brand/product-assets.test.ts
git commit -m "feat: apply the approved Vezor product lockup"
```

## Task 4: Run Final Frontend Verification And Commit

**Files:**
- Verify: `frontend/public/brand/product-symbol-ui.svg`
- Verify: `frontend/public/brand/product-lockup-ui.svg`
- Verify: `frontend/public/brand/argus-symbol-ui.svg`
- Verify: `frontend/public/brand/argus-lockup-ui.svg`
- Verify: `frontend/src/brand/product-assets.test.ts`
- Verify: `frontend/src/components/layout/ProductLockup.test.tsx`

- [ ] **Step 1: Run the targeted frontend brand checks together**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts src/components/layout/ProductLockup.test.tsx
```

Expected:

- PASS with `4 passed`.

- [ ] **Step 2: Run the frontend production build**

Run:

```bash
corepack pnpm --dir frontend build
```

Expected:

- PASS with `✓ built in ...`

- [ ] **Step 3: Run the existing prompt-8 end-to-end smoke test**

Run:

```bash
corepack pnpm --dir frontend exec playwright test e2e/prompt8-live-dashboard.spec.ts
```

Expected:

- PASS with `1 passed`

- [ ] **Step 4: Run the final diff hygiene check**

Run:

```bash
git diff --check
```

Expected:

- no output

- [ ] **Step 5: Commit the final verification checkpoint**

```bash
git add docs/brand/assets/source/vezor-symbol-product-ui.svg docs/brand/assets/source/vezor-lockup-product-ui.svg frontend/public/brand/product-symbol-ui.svg frontend/public/brand/product-lockup-ui.svg frontend/public/brand/argus-symbol-ui.svg frontend/public/brand/argus-lockup-ui.svg frontend/src/brand/product-assets.test.ts
git commit -m "feat: refresh the Vezor product logo assets"
```

## Self-Review

### Spec Coverage

- Rebuild attached symbol as SVG: covered in Task 2.
- Use rebuilt symbol in both symbol-only and full lockup assets: covered in Tasks 2 and 3.
- Keep `Vezor` wordmark and descriptor unchanged: covered in Task 3.
- Keep compatibility assets aligned: covered in Tasks 2 and 3.
- Preserve current asset wiring and `ProductLockup` behavior: covered by Tasks 1, 3, and 4 without modifying routing code.

### Placeholder Scan

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Every code-changing step includes concrete file paths, concrete code, and exact commands.

### Type And Interface Consistency

- Asset tests assert the same identifiers used in the planned SVGs:
  - `vezor-symbol-mark`
  - `symbol-ring`
  - `symbol-eye`
  - `symbol-core`
- Runtime asset paths remain:
  - `/brand/product-symbol-ui.svg`
  - `/brand/product-lockup-ui.svg`
