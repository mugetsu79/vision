import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

const standaloneSymbolMarkers = [
  'id="vezor-symbol-core"',
  'id="symbol-shards"',
  'id="symbol-eye"',
  'viewBox="48 48 416 416"',
] as const;

const surroundingSymbolMarkers = [
  "Soft aura behind the medallion",
  "Gradient disc",
  '<circle cx="300" cy="125" r="95"',
  '<circle cx="300" cy="125" r="82"',
  "Rounded square background",
  "Medallion ring",
  'id="bg"',
] as const;

async function readRepoFile(pathFromRoot: string): Promise<string> {
  return readFile(resolve(repoRoot, pathFromRoot), "utf8");
}

describe("product brand SVG assets", () => {
  test("source and runtime symbol assets use the standalone Vezor mark without a circular medallion", async () => {
    const sourceSymbol = await readRepoFile(
      "docs/brand/assets/source/vezor-symbol-product-ui.svg",
    );
    const productSymbol = await readRepoFile(
      "frontend/public/brand/product-symbol-ui.svg",
    );
    const compatibilitySymbol = await readRepoFile(
      "frontend/public/brand/argus-symbol-ui.svg",
    );

    for (const svg of [sourceSymbol, productSymbol, compatibilitySymbol]) {
      expect(svg).toContain('role="img"');
      expect(svg).toContain("<desc>");

      for (const marker of standaloneSymbolMarkers) {
        expect(svg).toContain(marker);
      }

      for (const marker of surroundingSymbolMarkers) {
        expect(svg).not.toContain(marker);
      }
    }

    expect(productSymbol).toBe(sourceSymbol);
    expect(compatibilitySymbol).toBe(sourceSymbol);
  });

});

describe("Vezor visual system tokens", () => {
  test("defines OmniSight logo field tokens and motion classes", async () => {
    const css = await readRepoFile("frontend/src/index.css");

    expect(css).toContain("--vezor-lens-cerulean");
    expect(css).toContain("--vezor-lens-violet");
    expect(css).toContain("--vezor-surface-depth");
    expect(css).toContain(".omnisight-field");
    expect(css).toContain(".omnisight-field__mark-stack");
    expect(css).not.toContain(".omnisight-field__lens");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
