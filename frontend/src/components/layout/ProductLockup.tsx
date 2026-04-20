import type { ImgHTMLAttributes } from "react";

import { getProductLockupAlt, productBrand } from "@/brand/product";
import { cn } from "@/lib/utils";

interface ProductLockupProps
  extends Omit<ImgHTMLAttributes<HTMLImageElement>, "alt" | "src"> {
  compact?: boolean;
  symbolOnly?: boolean;
}

export function ProductLockup({
  className,
  compact = false,
  symbolOnly = false,
  ...props
}: ProductLockupProps) {
  const src = symbolOnly ? productBrand.runtimeAssets.symbol : productBrand.runtimeAssets.lockup;
  const alt = getProductLockupAlt(symbolOnly);
  const baseClasses = symbolOnly
    ? "h-11 w-11 rounded-[1rem]"
    : compact
      ? "h-10 w-auto"
      : "h-12 w-auto";

  return (
    <img
      alt={alt}
      className={cn("block select-none", baseClasses, className)}
      decoding="async"
      draggable={false}
      src={src}
      {...props}
    />
  );
}
