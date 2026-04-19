import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-[color:var(--argus-border)] bg-[color:var(--argus-surface-soft)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--argus-text-muted)]",
        className,
      )}
      {...props}
    />
  );
}
