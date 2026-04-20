import { readFile, readdir } from "node:fs/promises";
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

describe("brand SVG assets", () => {
  test("keep Vezor metadata and rebuilt symbol ids", async () => {
    const svgFiles = (await readdir(brandAssetsDir)).filter((file) =>
      file.endsWith(".svg"),
    );

    expect(svgFiles.length).toBeGreaterThan(0);

    for (const file of svgFiles) {
      const svg = await readFile(join(brandAssetsDir, file), "utf8");

      expect(svg).toContain('role="img"');
      expect(svg).toMatch(/aria-label="Vezor (symbol|product lockup)"/);
      expect(svg).toContain("<title>Vezor");
      expect(svg).toContain("<desc>");

      for (const id of rebuiltSymbolIds) {
        expect(svg).toContain(`id="${id}"`);
      }
    }
  });
});
