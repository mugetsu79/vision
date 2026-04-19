import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-[#263754] bg-[#0b1421] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#a7bbd7]",
        className,
      )}
      {...props}
    />
  );
}
