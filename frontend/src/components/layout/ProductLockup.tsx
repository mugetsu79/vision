import type { HTMLAttributes } from "react";

import { getProductLockupAlt, productBrand } from "@/brand/product";
import { cn } from "@/lib/utils";

interface ProductLockupProps extends HTMLAttributes<HTMLDivElement> {
  compact?: boolean;
  symbolOnly?: boolean;
}

export function ProductLockup({
  className,
  compact = false,
  symbolOnly = false,
  ...props
}: ProductLockupProps) {
  const alt = getProductLockupAlt(symbolOnly);
  const baseClasses = symbolOnly
    ? "h-11 w-11"
    : compact
      ? "h-10"
      : "h-12";

  if (symbolOnly) {
    return (
      <img
        alt={alt}
        className={cn("block select-none", baseClasses, className)}
        decoding="async"
        draggable={false}
        src={productBrand.runtimeAssets.symbol}
      />
    );
  }

  return (
    <div
      aria-label={alt}
      role="group"
      className={cn("inline-flex select-none items-center gap-3", baseClasses, className)}
      {...props}
    >
      <img
        alt={`${productBrand.name} symbol`}
        className="aspect-square h-full w-auto shrink-0"
        decoding="async"
        draggable={false}
        src={productBrand.runtimeAssets.symbol}
      />
      <span className="flex items-center gap-2">
        <span className="text-[2.15rem] font-extrabold leading-none tracking-[-0.04em] text-[#f4f8ff] drop-shadow-[0_10px_22px_rgba(0,0,0,0.45)]">
          {productBrand.name}
        </span>
        <span className="mt-1 text-[0.44rem] font-bold uppercase leading-[1.5] tracking-[0.34em] text-[#9eabc1]">
          THE OMNISIGHT
          <br />
          PLATFORM
        </span>
      </span>
    </div>
  );
}
