import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

const uploadedIconMarkers = [
  'aria-label="Argus"',
  "<title>Argus \u2014 Icon</title>",
  'id="brandGrad"',
  'filter="url(#innerShadow)"',
] as const;

const boxedBackgroundMarkers = [
  'id="bg"',
  "Obsidian background",
  'fill="url(#bg)"',
  '<rect x="200" y="25" width="200" height="200"',
] as const;

const previousGeneratedSymbolMarkers = [
  'id="vezor-symbol-mark"',
  'id="symbol-shards"',
  'id="symbol-eye"',
] as const;

async function readRepoFile(pathFromRoot: string): Promise<string> {
  return readFile(resolve(repoRoot, pathFromRoot), "utf8");
}

describe("product brand SVG assets", () => {
  test("source and runtime symbol assets use the uploaded Argus icon", async () => {
    const uploadedIcon = await readRepoFile("argus-icon-from-upload.svg");
    const sourceIcon = await readRepoFile(
      "docs/brand/assets/source/argus-icon-from-upload.svg",
    );
    const sourceSymbol = await readRepoFile(
      "docs/brand/assets/source/vezor-symbol-product-ui.svg",
    );
    const productSymbol = await readRepoFile(
      "frontend/public/brand/product-symbol-ui.svg",
    );
    const compatibilitySymbol = await readRepoFile(
      "frontend/public/brand/argus-symbol-ui.svg",
    );

    for (const svg of [
      uploadedIcon,
      sourceIcon,
      sourceSymbol,
      productSymbol,
      compatibilitySymbol,
    ]) {
      expect(svg).toContain('role="img"');
      expect(svg).toContain("<desc>");

      for (const marker of uploadedIconMarkers) {
        expect(svg).toContain(marker);
      }

      for (const marker of boxedBackgroundMarkers) {
        expect(svg).not.toContain(marker);
      }

      for (const marker of previousGeneratedSymbolMarkers) {
        expect(svg).not.toContain(marker);
      }
    }

    expect(sourceIcon).toBe(uploadedIcon);
    expect(sourceSymbol).toBe(uploadedIcon);
    expect(productSymbol).toBe(sourceSymbol);
    expect(compatibilitySymbol).toBe(sourceSymbol);
  });

  test("source and runtime lockup assets embed the uploaded icon and Vezor lockup metadata", async () => {
    const sourceLockup = await readRepoFile(
      "docs/brand/assets/source/vezor-lockup-product-ui.svg",
    );
    const productLockup = await readRepoFile(
      "frontend/public/brand/product-lockup-ui.svg",
    );
    const compatibilityLockup = await readRepoFile(
      "frontend/public/brand/argus-lockup-ui.svg",
    );

    for (const svg of [sourceLockup, productLockup, compatibilityLockup]) {
      expect(svg).toContain('role="img"');
      expect(svg).toContain('aria-label="Vezor product lockup"');
      expect(svg).toContain("<title>Vezor product lockup</title>");
      expect(svg).toContain("<desc>");
      expect(svg).toContain("data:image/svg+xml;base64,");

      for (const marker of uploadedIconMarkers) {
        expect(svg).toContain(`data-upload-marker: ${marker}`);
      }

      for (const marker of boxedBackgroundMarkers) {
        expect(svg).not.toContain(marker);
      }

      for (const marker of previousGeneratedSymbolMarkers) {
        expect(svg).not.toContain(marker);
      }

      expect(svg).toContain(">Vezor<");
      expect(svg).toContain(">THE OMNISIGHT<");
      expect(svg).toContain(">PLATFORM<");
    }

    expect(productLockup).toBe(sourceLockup);
    expect(compatibilityLockup).toBe(sourceLockup);
  });
});

describe("Vezor visual system tokens", () => {
  test("defines OmniSight lens color tokens and field motion classes", async () => {
    const css = await readRepoFile("frontend/src/index.css");

    expect(css).toContain("--vezor-lens-cerulean");
    expect(css).toContain("--vezor-lens-violet");
    expect(css).toContain("--vezor-surface-depth");
    expect(css).toContain(".omnisight-field");
    expect(css).toContain(".omnisight-field--overview .omnisight-field__lens");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
