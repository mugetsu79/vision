import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

import { productBrand } from "@/brand/product";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

async function readRepoFile(pathFromRoot: string): Promise<string> {
  return readFile(resolve(repoRoot, pathFromRoot), "utf8");
}

async function readRepoBuffer(pathFromRoot: string): Promise<Buffer> {
  return readFile(resolve(repoRoot, pathFromRoot));
}

function expectPng(buffer: Buffer) {
  expect(buffer.subarray(1, 4).toString("ascii")).toBe("PNG");
}

function expectMp4(buffer: Buffer) {
  expect(buffer.subarray(4, 8).toString("ascii")).toBe("ftyp");
}

describe("product brand logo assets", () => {
  test("uses the official 2D, 3D, and no-background animated logo assets from docs/brand at runtime", async () => {
    expect(productBrand.runtimeAssets.logo2d).toBe("/brand/2d_logo_no_ring.png");
    expect(productBrand.runtimeAssets.logo3d).toBe("/brand/3d_logo_no_bg.png");
    expect(productBrand.runtimeAssets.logoAnimated).toBe("/brand/logo-no-bg.mp4");

    const source2d = await readRepoBuffer("docs/brand/2d_logo_no_ring.png");
    const runtime2d = await readRepoBuffer("frontend/public/brand/2d_logo_no_ring.png");
    const source3d = await readRepoBuffer("docs/brand/3d_logo_no_bg.png");
    const runtime3d = await readRepoBuffer("frontend/public/brand/3d_logo_no_bg.png");
    const sourceAnimated = await readRepoBuffer("docs/brand/logo-no-bg.mp4");
    const runtimeAnimated = await readRepoBuffer("frontend/public/brand/logo-no-bg.mp4");

    expectPng(source2d);
    expectPng(source3d);
    expectMp4(sourceAnimated);
    expect(runtime2d.equals(source2d)).toBe(true);
    expect(runtime3d.equals(source3d)).toBe(true);
    expect(runtimeAnimated.equals(sourceAnimated)).toBe(true);
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
    expect(css).not.toContain("@keyframes signin-stage-mark");
    expect(css).not.toContain("animation: signin-stage-mark");
    expect(css).toContain(
      ".signin-lens-stage .omnisight-field--stage .omnisight-field__mark-stack",
    );
    expect(css).toContain(
      ".signin-lens-stage .omnisight-field--stage .omnisight-field__ring",
    );
    expect(css).toContain(
      ".signin-lens-stage .omnisight-field--stage .omnisight-field__orbital-map",
    );
    expect(css).toContain("animation: signin-logo-depth");
    expect(css).toContain("@keyframes signin-logo-depth");
    expect(css).not.toContain("signin-orbital-scan");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
