import type { ImgHTMLAttributes } from "react";

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
  const src = symbolOnly ? "/brand/argus-symbol-ui.svg" : "/brand/argus-lockup-ui.svg";
  const alt = symbolOnly ? "Argus symbol" : "Argus product lockup";
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
