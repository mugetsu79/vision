export const productBrand = {
  name: "Vezor",
  descriptor: "The OmniSight Platform",
  runtimeAssets: {
    logo2d: "/brand/2d_logo_no_ring.png",
    logo3d: "/brand/3d_logo_no_bg.png",
  },
} as const;

export function getProductLockupAlt(symbolOnly: boolean): string {
  return symbolOnly
    ? `${productBrand.name} 2D logo`
    : `${productBrand.name} product lockup`;
}

export function getProductTitle(): string {
  return `${productBrand.name} | ${productBrand.descriptor}`;
}
