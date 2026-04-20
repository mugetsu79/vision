import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

const brandAssetsDir = join(
  dirname(fileURLToPath(import.meta.url)),
  "../../public/brand",
);

const rebuiltSymbolIds = [
  "vezor-symbol-mark",
  "symbol-ring",
  "symbol-eye",
  "symbol-core",
];

async function readBrandAsset(name: string): Promise<string> {
  return readFile(join(brandAssetsDir, name), "utf8");
}

describe("product brand SVG assets", () => {
  test("product and compatibility symbol assets expose the rebuilt Vezor symbol structure", async () => {
    const productSymbol = await readBrandAsset("product-symbol-ui.svg");
    const compatibilitySymbol = await readBrandAsset("argus-symbol-ui.svg");

    for (const svg of [productSymbol, compatibilitySymbol]) {
      expect(svg).toContain('role="img"');
      expect(svg).toContain('aria-label="Vezor symbol"');
      expect(svg).toContain("<title>Vezor symbol</title>");
      expect(svg).toContain("<desc>");

      for (const id of rebuiltSymbolIds) {
        expect(svg).toContain(`id="${id}"`);
      }

      expect(svg).not.toContain(">Argus<");
    }
  });

  test("product and compatibility lockup assets embed the rebuilt symbol and Vezor lockup metadata", async () => {
    const productLockup = await readBrandAsset("product-lockup-ui.svg");
    const compatibilityLockup = await readBrandAsset("argus-lockup-ui.svg");

    for (const svg of [productLockup, compatibilityLockup]) {
      expect(svg).toContain('role="img"');
      expect(svg).toContain('aria-label="Vezor product lockup"');
      expect(svg).toContain("<title>Vezor product lockup</title>");
      expect(svg).toContain("<desc>");

      for (const id of rebuiltSymbolIds) {
        expect(svg).toContain(`id="${id}"`);
      }

      expect(svg).toContain(">Vezor<");
      expect(svg).toContain(">THE OMNISIGHT<");
      expect(svg).toContain(">PLATFORM<");
      expect(svg).not.toContain(">Argus<");
    }
  });
});
