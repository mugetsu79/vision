import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

const rebuiltSymbolIds = [
  "vezor-symbol-mark",
  "symbol-ring",
  "symbol-shards",
  "symbol-eye",
  "symbol-core",
];

const legacySimplifiedMarkers = [
  'id="symbol-blades"',
  'stroke-dasharray="94 24',
] as const;

async function readRepoFile(pathFromRoot: string): Promise<string> {
  return readFile(resolve(repoRoot, pathFromRoot), "utf8");
}

describe("product brand SVG assets", () => {
  test("source and runtime symbol assets expose the rebuilt Vezor symbol structure", async () => {
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
      expect(svg).toContain('aria-label="Vezor symbol"');
      expect(svg).toContain("<title>Vezor symbol</title>");
      expect(svg).toContain("<desc>");

      for (const id of rebuiltSymbolIds) {
        expect(svg).toContain(`id="${id}"`);
      }

      for (const marker of legacySimplifiedMarkers) {
        expect(svg).not.toContain(marker);
      }

      expect(svg).not.toContain(">Argus<");
    }

    expect(productSymbol).toBe(sourceSymbol);
    expect(compatibilitySymbol).toBe(sourceSymbol);
  });

  test("source and runtime lockup assets embed the rebuilt symbol and Vezor lockup metadata", async () => {
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

      for (const id of rebuiltSymbolIds) {
        expect(svg).toContain(`id="${id}"`);
      }

      for (const marker of legacySimplifiedMarkers) {
        expect(svg).not.toContain(marker);
      }

      expect(svg).toContain(">Vezor<");
      expect(svg).toContain(">THE OMNISIGHT<");
      expect(svg).toContain(">PLATFORM<");
      expect(svg).not.toContain(">Argus<");
    }

    expect(productLockup).toBe(sourceLockup);
    expect(compatibilityLockup).toBe(sourceLockup);
  });
});
