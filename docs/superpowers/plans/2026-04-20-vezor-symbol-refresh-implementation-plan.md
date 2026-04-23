# Vezor Symbol Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the shipped Vezor symbol artwork with a refined SVG rebuild that stays close to the uploaded base symbol, using the existing v2 source assets as the implementation anchor, while keeping the current runtime asset paths and `Vezor` branding unchanged.

**Architecture:** Leave the React component and brand-path wiring alone. Update the product-specific source SVGs and the four runtime brand files together, using `docs/brand/assets/source/vezor-icon-v2.svg` and `docs/brand/assets/source/vezor-omnisight-logo-v2.svg` as the closest repo-owned anchors and `argus-icon-from-upload.svg` as the geometry reference. Drive the work with an asset regression test that fails on the old simplified symbol, then verify the unchanged `ProductLockup` component still resolves the same runtime paths.

**Tech Stack:** SVG, Vitest, React, Vite, Bash, Git

---

## File Structure Map

### Reference Anchors

- Read: `argus-icon-from-upload.svg`
- Read: `docs/brand/assets/source/vezor-icon-v2.svg`
- Read: `docs/brand/assets/source/vezor-omnisight-logo-v2.svg`

### Existing Files To Modify

- Modify: `frontend/src/brand/product-assets.test.ts`
- Modify: `docs/brand/assets/source/vezor-symbol-product-ui.svg`
- Modify: `docs/brand/assets/source/vezor-lockup-product-ui.svg`
- Modify: `frontend/public/brand/product-symbol-ui.svg`
- Modify: `frontend/public/brand/argus-symbol-ui.svg`
- Modify: `frontend/public/brand/product-lockup-ui.svg`
- Modify: `frontend/public/brand/argus-lockup-ui.svg`

### Existing Files To Reuse Without Changes

- Reuse: `frontend/src/brand/product.ts`
- Reuse: `frontend/src/components/layout/ProductLockup.tsx`
- Reuse: `frontend/src/components/layout/ProductLockup.test.tsx`

## Task 1: Tighten The Asset Contract Around The Real SVG Anchors

**Files:**
- Modify: `frontend/src/brand/product-assets.test.ts`
- Read: `argus-icon-from-upload.svg`
- Read: `docs/brand/assets/source/vezor-icon-v2.svg`
- Read: `docs/brand/assets/source/vezor-omnisight-logo-v2.svg`

- [ ] **Step 1: Rewrite the asset regression test so it fails on the old simplified symbol**

Update `frontend/src/brand/product-assets.test.ts` to keep the existing runtime asset-path assertions, but make the SVG contract explicit and anchored to the approved Vezor naming and structure:

```ts
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

const brandAssetsDir = join(
  dirname(fileURLToPath(import.meta.url)),
  "../../public/brand",
);

async function readBrandAsset(name: string): Promise<string> {
  return readFile(join(brandAssetsDir, name), "utf8");
}

const symbolMarkers = [
  'role="img"',
  'aria-label="Vezor symbol"',
  "<title>Vezor symbol</title>",
  'id="vezor-symbol-mark"',
  'id="symbol-ring"',
  'id="symbol-eye"',
  'id="symbol-core"',
] as const;

const lockupMarkers = [
  'role="img"',
  'aria-label="Vezor product lockup"',
  "<title>Vezor product lockup</title>",
  'id="vezor-symbol-mark"',
  'id="symbol-ring"',
  'id="symbol-eye"',
  'id="symbol-core"',
  ">Vezor<",
  ">THE OMNISIGHT<",
  ">PLATFORM<",
] as const;

describe("product brand SVG assets", () => {
  test("runtime symbol assets have the rebuilt Vezor symbol contract", async () => {
    const productSymbol = await readBrandAsset("product-symbol-ui.svg");
    const compatibilitySymbol = await readBrandAsset("argus-symbol-ui.svg");

    for (const svg of [productSymbol, compatibilitySymbol]) {
      for (const marker of symbolMarkers) {
        expect(svg).toContain(marker);
      }
      expect(svg).not.toContain(">Argus<");
    }
  });

  test("runtime lockup assets have the rebuilt Vezor product lockup contract", async () => {
    const productLockup = await readBrandAsset("product-lockup-ui.svg");
    const compatibilityLockup = await readBrandAsset("argus-lockup-ui.svg");

    for (const svg of [productLockup, compatibilityLockup]) {
      for (const marker of lockupMarkers) {
        expect(svg).toContain(marker);
      }
      expect(svg).not.toContain(">Argus<");
    }
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails against the current simplified assets**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts
```

Expected:

- FAIL because the current runtime SVGs still reflect the older simplified symbol and lockup treatment, not the refined Vezor rebuild.

- [ ] **Step 3: Commit the failing-test checkpoint**

```bash
git add frontend/src/brand/product-assets.test.ts
git commit -m "test: lock down the Vezor asset contract"
```

## Task 2: Rebuild The Runtime Symbol From The Uploaded Base And V2 Anchor

**Files:**
- Modify: `docs/brand/assets/source/vezor-symbol-product-ui.svg`
- Modify: `frontend/public/brand/product-symbol-ui.svg`
- Modify: `frontend/public/brand/argus-symbol-ui.svg`
- Test: `frontend/src/brand/product-assets.test.ts`
- Read: `argus-icon-from-upload.svg`
- Read: `docs/brand/assets/source/vezor-icon-v2.svg`

- [ ] **Step 1: Rebuild the product-symbol source SVG from the closer v2 anchor**

Use the existing v2 source SVG as the implementation anchor, then keep the uploaded base symbol feel intact while cleaning up the product SVG for small-size use.

Run:

```bash
cp docs/brand/assets/source/vezor-icon-v2.svg docs/brand/assets/source/vezor-symbol-product-ui.svg
```

Then normalize the copied source so the final source asset header stays:

```xml
<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Vezor symbol">
  <title>Vezor symbol</title>
  <desc>Refined eye-and-radar symbol rebuilt from the uploaded base and tuned for product use.</desc>
</svg>
```

Keep the geometry closer to the uploaded base than to the old simplified runtime symbol, keep the transparent-background runtime treatment, add stable `id="vezor-symbol-mark"`, `id="symbol-ring"`, `id="symbol-eye"`, and `id="symbol-core"` hooks, and ensure the refined symbol no longer uses the old dashed-ring treatment.

- [ ] **Step 2: Copy the normalized source asset into both runtime symbol files**

Run:

```bash
cp docs/brand/assets/source/vezor-symbol-product-ui.svg frontend/public/brand/product-symbol-ui.svg
cp docs/brand/assets/source/vezor-symbol-product-ui.svg frontend/public/brand/argus-symbol-ui.svg
```

- [ ] **Step 3: Run the symbol-only regression slice**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts -t "runtime symbol assets have the rebuilt Vezor symbol contract"
```

Expected:

- PASS for the symbol asset contract.
- The lockup contract may still fail until the full lockup files are updated.

- [ ] **Step 4: Commit the symbol refresh checkpoint**

```bash
git add docs/brand/assets/source/vezor-symbol-product-ui.svg frontend/public/brand/product-symbol-ui.svg frontend/public/brand/argus-symbol-ui.svg frontend/src/brand/product-assets.test.ts
git commit -m "feat: refresh the Vezor runtime symbol"
```

## Task 3: Rebuild The Runtime Lockup Around The Same Vezor Symbol Language

**Files:**
- Modify: `docs/brand/assets/source/vezor-lockup-product-ui.svg`
- Modify: `frontend/public/brand/product-lockup-ui.svg`
- Modify: `frontend/public/brand/argus-lockup-ui.svg`
- Test: `frontend/src/brand/product-assets.test.ts`
- Test: `frontend/src/components/layout/ProductLockup.test.tsx`
- Read: `docs/brand/assets/source/vezor-omnisight-logo-v2.svg`

- [ ] **Step 1: Rebuild the product-lockup source SVG from the v2 lockup anchor**

Use the closer repo-owned v2 lockup source as the implementation anchor, and keep the current Vezor wordmark and descriptor treatment intact.

Run:

```bash
cp docs/brand/assets/source/vezor-omnisight-logo-v2.svg docs/brand/assets/source/vezor-lockup-product-ui.svg
```

If the copied source needs metadata normalization, keep the top-level labels aligned to Vezor:

```xml
<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Vezor product lockup">
  <title>Vezor product lockup</title>
  <desc>Vezor lockup pairing the refined symbol with the existing wordmark and descriptor.</desc>
</svg>
```

Do not change the React component or runtime asset paths; only the SVG artwork should move. Keep the embedded symbol language aligned with `docs/brand/assets/source/vezor-symbol-product-ui.svg`.

- [ ] **Step 2: Copy the normalized source lockup into both runtime lockup files**

Run:

```bash
cp docs/brand/assets/source/vezor-lockup-product-ui.svg frontend/public/brand/product-lockup-ui.svg
cp docs/brand/assets/source/vezor-lockup-product-ui.svg frontend/public/brand/argus-lockup-ui.svg
```

- [ ] **Step 3: Run the asset tests and the existing lockup component test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/brand/product-assets.test.ts src/components/layout/ProductLockup.test.tsx
```

Expected:

- PASS with the runtime assets now matching the new Vezor contract.

- [ ] **Step 4: Run the production build and diff hygiene check**

Run:

```bash
corepack pnpm --dir frontend build
git diff --check
```

Expected:

- Frontend build passes.
- `git diff --check` prints no output.

- [ ] **Step 5: Commit the final lockup refresh checkpoint**

```bash
git add docs/brand/assets/source/vezor-lockup-product-ui.svg frontend/public/brand/product-lockup-ui.svg frontend/public/brand/argus-lockup-ui.svg frontend/src/brand/product-assets.test.ts
git commit -m "feat: refresh the Vezor runtime lockup"
```

## Self-Review

### Spec Coverage

- Uploaded base symbol remains the geometry reference: covered by the reference-anchors section and Task 2.
- Closer repo-owned v2 assets are the implementation anchor: covered by the architecture and Tasks 2 and 3.
- Product-specific source SVGs stay aligned with runtime exports: covered by Tasks 2 and 3.
- Runtime asset paths stay unchanged: covered by the reuse list and the task commands that only replace SVG files.
- Product name remains Vezor and descriptor remains The OmniSight Platform: covered by Task 1 assertions and Task 3 metadata.
- Existing `ProductLockup` behavior stays intact: covered by the unchanged component reuse and the Task 3 test run.

### Placeholder Scan

- No `TODO`, `TBD`, or `implement later` placeholders remain.
- Every file-changing step names the exact files and exact commands.

### Type And Interface Consistency

- The runtime SVG names stay consistent across tests and tasks: `product-symbol-ui.svg`, `argus-symbol-ui.svg`, `product-lockup-ui.svg`, `argus-lockup-ui.svg`.
- The asset test and component test both continue to assert the same `Vezor` runtime contract.
- The React brand wiring in `frontend/src/brand/product.ts` is intentionally untouched.
