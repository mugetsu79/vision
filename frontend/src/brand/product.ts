export const productBrand = {
  name: "Vezor",
  descriptor: "The OmniSight Platform",
  runtimeAssets: {
    lockup: "/brand/product-lockup-ui.svg",
    symbol: "/brand/product-symbol-ui.svg",
  },
} as const;

export function getProductLockupAlt(symbolOnly: boolean): string {
  return symbolOnly
    ? `${productBrand.name} symbol`
    : `${productBrand.name} product lockup`;
}

export function getProductTitle(): string {
  return `${productBrand.name} | ${productBrand.descriptor}`;
}
